"""Stable data contracts shared by camera, processing, recording, and UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass(frozen=True, slots=True)
class CameraDeviceInfo:
    model: str
    serial_number: str
    ip_address: str = ""
    transport: str = "GigE"

    @property
    def display_name(self) -> str:
        location = f" · {self.ip_address}" if self.ip_address else ""
        return f"{self.model} · SN {self.serial_number}{location}"


@dataclass(frozen=True, slots=True)
class CameraConfig:
    exposure_us: float = 1200.0
    gain_db: float = 0.0
    pixel_format: str = "Mono8"
    offset_x: int = 0
    offset_y: int = 880
    width: int = 2448
    height: int = 300
    timeout_ms: int = 2000

    def __post_init__(self) -> None:
        if self.exposure_us <= 0 or not np.isfinite(self.exposure_us):
            raise ValueError("exposure_us 必须是有限正数")
        if not np.isfinite(self.gain_db):
            raise ValueError("gain_db 必须是有限数")
        if self.pixel_format not in {"Mono8", "Mono12"}:
            raise ValueError("pixel_format 必须是 Mono8 或 Mono12")
        if min(self.offset_x, self.offset_y) < 0:
            raise ValueError("ROI 偏移不能为负数")
        if min(self.width, self.height, self.timeout_ms) <= 0:
            raise ValueError("ROI 尺寸和 timeout_ms 必须为正数")


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    image: np.ndarray
    camera_frame_number: int
    camera_timestamp_ticks: int | None
    host_timestamp_ns: int
    host_monotonic_ns: int
    offset_x: int = 0
    offset_y: int = 0

    def __post_init__(self) -> None:
        if self.image.ndim != 2 or self.image.dtype not in (
            np.dtype(np.uint8),
            np.dtype(np.uint16),
        ):
            raise ValueError("CapturedFrame.image 必须是二维 uint8/uint16 灰度图")


@dataclass(frozen=True, slots=True)
class FrameResult:
    frame: CapturedFrame
    centers_uv_full: np.ndarray
    points_ground: np.ndarray
    section_xz: np.ndarray
    extraction_ms: float
    reconstruction_ms: float
    total_ms: float
    calibration_package_id: str
    calibration_manifest_sha256: str
    algorithm_config_sha256: str
    filtered: dict[str, int] = field(default_factory=dict)
    _overlay_rgb: np.ndarray | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def overlay_rgb(self) -> np.ndarray:
        overlay = self._overlay_rgb
        if overlay is None:
            from .pipeline import render_overlay

            centers_local = self.centers_uv_full.copy()
            if centers_local.size:
                centers_local[:, 0] -= self.frame.offset_x
                centers_local[:, 1] -= self.frame.offset_y
            overlay = render_overlay(self.frame.image, centers_local)
            object.__setattr__(self, "_overlay_rgb", overlay)
        return overlay


class CameraSession(Protocol):
    device: CameraDeviceInfo
    config: CameraConfig

    def configure(self, config: CameraConfig) -> CameraConfig: ...

    def start(self) -> None: ...

    def get_frame(self, timeout_ms: int | None = None) -> CapturedFrame: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...
