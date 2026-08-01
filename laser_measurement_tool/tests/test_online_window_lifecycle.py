"""Online window state and camera-configuration lifecycle tests."""

from __future__ import annotations

import os
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QApplication

from app_config import DEFAULT_CONFIG_PATH, load_app_config
from online.window import (
    ConstrainedImageViewBox,
    OnlineCameraWindow,
    OnlineState,
    _fit_image_view,
)


class OnlineWindowLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])
        cls.config = load_app_config(DEFAULT_CONFIG_PATH)

    def _wait_for_state(
        self,
        window: OnlineCameraWindow,
        expected: OnlineState,
        timeout_s: float = 2.0,
    ) -> None:
        deadline = time.monotonic() + timeout_s
        while window._online_state is not expected and time.monotonic() < deadline:
            self.application.processEvents()
            time.sleep(0.005)
        self.assertIs(window._online_state, expected)

    def test_stop_is_non_blocking_and_restores_idle_controls(self) -> None:
        window = OnlineCameraWindow(self.config, simulate=True)
        window.connect_camera()
        window.start_stream()
        self.assertIs(window._online_state, OnlineState.STREAMING)
        self.assertFalse(window.camera_settings_group.isEnabled())

        started = time.perf_counter()
        window.stop_stream()
        self.assertLess(time.perf_counter() - started, 0.1)
        self.assertIs(window._online_state, OnlineState.STOPPING)
        self._wait_for_state(window, OnlineState.CONNECTED)
        self.assertTrue(window.camera_settings_group.isEnabled())
        self.assertEqual(window.capture_fps_label.text(), "0.0")
        window.disconnect_camera()
        window.close()

    def test_restart_applies_changed_camera_config(self) -> None:
        window = OnlineCameraWindow(self.config, simulate=True)
        window.connect_camera()
        window.start_stream()
        window.stop_stream()
        self._wait_for_state(window, OnlineState.CONNECTED)

        window.exposure.setValue(4321.0)
        window.roi_height.setValue(200)
        window.offset_y.setValue(900)
        window.start_stream()
        self.assertEqual(window._session.config.exposure_us, 4321.0)
        self.assertEqual(window._session.config.height, 200)
        self.assertEqual(window._session.config.offset_y, 900)
        window.disconnect_camera()
        self._wait_for_state(window, OnlineState.DISCONNECTED)
        window.close()

    def test_disconnect_while_streaming_finishes_shutdown(self) -> None:
        window = OnlineCameraWindow(self.config, simulate=True)
        window.connect_camera()
        window.start_stream()
        window.disconnect_camera()
        self.assertTrue(window._pending_disconnect)
        self._wait_for_state(window, OnlineState.DISCONNECTED)
        self.assertIsNone(window._session)
        self.assertFalse(window._controller.running)
        window.close()

    def test_failed_close_keeps_session_available_for_retry(self) -> None:
        window = OnlineCameraWindow(self.config, simulate=True)
        window.connect_camera()
        session = window._session
        original_close = session.close

        def fail_close() -> None:
            raise RuntimeError("close failed")

        session.close = fail_close

        self.assertFalse(window._close_camera_session())
        self.assertIs(window._session, session)
        self.assertIs(window._online_state, OnlineState.ERROR)

        session.close = original_close
        self.assertTrue(window._close_camera_session())
        window.close()

    def test_image_preview_stays_reachable_and_cannot_zoom_beyond_home(self) -> None:
        view_box = ConstrainedImageViewBox()
        view = pg.PlotWidget(viewBox=view_box)
        view.resize(1200, 400)
        view.setAspectLocked(True)
        view.show()
        self.application.processEvents()
        try:
            for height in (300, 2048):
                image = np.zeros((height, 2448), dtype=np.uint8)
                for mode in ("width", "fit"):
                    _fit_image_view(view, image, mode)
                    home_x, home_y = view_box.viewRange()
                    home_span = (
                        home_x[1] - home_x[0],
                        home_y[1] - home_y[0],
                    )
                    if mode == "fit":
                        self.assertLessEqual(home_x[0], 0)
                        self.assertGreaterEqual(home_x[1], 2448)
                        self.assertLessEqual(home_y[0], 0)
                        self.assertGreaterEqual(home_y[1], height)

                    view_box.scaleBy([0.5, 0.5])
                    view_box.translateBy(x=100_000, y=100_000)
                    moved_x, moved_y = view_box.viewRange()
                    self.assertGreater(moved_x[1], 0)
                    self.assertLess(moved_x[0], 2448)
                    self.assertGreater(moved_y[1], 0)
                    self.assertLess(moved_y[0], height)

                    view_box.scaleBy([100.0, 100.0])
                    final_x, final_y = view_box.viewRange()
                    self.assertLessEqual(
                        final_x[1] - final_x[0], home_span[0] + 1e-6
                    )
                    self.assertLessEqual(
                        final_y[1] - final_y[0], home_span[1] + 1e-6
                    )
        finally:
            view.close()


if __name__ == "__main__":
    unittest.main()
