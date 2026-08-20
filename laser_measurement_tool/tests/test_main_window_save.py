"""Main-window result packaging tests."""

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app_config import load_app_config
from gui.main_window import MainWindow


class MainWindowSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_extraction_stays_in_memory_until_result_is_saved(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            window = MainWindow(load_app_config())
            self.assertEqual(window.online_button.text(), "在线相机")
            window._output_directory = output_directory
            window._image = np.zeros((200, 200), dtype=np.uint8)
            window._image_path = output_directory / "sample.tif"
            window.image_view.set_image(window._image)
            centres = np.array(
                [[90.0, 100.0], [100.0, 100.2], [110.0, 100.4]],
                dtype=np.float64,
            )

            with patch("gui.main_window.extract_laser_center", return_value=centres):
                window._extract_laser_line()

            self.assertEqual(list(output_directory.iterdir()), [])
            self.assertIsNone(window.last_laser_csv_path)

            window._save_results()
            result_directory = output_directory / "sample_measure"
            names = {path.name for path in result_directory.iterdir()}
            self.assertEqual(
                names,
                {
                    "laser_center.csv",
                    "result.json",
                    "overlay.png",
                    "full_laser_ground.ply",
                },
            )
            payload = json.loads(
                (result_directory / "result.json").read_text(encoding="utf-8")
            )
            self.assertFalse(payload["measurement_performed"])
            self.assertEqual(payload["laser_center_csv"], "laser_center.csv")
            self.assertNotIn("obstacles", payload)
            self.assertNotIn("ground_reference_mode", payload)
            self.assertNotIn("results_mm", payload)
            self.assertIsNone(payload["height_raw"])
            self.assertIsNone(payload["height_stage_a"])
            self.assertFalse(payload["stage_a_enabled"])
            self.assertFalse(payload["stage_a_valid"])
            self.assertEqual(
                window.last_laser_csv_path,
                result_directory / "laser_center.csv",
            )
            window.close()

    def test_hardware_roi_metadata_restores_full_image_offset(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            image_path = directory / "frame_000001.tiff"
            (directory / "frames.csv").write_text(
                "filename,offset_x,offset_y\n"
                "frame_000001.tiff,0,880\n",
                encoding="utf-8",
            )
            window = MainWindow(load_app_config())
            try:
                offset = window._resolve_loaded_image_offset(
                    image_path,
                    np.zeros((300, 2448), dtype=np.uint8),
                )
                self.assertEqual(offset, (0, 880))
                window._image_offset = offset or (0, 0)
                local = np.array([[100.0, 145.25]], dtype=np.float64)
                np.testing.assert_allclose(
                    window._centers_in_calibration_coordinates(local),
                    np.array([[100.0, 1025.25]], dtype=np.float64),
                )
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
