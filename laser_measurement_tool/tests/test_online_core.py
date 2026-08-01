from __future__ import annotations

import csv
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from app_config import DEFAULT_CONFIG_PATH, load_app_config
from online.fake_camera import SyntheticCameraSession
from online.models import CameraConfig, CapturedFrame
from online.pipeline import FramePipeline
from online.recording import FrameRecorder
from online.runtime import LatestFrameSlot


def _frame(number: int, dtype: np.dtype = np.dtype(np.uint8)) -> CapturedFrame:
    return CapturedFrame(
        np.full((8, 12), number, dtype=dtype),
        camera_frame_number=number,
        camera_timestamp_ticks=number * 10,
        host_timestamp_ns=time.time_ns(),
        host_monotonic_ns=time.perf_counter_ns(),
        offset_x=0,
        offset_y=10,
    )


class OnlineCoreTests(unittest.TestCase):
    def test_camera_config_validation(self) -> None:
        with self.assertRaises(ValueError):
            CameraConfig(pixel_format="Mono12Packed")
        with self.assertRaises(ValueError):
            CameraConfig(offset_y=-1)

    def test_latest_slot_replaces_stale_frame(self) -> None:
        slot = LatestFrameSlot()
        slot.put(_frame(1))
        slot.put(_frame(2))
        self.assertEqual(slot.overwritten, 1)
        self.assertEqual(slot.take(0.01).camera_frame_number, 2)
        self.assertIsNone(slot.take(0.01))

    def test_pipeline_restores_full_sensor_roi_coordinates(self) -> None:
        config = CameraConfig(
            pixel_format="Mono8", offset_x=0, offset_y=960, width=2448, height=128
        )
        camera = SyntheticCameraSession(config, target_fps=1000)
        camera.start()
        result = FramePipeline(load_app_config(DEFAULT_CONFIG_PATH)).run_frame(
            camera.get_frame()
        )
        camera.stop()
        self.assertGreater(len(result.centers_uv_full), 2300)
        self.assertGreater(float(np.median(result.centers_uv_full[:, 1])), 1000.0)
        self.assertLess(float(np.median(result.centers_uv_full[:, 1])), 1050.0)
        self.assertEqual(result.overlay_rgb.shape, (128, 2448, 3))
        self.assertEqual(result.section_xz.shape[1], 2)

    def test_recorder_writes_lossless_frames_and_gap_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            recorder = FrameRecorder(queue_capacity=4)
            config = CameraConfig(pixel_format="Mono12", width=12, height=8)
            recorder.start(temporary, 2, config)
            self.assertTrue(recorder.enqueue(_frame(10, np.dtype(np.uint16))))
            self.assertTrue(recorder.enqueue(_frame(12, np.dtype(np.uint16))))
            result = recorder.wait(5.0)
            assert result is not None
            self.assertEqual(result.saved_frames, 2)
            self.assertEqual(result.detected_frame_gaps, 1)
            self.assertEqual(len(list(result.output_dir.glob("*.tiff"))), 2)
            with (result.output_dir / "frames.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[1]["frame_gap"], "1")

            recorder.start(temporary, 1, config)
            self.assertTrue(recorder.enqueue(_frame(20, np.dtype(np.uint16))))
            second = recorder.wait(5.0)
            assert second is not None
            with (second.output_dir / "frames.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as stream:
                second_rows = list(csv.DictReader(stream))
            self.assertEqual(second_rows[0]["camera_frame_number"], "20")


if __name__ == "__main__":
    unittest.main()
