from __future__ import annotations

import argparse
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import capture_laser_dataset as capture
import batch_process


def make_args(dataset: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dataset": dataset,
        "exp_id": "T001",
        "frames": 1,
        "exposure_us": 2000.0,
        "gain": 0.0,
        "material": "white_board",
        "distance_mm": 300.0,
        "baseline_mm": 80.0,
        "laser_angle_deg": 15.0,
        "pixel_format": "Mono12",
        "offset_x": 0,
        "offset_y": 0,
        "width": None,
        "height": None,
        "warmup_frames": 0,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def settings(pixel_format: str = "Mono12") -> capture.CameraSettings:
    return capture.CameraSettings(
        exposure_us=2000.0,
        gain=0.0,
        pixel_format=pixel_format,
        offset_x=0,
        offset_y=0,
        width=64,
        height=48,
    )


class FakeRawImage:
    def __init__(self, image: np.ndarray) -> None:
        self.image = image

    def get_numpy_array(self) -> np.ndarray:
        return self.image


class FakeDataStream:
    def __init__(self, images: list[FakeRawImage | None]) -> None:
        self.images = iter(images)

    def get_image(self) -> FakeRawImage | None:
        return next(self.images, None)


class FakeCamera:
    def __init__(self, images: list[FakeRawImage | None]) -> None:
        self.data_stream = [FakeDataStream(images)]
        self.stream_started = False
        self.stream_stopped = False
        self.closed = False

    def stream_on(self) -> None:
        self.stream_started = True

    def stream_off(self) -> None:
        self.stream_stopped = True

    def close_device(self) -> None:
        self.closed = True


class FakeDeviceManager:
    def __init__(self, camera: FakeCamera) -> None:
        self.camera = camera

    def update_all_device_list(self) -> tuple[int, list[dict[str, object]]]:
        return 1, [
            {
                "device_class": FakeGX.GxDeviceClassList.U3V,
                "model_name": "FakeMono",
                "sn": "TEST123",
            }
        ]

    def open_device_by_index(self, index: int) -> FakeCamera:
        if index != 1:
            raise AssertionError(index)
        return self.camera


class FakeGX:
    class GxDeviceClassList:
        U3V = 1

    def __init__(self, camera: FakeCamera) -> None:
        self.manager = FakeDeviceManager(camera)

    def DeviceManager(self) -> FakeDeviceManager:
        return self.manager


class CaptureLaserDatasetTests(unittest.TestCase):
    def test_parser_defaults_and_case_insensitive_pixel_format(self) -> None:
        args = capture.build_parser().parse_args(
            [
                "--exp-id",
                "A001",
                "--exposure-us",
                "2000",
                "--material",
                "white_board",
                "--distance-mm",
                "300",
                "--baseline-mm",
                "80",
                "--laser-angle-deg",
                "15",
                "--pixel-format",
                "mOnO12",
            ]
        )
        capture.validate_args(args)

        self.assertEqual(args.dataset, capture.DEFAULT_DATASET)
        self.assertEqual(args.frames, 50)
        self.assertEqual(args.gain, 0.0)
        self.assertEqual(args.pixel_format, "Mono12")
        self.assertEqual(args.warmup_frames, 10)
        self.assertIsNone(args.width)
        self.assertIsNone(args.height)

    def test_roi_arguments_must_be_complete_and_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "provided together"):
                capture.validate_args(make_args(Path(temp_dir), width=320))
            with self.assertRaisesRegex(ValueError, "full-frame"):
                capture.validate_args(make_args(Path(temp_dir), offset_x=8))

    def test_metadata_header_and_atomic_append(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.csv"
            self.assertEqual(capture.ensure_metadata(metadata_path), set())
            row = capture._metadata_row(make_args(Path(temp_dir)), settings())
            capture.append_metadata_atomic(metadata_path, row)

            with metadata_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)

            self.assertEqual(tuple(reader.fieldnames or ()), capture.METADATA_FIELDS)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["exp_id"], "T001")
            self.assertEqual(rows[0]["image_dir"], "raw/T001")
            self.assertEqual(rows[0]["pixel_format"], "Mono12")
            self.assertEqual(rows[0]["roi_width"], "64")

    def test_write_png_preserves_uint8_and_uint16(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            images = (
                np.arange(24, dtype=np.uint8).reshape(4, 6),
                (np.arange(24, dtype=np.uint16).reshape(4, 6) * 173),
            )
            for index, expected in enumerate(images):
                path = root / f"image_{index}.png"
                capture.write_png(path, expected)
                actual = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                self.assertIsNotNone(actual)
                self.assertEqual(actual.dtype, expected.dtype)
                np.testing.assert_array_equal(actual, expected)

    def test_duplicate_exp_id_or_directory_is_rejected_before_camera_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_path = root / "metadata.csv"
            capture.ensure_metadata(metadata_path)
            capture.append_metadata_atomic(
                metadata_path, capture._metadata_row(make_args(root), settings())
            )
            with self.assertRaisesRegex(RuntimeError, "already exists in metadata"):
                capture.acquire_dataset(make_args(root))

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "raw" / "T001").mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "directory already exists"):
                capture.acquire_dataset(make_args(root))

    def test_successful_capture_is_compatible_with_batch_metadata_loader(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = np.arange(48 * 64, dtype=np.uint16).reshape(48, 64)
            camera = FakeCamera([FakeRawImage(image)])
            with patch.object(capture, "configure_camera", return_value=settings()):
                result = capture.acquire_dataset(
                    make_args(root), gx=FakeGX(camera), utility=object()
                )

            self.assertEqual(result.saved_frames, 1)
            self.assertTrue(camera.stream_stopped)
            self.assertTrue(camera.closed)
            saved = cv2.imread(
                str(result.output_dir / "frame_0001.png"), cv2.IMREAD_UNCHANGED
            )
            self.assertEqual(saved.dtype, np.uint16)
            np.testing.assert_array_equal(saved, image)

            experiments = batch_process.load_metadata(root / "metadata.csv")
            self.assertEqual(len(experiments), 1)
            self.assertEqual(experiments[0]["exp_id"], "T001")
            self.assertEqual(experiments[0]["image_dir"], "raw/T001")

    def test_get_image_failure_stops_stream_closes_camera_and_cleans_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            camera = FakeCamera([None])
            with patch.object(capture, "configure_camera", return_value=settings()):
                with self.assertRaisesRegex(RuntimeError, "Failed to acquire frame"):
                    capture.acquire_dataset(
                        make_args(root), gx=FakeGX(camera), utility=object()
                    )

            self.assertTrue(camera.stream_started)
            self.assertTrue(camera.stream_stopped)
            self.assertTrue(camera.closed)
            self.assertFalse((root / "raw" / "T001").exists())
            self.assertEqual(capture.ensure_metadata(root / "metadata.csv"), set())
            self.assertEqual(list((root / "raw").glob(".T001.*")), [])

    def test_save_failure_stops_stream_closes_camera_and_cleans_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = np.zeros((48, 64), dtype=np.uint16)
            camera = FakeCamera([FakeRawImage(image)])

            def fail_save(_path: Path, _image: np.ndarray) -> None:
                raise OSError("simulated save failure")

            with patch.object(capture, "configure_camera", return_value=settings()):
                with self.assertRaisesRegex(OSError, "simulated save failure"):
                    capture.acquire_dataset(
                        make_args(root),
                        gx=FakeGX(camera),
                        utility=object(),
                        image_writer=fail_save,
                    )

            self.assertTrue(camera.stream_started)
            self.assertTrue(camera.stream_stopped)
            self.assertTrue(camera.closed)
            self.assertFalse((root / "raw" / "T001").exists())
            self.assertEqual(capture.ensure_metadata(root / "metadata.csv"), set())


if __name__ == "__main__":
    unittest.main()
