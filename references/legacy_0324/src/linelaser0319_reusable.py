from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

import cv2
import numpy as np


@dataclass(frozen=True)
class Legacy0319RobotInstall:
    height: float = 26.94
    pitch_deg: float = 36.0
    roll_deg: float = 0.0
    yaw_deg: float = 0.0
    offset_forward: float = 0.0


@dataclass(frozen=True)
class Legacy0319StegerParams:
    gray_threshold: float = 200.0
    eigen_threshold: float = 170.0


@dataclass(frozen=True)
class Legacy0319Config:
    """
    Default parameters copied from `0319linelaser3d02.py`.
    """

    camera_matrix: np.ndarray = field(
        default_factory=lambda: np.array(
            [[1135.5, 0.0, 944.5], [0.0, 1135.5, 625.0], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )
    )
    dist_coeffs: np.ndarray = field(
        default_factory=lambda: np.array([0.037, -0.043, 0.0, 0.0, 0.0], dtype=np.float64)
    )
    plane_abcd: np.ndarray = field(
        default_factory=lambda: np.array([-0.016, 0.946, 0.321, -108.0], dtype=np.float64)
    )
    robot_install: Legacy0319RobotInstall = field(default_factory=Legacy0319RobotInstall)
    steger: Legacy0319StegerParams = field(default_factory=Legacy0319StegerParams)


@dataclass(frozen=True)
class Legacy0319ExtractionDebug:
    points_uv: np.ndarray
    candidate_mask: np.ndarray
    nms_mask: np.ndarray


@dataclass
class Legacy0319Result:
    undistorted_bgr: np.ndarray
    updated_camera_matrix: np.ndarray
    preprocess_gray: np.ndarray
    points_uv: np.ndarray
    points_robot_xyz: np.ndarray
    candidate_mask: np.ndarray
    nms_mask: np.ndarray

    preprocess_ms: float
    extract_ms: float
    reconstruct_ms: float
    total_ms: float


def compute_cam_to_robot_transform(robot_install: Legacy0319RobotInstall) -> np.ndarray:
    """
    Build 4x4 camera-to-robot transform matrix.

    Robot frame:
    - X forward
    - Y left
    - Z up
    """

    pitch = np.deg2rad(robot_install.pitch_deg)
    roll = np.deg2rad(robot_install.roll_deg)
    yaw = np.deg2rad(robot_install.yaw_deg)

    s_p, c_p = np.sin(pitch), np.cos(pitch)
    s_r, c_r = np.sin(roll), np.cos(roll)
    s_y, c_y = np.sin(yaw), np.cos(yaw)

    r_pitch = np.array(
        [
            [0.0, -s_p, c_p],
            [-1.0, 0.0, 0.0],
            [0.0, -c_p, -s_p],
        ],
        dtype=np.float64,
    )

    r_roll = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, c_r, -s_r],
            [0.0, s_r, c_r],
        ],
        dtype=np.float64,
    )

    r_yaw = np.array(
        [
            [c_y, -s_y, 0.0],
            [s_y, c_y, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )

    # Keep legacy pitch/roll convention and append yaw around robot Z axis.
    r_final = r_yaw @ r_roll @ r_pitch
    t = np.array([[robot_install.offset_forward], [0.0], [robot_install.height]], dtype=np.float64)

    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = r_final
    transform[:3, 3:] = t
    return transform


def undistort_image_legacy0319(
    image_bgr: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    h, w = image_bgr.shape[:2]
    new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coeffs, (w, h), 1, (w, h))
    undistorted = cv2.undistort(image_bgr, camera_matrix, dist_coeffs, None, new_camera_matrix)
    return undistorted, new_camera_matrix


def preprocess_rg_difference_legacy0319(image_bgr: np.ndarray) -> np.ndarray:
    """
    Legacy 0319 preprocess:
    - use R-G to suppress background
    - normalize to 0..255
    """

    _b, g, r = cv2.split(image_bgr)
    diff = r.astype(np.int16) - g.astype(np.int16)
    diff[diff < 0] = 0
    gray = diff.astype(np.uint8)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    return gray


def steger_extract_subpixel_legacy0319(
    image_gray: np.ndarray,
    gray_threshold: float,
    eigen_threshold: float,
) -> np.ndarray:
    """
    Vectorized Steger extraction with local 5x5 NMS.

    Returns Nx2 array: [u, v].
    """

    result = steger_extract_subpixel_debug_legacy0319(
        image_gray=image_gray,
        gray_threshold=gray_threshold,
        eigen_threshold=eigen_threshold,
    )
    return result.points_uv


def steger_extract_subpixel_debug_legacy0319(
    image_gray: np.ndarray,
    gray_threshold: float,
    eigen_threshold: float,
) -> Legacy0319ExtractionDebug:
    gray_u8 = image_gray.astype(np.uint8)
    img = gray_u8.astype(np.float32)

    dx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=3)
    dxx = cv2.Sobel(dx, cv2.CV_32F, 1, 0, ksize=3)
    dyy = cv2.Sobel(dy, cv2.CV_32F, 0, 1, ksize=3)
    dxy = cv2.Sobel(dx, cv2.CV_32F, 0, 1, ksize=3)

    tmp = np.sqrt((dxx - dyy) ** 2 + 4.0 * dxy**2)
    lambda2 = (dxx + dyy - tmp) / 2.0

    nx = lambda2 - dyy
    ny = dxy
    norm = np.sqrt(nx**2 + ny**2)
    valid_norm = norm > 1e-6

    nx = np.where(valid_norm, nx / np.where(valid_norm, norm, 1.0), 0.0)
    ny = np.where(valid_norm, ny / np.where(valid_norm, norm, 1.0), 0.0)

    numerator = dx * nx + dy * ny
    denominator = dxx * nx**2 + 2.0 * dxy * nx * ny + dyy * ny**2
    denominator = np.where(np.abs(denominator) < 1e-6, 1e-6, denominator)
    t = -numerator / denominator

    mask_t = (np.abs(t * nx) <= 0.3) & (np.abs(t * ny) <= 0.3)
    mask_gray = gray_u8 > float(gray_threshold)
    mask_eig = lambda2 < -float(eigen_threshold)
    candidate_mask_bool = mask_t & mask_gray & mask_eig

    # Keep only local maxima in |lambda2| over 5x5 window.
    abs_lambda2 = np.abs(lambda2)
    local_max = cv2.dilate(abs_lambda2, np.ones((5, 5), dtype=np.uint8))
    nms_mask_bool = candidate_mask_bool & (abs_lambda2 >= local_max - 1e-6)

    ys, xs = np.where(nms_mask_bool)
    if len(xs) == 0:
        return Legacy0319ExtractionDebug(
            points_uv=np.zeros((0, 2), dtype=np.float32),
            candidate_mask=(candidate_mask_bool.astype(np.uint8) * 255),
            nms_mask=(nms_mask_bool.astype(np.uint8) * 255),
        )

    t_vals = t[ys, xs]
    nx_vals = nx[ys, xs]
    ny_vals = ny[ys, xs]

    u = xs.astype(np.float32) + t_vals.astype(np.float32) * nx_vals.astype(np.float32)
    v = ys.astype(np.float32) + t_vals.astype(np.float32) * ny_vals.astype(np.float32)
    return Legacy0319ExtractionDebug(
        points_uv=np.column_stack([u, v]).astype(np.float32),
        candidate_mask=(candidate_mask_bool.astype(np.uint8) * 255),
        nms_mask=(nms_mask_bool.astype(np.uint8) * 255),
    )


def pixels_to_robot_3d_legacy0319(
    points_uv: np.ndarray,
    camera_matrix: np.ndarray,
    plane_abcd: np.ndarray,
    cam_to_robot_transform: np.ndarray,
) -> np.ndarray:
    if points_uv is None or len(points_uv) == 0:
        return np.zeros((0, 3), dtype=np.float64)

    fx = float(camera_matrix[0, 0])
    fy = float(camera_matrix[1, 1])
    cx = float(camera_matrix[0, 2])
    cy = float(camera_matrix[1, 2])

    u = points_uv[:, 0].astype(np.float64)
    v = points_uv[:, 1].astype(np.float64)

    u_norm = (u - cx) / fx
    v_norm = (v - cy) / fy

    a, b, c, d = plane_abcd.astype(np.float64)
    denominator = a * u_norm + b * v_norm + c
    valid = np.abs(denominator) > 1e-6
    if not np.any(valid):
        return np.zeros((0, 3), dtype=np.float64)

    zc = -d / denominator[valid]
    xc = zc * u_norm[valid]
    yc = zc * v_norm[valid]

    points_cam = np.vstack([xc, yc, zc, np.ones_like(zc)])
    points_robot = cam_to_robot_transform @ points_cam

    xr = points_robot[0, :]
    yr = points_robot[1, :]
    zr = points_robot[2, :]
    return np.column_stack([xr, yr, zr]).astype(np.float64)


def run_legacy0319_pipeline(
    image_bgr: np.ndarray,
    config: Legacy0319Config = Legacy0319Config(),
) -> Legacy0319Result:
    t0 = perf_counter()

    undistorted, updated_camera = undistort_image_legacy0319(
        image_bgr=image_bgr,
        camera_matrix=config.camera_matrix,
        dist_coeffs=config.dist_coeffs,
    )

    preprocess_gray = preprocess_rg_difference_legacy0319(undistorted)
    t1 = perf_counter()

    extraction = steger_extract_subpixel_debug_legacy0319(
        image_gray=preprocess_gray,
        gray_threshold=config.steger.gray_threshold,
        eigen_threshold=config.steger.eigen_threshold,
    )
    points_uv = extraction.points_uv
    t2 = perf_counter()

    transform = compute_cam_to_robot_transform(config.robot_install)
    points_xyz = pixels_to_robot_3d_legacy0319(
        points_uv=points_uv,
        camera_matrix=updated_camera,
        plane_abcd=config.plane_abcd,
        cam_to_robot_transform=transform,
    )
    t3 = perf_counter()

    return Legacy0319Result(
        undistorted_bgr=undistorted,
        updated_camera_matrix=updated_camera,
        preprocess_gray=preprocess_gray,
        points_uv=points_uv,
        points_robot_xyz=points_xyz,
        candidate_mask=extraction.candidate_mask,
        nms_mask=extraction.nms_mask,
        preprocess_ms=(t1 - t0) * 1000.0,
        extract_ms=(t2 - t1) * 1000.0,
        reconstruct_ms=(t3 - t2) * 1000.0,
        total_ms=(t3 - t0) * 1000.0,
    )


def draw_overlay_points(image_bgr: np.ndarray, points_uv: np.ndarray, color=(0, 255, 255), radius: int = 1) -> np.ndarray:
    canvas = image_bgr.copy()
    if points_uv is None or len(points_uv) == 0:
        return canvas

    pts = np.round(points_uv).astype(np.int32)
    for x, y in pts:
        cv2.circle(canvas, (int(x), int(y)), int(radius), color, -1, lineType=cv2.LINE_AA)
    return canvas


def build_legacy0319_config_from_pipeline(
    pipeline_config,
    gray_threshold: float = 200.0,
    eigen_threshold: float = 170.0,
) -> Legacy0319Config:
    """
    Build Legacy0319Config from project config objects such as PipelineConfig / PipelineConfigYaw.
    """

    install = pipeline_config.robot_install
    return Legacy0319Config(
        camera_matrix=np.asarray(pipeline_config.camera_matrix, dtype=np.float64).copy(),
        dist_coeffs=np.asarray(pipeline_config.dist_coeffs, dtype=np.float64).copy(),
        plane_abcd=np.asarray(pipeline_config.plane_abcd, dtype=np.float64).copy(),
        robot_install=Legacy0319RobotInstall(
            height=float(install.height),
            pitch_deg=float(install.pitch_deg),
            roll_deg=float(install.roll_deg),
            yaw_deg=float(getattr(install, "yaw_deg", 0.0)),
            offset_forward=float(install.offset_forward),
        ),
        steger=Legacy0319StegerParams(
            gray_threshold=float(gray_threshold),
            eigen_threshold=float(eigen_threshold),
        ),
    )
