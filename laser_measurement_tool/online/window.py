"""Standalone online camera window; reusable from the offline main tool."""

from __future__ import annotations

import threading
import time
from collections import deque
from enum import Enum, auto
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QVector3D
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QStackedLayout,
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
from laser.backends import AVAILABLE_METHODS

from .controller import OnlineController
from .fake_camera import SyntheticCameraSession
from .models import CameraConfig, CameraDeviceInfo, CapturedFrame, FrameResult
from .mvs_camera import MvsCameraSession, list_devices
from .pipeline import FramePipeline
from .recording import FrameRecorder


pg.setConfigOptions(imageAxisOrder="row-major")


class PointCloudGLViewWidget(gl.GLViewWidget):
    """GL view that reports camera changes for the orientation compass."""

    camera_changed = Signal()

    def setCameraPosition(self, *args, **kwargs) -> None:  # noqa: N802
        super().setCameraPosition(*args, **kwargs)
        self.camera_changed.emit()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().mouseMoveEvent(event)
        self.camera_changed.emit()

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().wheelEvent(event)
        self.camera_changed.emit()


class ConstrainedImageViewBox(pg.ViewBox):
    """Keep a zoomed image reachable while allowing bounded inspection."""

    def __init__(self) -> None:
        super().__init__()
        self._image_size: tuple[float, float] | None = None
        self._home_span: tuple[float, float] | None = None
        self.reset_callback = None

    def clear_image_constraints(self) -> None:
        self._image_size = None
        self._home_span = None
        self.setLimits(
            xMin=None,
            xMax=None,
            yMin=None,
            yMax=None,
            minXRange=None,
            maxXRange=None,
            minYRange=None,
            maxYRange=None,
        )

    def set_image_constraints(self, width: int, height: int) -> None:
        x_range, y_range = self.viewRange()
        self._image_size = (float(width), float(height))
        self._home_span = (
            x_range[1] - x_range[0],
            y_range[1] - y_range[0],
        )
        self.setLimits(
            minXRange=1.0,
            maxXRange=self._home_span[0],
            minYRange=1.0,
            maxYRange=self._home_span[1],
        )
        self._constrain_to_image()

    def translateBy(self, t=None, x=None, y=None) -> None:  # noqa: N802
        if self._image_size is None:
            super().translateBy(t=t, x=x, y=y)
            return
        if t is not None:
            x = t.x() if hasattr(t, "x") else t[0]
            y = t.y() if hasattr(t, "y") else t[1]
        x_range, y_range = self.viewRange()
        translated_x = (
            x_range[0] + float(x or 0.0),
            x_range[1] + float(x or 0.0),
        )
        translated_y = (
            y_range[0] + float(y or 0.0),
            y_range[1] + float(y or 0.0),
        )
        self._set_bounded_range(translated_x, translated_y)

    def scaleBy(self, s=None, center=None, x=None, y=None) -> None:  # noqa: N802
        if self._image_size is None or self._home_span is None:
            super().scaleBy(s=s, center=center, x=x, y=y)
            return
        if s is not None:
            x, y = s[0], s[1]
        if x is None and y is None:
            return
        if self.state["aspectLocked"] is not False:
            scale = float(y if y is not None else x)
            x = y = scale
        x_scale = float(x if x is not None else 1.0)
        y_scale = float(y if y is not None else 1.0)
        x_range, y_range = self.viewRange()
        current_span = (
            x_range[1] - x_range[0],
            y_range[1] - y_range[0],
        )
        if x_scale > 1.0 or y_scale > 1.0:
            maximum_scale = min(
                self._home_span[0] / current_span[0],
                self._home_span[1] / current_span[1],
            )
            x_scale = min(x_scale, maximum_scale)
            y_scale = min(y_scale, maximum_scale)
        if center is None:
            centre_x = (x_range[0] + x_range[1]) * 0.5
            centre_y = (y_range[0] + y_range[1]) * 0.5
        else:
            centre_x = center.x() if hasattr(center, "x") else center[0]
            centre_y = center.y() if hasattr(center, "y") else center[1]
        scaled_x = (
            centre_x + (x_range[0] - centre_x) * x_scale,
            centre_x + (x_range[1] - centre_x) * x_scale,
        )
        scaled_y = (
            centre_y + (y_range[0] - centre_y) * y_scale,
            centre_y + (y_range[1] - centre_y) * y_scale,
        )
        self._set_bounded_range(scaled_x, scaled_y)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self.reset_callback is not None:
            self.reset_callback()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _constrain_to_image(self) -> None:
        if self._image_size is None:
            return
        x_range, y_range = self.viewRange()
        self._set_bounded_range(x_range, y_range)

    def _set_bounded_range(self, x_range, y_range) -> None:
        if self._image_size is None:
            return
        width, height = self._image_size
        bounded_x = _bounded_view_range(x_range, width)
        bounded_y = _bounded_view_range(y_range, height)
        current_x, current_y = self.viewRange()
        if bounded_x != tuple(current_x) or bounded_y != tuple(current_y):
            self.setRange(xRange=bounded_x, yRange=bounded_y, padding=0)


class OnlineState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    STARTING = auto()
    STREAMING = auto()
    STOPPING = auto()
    ERROR = auto()


class OnlineCameraWindow(QMainWindow):
    """Connect, acquire, process, inspect, snapshot, and record camera frames."""

    def __init__(
        self,
        config: AppConfig,
        *,
        simulate: bool = False,
        extraction_method: str | None = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._simulate = simulate
        self._initial_extraction_method = (
            extraction_method or config.extraction_method
        )
        self._pipeline = FramePipeline(config, self._initial_extraction_method)
        self._controller = OnlineController(self)
        self._recorder = FrameRecorder()
        self._session: MvsCameraSession | SyntheticCameraSession | None = None
        self._last_result: FrameResult | None = None
        self._trail: deque[tuple[float, np.ndarray]] = deque(maxlen=30)
        self._displayed_frames = 0
        self._display_started = time.monotonic()
        self._last_render_at = 0.0
        self._raw_view_shape: tuple[int, int] | None = None
        self._extracted_view_shape: tuple[int, int] | None = None
        self._section_x_bounds: tuple[float, float] | None = None
        self._section_points = np.empty((0, 2), dtype=np.float64)
        self._section_points_ground = np.empty((0, 3), dtype=np.float64)
        self._online_state = OnlineState.DISCONNECTED
        self._device_count = 0
        self._pending_disconnect = False
        self._stop_due_to_error = False
        self._shutdown_thread: threading.Thread | None = None
        self._closing = False
        self._build_ui()
        self._connect_signals()
        self._set_online_state(OnlineState.DISCONNECTED)
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
        image_tab = QWidget(self.tabs)
        image_layout = QVBoxLayout(image_tab)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)
        image_toolbar = QFrame(image_tab)
        image_toolbar.setObjectName("imageToolbar")
        image_toolbar_layout = QHBoxLayout(image_toolbar)
        image_toolbar_layout.setContentsMargins(12, 7, 12, 7)
        image_toolbar_layout.setSpacing(6)
        image_title = QLabel("图像预览", image_toolbar)
        image_title.setObjectName("imageTitle")
        image_toolbar_layout.addWidget(image_title)
        image_toolbar_layout.addSpacing(12)
        image_toolbar_layout.addWidget(QLabel("视野", image_toolbar))
        self.image_view_mode_buttons = QButtonGroup(image_tab)
        self.image_view_mode_buttons.setExclusive(True)
        self.image_width_mode_button = QPushButton("铺满宽度", image_toolbar)
        self.image_fit_mode_button = QPushButton("整图适配", image_toolbar)
        for button, mode in (
            (self.image_width_mode_button, "width"),
            (self.image_fit_mode_button, "fit"),
        ):
            button.setCheckable(True)
            button.setProperty("imageViewMode", True)
            button.setFixedHeight(28)
            button.clicked.connect(
                lambda _checked=False, name=mode: self._set_image_view_mode(name)
            )
            self.image_view_mode_buttons.addButton(button)
            image_toolbar_layout.addWidget(button)
        self.image_width_mode_button.setChecked(True)
        self._image_view_mode = "width"
        image_toolbar_layout.addStretch(1)
        self.image_reset_button = QPushButton("复位视野", image_toolbar)
        self.image_reset_button.setFixedHeight(28)
        self.image_reset_button.setToolTip("恢复两个预览框的初始视野；也可双击图像")
        self.image_reset_button.clicked.connect(self._reset_image_views)
        image_toolbar_layout.addWidget(self.image_reset_button)
        image_layout.addWidget(image_toolbar)

        image_splitter = QSplitter(Qt.Orientation.Vertical, image_tab)
        raw_view_box = ConstrainedImageViewBox()
        raw_view_box.reset_callback = self._reset_image_views
        self.raw_image_view = pg.PlotWidget(
            image_splitter, viewBox=raw_view_box
        )
        self.raw_image_view.setTitle("原始图像")
        self.raw_image_view.setBackground("#25282d")
        self.raw_image_view.hideAxis("left")
        self.raw_image_view.hideAxis("bottom")
        self.raw_image_view.setAspectLocked(True)
        self.raw_image_view.getViewBox().invertY(True)
        self.raw_image_view.getViewBox().setMenuEnabled(False)
        self.raw_image_item = pg.ImageItem()
        self.raw_image_view.addItem(self.raw_image_item)
        self.raw_image_boundary = pg.PlotDataItem(
            pen=pg.mkPen("#aeb4bc", width=1)
        )
        self.raw_image_boundary.setZValue(10)
        self.raw_image_view.addItem(self.raw_image_boundary)
        extracted_view_box = ConstrainedImageViewBox()
        extracted_view_box.reset_callback = self._reset_image_views
        self.extracted_image_view = pg.PlotWidget(
            image_splitter, viewBox=extracted_view_box
        )
        self.extracted_image_view.setTitle("激光中心提取")
        self.extracted_image_view.setBackground("#25282d")
        self.extracted_image_view.hideAxis("left")
        self.extracted_image_view.hideAxis("bottom")
        self.extracted_image_view.setAspectLocked(True)
        self.extracted_image_view.getViewBox().invertY(True)
        self.extracted_image_view.getViewBox().setMenuEnabled(False)
        self.extracted_image_item = pg.ImageItem()
        self.extracted_image_view.addItem(self.extracted_image_item)
        self.extracted_image_boundary = pg.PlotDataItem(
            pen=pg.mkPen("#aeb4bc", width=1)
        )
        self.extracted_image_boundary.setZValue(10)
        self.extracted_image_view.addItem(self.extracted_image_boundary)
        image_splitter.addWidget(self.raw_image_view)
        image_splitter.addWidget(self.extracted_image_view)
        image_splitter.setStretchFactor(0, 1)
        image_splitter.setStretchFactor(1, 1)
        image_splitter.setChildrenCollapsible(False)
        image_layout.addWidget(image_splitter, 1)
        image_tab.setStyleSheet(
            """
            QFrame#imageToolbar {
                background: #f8fafc;
                border-bottom: 1px solid #cbd3dc;
            }
            QLabel#imageTitle { font-weight: 600; color: #20262d; }
            QPushButton[imageViewMode="true"] {
                min-width: 72px;
                padding: 2px 9px;
                border: 1px solid #b8c1cb;
                border-radius: 4px;
                background: #ffffff;
            }
            QPushButton[imageViewMode="true"]:checked {
                color: #174ea6;
                border-color: #79a7e3;
                background: #e7f0fc;
            }
            """
        )
        self.tabs.addTab(image_tab, "图像与条纹")
        point_tab = QWidget(self.tabs)
        point_layout = QVBoxLayout(point_tab)
        point_layout.setContentsMargins(0, 0, 0, 0)
        point_layout.setSpacing(0)

        point_toolbar = QFrame(point_tab)
        point_toolbar.setObjectName("pointToolbar")
        toolbar_layout = QHBoxLayout(point_toolbar)
        toolbar_layout.setContentsMargins(12, 7, 12, 7)
        toolbar_layout.setSpacing(6)
        point_title = QLabel("三维分析", point_toolbar)
        point_title.setObjectName("pointTitle")
        toolbar_layout.addWidget(point_title)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(QLabel("视角", point_toolbar))
        self.point_view_buttons = QButtonGroup(point_tab)
        self.point_view_buttons.setExclusive(True)
        for preset, title in (
            ("perspective", "透视"),
            ("top", "俯视"),
            ("front", "前视"),
            ("side", "侧视"),
        ):
            button = QPushButton(title, point_toolbar)
            button.setCheckable(True)
            button.setProperty("viewPreset", True)
            button.setFixedHeight(28)
            button.clicked.connect(
                lambda _checked=False, name=preset: self._set_point_view_preset(
                    name
                )
            )
            self.point_view_buttons.addButton(button)
            toolbar_layout.addWidget(button)
            if preset == "perspective":
                button.setChecked(True)
        toolbar_layout.addStretch(1)
        self.grid_checkbox = QCheckBox("地面网格", point_toolbar)
        self.grid_checkbox.setChecked(True)
        self.origin_checkbox = QCheckBox("原点标记", point_toolbar)
        self.origin_checkbox.setChecked(True)
        self.compass_checkbox = QCheckBox("方向罗盘", point_toolbar)
        self.compass_checkbox.setChecked(True)
        self.trail_checkbox = QCheckBox("时间轨迹", point_toolbar)
        self.trail_checkbox.setChecked(True)
        self.fit_points_button = QPushButton("适配点云", point_toolbar)
        self.fit_points_button.setFixedHeight(28)
        toolbar_layout.addWidget(self.grid_checkbox)
        toolbar_layout.addWidget(self.origin_checkbox)
        toolbar_layout.addWidget(self.compass_checkbox)
        toolbar_layout.addWidget(self.trail_checkbox)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(self.fit_points_button)
        point_layout.addWidget(point_toolbar)

        point_scene = QWidget(point_tab)
        point_stack = QStackedLayout(point_scene)
        point_stack.setContentsMargins(0, 0, 0, 0)
        point_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.point_view = PointCloudGLViewWidget(point_scene)
        self.point_view.setBackgroundColor("#eef1f4")
        self.point_view.setCameraPosition(
            distance=560,
            elevation=24,
            azimuth=-60,
        )
        self._add_ground_reference()
        self.trail_point_item = gl.GLScatterPlotItem(
            size=2.0,
            pxMode=True,
            glOptions="translucent",
        )
        self.current_point_item = gl.GLScatterPlotItem(
            size=4.0,
            pxMode=True,
            glOptions="translucent",
        )
        self.point_view.addItem(self.trail_point_item)
        self.point_view.addItem(self.current_point_item)
        self._height_colormap = pg.colormap.get("viridis")
        point_stack.addWidget(self.point_view)

        compass_overlay = QWidget(point_scene)
        compass_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        compass_layout = QVBoxLayout(compass_overlay)
        compass_layout.setContentsMargins(0, 0, 14, 14)
        compass_layout.addStretch(1)
        compass_row = QHBoxLayout()
        compass_row.addStretch(1)
        compass_frame = QFrame(compass_overlay)
        self.orientation_compass = compass_frame
        compass_frame.setObjectName("orientationCompass")
        compass_frame.setFixedSize(138, 138)
        compass_frame_layout = QVBoxLayout(compass_frame)
        compass_frame_layout.setContentsMargins(1, 1, 1, 1)
        self.orientation_view = gl.GLViewWidget(compass_frame)
        self.orientation_view.setBackgroundColor("#eef1f4")
        self.orientation_view.setCameraPosition(
            distance=3.8,
            elevation=24,
            azimuth=-60,
        )
        compass_frame_layout.addWidget(self.orientation_view)
        self._add_orientation_gizmo()
        compass_row.addWidget(compass_frame)
        compass_layout.addLayout(compass_row)
        point_stack.addWidget(compass_overlay)
        point_stack.setCurrentWidget(compass_overlay)
        point_layout.addWidget(point_scene, 1)

        point_footer = QFrame(point_tab)
        point_footer.setObjectName("pointFooter")
        footer_layout = QHBoxLayout(point_footer)
        footer_layout.setContentsMargins(12, 7, 12, 7)
        footer_layout.setSpacing(14)
        self.point_count_label = QLabel("当前截面 0 点", point_footer)
        self.point_range_label = QLabel(
            "Xg --  |  Yg --  |  Zg --", point_footer
        )
        self.height_min_label = QLabel("--", point_footer)
        self.height_max_label = QLabel("--", point_footer)
        height_gradient = QFrame(point_footer)
        height_gradient.setObjectName("heightGradient")
        height_gradient.setFixedSize(110, 9)
        self.point_compensation_label = QLabel(point_footer)
        self._set_compensation_status()
        footer_layout.addWidget(self.point_count_label)
        footer_layout.addWidget(self.point_range_label, 1)
        footer_layout.addWidget(QLabel("Zg 高度", point_footer))
        footer_layout.addWidget(self.height_min_label)
        footer_layout.addWidget(height_gradient)
        footer_layout.addWidget(self.height_max_label)
        trail_legend = QLabel(
            '<span style="color:#1266b3; font-size:16px;">&#8226;</span> '
            "1 s 轨迹",
            point_footer,
        )
        footer_layout.addWidget(trail_legend)
        footer_layout.addWidget(self.point_compensation_label)
        point_layout.addWidget(point_footer)

        point_tab.setStyleSheet(
            """
            QFrame#pointToolbar, QFrame#pointFooter {
                background: #f8fafc;
                border-color: #cbd3dc;
            }
            QFrame#pointToolbar { border-bottom: 1px solid #cbd3dc; }
            QFrame#pointFooter { border-top: 1px solid #cbd3dc; }
            QFrame#orientationCompass {
                background: #eef1f4;
                border: none;
            }
            QLabel#pointTitle { font-weight: 600; color: #20262d; }
            QPushButton[viewPreset="true"] {
                min-width: 48px;
                padding: 2px 9px;
                border: 1px solid #b8c1cb;
                border-radius: 4px;
                background: #ffffff;
            }
            QPushButton[viewPreset="true"]:checked {
                color: #174ea6;
                border-color: #79a7e3;
                background: #e7f0fc;
            }
            QFrame#heightGradient {
                border: 1px solid #9da7b2;
                border-radius: 2px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #440154, stop:0.25 #3b528b,
                    stop:0.5 #21918c, stop:0.75 #5ec962,
                    stop:1 #fde725
                );
            }
            """
        )
        self.grid_checkbox.toggled.connect(self.ground_grid.setVisible)
        self.origin_checkbox.toggled.connect(self._set_origin_visible)
        self.compass_checkbox.toggled.connect(
            self.orientation_compass.setVisible
        )
        self.trail_checkbox.toggled.connect(self.trail_point_item.setVisible)
        self.fit_points_button.clicked.connect(self._fit_point_cloud)
        self.point_view.camera_changed.connect(self._sync_orientation_gizmo)
        self.tabs.addTab(point_tab, "三维截面与时间轨迹")

        section_tab = QWidget(self.tabs)
        section_layout = QVBoxLayout(section_tab)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(0)
        section_toolbar = QFrame(section_tab)
        section_toolbar.setObjectName("sectionToolbar")
        section_toolbar_layout = QHBoxLayout(section_toolbar)
        section_toolbar_layout.setContentsMargins(12, 7, 12, 7)
        section_toolbar_layout.setSpacing(10)
        section_title = QLabel("截面分析", section_toolbar)
        section_title.setObjectName("sectionTitle")
        section_toolbar_layout.addWidget(section_title)
        self.section_grid_checkbox = QCheckBox("网格", section_toolbar)
        self.section_grid_checkbox.setChecked(True)
        self.section_zero_checkbox = QCheckBox("零基准", section_toolbar)
        self.section_zero_checkbox.setChecked(True)
        self.section_crosshair_checkbox = QCheckBox("十字游标", section_toolbar)
        self.section_crosshair_checkbox.setChecked(True)
        self.section_auto_height_checkbox = QCheckBox("自动高度", section_toolbar)
        self.section_auto_height_checkbox.setChecked(True)
        self.section_max_dx = _double_spin(
            section_toolbar, 0.1, 100.0, 2.0, " mm"
        )
        self.section_max_dz = _double_spin(
            section_toolbar, 0.1, 100.0, 3.0, " mm"
        )
        self.section_max_distance = _double_spin(
            section_toolbar, 0.1, 100.0, 4.0, " mm"
        )
        for control in (
            self.section_max_dx,
            self.section_max_dz,
            self.section_max_distance,
        ):
            control.setDecimals(1)
            control.setSingleStep(0.5)
            control.setFixedWidth(82)
        self.section_fit_button = QPushButton("适配截面", section_toolbar)
        self.section_fit_button.setFixedHeight(28)
        section_toolbar_layout.addWidget(QLabel("断线阈值", section_toolbar))
        section_toolbar_layout.addWidget(QLabel("ΔXg", section_toolbar))
        section_toolbar_layout.addWidget(self.section_max_dx)
        section_toolbar_layout.addWidget(QLabel("ΔZg", section_toolbar))
        section_toolbar_layout.addWidget(self.section_max_dz)
        section_toolbar_layout.addWidget(QLabel("3D", section_toolbar))
        section_toolbar_layout.addWidget(self.section_max_distance)
        section_toolbar_layout.addStretch(1)
        section_toolbar_layout.addWidget(self.section_grid_checkbox)
        section_toolbar_layout.addWidget(self.section_zero_checkbox)
        section_toolbar_layout.addWidget(self.section_crosshair_checkbox)
        section_toolbar_layout.addWidget(self.section_auto_height_checkbox)
        section_toolbar_layout.addSpacing(8)
        section_toolbar_layout.addWidget(self.section_fit_button)
        section_layout.addWidget(section_toolbar)

        self.section_view = pg.PlotWidget(section_tab)
        self.section_view.setBackground("#eef1f4")
        self.section_view.setLabel("bottom", "Xg", units="mm")
        self.section_view.setLabel("left", "Zg", units="mm")
        self.section_view.showGrid(x=True, y=True, alpha=0.22)
        axis_pen = pg.mkPen("#687482", width=1)
        text_pen = pg.mkPen("#28313a")
        for axis_name in ("bottom", "left"):
            axis = self.section_view.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)
            axis.setTickFont(QFont("Segoe UI", 10))
        self.section_curve = self.section_view.plot(
            pen=pg.mkPen((0, 127, 123, 155), width=1.4),
        )
        self.section_curve.setZValue(1)
        self.section_scatter = pg.ScatterPlotItem(
            size=4.0,
            pen=pg.mkPen((0, 91, 88, 210), width=0.7),
            brush=pg.mkBrush(0, 154, 148, 205),
            pxMode=True,
        )
        self.section_scatter.setZValue(3)
        self.section_view.addItem(self.section_scatter)
        self.section_zero_line = pg.InfiniteLine(
            pos=0.0,
            angle=0,
            pen=pg.mkPen(
                "#657585", width=1.3, style=Qt.PenStyle.DashLine
            ),
        )
        self.section_zero_line.setZValue(2)
        self.section_view.addItem(self.section_zero_line)
        crosshair_pen = pg.mkPen(
            "#31475e", width=1, style=Qt.PenStyle.DashLine
        )
        self.section_crosshair_x = pg.InfiniteLine(
            angle=90, movable=False, pen=crosshair_pen
        )
        self.section_crosshair_z = pg.InfiniteLine(
            angle=0, movable=False, pen=crosshair_pen
        )
        self.section_crosshair_x.setZValue(10)
        self.section_crosshair_z.setZValue(10)
        self.section_crosshair_x.hide()
        self.section_crosshair_z.hide()
        self.section_view.addItem(self.section_crosshair_x, ignoreBounds=True)
        self.section_view.addItem(self.section_crosshair_z, ignoreBounds=True)
        section_layout.addWidget(self.section_view, 1)

        section_footer = QFrame(section_tab)
        section_footer.setObjectName("sectionFooter")
        section_footer_layout = QHBoxLayout(section_footer)
        section_footer_layout.setContentsMargins(12, 7, 12, 7)
        section_footer_layout.setSpacing(16)
        self.section_count_label = QLabel("截面 0 点", section_footer)
        self.section_range_label = QLabel(
            "Xg --  |  Zg --", section_footer
        )
        self.section_extrema_label = QLabel(
            "最低 --  |  最高 --", section_footer
        )
        self.section_cursor_label = QLabel(
            "游标 Xg --  Zg --", section_footer
        )
        self.section_cursor_label.setObjectName("sectionCursor")
        section_footer_layout.addWidget(self.section_count_label)
        section_footer_layout.addWidget(self.section_range_label, 1)
        section_footer_layout.addWidget(self.section_extrema_label)
        section_footer_layout.addWidget(self.section_cursor_label)
        section_layout.addWidget(section_footer)

        section_tab.setStyleSheet(
            """
            QFrame#sectionToolbar, QFrame#sectionFooter {
                background: #f8fafc;
                border-color: #cbd3dc;
            }
            QFrame#sectionToolbar { border-bottom: 1px solid #cbd3dc; }
            QFrame#sectionFooter { border-top: 1px solid #cbd3dc; }
            QLabel#sectionTitle { font-weight: 600; color: #20262d; }
            QLabel#sectionCursor { color: #174ea6; font-weight: 600; }
            """
        )
        self.section_grid_checkbox.toggled.connect(
            self._set_section_grid_visible
        )
        self.section_zero_checkbox.toggled.connect(
            self.section_zero_line.setVisible
        )
        self.section_crosshair_checkbox.toggled.connect(
            self._set_section_crosshair_enabled
        )
        self.section_auto_height_checkbox.toggled.connect(
            self._set_section_auto_height
        )
        self.section_max_dx.valueChanged.connect(
            self._refresh_section_connections
        )
        self.section_max_dz.valueChanged.connect(
            self._refresh_section_connections
        )
        self.section_max_distance.valueChanged.connect(
            self._refresh_section_connections
        )
        self.section_fit_button.clicked.connect(self._fit_section_view)
        self.section_view.getViewBox().sigRangeChangedManually.connect(
            self._on_section_range_changed_manually
        )
        self._section_mouse_proxy = pg.SignalProxy(
            self.section_view.scene().sigMouseMoved,
            rateLimit=30,
            slot=self._on_section_mouse_moved,
        )
        self.tabs.addTab(section_tab, "二维截面")
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self._control_panel())
        self.setCentralWidget(central)

    def _add_ground_reference(self) -> None:
        self.ground_grid = gl.GLGridItem(
            color=(88, 100, 112, 72),
            antialias=True,
            glOptions="translucent",
        )
        self.ground_grid.setSize(x=500, y=300)
        self.ground_grid.setSpacing(50, 50)
        self.ground_grid.setDepthValue(-10)
        self.point_view.addItem(self.ground_grid)

        self.ground_origin_cross = gl.GLLinePlotItem(
            pos=np.asarray(
                [
                    (-9.0, 0.0, 0.15),
                    (9.0, 0.0, 0.15),
                    (0.0, -9.0, 0.15),
                    (0.0, 9.0, 0.15),
                ],
                dtype=np.float32,
            ),
            color=(0.18, 0.21, 0.24, 0.9),
            width=2.0,
            antialias=True,
            mode="lines",
            glOptions="translucent",
        )
        self.ground_origin = gl.GLScatterPlotItem(
            pos=np.zeros((1, 3), dtype=np.float32),
            color=np.asarray([[0.08, 0.09, 0.11, 1.0]], dtype=np.float32),
            size=7.0,
            pxMode=True,
            glOptions="opaque",
        )
        self.ground_origin_items = (
            self.ground_origin_cross,
            self.ground_origin,
        )
        self.point_view.addItem(self.ground_origin_cross)
        self.point_view.addItem(self.ground_origin)

    def _add_orientation_gizmo(self) -> None:
        axis_specs = (
            (
                "Xg",
                (1.2, 0.0, 0.0),
                ((-0.18, 0.08, 0.0), (-0.18, -0.08, 0.0)),
                (0.82, 0.12, 0.12, 1.0),
            ),
            (
                "Yg",
                (0.0, 1.2, 0.0),
                ((0.08, -0.18, 0.0), (-0.08, -0.18, 0.0)),
                (0.08, 0.55, 0.22, 1.0),
            ),
            (
                "Zg",
                (0.0, 0.0, 1.2),
                ((0.08, 0.0, -0.18), (-0.08, 0.0, -0.18)),
                (0.08, 0.30, 0.82, 1.0),
            ),
        )
        label_font = QFont("Segoe UI", 9)
        label_font.setBold(True)
        self.orientation_axes: list[gl.GLLinePlotItem] = []
        self.orientation_labels: list[gl.GLTextItem] = []
        for label, endpoint, arrow_offsets, color in axis_specs:
            endpoint_array = np.asarray(endpoint, dtype=np.float32)
            vertices = np.asarray(
                [
                    (0.0, 0.0, 0.0),
                    endpoint_array,
                    endpoint_array,
                    endpoint_array + arrow_offsets[0],
                    endpoint_array,
                    endpoint_array + arrow_offsets[1],
                ],
                dtype=np.float32,
            )
            axis = gl.GLLinePlotItem(
                pos=vertices,
                color=color,
                width=3.0,
                antialias=True,
                mode="lines",
                glOptions="opaque",
            )
            text = gl.GLTextItem(
                pos=endpoint_array * 1.05,
                color=tuple(int(channel * 255) for channel in color),
                text=label,
                font=label_font,
                glOptions="translucent",
            )
            self.orientation_axes.append(axis)
            self.orientation_labels.append(text)
            self.orientation_view.addItem(axis)
            self.orientation_view.addItem(text)
        origin = gl.GLScatterPlotItem(
            pos=np.zeros((1, 3), dtype=np.float32),
            color=np.asarray([[0.12, 0.14, 0.17, 1.0]], dtype=np.float32),
            size=6.0,
            pxMode=True,
            glOptions="opaque",
        )
        self.orientation_view.addItem(origin)

    def _set_origin_visible(self, visible: bool) -> None:
        for item in self.ground_origin_items:
            item.setVisible(visible)

    def _sync_orientation_gizmo(self) -> None:
        camera = self.point_view.cameraParams()
        self.orientation_view.setCameraPosition(
            pos=QVector3D(0.0, 0.0, 0.0),
            distance=3.8,
            elevation=float(camera["elevation"]),
            azimuth=float(camera["azimuth"]),
        )

    def _set_compensation_status(self) -> None:
        compensation = self._pipeline.package.calibration.get(
            "ground_u_compensation"
        )
        if compensation is None:
            self.point_compensation_label.setText("Zg 补偿 未启用")
            self.point_compensation_label.setStyleSheet("color: #6b7280;")
            self.point_compensation_label.setToolTip(
                "当前标定包没有 ground_u_compensation"
            )
            return
        bias = np.asarray(compensation["bias_mm"], dtype=np.float64)
        z_offset = float(compensation.get("z_offset_mm", 0.0))
        self.point_compensation_label.setText("Zg 补偿 已应用")
        self.point_compensation_label.setStyleSheet(
            "color: #167344; font-weight: 600;"
        )
        self.point_compensation_label.setToolTip(
            "Zg = Zg_raw - bias(u) - z_offset\n"
            f"bias 范围：{bias.min():.3f} ~ {bias.max():.3f} mm\n"
            f"z_offset：{z_offset:.3f} mm"
        )

    def _set_point_view_preset(self, preset: str) -> None:
        camera = {
            "perspective": (24.0, -60.0),
            "top": (89.9, -90.0),
            "front": (0.0, -90.0),
            "side": (0.0, 0.0),
        }
        elevation, azimuth = camera[preset]
        self.point_view.setCameraPosition(
            pos=QVector3D(0.0, 0.0, 20.0),
            distance=560.0,
            elevation=elevation,
            azimuth=azimuth,
        )

    def _fit_point_cloud(self) -> None:
        if self._last_result is None or not len(
            self._last_result.points_ground
        ):
            return
        points = np.asarray(
            self._last_result.points_ground, dtype=np.float64
        )
        points = points[np.isfinite(points).all(axis=1)]
        if not len(points):
            return
        minimum = points.min(axis=0)
        maximum = points.max(axis=0)
        centre = (minimum + maximum) * 0.5
        span = max(float(np.max(maximum - minimum)), 160.0)
        self.point_view.setCameraPosition(
            pos=QVector3D(*(float(value) for value in centre)),
            distance=min(max(span * 1.45, 280.0), 1800.0),
        )

    def _update_point_summary(self, points_ground: np.ndarray) -> None:
        points = np.asarray(points_ground, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3:
            points = np.empty((0, 3), dtype=np.float64)
        points = points[np.isfinite(points).all(axis=1)]
        if not len(points):
            self.point_count_label.setText("当前截面 0 点")
            self.point_range_label.setText("Xg --  |  Yg --  |  Zg --")
            self.height_min_label.setText("--")
            self.height_max_label.setText("--")
            return
        minimum = points.min(axis=0)
        maximum = points.max(axis=0)
        self.point_count_label.setText(f"当前截面 {len(points)} 点")
        self.point_range_label.setText(
            f"Xg {minimum[0]:.1f} ~ {maximum[0]:.1f} mm  |  "
            f"Yg {minimum[1]:.1f} ~ {maximum[1]:.1f} mm  |  "
            f"Zg {minimum[2]:.1f} ~ {maximum[2]:.1f} mm"
        )
        self.height_min_label.setText(f"{minimum[2]:.1f}")
        self.height_max_label.setText(f"{maximum[2]:.1f} mm")

    def _height_colors(self, points_ground: np.ndarray) -> np.ndarray:
        zg = np.asarray(points_ground[:, 2], dtype=np.float64)
        minimum = float(zg.min())
        maximum = float(zg.max())
        if maximum > minimum:
            normalized = (zg - minimum) / (maximum - minimum)
        else:
            normalized = np.full(len(zg), 0.5, dtype=np.float64)
        return np.ascontiguousarray(
            self._height_colormap.map(normalized, mode="float"),
            dtype=np.float32,
        )

    def _set_section_grid_visible(self, visible: bool) -> None:
        self.section_view.showGrid(x=visible, y=visible, alpha=0.22)

    def _set_section_crosshair_enabled(self, enabled: bool) -> None:
        if enabled:
            return
        self.section_crosshair_x.hide()
        self.section_crosshair_z.hide()
        self.section_cursor_label.setText("游标 Xg --  Zg --")

    def _set_section_auto_height(self, enabled: bool) -> None:
        self.section_view.getViewBox().enableAutoRange(
            axis=pg.ViewBox.YAxis,
            enable=enabled,
        )

    def _fit_section_view(self) -> None:
        if self._section_x_bounds is not None:
            lower, upper = self._section_x_bounds
            self.section_view.getViewBox().setXRange(
                lower, upper, padding=0
            )
        if not len(self._section_points):
            return
        minimum = float(self._section_points[:, 1].min())
        maximum = float(self._section_points[:, 1].max())
        span = max(maximum - minimum, 1.0)
        padding = span * 0.08
        self.section_view.getViewBox().setYRange(
            minimum - padding,
            maximum + padding,
            padding=0,
        )
        self.section_auto_height_checkbox.setChecked(True)
        self._set_section_auto_height(True)

    def _on_section_range_changed_manually(
        self, changed_axes: tuple[bool, bool]
    ) -> None:
        if changed_axes[1] and self.section_auto_height_checkbox.isChecked():
            self.section_auto_height_checkbox.setChecked(False)

    def _reset_section_view(self) -> None:
        self._section_x_bounds = None
        self._section_points = np.empty((0, 2), dtype=np.float64)
        self._section_points_ground = np.empty((0, 3), dtype=np.float64)
        self.section_curve.setData([], [])
        self.section_scatter.setData([], [])
        view_box = self.section_view.getViewBox()
        view_box.setLimits(xMin=None, xMax=None, maxXRange=None)
        view_box.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        view_box.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        self.section_auto_height_checkbox.setChecked(True)
        self.section_count_label.setText("截面 0 点")
        self.section_range_label.setText("Xg --  |  Zg --")
        self.section_extrema_label.setText("最低 --  |  最高 --")
        self._set_section_crosshair_enabled(False)

    def _update_section_view(self, points_ground: np.ndarray) -> None:
        ground = np.asarray(points_ground, dtype=np.float64)
        if ground.ndim != 2 or ground.shape[1] != 3:
            ground = np.empty((0, 3), dtype=np.float64)
        ground = ground[np.isfinite(ground).all(axis=1)]
        self._section_points_ground = np.ascontiguousarray(ground)
        points = ground[:, (0, 2)]
        self._section_points = np.ascontiguousarray(points)
        if not len(points):
            self.section_curve.setData([], [])
            self.section_scatter.setData([], [])
            self.section_count_label.setText("截面 0 点")
            self.section_range_label.setText("Xg --  |  Zg --")
            self.section_extrema_label.setText("最低 --  |  最高 --")
            return

        self.section_scatter.setData(x=points[:, 0], y=points[:, 1])
        self._refresh_section_connections()
        minimum = points.min(axis=0)
        maximum = points.max(axis=0)
        self.section_range_label.setText(
            f"Xg {minimum[0]:.1f} ~ {maximum[0]:.1f} mm  |  "
            f"Zg {minimum[1]:.1f} ~ {maximum[1]:.1f} mm"
        )
        self.section_extrema_label.setText(
            f"最低 {minimum[1]:.1f} mm  |  最高 {maximum[1]:.1f} mm"
        )
        if self._section_x_bounds is None:
            self._set_section_x_limits(minimum[0], maximum[0])
        if self.section_auto_height_checkbox.isChecked():
            self.section_view.getViewBox().enableAutoRange(
                axis=pg.ViewBox.YAxis,
                enable=True,
            )

    def _refresh_section_connections(self) -> None:
        points = self._section_points
        if not len(points):
            self.section_curve.setData([], [])
            self.section_count_label.setText("截面 0 点")
            return
        connections = _section_connection_mask(
            self._section_points_ground,
            max_dx=self.section_max_dx.value(),
            max_dz=self.section_max_dz.value(),
            max_distance=self.section_max_distance.value(),
        )
        self.section_curve.setData(
            points[:, 0],
            points[:, 1],
            connect=connections,
            skipFiniteCheck=True,
        )
        segment_count = 1 + int(np.count_nonzero(connections[:-1] == 0))
        self.section_count_label.setText(
            f"截面 {len(points)} 点 · {segment_count} 段"
        )

    def _set_section_x_limits(self, minimum: float, maximum: float) -> None:
        interval = 10.0
        lower = float(np.floor(minimum / interval) * interval)
        upper = float(np.ceil(maximum / interval) * interval)
        if upper <= lower:
            centre = (minimum + maximum) * 0.5
            lower = centre - interval * 0.5
            upper = centre + interval * 0.5
        self._section_x_bounds = (lower, upper)
        view_box = self.section_view.getViewBox()
        view_box.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        view_box.setLimits(
            xMin=lower,
            xMax=upper,
            maxXRange=upper - lower,
        )
        view_box.setXRange(lower, upper, padding=0)

    def _on_section_mouse_moved(self, event: tuple[object, ...]) -> None:
        if (
            not self.section_crosshair_checkbox.isChecked()
            or not len(self._section_points)
        ):
            return
        scene_position = event[0]
        if not self.section_view.sceneBoundingRect().contains(scene_position):
            self.section_crosshair_x.hide()
            self.section_crosshair_z.hide()
            return
        mouse_point = self.section_view.getViewBox().mapSceneToView(
            scene_position
        )
        index = int(
            np.argmin(np.abs(self._section_points[:, 0] - mouse_point.x()))
        )
        xg, zg = self._section_points[index]
        self.section_crosshair_x.setPos(float(xg))
        self.section_crosshair_z.setPos(float(zg))
        self.section_crosshair_x.show()
        self.section_crosshair_z.show()
        self.section_cursor_label.setText(
            f"游标 Xg {xg:.2f} mm  Zg {zg:.2f} mm"
        )

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

        self.camera_settings_group = QGroupBox("采集参数（停流后应用）", panel)
        form = QFormLayout(self.camera_settings_group)
        self.pixel_format = QComboBox(self.camera_settings_group)
        self.pixel_format.addItems(["Mono8", "Mono12"])
        self.exposure = QDoubleSpinBox(self.camera_settings_group)
        self.exposure.setRange(1.0, 1_000_000.0)
        self.exposure.setValue(1200.0)
        self.exposure.setSuffix(" μs")
        self.gain = QDoubleSpinBox(self.camera_settings_group)
        self.gain.setRange(-20.0, 40.0)
        self.offset_x = _spin(self.camera_settings_group, 0, 2447, 0)
        self.offset_y = _spin(self.camera_settings_group, 0, 2047, 880)
        self.roi_width = _spin(self.camera_settings_group, 1, 2448, 2448)
        self.roi_height = _spin(self.camera_settings_group, 1, 2048, 300)
        form.addRow("像素格式", self.pixel_format)
        form.addRow("曝光", self.exposure)
        form.addRow("增益", self.gain)
        form.addRow("Offset X", self.offset_x)
        form.addRow("Offset Y", self.offset_y)
        form.addRow("宽度", self.roi_width)
        form.addRow("高度", self.roi_height)
        layout.addWidget(self.camera_settings_group)

        self.processing_group = QGroupBox("处理参数（停流后应用）", panel)
        processing_form = QFormLayout(self.processing_group)
        self.extraction_method_combo = QComboBox(self.processing_group)
        self.extraction_method_combo.addItems(list(AVAILABLE_METHODS))
        method_index = self.extraction_method_combo.findText(
            self._initial_extraction_method
        )
        if method_index >= 0:
            self.extraction_method_combo.setCurrentIndex(method_index)
        processing_form.addRow("提取算法", self.extraction_method_combo)
        layout.addWidget(self.processing_group)

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
        self._controller.raw_frame_ready.connect(self._show_raw_frame, queued)
        self._controller.result_ready.connect(self._show_result, queued)
        self._controller.stats_updated.connect(self._show_stats, queued)
        self._controller.failed.connect(self._show_error, queued)
        self._controller.stopped.connect(self._on_stream_stopped, queued)

    def _set_online_state(
        self, state: OnlineState, message: str | None = None
    ) -> None:
        self._online_state = state
        if message is None:
            message = {
                OnlineState.DISCONNECTED: "未连接",
                OnlineState.CONNECTING: "连接中",
                OnlineState.CONNECTED: "已连接",
                OnlineState.STARTING: "启动中",
                OnlineState.STREAMING: "取流中",
                OnlineState.STOPPING: "停止中",
                OnlineState.ERROR: "错误",
            }[state]
            if state is OnlineState.DISCONNECTED and self._device_count:
                message = f"未连接 · 发现 {self._device_count} 台设备"
        self.state_label.setText(message)
        self._update_control_states()

    def _update_control_states(self) -> None:
        state = self._online_state
        has_session = self._session is not None
        disconnected = state is OnlineState.DISCONNECTED
        recoverable_disconnected = not has_session and state in {
            OnlineState.DISCONNECTED,
            OnlineState.ERROR,
        }
        idle = state is OnlineState.CONNECTED
        streaming = state is OnlineState.STREAMING
        busy = state in {
            OnlineState.CONNECTING,
            OnlineState.STARTING,
            OnlineState.STOPPING,
        }
        self.device_combo.setEnabled(recoverable_disconnected)
        self.refresh_button.setEnabled(recoverable_disconnected)
        self.connect_button.setEnabled(
            recoverable_disconnected and self._device_count > 0
        )
        self.disconnect_button.setEnabled(has_session and not busy)
        self.start_button.setEnabled(idle)
        self.stop_button.setEnabled(streaming)
        editable = disconnected or idle or (
            state is OnlineState.ERROR and not has_session
        )
        self.camera_settings_group.setEnabled(editable)
        self.processing_group.setEnabled(editable)
        self.snapshot_button.setEnabled(
            self._last_result is not None and not busy
        )
        self.record_count.setEnabled(streaming and not self._recorder.active)
        self.record_button.setEnabled(streaming and not self._recorder.active)

    def _on_stream_stopped(self) -> None:
        self.capture_fps_label.setText("0.0")
        self.process_fps_label.setText("0.0")
        self.display_fps_label.setText("0.0")
        if self._pending_disconnect:
            self._pending_disconnect = False
            self._close_camera_session()
            return
        if self._stop_due_to_error:
            self._stop_due_to_error = False
            self._set_online_state(OnlineState.ERROR)
            return
        self._set_online_state(
            OnlineState.CONNECTED
            if self._session is not None
            else OnlineState.DISCONNECTED
        )

    def _close_camera_session(self) -> bool:
        if self._recorder.active:
            self._cancel_recording()
        if self._recorder.cancelled:
            try:
                self._recorder.wait(2.0)
            except Exception:
                pass
        session = self._session
        if session is not None:
            try:
                session.close()
            except Exception as error:
                self._set_online_state(OnlineState.ERROR, f"关闭失败：{error}")
                return False
        self._session = None
        self._last_result = None
        self._set_online_state(OnlineState.DISCONNECTED)
        if self._closing:
            QTimer.singleShot(0, self.close)
        return True

    def refresh_devices(self) -> None:
        if self._session is not None:
            return
        self.device_combo.clear()
        try:
            devices = (
                [SyntheticCameraSession.device]
                if self._simulate
                else list_devices()
            )
        except Exception as error:
            self._device_count = 0
            self._set_online_state(OnlineState.ERROR, "SDK 不可用")
            QMessageBox.warning(self, "相机 SDK", str(error))
            return
        for device in devices:
            self.device_combo.addItem(device.display_name, device)
        self._device_count = len(devices)
        self._set_online_state(OnlineState.DISCONNECTED)

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

    def _sync_camera_config(self, config: CameraConfig) -> None:
        self.pixel_format.setCurrentText(config.pixel_format)
        self.exposure.setValue(config.exposure_us)
        self.gain.setValue(config.gain_db)
        self.offset_x.setValue(config.offset_x)
        self.offset_y.setValue(config.offset_y)
        self.roi_width.setValue(config.width)
        self.roi_height.setValue(config.height)

    def _apply_camera_config(self) -> None:
        if self._session is None:
            return
        requested = self._camera_config()
        if requested == self._session.config:
            return
        try:
            applied = self._session.configure(requested)
        except RuntimeError as configure_error:
            device = self._session.device
            try:
                self._session.close()
            finally:
                self._session = None
            try:
                self._session = (
                    SyntheticCameraSession(requested)
                    if self._simulate
                    else MvsCameraSession.open(device.serial_number, requested)
                )
            except Exception as reopen_error:
                raise RuntimeError(
                    "停流后应用采集参数失败，自动重连也未成功："
                    f"{reopen_error}"
                ) from configure_error
            applied = self._session.config
        self._sync_camera_config(applied)

    def connect_camera(self) -> None:
        if self._session is not None:
            return
        self._stop_due_to_error = False
        device: CameraDeviceInfo | None = self.device_combo.currentData()
        if device is None:
            QMessageBox.information(self, "未选择相机", "请先刷新并选择相机")
            return
        self._set_online_state(OnlineState.CONNECTING)
        QApplication.processEvents()
        try:
            config = self._camera_config()
            self._session = (
                SyntheticCameraSession(config)
                if self._simulate
                else MvsCameraSession.open(device.serial_number, config)
            )
        except Exception as error:
            self._session = None
            self._show_error(str(error))
            return
        self._sync_camera_config(self._session.config)
        self._last_result = None
        self._set_online_state(OnlineState.CONNECTED)

    def disconnect_camera(self) -> None:
        self._cancel_recording()
        if self._online_state is OnlineState.STOPPING:
            self._pending_disconnect = True
            return
        if self._controller.running:
            self._pending_disconnect = True
            self.stop_stream()
            return
        self._close_camera_session()

    def start_stream(self) -> None:
        if self._session is None:
            self.connect_camera()
        if self._session is None or self._controller.running:
            return
        self._stop_due_to_error = False
        self._set_online_state(OnlineState.STARTING)
        QApplication.processEvents()
        try:
            self._apply_camera_config()
            self._pipeline = FramePipeline(
                self._config, self.extraction_method_combo.currentText()
            )
            self._set_compensation_status()
            self._trail.clear()
            self._reset_section_view()
            self._displayed_frames = 0
            self._display_started = time.monotonic()
            self._last_render_at = 0.0
            self._controller.start(self._session, self._pipeline, self._recorder)
            self._set_online_state(OnlineState.STREAMING)
        except Exception as error:
            self._show_error(str(error))

    def stop_stream(self) -> None:
        self._cancel_recording()
        if self._online_state is OnlineState.STOPPING:
            return
        if not self._controller.running:
            self._set_online_state(
                OnlineState.CONNECTED
                if self._session is not None
                else OnlineState.DISCONNECTED
            )
            return
        self._set_online_state(OnlineState.STOPPING)
        self._shutdown_thread = threading.Thread(
            target=self._controller.stop,
            name="online-controller-stop",
            daemon=True,
        )
        self._shutdown_thread.start()

    def _cancel_recording(self) -> None:
        if not self._recorder.active:
            return
        self._recorder.cancel()
        self.record_label.setText("取消中")
        self._update_control_states()

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
            self._set_online_state(OnlineState.STREAMING, "录制中")
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

    def _set_image_view_mode(self, mode: str) -> None:
        if mode not in {"width", "fit"}:
            raise ValueError(f"未知图像视野模式: {mode}")
        self._image_view_mode = mode
        self._reset_image_views()

    def _reset_image_views(self) -> None:
        for view, item in (
            (self.raw_image_view, self.raw_image_item),
            (self.extracted_image_view, self.extracted_image_item),
        ):
            image = item.image
            if isinstance(image, np.ndarray) and image.size:
                _fit_image_view(view, image, self._image_view_mode)

    def _show_raw_frame(self, frame: CapturedFrame) -> None:
        if self.tabs.currentIndex() != 0:
            return
        image_shape = frame.image.shape[:2]
        shape_changed = image_shape != self._raw_view_shape
        raw_levels = (0, 255) if frame.image.dtype == np.uint8 else (0, 4095)
        self.raw_image_item.setImage(
            frame.image,
            autoLevels=False,
            levels=raw_levels,
        )
        _set_image_boundary(self.raw_image_boundary, frame.image)
        if shape_changed:
            self._raw_view_shape = image_shape
            _fit_image_view(
                self.raw_image_view, frame.image, self._image_view_mode
            )

    def _show_result(self, result: FrameResult) -> None:
        first_result = self._last_result is None
        self._last_result = result
        if first_result:
            self._update_control_states()
        now = time.monotonic()
        if now - self._last_render_at < 0.075:
            return
        self._last_render_at = now
        while self._trail and now - self._trail[0][0] > 1.0:
            self._trail.popleft()
        current = result.points_ground
        self._update_point_summary(current)
        if len(current):
            self._trail.append((now, current[::4].copy()))
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            image_shape = result.overlay_rgb.shape[:2]
            shape_changed = image_shape != self._extracted_view_shape
            self.extracted_image_item.setImage(
                result.overlay_rgb, autoLevels=False
            )
            _set_image_boundary(
                self.extracted_image_boundary, result.overlay_rgb
            )
            if shape_changed:
                self._extracted_view_shape = image_shape
                _fit_image_view(
                    self.extracted_image_view,
                    result.overlay_rgb,
                    self._image_view_mode,
                )
        elif current_tab == 1:
            trail_points: list[np.ndarray] = []
            trail_colors: list[np.ndarray] = []
            for timestamp, cloud in self._trail:
                if not len(cloud):
                    continue
                age = min(1.0, (now - timestamp) / 1.0)
                color = np.tile(
                    [0.04, 0.36, 0.72, max(0.14, 0.78 * (1.0 - age))],
                    (len(cloud), 1),
                )
                trail_points.append(cloud.astype(np.float32, copy=False))
                trail_colors.append(color.astype(np.float32))
            if trail_points:
                self.trail_point_item.setData(
                    pos=np.vstack(trail_points),
                    color=np.vstack(trail_colors),
                    size=2.0,
                )
            else:
                self.trail_point_item.setData(
                    pos=np.empty((0, 3), dtype=np.float32)
                )
            if len(current):
                self.current_point_item.setData(
                    pos=current.astype(np.float32, copy=False),
                    color=self._height_colors(current),
                    size=5.0,
                )
            else:
                self.current_point_item.setData(
                    pos=np.empty((0, 3), dtype=np.float32)
                )
        else:
            self._update_section_view(result.points_ground)
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
        self._update_control_states()
        if self._recorder.error is not None:
            self.record_label.setText("失败")
            self._show_error(str(self._recorder.error))
            return
        result = self._recorder.result
        if self._recorder.cancelled and result is None:
            if self.record_label.text() == "取消中":
                self.record_label.setText("已取消")
            return
        if result is not None and not self.record_label.text().startswith("完成"):
            self.record_label.setText(
                f"完成 {result.saved_frames} 帧，缺口 {result.detected_frame_gaps}"
            )
            if self._controller.running:
                self._set_online_state(OnlineState.STREAMING)

    def _show_error(self, message: str) -> None:
        self._stop_due_to_error = True
        if self._controller.running:
            if self._online_state is not OnlineState.STOPPING:
                self.stop_stream()
            self._set_online_state(OnlineState.STOPPING, "错误，正在停止")
        else:
            self._set_online_state(OnlineState.ERROR)
        QMessageBox.critical(self, "在线相机错误", message)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        if (
            self._closing
            and self._session is None
            and not self._controller.running
        ):
            event.accept()
            return
        self._closing = True
        self._cancel_recording()
        if (
            self._controller.running
            or self._online_state is OnlineState.STOPPING
        ):
            self._pending_disconnect = True
            self.stop_stream()
            event.ignore()
            return
        if self._close_camera_session():
            event.accept()
        else:
            event.ignore()


def _spin(parent: QWidget, minimum: int, maximum: int, value: int) -> QSpinBox:
    widget = QSpinBox(parent)
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    return widget


def _double_spin(
    parent: QWidget,
    minimum: float,
    maximum: float,
    value: float,
    suffix: str = "",
) -> QDoubleSpinBox:
    widget = QDoubleSpinBox(parent)
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    widget.setSuffix(suffix)
    return widget


def _section_connection_mask(
    points_ground: np.ndarray,
    *,
    max_dx: float,
    max_dz: float,
    max_distance: float,
) -> np.ndarray:
    points = np.asarray(points_ground, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points_ground 必须是形状为 (N, 3) 的数组")
    if min(max_dx, max_dz, max_distance) <= 0:
        raise ValueError("截面断线阈值必须大于 0")
    connections = np.zeros(len(points), dtype=np.int32)
    if len(points) < 2:
        return connections
    differences = np.diff(points, axis=0)
    distances = np.linalg.norm(differences, axis=1)
    continuous = (
        (np.abs(differences[:, 0]) <= max_dx)
        & (np.abs(differences[:, 2]) <= max_dz)
        & (distances <= max_distance)
    )
    # PlotCurveItem uses item i to decide whether point i connects to i + 1.
    connections[:-1] = continuous.astype(np.int32)
    return connections


def _set_image_boundary(boundary: pg.PlotDataItem, image: np.ndarray) -> None:
    height, width = image.shape[:2]
    boundary.setData(
        [0, width, width, 0, 0],
        [0, 0, height, height, 0],
    )


def _bounded_view_range(
    current_range: list[float] | tuple[float, float], extent: float
) -> tuple[float, float]:
    lower, upper = map(float, current_range)
    span = upper - lower
    if span >= extent:
        centre = extent * 0.5
        return centre - span * 0.5, centre + span * 0.5
    if lower < 0:
        return 0.0, span
    if upper > extent:
        return extent - span, extent
    return lower, upper


def _fit_image_view(
    view: pg.PlotWidget, image: np.ndarray, mode: str = "width"
) -> None:
    height, width = image.shape[:2]
    view_box = view.getViewBox()
    if not isinstance(view_box, ConstrainedImageViewBox):
        raise TypeError("图像预览必须使用 ConstrainedImageViewBox")
    view_box.clear_image_constraints()
    view_box.setRange(
        xRange=(0, width),
        yRange=(0, height),
        padding=0,
    )
    if mode == "width":
        view_box.setXRange(0, width, padding=0)
    elif mode != "fit":
        raise ValueError(f"未知图像视野模式: {mode}")
    view_box.set_image_constraints(width, height)
