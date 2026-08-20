"""Calibration-consistent processing of one acquired camera frame."""

from __future__ import annotations

import hashlib
import threading
import time

import cv2
import numpy as np

from app_config import AppConfig
from calibration.manifest import CalibrationPackage, load_calibration_package
from correction.stage_a_height_scale import resolve_stage_a_height_scale
from gui.image_view import _to_uint8_display
from laser.backends import create_extraction_params
from laser.laser_extractor import extract_laser_center
from reconstruction.reconstructor import reconstruct_uv_to_ground

from .models import CapturedFrame, FrameResult


class FramePipeline:
    """Run the selected extraction and reconstruction path for one frame."""

    def __init__(
        self,
        config: AppConfig,
        extraction_method: str | None = None,
        system: str | None = None,
    ) -> None:
        if config.calibration.manifest is None:
            raise ValueError("在线测量配置必须指定 calibration.manifest")
        self.config = config
        self.system = (system or config.system).strip().lower()
        self._stage_a_frame_metadata = resolve_stage_a_height_scale(
            None,
            system=self.system,
            correction=self.config.correction,
        )
        self.extraction_method = extraction_method or config.extraction_method
        self.extraction_options = dict(
            config.extraction_options_by_method.get(self.extraction_method, {})
        )
        self.package: CalibrationPackage = load_calibration_package(
            config.calibration.manifest
        )
        self._calibration_lock = threading.RLock()
        self._ground_extrinsic_source = "reference"
        self._reference_R = np.ascontiguousarray(
            np.asarray(self.package.calibration["R"], dtype=np.float64).copy()
        )
        self._reference_t = np.ascontiguousarray(
            np.asarray(self.package.calibration["t"], dtype=np.float64).copy()
        )
        self.extraction_params = create_extraction_params(
            self.extraction_method, self.extraction_options
        )
        self.algorithm_config_sha256 = _algorithm_hash(
            self.extraction_method, self.extraction_options
        )

    def run_frame(self, frame: CapturedFrame) -> FrameResult:
        self._validate_frame_bounds(frame)
        total_start = time.perf_counter_ns()
        extraction_start = time.perf_counter_ns()
        centers_local = extract_laser_center(
            frame.image,
            self.extraction_params,
            image_offset=(frame.offset_x, frame.offset_y),
        )
        extraction_ms = (time.perf_counter_ns() - extraction_start) / 1e6

        centers_full = centers_local.copy()
        if centers_full.size:
            centers_full[:, 0] += frame.offset_x
            centers_full[:, 1] += frame.offset_y

        reconstruction_start = time.perf_counter_ns()
        with self._calibration_lock:
            calibration = dict(self.package.calibration)
            ground_extrinsic_source = self._ground_extrinsic_source
        reconstructed = reconstruct_uv_to_ground(
            centers_full,
            calibration,
            self.config.reconstruction,
        )
        reconstruction_ms = (time.perf_counter_ns() - reconstruction_start) / 1e6
        points = reconstructed.points_ground
        section = (
            np.ascontiguousarray(points[:, (0, 2)])
            if len(points)
            else np.empty((0, 2), dtype=np.float64)
        )
        total_ms = (time.perf_counter_ns() - total_start) / 1e6
        return FrameResult(
            frame=frame,
            centers_uv_full=np.ascontiguousarray(centers_full),
            points_camera=reconstructed.points_camera,
            points_ground=points,
            section_xz=section,
            extraction_ms=extraction_ms,
            reconstruction_ms=reconstruction_ms,
            total_ms=total_ms,
            calibration_package_id=self.package.package_id,
            calibration_manifest_sha256=self.package.manifest_sha256,
            algorithm_config_sha256=self.algorithm_config_sha256,
            ground_extrinsic_source=ground_extrinsic_source,
            **self._stage_a_frame_metadata.as_dict(),
            filtered=reconstructed.filtered,
            pixels_uv=reconstructed.pixels_uv,
        )

    @property
    def ground_extrinsic_source(self) -> str:
        """当前运行时 ground 外参来源：``reference`` 或 ``session``。"""
        with self._calibration_lock:
            return self._ground_extrinsic_source

    @property
    def reference_ground_extrinsic(self) -> tuple[np.ndarray, np.ndarray]:
        """返回 reference R/t 的副本，用于 Session 标定差异比较。"""
        return self._reference_R.copy(), self._reference_t.copy()

    def calibration_for_reconstruction(self) -> dict[str, object]:
        """返回线程安全的当前运行时标定快照。"""
        with self._calibration_lock:
            calibration = dict(self.package.calibration)
            calibration["R"] = np.asarray(
                calibration["R"], dtype=np.float64
            ).copy()
            calibration["t"] = np.asarray(
                calibration["t"], dtype=np.float64
            ).copy()
            return calibration

    def apply_session_ground_extrinsic(
        self,
        R_camera_to_ground: np.ndarray,
        t_camera_to_ground: np.ndarray,
    ) -> None:
        """仅替换当前进程内的 ground R/t，不写入 reference 文件。"""
        rotation = np.asarray(R_camera_to_ground, dtype=np.float64)
        translation = np.asarray(t_camera_to_ground, dtype=np.float64).reshape(-1)
        if rotation.shape != (3, 3) or translation.shape != (3,):
            raise ValueError("Session ground 外参必须是 R(3x3) 和 t(3)")
        if not np.isfinite(rotation).all() or not np.isfinite(translation).all():
            raise ValueError("Session ground 外参必须包含有限数值")
        with self._calibration_lock:
            self.package.calibration["R"] = np.ascontiguousarray(rotation.copy())
            self.package.calibration["t"] = np.ascontiguousarray(translation.copy())
            self._ground_extrinsic_source = "session"

    def reset_ground_extrinsic(self) -> None:
        """恢复当前进程内的 reference R/t；不写入 reference 文件。"""
        with self._calibration_lock:
            self.package.calibration["R"] = self._reference_R.copy()
            self.package.calibration["t"] = self._reference_t.copy()
            self._ground_extrinsic_source = "reference"

    def _validate_frame_bounds(self, frame: CapturedFrame) -> None:
        height, width = frame.image.shape
        if frame.offset_x + width > self.package.image_width:
            raise ValueError("相机 ROI 横向范围超出标定图像尺寸")
        if frame.offset_y + height > self.package.image_height:
            raise ValueError("相机 ROI 纵向范围超出标定图像尺寸")


def _algorithm_hash(method: str, options: dict[str, object]) -> str:
    import json

    payload = {"method": method, "options": options}
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def render_overlay(image: np.ndarray, centers_local: np.ndarray) -> np.ndarray:
    """Render the extracted centers only when a preview actually needs them."""
    gray = _to_uint8_display(image)
    canvas = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    for u, v in centers_local:
        cv2.circle(
            canvas,
            (int(round(u)), int(round(v))),
            1,
            (50, 255, 90),
            -1,
            lineType=cv2.LINE_AA,
        )
    return canvas
