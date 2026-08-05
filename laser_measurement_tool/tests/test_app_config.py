"""app_config 统一配置加载的单元测试。"""

import tempfile
import unittest
from pathlib import Path

from app_config import DEFAULT_CONFIG_PATH, AppConfigError, load_app_config
from calibration.config_loader import load_calibration_files


_VALID_CONFIG = """
schema_version: 1
calibration:
  intrinsics: calib/intrinsics.yaml
  laser_plane: calib/laser_plane.yaml
  extrinsics: calib/extrinsics.yaml
  ground_u_compensation: null
extraction:
  method: centroid
  centroid:
    background_kernel: 31
    min_local_contrast_dn: 15.0
  steger: {}
reconstruction:
  min_camera_depth_mm: 200.0
  max_camera_depth_mm: 900.0
measurement:
  outlier_sigma_multiplier: 2.5
  min_baseline_points: 10
  min_height_points: 10
output:
  dir: results
  save_overlay_png: false
  save_full_pointcloud_ply: false
"""


class LoadAppConfigTest(unittest.TestCase):
    def _write_config(self, content: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        path = directory / "measure_tool.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_config_parses_and_resolves_paths(self) -> None:
        path = self._write_config(_VALID_CONFIG)
        config = load_app_config(path)
        base = path.parent
        self.assertEqual(
            config.calibration.intrinsics, (base / "calib/intrinsics.yaml").resolve()
        )
        self.assertIsNone(config.calibration.ground_u_compensation)
        self.assertEqual(config.extraction_method, "centroid")
        self.assertEqual(
            config.extraction_options["background_kernel"], 31
        )
        self.assertIn("steger", config.extraction_options_by_method)
        self.assertEqual(config.reconstruction.min_camera_depth_mm, 200.0)
        self.assertEqual(config.measurement.outlier_sigma_multiplier, 2.5)
        assert config.output is not None
        self.assertEqual(config.output.directory, (base / "results").resolve())
        self.assertFalse(config.output.save_overlay_png)
        self.assertTrue(config.output.save_pointcloud_csv)
        self.assertFalse(config.output.save_full_pointcloud_ply)

    def test_absolute_paths_are_kept(self) -> None:
        directory = Path(tempfile.mkdtemp())
        absolute = directory / "somewhere" / "intrinsics.yaml"
        content = _VALID_CONFIG.replace(
            "calib/intrinsics.yaml", absolute.as_posix()
        )
        path = self._write_config(content)
        config = load_app_config(path)
        self.assertEqual(config.calibration.intrinsics, absolute)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(AppConfigError):
            load_app_config(Path(tempfile.mkdtemp()) / "missing.yaml")

    def test_missing_calibration_section_raises(self) -> None:
        path = self._write_config("schema_version: 1\nextraction:\n  method: centroid\n")
        with self.assertRaises(AppConfigError):
            load_app_config(path)

    def test_unknown_reconstruction_key_raises(self) -> None:
        content = _VALID_CONFIG.replace(
            "min_camera_depth_mm: 200.0", "bogus_key: 1.0"
        )
        path = self._write_config(content)
        with self.assertRaises(AppConfigError):
            load_app_config(path)

    def test_invalid_measurement_value_raises(self) -> None:
        content = _VALID_CONFIG.replace(
            "outlier_sigma_multiplier: 2.5", "outlier_sigma_multiplier: -1.0"
        )
        path = self._write_config(content)
        with self.assertRaises(AppConfigError):
            load_app_config(path)

    def test_default_config_and_calibration_are_self_contained(self) -> None:
        config = load_app_config(DEFAULT_CONFIG_PATH)
        self.assertEqual(config.extraction_method, "steger")
        self.assertEqual(config.extraction_options["sigma"], 1.5)
        tool_directory = DEFAULT_CONFIG_PATH.parent.parent.resolve()
        paths = (
            config.calibration.intrinsics,
            config.calibration.laser_plane,
            config.calibration.extrinsics,
            config.calibration.ground_u_compensation,
            config.calibration.manifest,
        )
        for path in paths:
            assert path is not None
            path.resolve().relative_to(tool_directory)
            self.assertTrue(path.is_file())

        calibration = load_calibration_files(
            config.calibration.intrinsics,
            config.calibration.laser_plane,
            config.calibration.extrinsics,
            config.calibration.ground_u_compensation,
        )
        self.assertEqual(calibration["K"].shape, (3, 3))
        self.assertEqual(calibration["plane_abcd"].shape, (4,))
        self.assertEqual(calibration["R"].shape, (3, 3))
        self.assertEqual(len(calibration["ground_u_compensation"]["bias_mm"]), 2448)


if __name__ == "__main__":
    unittest.main()
