from __future__ import annotations

import time

import numpy as np

from ..models import Frame, FrameMetadata


class SyntheticFrameSource:
    def __init__(
        self,
        width: int,
        height: int,
        stripe_row_px: float,
        stripe_slope: float = 0.0,
        sigma_px: float = 1.4,
        amplitude: float = 220.0,
        background: float = 8.0,
        noise_std: float = 1.0,
        seed: int = 0,
        exposure_us: float = 2000.0,
        gain_db: float = 0.0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("合成图像宽高必须为正数")
        if sigma_px <= 0:
            raise ValueError("sigma_px 必须大于零")
        self.width = width
        self.height = height
        self.stripe_row_px = stripe_row_px
        self.stripe_slope = stripe_slope
        self.sigma_px = sigma_px
        self.amplitude = amplitude
        self.background = background
        self.noise_std = noise_std
        self.exposure_us = exposure_us
        self.gain_db = gain_db
        self._rng = np.random.default_rng(seed)
        self._frame_id = 0

    def capture(self) -> Frame:
        columns = np.arange(self.width, dtype=np.float32)
        rows = np.arange(self.height, dtype=np.float32)[:, None]
        centers = self.stripe_row_px + self.stripe_slope * (
            columns - (self.width - 1) / 2.0
        )
        image = self.background + self.amplitude * np.exp(
            -0.5 * ((rows - centers) / self.sigma_px) ** 2
        )
        if self.noise_std > 0:
            image += self._rng.normal(0.0, self.noise_std, image.shape)
        image_u8 = np.clip(image, 0, 255).astype(np.uint8)
        metadata = FrameMetadata(
            frame_id=self._frame_id,
            timestamp_ns=time.time_ns(),
            width=self.width,
            height=self.height,
            exposure_us=self.exposure_us,
            gain_db=self.gain_db,
            pixel_format="Mono8",
            camera_model="SYNTHETIC",
            serial_number="SYNTHETIC-000",
            sdk_version="none",
        )
        self._frame_id += 1
        return Frame(image=image_u8, metadata=metadata)
