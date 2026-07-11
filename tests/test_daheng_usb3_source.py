from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from line_laser_static.bootstrap import build_pipeline
from line_laser_static.config import load_run_config
from line_laser_static.sources import DahengUsb3FrameSource


ROOT = Path(__file__).resolve().parents[1]


class FakeFeature:
    def __init__(self, value: object) -> None:
        self.value = value
        self.history: list[object] = []

    def is_implemented(self) -> bool:
        return True

    def is_writable(self) -> bool:
        return True

    def set(self, value: object) -> None:
        self.value = value
        self.history.append(value)

    def get(self) -> object:
        return self.value


class FakeRawImage:
    def __init__(self, image: np.ndarray | None, status: int = 0) -> None:
        self.image = image
        self.status = status

    def get_numpy_array(self) -> np.ndarray | None:
        return self.image

    def get_status(self) -> int:
        return self.status

    def get_frame_id(self) -> int:
        return 42


class FakeStream:
    def __init__(self, raw_image: FakeRawImage | None) -> None:
        self.raw_image = raw_image
        self.requested_timeout: int | None = None

    def get_image(self, timeout: int) -> FakeRawImage | None:
        self.requested_timeout = timeout
        return self.raw_image


class FakeCamera:
    def __init__(self, raw_image: FakeRawImage | None) -> None:
        self.Width = FakeFeature(8)
        self.Height = FakeFeature(4)
        self.OffsetX = FakeFeature(0)
        self.OffsetY = FakeFeature(0)
        self.PixelFormat = FakeFeature("MONO8")
        self.ExposureAuto = FakeFeature("OFF")
        self.GainAuto = FakeFeature("OFF")
        self.TriggerMode = FakeFeature("OFF")
        self.ExposureTime = FakeFeature(1000.0)
        self.Gain = FakeFeature(0.0)
        self.data_stream = [FakeStream(raw_image)]
        self.stream_started = False
        self.stream_stopped = False
        self.closed = False

    def stream_on(self) -> None:
        self.stream_started = True

    def stream_off(self) -> None:
        self.stream_stopped = True

    def close_device(self) -> None:
        self.closed = True


class FakeManager:
    def __init__(self, camera: FakeCamera, devices: list[dict[str, str]]) -> None:
        self.camera = camera
        self.devices = devices
        self.opened_by: tuple[str, object] | None = None

    def update_device_list(
        self, timeout: int
    ) -> tuple[int, list[dict[str, str]]]:
        return len(self.devices), self.devices

    def open_device_by_sn(self, serial_number: str) -> FakeCamera:
        self.opened_by = ("sn", serial_number)
        return self.camera

    def open_device_by_index(self, device_index: int) -> FakeCamera:
        self.opened_by = ("index", device_index)
        return self.camera


def make_fake_sdk(raw_image: FakeRawImage | None) -> tuple[object, FakeManager]:
    camera = FakeCamera(raw_image)
    manager = FakeManager(
        camera,
        [{"sn": "SN-USB3-001", "model_name": "ME2P-1230-23U3M"}],
    )
    sdk = SimpleNamespace(
        __version__="test-sdk",
        DeviceManager=lambda: manager,
        GxAutoEntry=SimpleNamespace(OFF="AUTO_OFF"),
        GxSwitchEntry=SimpleNamespace(OFF="SWITCH_OFF"),
        GxPixelFormatEntry=SimpleNamespace(MONO8="MONO8", MONO12="MONO12"),
        GxFrameStatusList=SimpleNamespace(INCOMPLETE=1),
    )
    return sdk, manager


def make_source(**overrides: object) -> DahengUsb3FrameSource:
    options: dict[str, object] = {
        "serial_number": "SN-USB3-001",
        "width": 8,
        "height": 4,
        "offset_x_px": 2,
        "offset_y_px": 3,
        "full_width_px": 16,
        "full_height_px": 12,
        "pixel_format": "Mono8",
        "exposure_us": 2500.0,
        "gain_db": 1.5,
        "capture_timeout_ms": 1234,
    }
    options.update(overrides)
    return DahengUsb3FrameSource(**options)


class DahengUsb3FrameSourceTests(unittest.TestCase):
    def test_captures_mono_frame_and_closes_camera(self) -> None:
        sdk_image = np.arange(32, dtype=np.uint8).reshape(4, 8)
        sdk, manager = make_fake_sdk(FakeRawImage(sdk_image))

        with patch(
            "line_laser_static.sources.daheng_usb3._load_gxipy",
            return_value=sdk,
        ):
            frame = make_source().capture()

        camera = manager.camera
        self.assertEqual(manager.opened_by, ("sn", "SN-USB3-001"))
        self.assertTrue(camera.stream_started)
        self.assertTrue(camera.stream_stopped)
        self.assertTrue(camera.closed)
        self.assertEqual(camera.data_stream[0].requested_timeout, 1234)
        self.assertEqual(frame.image.shape, (4, 8))
        self.assertEqual(frame.metadata.frame_id, 42)
        self.assertEqual(frame.metadata.offset_x_px, 2)
        self.assertEqual(frame.metadata.offset_y_px, 3)
        self.assertEqual(frame.metadata.full_width_px, 16)
        self.assertEqual(frame.metadata.full_height_px, 12)
        self.assertEqual(frame.metadata.pixel_format, "Mono8")
        self.assertEqual(frame.metadata.camera_model, "ME2P-1230-23U3M")
        self.assertEqual(frame.metadata.sdk_version, "test-sdk")

        sdk_image.fill(0)
        self.assertNotEqual(int(frame.image.sum()), 0)

    def test_configures_roi_exposure_gain_and_mono_format(self) -> None:
        sdk, manager = make_fake_sdk(
            FakeRawImage(np.ones((4, 8), dtype=np.uint8))
        )

        with patch(
            "line_laser_static.sources.daheng_usb3._load_gxipy",
            return_value=sdk,
        ):
            make_source().capture()

        camera = manager.camera
        self.assertEqual(camera.Width.value, 8)
        self.assertEqual(camera.Height.value, 4)
        self.assertEqual(camera.OffsetX.history, [0, 2])
        self.assertEqual(camera.OffsetY.history, [0, 3])
        self.assertEqual(camera.PixelFormat.value, "MONO8")
        self.assertEqual(camera.ExposureTime.value, 2500.0)
        self.assertEqual(camera.Gain.value, 1.5)
        self.assertEqual(camera.TriggerMode.value, "SWITCH_OFF")

    def test_opens_camera_by_one_based_device_index(self) -> None:
        sdk, manager = make_fake_sdk(
            FakeRawImage(np.ones((4, 8), dtype=np.uint8))
        )

        with patch(
            "line_laser_static.sources.daheng_usb3._load_gxipy",
            return_value=sdk,
        ):
            make_source(serial_number=None, device_index=1).capture()

        self.assertEqual(manager.opened_by, ("index", 1))

    def test_no_camera_reports_usb3_driver_hint(self) -> None:
        sdk, manager = make_fake_sdk(None)
        manager.devices = []

        with patch(
            "line_laser_static.sources.daheng_usb3._load_gxipy",
            return_value=sdk,
        ):
            with self.assertRaisesRegex(RuntimeError, "USB3、驱动和相机供电"):
                make_source().capture()

        self.assertFalse(manager.camera.stream_started)
        self.assertFalse(manager.camera.closed)

    def test_timeout_still_stops_and_closes_camera(self) -> None:
        sdk, manager = make_fake_sdk(None)

        with patch(
            "line_laser_static.sources.daheng_usb3._load_gxipy",
            return_value=sdk,
        ):
            with self.assertRaisesRegex(TimeoutError, "1234 ms"):
                make_source().capture()

        self.assertTrue(manager.camera.stream_stopped)
        self.assertTrue(manager.camera.closed)

    def test_incomplete_frame_is_rejected_and_camera_is_closed(self) -> None:
        sdk, manager = make_fake_sdk(
            FakeRawImage(np.ones((4, 8), dtype=np.uint8), status=1)
        )

        with patch(
            "line_laser_static.sources.daheng_usb3._load_gxipy",
            return_value=sdk,
        ):
            with self.assertRaisesRegex(RuntimeError, "不完整帧"):
                make_source().capture()

        self.assertTrue(manager.camera.stream_stopped)
        self.assertTrue(manager.camera.closed)

    def test_usb3_config_builds_without_importing_gxipy(self) -> None:
        config = load_run_config(
            ROOT / "configs" / "me2p_1230_450nm_daheng_usb3.json"
        )

        pipeline, calibration = build_pipeline(config)

        self.assertIsInstance(pipeline.source, DahengUsb3FrameSource)
        self.assertEqual(pipeline.source.height, 512)
        self.assertEqual(pipeline.source.offset_y_px, 1244)
        self.assertEqual(calibration.image_size, (4096, 3000))


if __name__ == "__main__":
    unittest.main()
