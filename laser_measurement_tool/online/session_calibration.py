"""Runtime/session metadata helpers for online ground calibration."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np

from calibration.session_ground import (
    SessionGroundBoardConfig,
    SessionGroundExtrinsic,
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


def build_session_ground_payload(
    result: SessionGroundExtrinsic,
    board_config: SessionGroundBoardConfig,
    *,
    frame_number: int | None,
    frame_offset: tuple[int, int] | None,
    reference_R: np.ndarray,
    reference_t: np.ndarray,
    runtime_source: str,
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
        "schema_version": 1,
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
    }


def save_session_ground_payload(path: str | Path, payload: dict[str, Any]) -> Path:
    """Atomically save the latest session record, replacing that record only."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
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
    "build_session_ground_payload",
    "compare_ground_extrinsics",
    "merge_session_ground_sanity",
    "save_session_ground_payload",
]
