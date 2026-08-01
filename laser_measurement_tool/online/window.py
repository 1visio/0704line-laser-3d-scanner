"""Standalone online camera window; reusable from the offline main tool."""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
except ImportError as error:  # pragma: no cover - depends on deployment
    raise RuntimeError(
        "在线界面需要 pyqtgraph 和 PyOpenGL；请运行 requirements.txt 中的依赖安装。"
    ) from error

from app_config import AppConfig

from .controller import OnlineController
from .fake_camera import SyntheticCameraSession
from .models import CameraConfig, CameraDeviceInfo, FrameResult
from .mvs_camera import MvsCameraSession, list_devices
from .pipeline import FramePipeline
from .recording import FrameRecorder


pg.setConfigOptions(imageAxisOrder="row-major")


class OnlineCameraWindow(QMainWindow):
    """Connect, acquire, process, inspect, snapshot, and record camera frames."""

    def __init__(self, config: AppConfig, *, simulate: bool = False) -> None:
        super().__init__()
        self._config = config
        self._simulate = simulate
        self._pipeline = FramePipeline(config)
        self._controller = OnlineController(self)
        self._recorder = FrameRecorder()
        self._session: MvsCameraSession | SyntheticCameraSession | None = None
        self._last_result: FrameResult | None = None
        self._trail: deque[tuple[float, np.ndarray]] = deque(maxlen=30)
        self._displayed_frames = 0
        self._display_started = time.monotonic()
        self._last_render_at = 0.0
        self._build_ui()
        self._connect_signals()
        self._record_timer = QTimer(self)
        self._record_timer.setInterval(250)
        self._record_timer.timeout.connect(self._poll_recording)
        self._record_timer.start()
        self.setWindowTitle("在线线激光三维截面 · MV-CS050-60GM")
        self.resize(1500, 900)
        self.refresh_devices()

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QHBoxLayout(central)
        self.tabs = QTabWidget(central)
        self.image_view = pg.PlotWidget(self.tabs)
        self.image_view.hideAxis("left")
        self.image_view.hideAxis("bottom")
        self.image_view.setAspectLocked(True)
        self.image_item = pg.ImageItem()
        self.image_view.addItem(self.image_item)
        self.tabs.addTab(self.image_view, "图像与条纹")
        self.point_view = gl.GLViewWidget(self.tabs)
        self.point_view.setCameraPosition(distance=800)
        self.point_item = gl.GLScatterPlotItem(size=2.0, pxMode=True)
        self.point_view.addItem(self.point_item)
        self.tabs.addTab(self.point_view, "三维截面与时间轨迹")
        self.section_view = pg.PlotWidget(self.tabs)
        self.section_view.setLabel("bottom", "Xg", units="mm")
        self.section_view.setLabel("left", "Zg", units="mm")
        self.section_curve = self.section_view.plot(pen=pg.mkPen("#46d6a0", width=2))
        self.tabs.addTab(self.section_view, "二维截面")
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self._control_panel())
        self.setCentralWidget(central)

    def _control_panel(self) -> QWidget:
        panel = QWidget(self)
        panel.setFixedWidth(330)
        layout = QVBoxLayout(panel)
        device_group = QGroupBox("相机", panel)
        device_layout = QVBoxLayout(device_group)
        self.device_combo = QComboBox(device_group)
        row = QHBoxLayout()
        self.refresh_button = QPushButton("刷新", device_group)
        self.connect_button = QPushButton("连接", device_group)
        self.disconnect_button = QPushButton("断开", device_group)
        row.addWidget(self.refresh_button)
        row.addWidget(self.connect_button)
        row.addWidget(self.disconnect_button)
        device_layout.addWidget(self.device_combo)
        device_layout.addLayout(row)
        layout.addWidget(device_group)

        settings = QGroupBox("采集参数（停流后应用）", panel)
        form = QFormLayout(settings)
        self.pixel_format = QComboBox(settings)
        self.pixel_format.addItems(["Mono12", "Mono8"])
        self.exposure = QDoubleSpinBox(settings)
        self.exposure.setRange(1.0, 1_000_000.0)
        self.exposure.setValue(1000.0)
        self.exposure.setSuffix(" μs")
        self.gain = QDoubleSpinBox(settings)
        self.gain.setRange(-20.0, 40.0)
        self.offset_x = _spin(settings, 0, 2447, 0)
        self.offset_y = _spin(settings, 0, 2047, 992)
        self.roi_width = _spin(settings, 1, 2448, 2448)
        self.roi_height = _spin(settings, 1, 2048, 64)
        form.addRow("像素格式", self.pixel_format)
        form.addRow("曝光", self.exposure)
        form.addRow("增益", self.gain)
        form.addRow("Offset X", self.offset_x)
        form.addRow("Offset Y", self.offset_y)
        form.addRow("宽度", self.roi_width)
        form.addRow("高度", self.roi_height)
        layout.addWidget(settings)

        stream_group = QGroupBox("在线运行", panel)
        stream_layout = QVBoxLayout(stream_group)
        row = QHBoxLayout()
        self.start_button = QPushButton("开始", stream_group)
        self.stop_button = QPushButton("停止", stream_group)
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        stream_layout.addLayout(row)
        self.snapshot_button = QPushButton("保存当前帧", stream_group)
        stream_layout.addWidget(self.snapshot_button)
        record_row = QHBoxLayout()
        self.record_count = _spin(stream_group, 1, 100000, 100)
        self.record_button = QPushButton("定长录制", stream_group)
        record_row.addWidget(self.record_count)
        record_row.addWidget(self.record_button)
        stream_layout.addLayout(record_row)
        layout.addWidget(stream_group)

        stats = QGroupBox("实时状态", panel)
        stats_layout = QFormLayout(stats)
        self.state_label = QLabel("未连接", stats)
        self.capture_fps_label = QLabel("—", stats)
        self.process_fps_label = QLabel("—", stats)
        self.display_fps_label = QLabel("—", stats)
        self.processing_ms_label = QLabel("—", stats)
        self.drop_label = QLabel("—", stats)
        self.record_label = QLabel("未录制", stats)
        for title, label in (
            ("状态", self.state_label),
            ("采集 fps", self.capture_fps_label),
            ("处理 fps", self.process_fps_label),
            ("显示 fps", self.display_fps_label),
            ("单帧处理", self.processing_ms_label),
            ("丢帧/覆盖", self.drop_label),
            ("录制", self.record_label),
        ):
            stats_layout.addRow(title, label)
        layout.addWidget(stats)
        note = QLabel("历史点仅表示最近 1 秒时间轨迹，不是连续扫描表面。", panel)
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return panel

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self.refresh_devices)
        self.connect_button.clicked.connect(self.connect_camera)
        self.disconnect_button.clicked.connect(self.disconnect_camera)
        self.start_button.clicked.connect(self.start_stream)
        self.stop_button.clicked.connect(self.stop_stream)
        self.snapshot_button.clicked.connect(self.save_snapshot)
        self.record_button.clicked.connect(self.start_recording)
        queued = Qt.ConnectionType.QueuedConnection
        self._controller.result_ready.connect(self._show_result, queued)
        self._controller.stats_updated.connect(self._show_stats, queued)
        self._controller.failed.connect(self._show_error, queued)
        self._controller.stopped.connect(lambda: self.state_label.setText("已连接"))

    def refresh_devices(self) -> None:
        self.device_combo.clear()
        try:
            devices = (
                [SyntheticCameraSession.device]
                if self._simulate
                else list_devices()
            )
        except Exception as error:
            self.state_label.setText("SDK 不可用")
            QMessageBox.warning(self, "相机 SDK", str(error))
            return
        for device in devices:
            self.device_combo.addItem(device.display_name, device)
        self.state_label.setText(f"发现 {len(devices)} 台设备")

    def _camera_config(self) -> CameraConfig:
        return CameraConfig(
            exposure_us=self.exposure.value(),
            gain_db=self.gain.value(),
            pixel_format=self.pixel_format.currentText(),
            offset_x=self.offset_x.value(),
            offset_y=self.offset_y.value(),
            width=self.roi_width.value(),
            height=self.roi_height.value(),
        )

    def connect_camera(self) -> None:
        if self._session is not None:
            return
        device: CameraDeviceInfo | None = self.device_combo.currentData()
        if device is None:
            QMessageBox.information(self, "未选择相机", "请先刷新并选择相机")
            return
        try:
            config = self._camera_config()
            self._session = (
                SyntheticCameraSession(config)
                if self._simulate
                else MvsCameraSession.open(device.serial_number, config)
            )
        except Exception as error:
            self._show_error(str(error))
            return
        self.state_label.setText("已连接")

    def disconnect_camera(self) -> None:
        self.stop_stream()
        if self._session is not None:
            try:
                self._session.close()
            except Exception as error:
                self._show_error(str(error))
            self._session = None
        self.state_label.setText("未连接")

    def start_stream(self) -> None:
        if self._session is None:
            self.connect_camera()
        if self._session is None or self._controller.running:
            return
        try:
            self._trail.clear()
            self._controller.start(self._session, self._pipeline, self._recorder)
            self.state_label.setText("取流中")
        except Exception as error:
            self._show_error(str(error))

    def stop_stream(self) -> None:
        if self._controller.running:
            self._controller.stop()

    def start_recording(self) -> None:
        if not self._controller.running or self._session is None:
            QMessageBox.information(self, "未取流", "请先连接相机并开始取流")
            return
        root = (
            self._config.output.directory / "online_recordings"
            if self._config.output is not None
            else Path(__file__).resolve().parents[1] / "output" / "online_recordings"
        )
        try:
            target = self._recorder.start(
                root, self.record_count.value(), self._session.config
            )
            self.record_label.setText(f"录制中 → {target.name}")
            self.state_label.setText("录制中")
        except Exception as error:
            self._show_error(str(error))

    def save_snapshot(self) -> None:
        if self._last_result is None:
            QMessageBox.information(self, "没有图像", "当前尚无可保存帧")
            return
        default_suffix = ".png" if self._last_result.frame.image.dtype == np.uint8 else ".tiff"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存当前帧",
            f"frame_{self._last_result.frame.camera_frame_number:06d}{default_suffix}",
            "图像 (*.png *.tif *.tiff)",
        )
        if path and not cv2.imwrite(path, self._last_result.frame.image):
            self._show_error(f"无法保存图像: {path}")

    def _show_result(self, result: FrameResult) -> None:
        self._last_result = result
        now = time.monotonic()
        if now - self._last_render_at < 0.075:
            return
        self._last_render_at = now
        while self._trail and now - self._trail[0][0] > 1.0:
            self._trail.popleft()
        current = result.points_ground
        if len(current):
            self._trail.append((now, current[::4].copy()))
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            first_image = self.image_item.image is None
            self.image_item.setImage(result.overlay_rgb, autoLevels=False)
            if first_image:
                self.image_view.autoRange()
        elif current_tab == 1:
            points: list[np.ndarray] = []
            colors: list[np.ndarray] = []
            for timestamp, cloud in self._trail:
                if not len(cloud):
                    continue
                age = min(1.0, (now - timestamp) / 1.0)
                color = np.tile(
                    [0.18, 0.82, 0.64, max(0.12, 1.0 - age)], (len(cloud), 1)
                )
                points.append(cloud.astype(np.float32, copy=False))
                colors.append(color.astype(np.float32))
            if len(current):
                points.append(current.astype(np.float32, copy=False))
                colors.append(
                    np.tile([0.95, 0.85, 0.20, 1.0], (len(current), 1)).astype(
                        np.float32
                    )
                )
            if points:
                self.point_item.setData(
                    pos=np.vstack(points), color=np.vstack(colors), size=2.0
                )
            else:
                self.point_item.setData(pos=np.empty((0, 3), dtype=np.float32))
        elif len(result.section_xz):
            self.section_curve.setData(
                result.section_xz[:, 0], result.section_xz[:, 1]
            )
        else:
            self.section_curve.setData([], [])
        self._displayed_frames += 1

    def _show_stats(self, stats: dict[str, float | int]) -> None:
        self.capture_fps_label.setText(f"{float(stats['capture_fps']):.1f}")
        self.process_fps_label.setText(f"{float(stats['process_fps']):.1f}")
        elapsed = max(time.monotonic() - self._display_started, 1e-9)
        self.display_fps_label.setText(f"{self._displayed_frames / elapsed:.1f}")
        self.processing_ms_label.setText(f"{float(stats['processing_ms']):.1f} ms")
        self.drop_label.setText(
            f"{int(stats['camera_gaps'])} / {int(stats['queue_overwrites'])}"
        )

    def _poll_recording(self) -> None:
        if self._recorder.active:
            return
        if self._recorder.error is not None:
            self.record_label.setText("失败")
            self._show_error(str(self._recorder.error))
            return
        result = self._recorder.result
        if result is not None and not self.record_label.text().startswith("完成"):
            self.record_label.setText(
                f"完成 {result.saved_frames} 帧，缺口 {result.detected_frame_gaps}"
            )
            if self._controller.running:
                self.state_label.setText("取流中")

    def _show_error(self, message: str) -> None:
        self.state_label.setText("错误")
        QMessageBox.critical(self, "在线相机错误", message)
        if self._controller.running:
            self._controller.stop()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.disconnect_camera()
        event.accept()


def _spin(parent: QWidget, minimum: int, maximum: int, value: int) -> QSpinBox:
    widget = QSpinBox(parent)
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    return widget
