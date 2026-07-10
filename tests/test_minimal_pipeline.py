from __future__ import annotations

import json
import tempfile
import unittest

import numpy as np

from line_laser_static.algorithms import CentroidStripeExtractor
from line_laser_static.calibration import LaserCalibration
from line_laser_static.models import StripeProfile
from line_laser_static.pipeline import StaticProfilePipeline
from line_laser_static.reconstruction import RayPlaneReconstructor
from line_laser_static.sources import SyntheticFrameSource


def make_calibration(width: int = 64, height: int = 48) -> LaserCalibration:
    return LaserCalibration(
        version="test-v1",
        image_size=(width, height),
        camera_matrix=np.array(
            [
                [100.0, 0.0, (width - 1) / 2],
                [0.0, 100.0, (height - 1) / 2],
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
        dataset_id="synthetic-test",
        status="TEST_ONLY",
    )


class MinimalPipelineTests(unittest.TestCase):
    def test_centroid_extracts_subpixel_stripe(self) -> None:
        source = SyntheticFrameSource(
            width=64,
            height=48,
            stripe_row_px=20.25,
            sigma_px=1.2,
            amplitude=220,
            background=5,
            noise_std=0,
        )
        profile = CentroidStripeExtractor(window_radius=4, min_contrast=30).extract(
            source.capture()
        )

        self.assertTrue(profile.valid.all())
        self.assertLess(float(np.max(np.abs(profile.v_px - 20.25))), 0.05)

    def test_reconstruction_marks_invalid_points_as_nan(self) -> None:
        profile = StripeProfile(
            u_px=np.array([20.0, 30.0]),
            v_px=np.array([20.0, 21.0]),
            intensity=np.array([200.0, 10.0]),
            confidence=np.array([0.9, 0.1]),
            valid=np.array([True, False]),
        )
        cloud = RayPlaneReconstructor(make_calibration()).reconstruct(profile)

        self.assertAlmostEqual(float(cloud.z_mm[0]), 1000.0)
        self.assertTrue(np.isnan(cloud.x_mm[1]))
        self.assertFalse(bool(cloud.valid[1]))

    def test_pipeline_exports_contract_and_traceability(self) -> None:
        source = SyntheticFrameSource(64, 48, stripe_row_px=20.25, noise_std=0)
        pipeline = StaticProfilePipeline(
            source,
            CentroidStripeExtractor(),
            RayPlaneReconstructor(make_calibration()),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts = pipeline.run_once(temp_dir, {"config_version": "test-config-v1"})
            csv_header = artifacts.csv_path.read_text(encoding="utf-8").splitlines()[0]
            summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))

            self.assertEqual(
                csv_header, "x_mm,y_mm,z_mm,intensity,confidence,valid"
            )
            self.assertTrue(artifacts.ply_path.exists())
            self.assertEqual(summary["context"]["config_version"], "test-config-v1")
            self.assertEqual(summary["point_cloud"]["valid_count"], 64)


if __name__ == "__main__":
    unittest.main()
