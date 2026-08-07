from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import numpy as np

from line_laser_static.algorithms import (
    MonoStripeExtractor,
    SensorRoiMonoStripeExtractor,
)
from line_laser_static.bootstrap import build_pipeline
from line_laser_static.config import load_run_config
from line_laser_static.models import Frame, FrameMetadata


ROOT = Path(__file__).resolve().parents[1]


def make_sensor_roi_frame() -> tuple[Frame, np.ndarray]:
    width = 96
    height = 64
    columns = np.arange(width, dtype=np.float64)
    centers = 25.35 + 0.01 * (columns - (width - 1) / 2.0)
    rows = np.arange(height, dtype=np.float64)[:, None]
    image = 20.0 + 180.0 * np.exp(-0.5 * ((rows - centers) / 1.7) ** 2)
    image_u8 = np.clip(image, 0, 255).astype(np.uint8)
    frame = Frame(
        image=image_u8,
        metadata=FrameMetadata(
            frame_id=0,
            timestamp_ns=0,
            width=width,
            height=height,
            exposure_us=2000.0,
            gain_db=0.0,
            pixel_format="Mono8",
            camera_model="TEST-SENSOR-ROI",
            serial_number="TEST-ROI-000",
            sdk_version="test",
            offset_x_px=100,
            offset_y_px=1200,
            full_width_px=4096,
            full_height_px=3000,
        ),
    )
    return frame, centers


class SensorRoiMonoStripeExtractorTests(unittest.TestCase):
    def test_constructor_has_no_software_roi_parameters(self) -> None:
        parameters = inspect.signature(SensorRoiMonoStripeExtractor).parameters

        self.assertNotIn("roi_x_start", parameters)
        self.assertNotIn("roi_x_end", parameters)
        self.assertNotIn("roi_y_start", parameters)
        self.assertNotIn("roi_y_end", parameters)

    def test_hardware_roi_output_uses_full_sensor_coordinates(self) -> None:
        frame, expected_local_centers = make_sensor_roi_frame()
        extractor = SensorRoiMonoStripeExtractor(
            min_snr=5.0,
            min_fwhm_px=3.0,
            max_fwhm_px=6.0,
        )

        profile = extractor.extract(frame)

        self.assertEqual(float(profile.u_px[0]), 100.0)
        self.assertEqual(float(profile.u_px[-1]), 195.0)
        self.assertLess(
            float(
                np.median(
                    np.abs(profile.v_px - (expected_local_centers + 1200.0))
                )
            ),
            0.05,
        )
        self.assertTrue(bool(profile.valid.all()))

    def test_two_versions_only_differ_in_coordinate_origin(self) -> None:
        frame, _ = make_sensor_roi_frame()
        options = {
            "min_snr": 5.0,
            "min_fwhm_px": 3.0,
            "max_fwhm_px": 6.0,
        }

        local = MonoStripeExtractor(**options).extract(frame)
        full = SensorRoiMonoStripeExtractor(**options).extract(frame)

        np.testing.assert_allclose(full.u_px, local.u_px + 100.0)
        np.testing.assert_allclose(full.v_px, local.v_px + 1200.0)
        for field_name in (
            "intensity",
            "confidence",
            "valid",
            "contrast",
            "snr",
            "fwhm_px",
            "saturated",
        ):
            np.testing.assert_array_equal(
                getattr(full, field_name), getattr(local, field_name)
            )

    def test_metadata_rejects_roi_outside_full_image(self) -> None:
        with self.assertRaisesRegex(ValueError, "y 方向超出"):
            FrameMetadata(
                frame_id=0,
                timestamp_ns=0,
                width=4096,
                height=512,
                exposure_us=2000.0,
                gain_db=0.0,
                pixel_format="Mono8",
                camera_model="TEST",
                serial_number="TEST",
                sdk_version="test",
                offset_y_px=2600,
                full_width_px=4096,
                full_height_px=3000,
            )

    def test_sensor_roi_preset_restores_global_stripe_position(self) -> None:
        config = load_run_config(
            ROOT / "configs" / "me2p_1230_450nm_sensor_roi_preset.json"
        )
        pipeline, calibration = build_pipeline(config)

        frame = pipeline.source.capture()
        profile = pipeline.extractor.extract(frame)

        self.assertEqual(frame.image.shape, (512, 4096))
        self.assertEqual(frame.metadata.offset_y_px, 1244)
        self.assertEqual(calibration.image_size, (4096, 3000))
        self.assertEqual(profile.u_px.size, 4096)
        expected_centers = 1499.25 + 0.02 * (
            np.arange(4096, dtype=np.float64) - (4096 - 1) / 2.0
        )
        self.assertLess(
            float(np.median(np.abs(profile.v_px - expected_centers))), 0.08
        )
        self.assertTrue(bool(profile.valid.all()))


if __name__ == "__main__":
    unittest.main()
