"""Runtime/session metadata helpers for online ground calibration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np

from calibration.session_ground import (
    SessionGroundBoardConfig,
    SessionGroundExtrinsic,
    estimate_session_ground_extrinsic_from_corners,
)


def compare_ground_extrinsics(
    reference_R: np.ndarray,
    reference_t: np.ndarray,
    session_R: np.ndarray,
    session_t: np.ndarray,
) -> tuple[float, float]:
    """Return ``(translation_delta_mm, rotation_delta_deg)``.

    Both rotations are camera-to-ground rotations.  The relative rotation is
    therefore ``session_R @ reference_R.T``.
    """
    reference_rotation = _rotation_matrix(reference_R, "reference_R")
    session_rotation = _rotation_matrix(session_R, "session_R")
    reference_translation = _translation_vector(reference_t, "reference_t")
    session_translation = _translation_vector(session_t, "session_t")
    translation_delta = float(
        np.linalg.norm(session_translation - reference_translation)
    )
    relative = session_rotation @ reference_rotation.T
    cosine = float(np.clip((np.trace(relative) - 1.0) * 0.5, -1.0, 1.0))
    rotation_delta = float(np.degrees(np.arccos(cosine)))
    return translation_delta, rotation_delta


@dataclass(frozen=True, slots=True)
class SessionGroundRepeatability:
    """Repeatability summary for the accepted same-pose PnP frames."""

    required_frames: int
    accepted_frames: int
    translation_deltas_mm: tuple[float, ...]
    rotation_deltas_deg: tuple[float, ...]
    translation_mean_mm: float
    translation_std_mm: float
    translation_max_mm: float
    rotation_mean_deg: float
    rotation_std_deg: float
    rotation_max_deg: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "required_frames": self.required_frames,
            "accepted_frames": self.accepted_frames,
            "translation_deltas_mm": list(self.translation_deltas_mm),
            "rotation_deltas_deg": list(self.rotation_deltas_deg),
            "translation_mean_mm": self.translation_mean_mm,
            "translation_std_mm": self.translation_std_mm,
            "translation_max_mm": self.translation_max_mm,
            "rotation_mean_deg": self.rotation_mean_deg,
            "rotation_std_deg": self.rotation_std_deg,
            "rotation_max_deg": self.rotation_max_deg,
        }


def checkerboard_physical_polygon(
    corners: np.ndarray,
    *,
    pattern_cols: int,
    pattern_rows: int,
) -> np.ndarray:
    """Return the complete physical-board boundary from inner corners.

    The returned polygon extends one corner spacing beyond the detected inner
    corner grid on all four sides.  It is a display/quality-mask helper only;
    Laser Ground Check continues to use its PnP physical-board mask.
    """
    array = np.asarray(corners, dtype=np.float64).reshape(-1, 2)
    expected = int(pattern_cols) * int(pattern_rows)
    if array.shape != (expected, 2) or not np.isfinite(array).all():
        raise ValueError("corners 必须是完整且有限的棋盘角点")
    grid = array.reshape(int(pattern_rows), int(pattern_cols), 2)
    dx_top = grid[0, 1] - grid[0, 0]
    dx_bottom = grid[-1, -1] - grid[-1, -2]
    dy_left = grid[1, 0] - grid[0, 0]
    dy_right = grid[-1, -1] - grid[-2, -1]
    dx = (dx_top + dx_bottom) * 0.5
    dy = (dy_left + dy_right) * 0.5
    return np.ascontiguousarray(
        np.asarray(
            [
                grid[0, 0] - dx - dy,
                grid[0, -1] + dx - dy,
                grid[-1, -1] + dx + dy,
                grid[-1, 0] - dx + dy,
            ],
            dtype=np.float64,
        )
    )


def assess_checkerboard_image_quality(
    image: np.ndarray,
    corners: np.ndarray,
    *,
    pattern_cols: int,
    pattern_rows: int,
    saturation_ratio_warn: float,
    dynamic_range_p95_p5_warn: float,
    edge_margin_warn_px: float,
) -> dict[str, Any]:
    """Measure configurable warning-only image-quality indicators."""
    gray = np.asarray(image)
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    if gray.ndim != 2 or not gray.size:
        raise ValueError("image 必须是非空灰度图像")
    polygon = checkerboard_physical_polygon(
        corners,
        pattern_cols=pattern_cols,
        pattern_rows=pattern_rows,
    )
    height, width = gray.shape[:2]
    polygon_i = np.rint(polygon).astype(np.int32)
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(mask, polygon_i, 1)
    values = gray[mask.astype(bool)]
    if not len(values):
        raise ValueError("棋盘物理 mask 没有覆盖当前图像")
    maximum = float(np.iinfo(gray.dtype).max) if np.issubdtype(gray.dtype, np.integer) else float(np.max(values))
    saturation_level = maximum * 0.99
    saturation_ratio = float(np.mean(values.astype(np.float64) >= saturation_level))
    p95_p5 = float(np.percentile(values, 95.0) - np.percentile(values, 5.0))
    edge_margin = float(
        min(
            np.min(polygon[:, 0]),
            np.min(polygon[:, 1]),
            width - 1 - np.max(polygon[:, 0]),
            height - 1 - np.max(polygon[:, 1]),
        )
    )
    warnings: list[str] = []
    if saturation_ratio > float(saturation_ratio_warn):
        warnings.append("checkerboard_saturation_ratio_high")
    if p95_p5 < float(dynamic_range_p95_p5_warn):
        warnings.append("checkerboard_dynamic_range_low")
    if edge_margin < float(edge_margin_warn_px):
        warnings.append("checkerboard_too_close_to_image_edge")
    return {
        "saturation_ratio": saturation_ratio,
        "dynamic_range_p95_p5": p95_p5,
        "edge_margin_px": edge_margin,
        "warnings": warnings,
        "mask": "complete_physical_board_from_corners",
    }


def aggregate_session_ground_extrinsic(
    results: Sequence[SessionGroundExtrinsic],
    intrinsics: Any,
    board_config: SessionGroundBoardConfig,
    *,
    required_frames: int = 5,
) -> tuple[SessionGroundExtrinsic, SessionGroundRepeatability]:
    """Median-aggregate same-order corners, then reuse the shared PnP solve."""
    if len(results) != int(required_frames):
        raise ValueError(
            f"需要 {int(required_frames)} 个有效 PnP 帧，实际 {len(results)} 个"
        )
    expected_corners = board_config.pattern_cols * board_config.pattern_rows
    corner_arrays: list[np.ndarray] = []
    for index, result in enumerate(results, start=1):
        if result.status != "success" or result.detected_corners is None:
            raise ValueError(f"第 {index} 个 PnP 帧无效：{result.message}")
        corners = np.asarray(result.detected_corners, dtype=np.float32).reshape(-1, 2)
        if len(corners) != expected_corners:
            raise ValueError(
                f"第 {index} 个 PnP 帧角点数不是 {expected_corners}：{len(corners)}"
            )
        if not np.isfinite(corners).all():
            raise ValueError(f"第 {index} 个 PnP 帧包含非有限角点")
        corner_arrays.append(corners)

    stack = np.stack(corner_arrays, axis=0)
    # The detector/object-point protocol is row-major.  Reject a detector
    # reversal, while allowing ordinary sub-pixel frame-to-frame movement.
    reference = stack[0]
    rows = int(board_config.pattern_rows)
    cols = int(board_config.pattern_cols)
    reference_area = _corner_grid_area(reference, rows, cols)
    reference_dx, reference_dy = _corner_grid_directions(reference, rows, cols)
    for index, corners in enumerate(stack[1:], start=2):
        area = _corner_grid_area(corners, rows, cols)
        dx, dy = _corner_grid_directions(corners, rows, cols)
        if (
            reference_area * area < 0.0
            or float(reference_dx @ dx) <= 0.0
            or float(reference_dy @ dy) <= 0.0
        ):
            raise ValueError(f"第 {index} 个 PnP 帧角点顺序发生反向")

    aggregate_corners = np.ascontiguousarray(
        np.median(stack.astype(np.float64), axis=0).astype(np.float32)
    )
    final = estimate_session_ground_extrinsic_from_corners(
        aggregate_corners,
        intrinsics,
        board_config,
        detection_method="5_frame_median",
    )
    if final.status != "success" or final.R is None or final.t is None:
        raise ValueError(f"聚合角点 PnP 失败：{final.message}")

    translation_deltas: list[float] = []
    rotation_deltas: list[float] = []
    for result in results:
        if result.R is None or result.t is None:
            raise ValueError("有效 PnP 帧缺少 R/t")
        delta_t, delta_r = compare_ground_extrinsics(
            final.R,
            final.t,
            result.R,
            result.t,
        )
        translation_deltas.append(delta_t)
        rotation_deltas.append(delta_r)
    translation_array = np.asarray(translation_deltas, dtype=np.float64)
    rotation_array = np.asarray(rotation_deltas, dtype=np.float64)
    repeatability = SessionGroundRepeatability(
        required_frames=int(required_frames),
        accepted_frames=len(results),
        translation_deltas_mm=tuple(float(value) for value in translation_array),
        rotation_deltas_deg=tuple(float(value) for value in rotation_array),
        translation_mean_mm=float(np.mean(translation_array)),
        translation_std_mm=float(np.std(translation_array)),
        translation_max_mm=float(np.max(translation_array)),
        rotation_mean_deg=float(np.mean(rotation_array)),
        rotation_std_deg=float(np.std(rotation_array)),
        rotation_max_deg=float(np.max(rotation_array)),
    )
    return final, repeatability


def _corner_grid_area(corners: np.ndarray, rows: int, cols: int) -> float:
    grid = np.asarray(corners, dtype=np.float64).reshape(rows, cols, 2)
    top_left = grid[0, 0]
    top_right = grid[0, -1]
    bottom_left = grid[-1, 0]
    right = top_right - top_left
    down = bottom_left - top_left
    return float(right[0] * down[1] - right[1] * down[0])


def _corner_grid_directions(
    corners: np.ndarray, rows: int, cols: int
) -> tuple[np.ndarray, np.ndarray]:
    grid = np.asarray(corners, dtype=np.float64).reshape(rows, cols, 2)
    return grid[0, -1] - grid[0, 0], grid[-1, 0] - grid[0, 0]


def build_session_ground_payload(
    result: SessionGroundExtrinsic,
    board_config: SessionGroundBoardConfig,
    *,
    frame_number: int | None,
    frame_offset: tuple[int, int] | None,
    reference_R: np.ndarray,
    reference_t: np.ndarray,
    runtime_source: str,
    frame_host_monotonic_ns: int | None = None,
    session_generation: int | None = None,
    repeatability: SessionGroundRepeatability | Mapping[str, Any] | None = None,
    quality: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe record for the latest calibration attempt."""
    reference_rotation = _rotation_matrix(reference_R, "reference_R")
    reference_translation = _translation_vector(reference_t, "reference_t")
    valid = result.status == "success" and result.R is not None and result.t is not None
    if valid:
        assert result.R is not None and result.t is not None
        delta_translation, delta_rotation = compare_ground_extrinsics(
            reference_rotation,
            reference_translation,
            result.R,
            result.t,
        )
        session_extrinsic: dict[str, Any] | None = {
            "R_camera_to_ground": np.asarray(result.R, dtype=np.float64).tolist(),
            "t_camera_to_ground_mm": np.asarray(result.t, dtype=np.float64)
            .reshape(3)
            .tolist(),
            "T_ground_from_camera": np.asarray(
                result.T_ground_from_camera, dtype=np.float64
            ).tolist()
            if result.T_ground_from_camera is not None
            else None,
        }
        delta: dict[str, float] | None = {
            "translation_mm": delta_translation,
            "rotation_deg": delta_rotation,
        }
    else:
        session_extrinsic = None
        delta = None

    return {
        "schema_version": 2,
        "source": "session_ground_calibration",
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "VALID" if valid else "INVALID",
        "valid": valid,
        "message": result.message,
        "runtime": {
            "ground_extrinsic_source": runtime_source,
        },
        "board": {
            "pattern_cols": board_config.pattern_cols,
            "pattern_rows": board_config.pattern_rows,
            "square_size_mm": board_config.square_size_mm,
            "detector": board_config.detector,
        },
        "frame": {
            "camera_frame_number": frame_number,
            "host_monotonic_ns": frame_host_monotonic_ns,
            "session_generation": session_generation,
            "offset_x": frame_offset[0] if frame_offset is not None else None,
            "offset_y": frame_offset[1] if frame_offset is not None else None,
        },
        "detection": {
            "method": result.detection_method,
            "corner_count": (
                int(len(result.detected_corners))
                if result.detected_corners is not None
                else 0
            ),
            "corners": (
                np.asarray(result.detected_corners, dtype=np.float64).tolist()
                if result.detected_corners is not None
                else None
            ),
            "reprojection_rmse_px": result.reprojection_rmse_px,
        },
        "reference_extrinsic": {
            "R_camera_to_ground": reference_rotation.tolist(),
            "t_camera_to_ground_mm": reference_translation.tolist(),
        },
        "session_extrinsic": session_extrinsic,
        "delta": delta,
        "repeatability": (
            repeatability.as_dict()
            if isinstance(repeatability, SessionGroundRepeatability)
            else None if repeatability is None else dict(repeatability)
        ),
        "quality": None if quality is None else dict(quality),
    }


def save_session_ground_payload(path: str | Path, payload: dict[str, Any]) -> Path:
    """Atomically save the latest session record.

    PnP retries must not erase independently acquired Session ground-reference
    or laser-sanity records that are already in the same JSON file.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = dict(payload)
    if target.is_file():
        try:
            previous = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"无法读取 Session 标定 JSON: {target}: {error}") from error
        if isinstance(previous, dict):
            for key in (
                "session_ground_reference",
                "session_ground_reference_status",
                "laser_ground_sanity",
                "session_calibration_status",
            ):
                if key not in record and key in previous:
                    record[key] = previous[key]
            previous_runtime = previous.get("runtime")
            current_runtime = record.get("runtime")
            if isinstance(previous_runtime, dict) and isinstance(current_runtime, dict):
                record["runtime"] = {**previous_runtime, **current_runtime}
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


def merge_session_ground_sanity(
    path: str | Path,
    sanity_payload: dict[str, Any],
) -> Path:
    """Merge one laser-ground sanity record into the Session JSON.

    The PnP record remains intact; the check is stored under
    ``laser_ground_sanity`` and also exposes its status at the top level for
    scripts that do not need to understand the nested metrics.
    """
    target = Path(path)
    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"无法读取 Session 标定 JSON: {target}: {error}") from error
        if not isinstance(existing, dict):
            raise ValueError(f"Session 标定 JSON 根节点必须是对象: {target}")
    else:
        existing = {
            "schema_version": 1,
            "source": "session_ground_calibration",
        }

    existing["laser_ground_sanity"] = dict(sanity_payload)
    existing["session_calibration_status"] = sanity_payload.get("status", "INVALID")
    runtime = existing.get("runtime")
    if not isinstance(runtime, dict):
        runtime = {}
        existing["runtime"] = runtime
    if "ground_extrinsic_source" in sanity_payload:
        runtime["ground_extrinsic_source"] = sanity_payload[
            "ground_extrinsic_source"
        ]
    existing["saved_at_utc"] = datetime.now(timezone.utc).isoformat()
    return save_session_ground_payload(target, existing)


def merge_session_ground_reference(
    path: str | Path,
    reference_payload: Mapping[str, Any],
    *,
    ground_extrinsic_source: str,
) -> Path:
    """Merge the frozen linear ground reference into the Session JSON."""
    target = Path(path)
    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"无法读取 Session 标定 JSON: {target}: {error}") from error
        if not isinstance(existing, dict):
            raise ValueError(f"Session 标定 JSON 根节点必须是对象: {target}")
    else:
        existing = {
            "schema_version": 2,
            "source": "session_ground_calibration",
        }

    existing["session_ground_reference"] = dict(reference_payload)
    existing["session_ground_reference_status"] = reference_payload.get(
        "status", "INVALID"
    )
    runtime = existing.get("runtime")
    if not isinstance(runtime, dict):
        runtime = {}
        existing["runtime"] = runtime
    runtime["ground_extrinsic_source"] = ground_extrinsic_source
    runtime["ground_reference_source"] = reference_payload.get("source")
    existing["saved_at_utc"] = datetime.now(timezone.utc).isoformat()
    return save_session_ground_payload(target, existing)


def _rotation_matrix(value: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (3, 3) or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a finite 3x3 matrix")
    return np.ascontiguousarray(array)


def _translation_vector(value: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64).reshape(-1)
    if array.shape != (3,) or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a finite 3-vector")
    return np.ascontiguousarray(array)


__all__ = [
    "SessionGroundRepeatability",
    "aggregate_session_ground_extrinsic",
    "assess_checkerboard_image_quality",
    "build_session_ground_payload",
    "checkerboard_physical_polygon",
    "compare_ground_extrinsics",
    "merge_session_ground_sanity",
    "merge_session_ground_reference",
    "save_session_ground_payload",
]
