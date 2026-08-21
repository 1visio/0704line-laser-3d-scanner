from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from app_config import DEFAULT_CONFIG_PATH, load_app_config
from measurement.ground_reference import fit_session_ground_reference
from online.fake_camera import SyntheticCameraSession
from online.models import CameraConfig
from online.pipeline import FramePipeline
from online.session_calibration import (
    merge_session_ground_reference,
    save_session_ground_payload,
)


def _empty_ground_points() -> np.ndarray:
    s = np.linspace(-100.0, 100.0, 81)
    return np.column_stack(
        [
            s,
            np.zeros_like(s),
            0.02 * s + 1.5,
        ]
    )


class SessionGroundReferenceTests(unittest.TestCase):
    def test_session_fit_reuses_linear_baseline_kernel(self) -> None:
        config = load_app_config(DEFAULT_CONFIG_PATH)
        reference = fit_session_ground_reference(
            _empty_ground_points(), config.measurement
        )

        self.assertEqual(reference.status, "VALID")
        self.assertEqual(reference.source, "session_laser_ground")
        self.assertAlmostEqual(reference.slope, 0.02, places=10)
        self.assertAlmostEqual(reference.intercept, 1.5, places=10)
        self.assertLess(reference.rmse, 1.0e-10)
        self.assertEqual(reference.valid_s_range, (-100.0, 100.0))

        corrected, valid = reference.apply_to_points(_empty_ground_points())
        self.assertTrue(valid.all())
        np.testing.assert_allclose(corrected[:, 2], 0.0, atol=1.0e-10)

    def test_ground_reference_does_not_extrapolate_outside_fitted_s_domain(
        self,
    ) -> None:
        config = load_app_config(DEFAULT_CONFIG_PATH)
        reference = fit_session_ground_reference(
            _empty_ground_points(), config.measurement
        )
        points = np.asarray(
            [
                [0.0, 0.0, 1.5],
                [150.0, 0.0, 20.0],
            ],
            dtype=np.float64,
        )
        corrected, valid = reference.apply_to_points(points)
        np.testing.assert_array_equal(valid, np.asarray([True, False]))
        self.assertAlmostEqual(corrected[0, 2], 0.0, places=10)
        self.assertAlmostEqual(corrected[1, 2], 20.0, places=10)

    def test_reference_survives_switch_between_reference_and_session_pnp(self) -> None:
        config = load_app_config(DEFAULT_CONFIG_PATH)
        pipeline = FramePipeline(config)
        reference = fit_session_ground_reference(
            _empty_ground_points(), config.measurement
        )
        pipeline.apply_session_ground_reference(reference)

        points = _empty_ground_points()
        first, first_meta = pipeline.apply_ground_reference_to_points(points)
        pipeline.apply_session_ground_extrinsic(np.eye(3), np.zeros(3))
        second, second_meta = pipeline.apply_ground_reference_to_points(points)

        np.testing.assert_allclose(first, second)
        self.assertEqual(first_meta["ground_reference_status"], "applied")
        self.assertEqual(second_meta["ground_reference_status"], "applied")
        self.assertEqual(pipeline.ground_extrinsic_source, "session")
        self.assertIs(pipeline.session_ground_reference, reference)

        pipeline.reset_ground_extrinsic()
        self.assertEqual(pipeline.ground_extrinsic_source, "reference")
        self.assertIs(pipeline.session_ground_reference, reference)

    def test_pipeline_exposes_corrected_and_raw_ground_views(self) -> None:
        config = load_app_config(DEFAULT_CONFIG_PATH)
        pipeline = FramePipeline(config)
        camera = SyntheticCameraSession(
            CameraConfig(width=2448, height=128, offset_y=960), target_fps=1000
        )
        camera.start()
        try:
            frame = camera.get_frame()
            raw_result = pipeline.run_frame(frame)
            reference = fit_session_ground_reference(
                raw_result.points_ground, config.measurement
            )
            pipeline.apply_session_ground_reference(reference)
            corrected_result = pipeline.run_frame(frame)
        finally:
            camera.stop()

        np.testing.assert_array_equal(
            corrected_result.points_ground_raw, raw_result.points_ground
        )
        self.assertEqual(corrected_result.ground_reference_status, "applied")
        self.assertEqual(
            corrected_result.ground_reference_applied_count,
            len(corrected_result.points_ground),
        )
        self.assertEqual(corrected_result.ground_reference_out_of_range_count, 0)
        self.assertFalse(
            np.array_equal(corrected_result.points_ground, raw_result.points_ground)
        )

    def test_pnp_record_update_preserves_frozen_ground_reference_record(self) -> None:
        config = load_app_config(DEFAULT_CONFIG_PATH)
        reference = fit_session_ground_reference(
            _empty_ground_points(), config.measurement
        )
        with tempfile.TemporaryDirectory() as directory:
            path = f"{directory}/session_ground_calibration.json"
            save_session_ground_payload(
                path,
                {
                    "schema_version": 2,
                    "status": "VALID",
                    "runtime": {"ground_extrinsic_source": "reference"},
                },
            )
            merge_session_ground_reference(
                path,
                reference.as_dict(),
                ground_extrinsic_source="reference",
            )
            save_session_ground_payload(
                path,
                {
                    "schema_version": 2,
                    "status": "VALID",
                    "runtime": {"ground_extrinsic_source": "session"},
                },
            )
            saved = json.loads(Path(path).read_text(encoding="utf-8"))

        self.assertEqual(saved["session_ground_reference"]["status"], "VALID")
        self.assertEqual(saved["runtime"]["ground_extrinsic_source"], "session")


if __name__ == "__main__":
    unittest.main()
