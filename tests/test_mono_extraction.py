from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from line_laser_static.algorithms import MonoStripeExtractor
from line_laser_static.calibration import LaserCalibration, load_calibration
from line_laser_static.config import load_run_config
from line_laser_static.metrics import summarize_repeatability
from line_laser_static.models import Frame, FrameMetadata, StripeProfile
from line_laser_static.pipeline import StaticProfilePipeline
from line_laser_static.reconstruction import RayPlaneReconstructor
from line_laser_static.sources import SyntheticFrameSource


ROOT = Path(__file__).resolve().parents[1]


def make_frame(image: np.ndarray, pixel_format: str) -> Frame:
    height, width = image.shape
    return Frame(
        image=image,
        metadata=FrameMetadata(
            frame_id=0,
            timestamp_ns=0,
            width=width,
            height=height,
            exposure_us=2000.0,
            gain_db=0.0,
            pixel_format=pixel_format,
            camera_model="TEST-MONO",
            serial_number="TEST-000",
            sdk_version="test",
        ),
    )


def make_stripe_image(
    *,
    width: int = 96,
    height: int = 64,
    center: float = 25.35,
    sigma: float = 1.7,
    amplitude: float = 180.0,
    background: float = 20.0,
    noise_std: float = 0.0,
    sensor_max: int = 255,
    dtype: type[np.unsignedinteger] = np.uint8,
) -> tuple[np.ndarray, np.ndarray]:
    columns = np.arange(width, dtype=np.float64)
    centers = center + 0.01 * (columns - (width - 1) / 2.0)
    rows = np.arange(height, dtype=np.float64)[:, None]
    image = background + 0.02 * rows + amplitude * np.exp(
        -0.5 * ((rows - centers) / sigma) ** 2
    )
    if noise_std > 0.0:
        image += np.random.default_rng(7).normal(0.0, noise_std, image.shape)
    return np.clip(image, 0, sensor_max).astype(dtype), centers


def make_calibration(width: int = 96, height: int = 64) -> LaserCalibration:
    return LaserCalibration(
        version="test-v1",
        image_size=(width, height),
        camera_matrix=np.array(
            [
                [100.0, 0.0, (width - 1) / 2.0],
                [0.0, 100.0, (height - 1) / 2.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        ),
        distortion=np.zeros(5, dtype=np.float64),
        plane_normal=np.array([0.0, 0.0, 1.0], dtype=np.float64),
        plane_offset=-1000.0,
        coordinate_system="camera",
        unit="mm",
        mechanical_config_id="test-rig",
        dataset_id="test-data",
        status="TEST_ONLY",
    )


class MonoStripeExtractorTests(unittest.TestCase):
    def test_mono8_extracts_subpixel_center_and_quality(self) -> None:
        image, expected_centers = make_stripe_image(noise_std=0.5)
        profile = MonoStripeExtractor(
            window_radius=5,
            min_contrast=30.0,
            min_snr=5.0,
            min_fwhm_px=3.0,
            max_fwhm_px=6.0,
        ).extract(make_frame(image, "Mono8"))

        self.assertGreater(float(profile.valid.mean()), 0.98)
        self.assertLess(
            float(np.median(np.abs(profile.v_px - expected_centers))), 0.08
        )
        self.assertIsNotNone(profile.fwhm_px)
        self.assertGreater(float(np.median(profile.fwhm_px)), 3.5)
        self.assertLess(float(np.median(profile.fwhm_px)), 4.5)
        self.assertFalse(bool(profile.saturated.any()))

    def test_weak_or_saturated_stripes_are_rejected(self) -> None:
        weak_image, _ = make_stripe_image(amplitude=10.0, noise_std=1.0)
        saturated_image, _ = make_stripe_image(
            amplitude=300.0, background=0.0, noise_std=0.0
        )
        extractor = MonoStripeExtractor(
            min_contrast=30.0,
            min_snr=5.0,
            min_fwhm_px=2.0,
            max_fwhm_px=8.0,
        )

        weak = extractor.extract(make_frame(weak_image, "Mono8"))
        saturated = extractor.extract(make_frame(saturated_image, "Mono8"))

        self.assertFalse(bool(weak.valid.any()))
        self.assertTrue(bool(saturated.saturated.all()))
        self.assertFalse(bool(saturated.valid.any()))

    def test_mono12_uses_pixel_format_sensor_range(self) -> None:
        image, expected_centers = make_stripe_image(
            amplitude=2800.0,
            background=200.0,
            noise_std=5.0,
            sensor_max=4095,
            dtype=np.uint16,
        )
        profile = MonoStripeExtractor(
            min_contrast=480.0,
            min_snr=10.0,
            noise_floor=16.0,
            min_fwhm_px=3.0,
            max_fwhm_px=6.0,
        ).extract(make_frame(image, "Mono12"))

        self.assertTrue(bool(profile.valid.all()))
        self.assertLess(
            float(np.median(np.abs(profile.v_px - expected_centers))), 0.05
        )
        self.assertFalse(bool(profile.saturated.any()))

    def test_pipeline_summary_contains_mono_quality_metrics(self) -> None:
        source = SyntheticFrameSource(
            96, 64, stripe_row_px=25.35, sigma_px=1.7, noise_std=0.0
        )
        pipeline = StaticProfilePipeline(
            source,
            MonoStripeExtractor(
                min_snr=5.0, min_fwhm_px=3.0, max_fwhm_px=6.0
            ),
            RayPlaneReconstructor(make_calibration()),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = pipeline.run_once(temp_dir, {"config_version": "mono-test"})
            summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))

        self.assertIn("fwhm_px_median", summary["profile"])
        self.assertIn("snr_p05", summary["profile"])
        self.assertEqual(summary["profile"]["saturated_count"], 0)

    def test_repeatability_reports_column_center_std(self) -> None:
        profiles = []
        for offset in (-0.1, 0.0, 0.1):
            profiles.append(
                StripeProfile(
                    u_px=np.arange(8, dtype=np.float64),
                    v_px=np.full(8, 20.0 + offset),
                    intensity=np.full(8, 180.0),
                    confidence=np.ones(8),
                    valid=np.ones(8, dtype=bool),
                )
            )

        metrics = summarize_repeatability(profiles)

        self.assertAlmostEqual(metrics["center_std_px_median"], 0.1)
        self.assertEqual(metrics["repeatable_column_ratio"], 1.0)

    def test_450nm_presets_are_explicitly_non_measurement(self) -> None:
        run_config = load_run_config(
            ROOT / "configs" / "me2p_1230_450nm_preset.json"
        )
        calibration = load_calibration(run_config.calibration_file)

        self.assertEqual(calibration.image_size, (4096, 3000))
        self.assertAlmostEqual(calibration.camera_matrix[0, 0], 7246.376811594203)
        self.assertIn("NOT_FOR_MEASUREMENT", calibration.status)
        self.assertEqual(run_config.extraction.name, "mono")


if __name__ == "__main__":
    unittest.main()
