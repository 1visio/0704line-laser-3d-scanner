"""亚像素图像点到地面坐标系三维点的重建。

算法与 ``reconstruct_ground_pointcloud_v3.py`` 保持一致：
去畸变得到归一化射线 → 射线与激光平面求交（相机系）→ 用地面外参
``T_ground_from_camera`` 变换到地面系。所有长度单位为 mm。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


class ReconstructionInputError(ValueError):
    """重建输入（点、标定或参数）不满足约束。"""


@dataclass(frozen=True, slots=True)
class ReconstructionParams:
    """射线-平面求交的数值与工作距离约束。"""

    parallel_epsilon: float = 1.0e-9
    min_camera_depth_mm: float = 100.0
    max_camera_depth_mm: float = 1500.0

    def __post_init__(self) -> None:
        if self.parallel_epsilon <= 0.0:
            raise ReconstructionInputError("parallel_epsilon 必须为正数")
        if not 0.0 <= self.min_camera_depth_mm < self.max_camera_depth_mm:
            raise ReconstructionInputError(
                "工作距离必须满足 0 <= min_camera_depth_mm < max_camera_depth_mm"
            )


@dataclass(frozen=True, slots=True)
class ReconstructionResult:
    """有效点的像素坐标、相机系坐标与地面系坐标（逐行对齐）。"""

    pixels_uv: np.ndarray
    points_camera: np.ndarray
    points_ground: np.ndarray
    filtered: dict[str, int]

    @property
    def point_count(self) -> int:
        return len(self.pixels_uv)


def build_ground_transform(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """由 R、t 组装 4x4 的 ``T_ground_from_camera``。"""
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = np.asarray(R, dtype=np.float64)
    transform[:3, 3] = np.asarray(t, dtype=np.float64).reshape(3)
    return transform


def apply_ground_u_compensation(
    points_ground: np.ndarray,
    pixels_uv: np.ndarray,
    compensation: Mapping[str, Any] | None,
) -> np.ndarray:
    """按图像列坐标插值偏差，并执行 ``Zg_corrected = Zg_raw - bias(u)``。"""
    points = np.asarray(points_ground, dtype=np.float64)
    pixels = np.asarray(pixels_uv, dtype=np.float64)
    if compensation is None or len(points) == 0:
        return np.ascontiguousarray(points)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ReconstructionInputError("points_ground 必须是形状为 (N, 3) 的数组")
    if pixels.ndim != 2 or pixels.shape != (len(points), 2):
        raise ReconstructionInputError("pixels_uv 必须与 points_ground 逐行对齐")

    try:
        columns = np.asarray(compensation["column_u_px"], dtype=np.float64).reshape(-1)
        bias = np.asarray(compensation["bias_mm"], dtype=np.float64).reshape(-1)
    except (KeyError, TypeError, ValueError) as error:
        raise ReconstructionInputError(
            "ground_u_compensation 必须包含数值数组 column_u_px 和 bias_mm"
        ) from error
    if len(columns) == 0 or len(columns) != len(bias):
        raise ReconstructionInputError("ground_u_compensation 两列必须非空且等长")
    if not np.isfinite(columns).all() or not np.isfinite(bias).all():
        raise ReconstructionInputError("ground_u_compensation 包含 NaN 或无穷值")
    if np.any(np.diff(columns) <= 0.0):
        raise ReconstructionInputError("ground_u_compensation 的 column_u_px 必须严格递增")

    z_offset = _compensation_z_offset(compensation)
    corrected = points.copy()
    corrected[:, 2] -= np.interp(pixels[:, 0], columns, bias)
    corrected[:, 2] -= z_offset
    return np.ascontiguousarray(corrected)


def _compensation_z_offset(compensation: Mapping[str, Any]) -> float:
    if "z_offset_mm" not in compensation:
        return 0.0
    try:
        value = np.asarray(compensation["z_offset_mm"], dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ReconstructionInputError(
            "ground_u_compensation 的 z_offset_mm 必须是数值"
        ) from error
    if value.size != 1 or not np.isfinite(value).all():
        raise ReconstructionInputError(
            "ground_u_compensation 的 z_offset_mm 必须是单个有限数值"
        )
    return float(value.reshape(-1)[0])


def reconstruct_uv_to_ground(
    pixels_uv: np.ndarray,
    calibration: Mapping[str, Any],
    params: ReconstructionParams | None = None,
) -> ReconstructionResult:
    """把 ``(N, 2)`` 亚像素 ``(u, v)`` 重建为地面系三维点。

    ``calibration`` 使用 ``calibration.config_loader`` 返回的字典，
    至少包含 ``K``、``D``、``plane_abcd``、``R``、``t``。
    无效点（近平行、负深度、超出工作距离、非有限值）被剔除并计数。
    """
    if params is None:
        params = ReconstructionParams()

    points = np.asarray(pixels_uv, dtype=np.float64)
    empty_filtered = {
        "near_parallel": 0,
        "negative_depth": 0,
        "outside_working_distance": 0,
        "non_finite": 0,
    }
    if points.size == 0:
        empty = np.empty((0, 2), dtype=np.float64)
        return ReconstructionResult(
            pixels_uv=empty,
            points_camera=np.empty((0, 3), dtype=np.float64),
            points_ground=np.empty((0, 3), dtype=np.float64),
            filtered=empty_filtered,
        )
    if points.ndim != 2 or points.shape[1] != 2:
        raise ReconstructionInputError("pixels_uv 必须是形状为 (N, 2) 的数组")
    if not np.isfinite(points).all():
        raise ReconstructionInputError("pixels_uv 包含 NaN 或无穷值")

    K = np.asarray(calibration["K"], dtype=np.float64)
    D = np.asarray(calibration["D"], dtype=np.float64)
    plane = np.asarray(calibration["plane_abcd"], dtype=np.float64).reshape(4)
    normal_norm = float(np.linalg.norm(plane[:3]))
    if normal_norm <= np.finfo(np.float64).eps:
        raise ReconstructionInputError("激光平面法向量长度不能为零")
    plane = plane / normal_norm
    transform = build_ground_transform(calibration["R"], calibration["t"])

    normalized = cv2.undistortPoints(
        points.reshape(-1, 1, 2), K, D
    ).reshape(-1, 2)
    rays = np.column_stack(
        [normalized, np.ones(len(normalized), dtype=np.float64)]
    )
    denominator = rays @ plane[:3]
    stable = np.abs(denominator) > params.parallel_epsilon
    scale = np.full(len(rays), np.nan, dtype=np.float64)
    scale[stable] = -plane[3] / denominator[stable]
    points_camera = rays * scale[:, None]

    finite = np.isfinite(points_camera).all(axis=1) & np.isfinite(scale)
    positive = scale > 0.0
    within_distance = (
        (points_camera[:, 2] >= params.min_camera_depth_mm)
        & (points_camera[:, 2] <= params.max_camera_depth_mm)
    )
    valid = stable & finite & positive & within_distance
    filtered = {
        "near_parallel": int(np.count_nonzero(~stable)),
        "negative_depth": int(np.count_nonzero(stable & finite & ~positive)),
        "outside_working_distance": int(
            np.count_nonzero(stable & finite & positive & ~within_distance)
        ),
        "non_finite": int(np.count_nonzero(stable & ~finite)),
    }

    points_camera = points_camera[valid]
    valid_pixels = points[valid]
    homogeneous = np.column_stack(
        [points_camera, np.ones(len(points_camera), dtype=np.float64)]
    )
    # 方向严格为 ground <- camera；不得改用逆矩阵，也不对 Zg 取绝对值。
    points_ground = (transform @ homogeneous.T).T[:, :3]
    points_ground = apply_ground_u_compensation(
        points_ground,
        valid_pixels,
        calibration.get("ground_u_compensation"),
    )

    final_finite = np.isfinite(points_ground).all(axis=1)
    filtered["non_finite"] += int(np.count_nonzero(~final_finite))
    return ReconstructionResult(
        pixels_uv=np.ascontiguousarray(valid_pixels[final_finite]),
        points_camera=np.ascontiguousarray(points_camera[final_finite]),
        points_ground=np.ascontiguousarray(points_ground[final_finite]),
        filtered=filtered,
    )


def project_ground_points_to_pixels(
    points_ground: np.ndarray,
    calibration: Mapping[str, Any],
) -> np.ndarray:
    """把地面系三维点投影回图像像素坐标（用于叠加显示）。"""
    points = np.asarray(points_ground, dtype=np.float64).reshape(-1, 3)
    if points.size == 0:
        return np.empty((0, 2), dtype=np.float64)

    R = np.asarray(calibration["R"], dtype=np.float64)
    t = np.asarray(calibration["t"], dtype=np.float64).reshape(3)
    K = np.asarray(calibration["K"], dtype=np.float64)
    D = np.asarray(calibration["D"], dtype=np.float64)

    # ground -> camera：p_c = R^T (p_g - t)
    points_camera = (points - t) @ R
    pixels, _ = cv2.projectPoints(
        points_camera.reshape(-1, 1, 3),
        np.zeros(3, dtype=np.float64),
        np.zeros(3, dtype=np.float64),
        K,
        D,
    )
    return np.ascontiguousarray(pixels.reshape(-1, 2))
