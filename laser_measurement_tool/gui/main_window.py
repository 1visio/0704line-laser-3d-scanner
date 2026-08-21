"""图像视图与控制面板组成的应用主窗口。"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app_config import AppConfig
from calibration.config_loader import (
    CalibrationConfigError,
    CalibrationFileNotFoundError,
    load_calibration_files,
)
from calibration.manifest import load_calibration_package
from correction.stage_a_height_scale import (
    StageAHeightResult,
    apply_stage_a_height_scale,
)
from gui.image_view import ImageView, _to_uint8_display
from gui.point_cloud_view import PointCloudView
from gui.section_view import SectionView
from laser.backends import AVAILABLE_METHODS, create_extraction_params
from laser.laser_extractor import (
    LaserAlgorithmNotConfiguredError,
    LaserExtractionError,
    LaserExtractionParams,
    LaserExtractionParamsInput,
    extract_laser_center,
)
from measurement.height_measure import (
    HeightLineMeasurement,
    MeasurementError,
    measure_height_lines,
)
from measurement.ground_reference import SessionGroundReference
from measurement.roi_manager import RoiKind, RoiManager
from reconstruction.reconstructor import (
    ReconstructionInputError,
    ReconstructionResult,
    project_ground_points_to_pixels,
    reconstruct_uv_to_ground,
)
from utils.image_io import load_grayscale_image
from utils.image_metadata import (
    offset_from_mapping,
    read_image_offset_metadata,
)
from utils.result_io import (
    next_measurement_dir,
    save_image_png,
    save_ground_pointcloud_ply,
    save_laser_centers_csv,
    save_measurement_json,
    save_reconstructed_points_csv,
)


# The online camera defaults to this hardware ROI. It is only a prompt
# default; the user can enter the actual OffsetX/OffsetY, and sidecar metadata
# takes precedence when available.
_DEFAULT_HARD_ROI_OFFSET = (0, 880)


class MainWindow(QMainWindow):
    """单帧线激光测量工具的主窗口。"""

    extract_laser_requested = Signal()
    laser_centers_extracted = Signal(object, str)
    roi_selection_requested = Signal(str)
    roi_points_changed = Signal(object, object)
    reconstruction_requested = Signal()
    save_requested = Signal()

    def __init__(
        self,
        config: AppConfig | None = None,
        *,
        system: str | None = None,
        runtime_calibration: dict[str, Any] | None = None,
        ground_extrinsic_source: str = "reference",
        runtime_ground_reference: SessionGroundReference | None = None,
    ) -> None:
        super().__init__()
        self._app_config = config
        self._system = (
            system or (config.system if config is not None else "mvs")
        ).strip().lower()
        self._calibration: dict[str, Any] | None = runtime_calibration
        self._ground_extrinsic_source = ground_extrinsic_source
        self._ground_reference = runtime_ground_reference
        self._image: np.ndarray | None = None
        self._image_path: Path | None = None
        # 实时相机通常输出传感器 ROI。图像/ROI 仍使用 ROI 局部坐标，
        # 重建时再加回该偏移以匹配标定文件中的全幅像素坐标。
        self._image_offset = (0, 0)
        self._laser_centers = np.empty((0, 2), dtype=np.float64)
        self._laser_extraction_params: LaserExtractionParamsInput = (
            self._extraction_params_from_config(
                config.extraction_method if config else None
            )
        )
        self._last_laser_csv_path: Path | None = None
        self._output_directory = (
            config.output.directory
            if config is not None and config.output is not None
            else Path(__file__).resolve().parents[1] / "output"
        )
        self._roi_manager = RoiManager()
        self._baseline_points = np.empty((0, 2), dtype=np.float64)
        self._obstacle_points = np.empty((0, 2), dtype=np.float64)
        self._obstacle_point_groups: list[np.ndarray] = []
        self._last_measurements: list[HeightLineMeasurement] = []
        self._last_reconstruction: dict[str, ReconstructionResult] = {}
        self._last_obstacle_reconstructions: list[ReconstructionResult] = []
        self._last_full_reconstruction: ReconstructionResult | None = None
        self._last_overlay_segments: list[tuple[str, np.ndarray]] = []
        self._online_window: QMainWindow | None = None

        self.setWindowTitle("单帧线激光三维截面测量工具")
        self.resize(1200, 760)

        self.image_view = ImageView(self)
        self.point_cloud_view = PointCloudView(self)
        self.section_view = SectionView(self)
        self.view_stack = QStackedWidget(self)
        self.view_stack.addWidget(self.image_view)
        self.view_stack.addWidget(self.point_cloud_view)
        self.view_stack.addWidget(self.section_view)
        self.setCentralWidget(self._build_central_widget())
        self._connect_signals()
        self._set_image_actions_enabled(False)
        self.statusBar().showMessage("请加载灰度图像")

    @property
    def current_image(self) -> np.ndarray | None:
        """返回原始灰度数据，供后续算法控制器读取。"""
        return self._image

    @property
    def current_image_path(self) -> Path | None:
        """返回当前图像路径。"""
        return self._image_path

    @property
    def current_laser_centers(self) -> np.ndarray:
        """返回最近一次成功提取的 ``(u, v)`` 中心点。"""
        return self._laser_centers

    @property
    def current_laser_centers_full(self) -> np.ndarray:
        """返回按标定全幅像素坐标表示的最近中心点。"""
        return self._centers_in_calibration_coordinates(self._laser_centers)

    @property
    def last_laser_csv_path(self) -> Path | None:
        """返回最近一次成功保存的中心点 CSV 路径。"""
        return self._last_laser_csv_path

    @property
    def baseline_points(self) -> np.ndarray:
        """返回基准 ROI 内的亚像素激光中心点。"""
        return self._baseline_points

    @property
    def baseline_regions_full(self) -> tuple[tuple[float, float, float, float], ...]:
        """返回用户确认的基准 ROI，坐标为 full-sensor 像素。"""
        offset_x, offset_y = self._image_offset
        return tuple(
            (
                float(region.left + offset_x),
                float(region.top + offset_y),
                float(region.right + offset_x),
                float(region.bottom + offset_y),
            )
            for region in self._roi_manager.regions
            if region.kind is RoiKind.BASELINE
        )

    @property
    def obstacle_points(self) -> np.ndarray:
        """返回障碍物 ROI 内的亚像素激光中心点。"""
        return self._obstacle_points

    def set_laser_extraction_params(
        self,
        params: LaserExtractionParams | Mapping[str, Any],
    ) -> None:
        """注入现有 Steger、Gaussian 或 RANSAC backend 及参数。"""
        self._laser_extraction_params = params

    def open_image(self) -> None:
        """选择并加载受支持的灰度图像。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载灰度图像",
            "",
            "灰度图像 (*.tif *.tiff *.png *.bmp)",
        )
        if not file_path:
            return

        try:
            image = load_grayscale_image(file_path)
        except (FileNotFoundError, ValueError, OSError) as error:
            QMessageBox.critical(self, "加载失败", str(error))
            return

        image_path = Path(file_path)
        image_offset = self._resolve_loaded_image_offset(image_path, image)
        if image_offset is None:
            return
        self._set_frame_data(
            image,
            image_path,
            np.empty((0, 2), dtype=np.float64),
            image_offset=image_offset,
        )
        height, width = image.shape
        offset_suffix = (
            f" | Offset ({image_offset[0]}, {image_offset[1]})"
            if image_offset != (0, 0)
            else ""
        )
        self.statusBar().showMessage(
            f"已加载 {self._image_path.name} | {width} × {height} | {image.dtype}"
            f"{offset_suffix}"
        )

    def _calibration_image_size(self) -> tuple[int, int] | None:
        """返回标定包的全幅尺寸；无法读取时不阻断图像加载。"""
        if self._app_config is None or self._app_config.calibration.manifest is None:
            return None
        try:
            package = load_calibration_package(
                self._app_config.calibration.manifest
            )
        except (
            CalibrationConfigError,
            CalibrationFileNotFoundError,
            OSError,
            ValueError,
        ):
            return None
        return package.image_width, package.image_height

    @staticmethod
    def _offset_from_mapping(mapping: object) -> tuple[int, int] | None:
        """从常见的结果/帧元数据映射中读取硬件 ROI 偏移。"""
        return offset_from_mapping(mapping)

    @classmethod
    def _read_image_offset_metadata(cls, image_path: Path) -> tuple[int, int] | None:
        """读取录制 CSV、在线导出 JSON 或相邻 JSON 中的 ROI 偏移。"""
        return read_image_offset_metadata(image_path)

    def _resolve_loaded_image_offset(
        self, image_path: Path, image: np.ndarray
    ) -> tuple[int, int] | None:
        """为独立图像恢复硬件 ROI 到标定全幅的坐标偏移。"""
        full_size = self._calibration_image_size()
        if full_size is None:
            return (0, 0)

        width, height = int(image.shape[1]), int(image.shape[0])
        full_width, full_height = full_size
        if (width, height) == (full_width, full_height):
            return (0, 0)
        if width > full_width or height > full_height:
            QMessageBox.warning(
                self,
                "图像尺寸不匹配",
                f"当前图像为 {width} × {height}，超过标定全幅 "
                f"{full_width} × {full_height}，无法按当前标定重建。",
            )
            return None

        max_offset_x = full_width - width
        max_offset_y = full_height - height
        metadata_offset = self._read_image_offset_metadata(image_path)
        if metadata_offset is not None:
            offset_x, offset_y = metadata_offset
            if offset_x <= max_offset_x and offset_y <= max_offset_y:
                return metadata_offset

        default_x = min(_DEFAULT_HARD_ROI_OFFSET[0], max_offset_x)
        default_y = min(_DEFAULT_HARD_ROI_OFFSET[1], max_offset_y)
        prompt = (
            f"当前图像为 {width} × {height}，标定全幅为 "
            f"{full_width} × {full_height}。\n"
            "这是硬件 ROI 或软件裁剪图，请输入它在全幅图中的左上角偏移。\n"
            "若图像来自当前在线相机默认 ROI，OffsetY 通常为 880。"
        )
        offset_x, accepted = QInputDialog.getInt(
            self,
            "设置图像坐标偏移",
            f"{prompt}\nOffset X:",
            default_x,
            0,
            max_offset_x,
            1,
        )
        if not accepted:
            return None
        offset_y, accepted = QInputDialog.getInt(
            self,
            "设置图像坐标偏移",
            f"{prompt}\nOffset Y:",
            default_y,
            0,
            max_offset_y,
            1,
        )
        if not accepted:
            return None
        return int(offset_x), int(offset_y)

    def load_external_frame(
        self,
        image: np.ndarray,
        centers_uv_full: np.ndarray,
        *,
        image_name: str | Path = "online_frame.tiff",
        image_offset: tuple[int, int] = (0, 0),
    ) -> None:
        """加载实时窗口传入的单帧，并保留其全幅标定坐标。

        ``image`` 是相机 ROI 图像，``centers_uv_full`` 使用原始传感器
        坐标；ROI 框选在局部图像上进行，三维恢复时自动加回
        ``image_offset``。
        """
        frame = np.asarray(image)
        if frame.ndim != 2 or frame.dtype not in (np.uint8, np.uint16):
            raise ValueError("实时帧必须是二维 uint8/uint16 灰度图")
        centers = np.asarray(centers_uv_full, dtype=np.float64)
        if centers.ndim != 2 or centers.shape[1] != 2:
            raise ValueError("中心点必须是形状为 (N, 2) 的数组")
        if not np.isfinite(centers).all():
            raise ValueError("中心点包含 NaN 或无穷值")
        try:
            raw_offset = tuple(image_offset)
            if len(raw_offset) != 2:
                raise ValueError
            offset = tuple(int(value) for value in raw_offset)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("image_offset 必须是两个整数坐标") from error
        if min(offset) < 0:
            raise ValueError("图像偏移不能为负数")
        local_centers = centers - np.asarray(offset, dtype=np.float64)
        height, width = frame.shape
        if len(local_centers):
            if (
                np.min(local_centers[:, 0]) < -0.5
                or np.max(local_centers[:, 0]) >= width + 0.5
                or np.min(local_centers[:, 1]) < -0.5
                or np.max(local_centers[:, 1]) >= height + 0.5
            ):
                raise ValueError("实时中心点超出相机 ROI 范围")
        self._set_frame_data(
            frame,
            Path(image_name),
            local_centers,
            image_offset=offset,
        )
        self.statusBar().showMessage(
            f"已加载实时帧 | {width} × {height} | 中心点 {len(local_centers)} | "
            f"Offset ({offset[0]}, {offset[1]}) | "
            f"ground 外参: {self._ground_extrinsic_source}"
        )

    def load_frame(
        self,
        image: np.ndarray,
        centers_uv_full: np.ndarray,
        *,
        image_name: str | Path = "online_frame.tiff",
        image_offset: tuple[int, int] = (0, 0),
    ) -> None:
        """``load_external_frame`` 的简短别名，便于实时控制器调用。"""
        self.load_external_frame(
            image,
            centers_uv_full,
            image_name=image_name,
            image_offset=image_offset,
        )

    def _set_frame_data(
        self,
        image: np.ndarray,
        image_path: Path,
        centers_local: np.ndarray,
        *,
        image_offset: tuple[int, int],
    ) -> None:
        self._image = np.ascontiguousarray(image)
        self._image_path = image_path
        self._image_offset = tuple(int(value) for value in image_offset)
        self._laser_centers = np.ascontiguousarray(
            np.asarray(centers_local, dtype=np.float64).reshape(-1, 2)
        )
        self._last_laser_csv_path = None
        self._roi_manager.clear()
        self._update_roi_points()
        self.image_view.set_image(self._image)
        if len(self._laser_centers):
            self.image_view.set_laser_centers(self._laser_centers)
        self.point_cloud_view.clear()
        self.section_view.clear()
        self._show_image_view()
        self._set_image_actions_enabled(True)
        self.point_cloud_button.setEnabled(len(self._laser_centers) > 0)
        self.section_view_button.setEnabled(len(self._laser_centers) > 0)

    def _centers_in_calibration_coordinates(
        self, centers_local: np.ndarray
    ) -> np.ndarray:
        points = np.asarray(centers_local, dtype=np.float64).reshape(-1, 2)
        if not len(points) or self._image_offset == (0, 0):
            return np.ascontiguousarray(points)
        return np.ascontiguousarray(
            points + np.asarray(self._image_offset, dtype=np.float64)
        )

    def _apply_ground_reference_to_reconstruction(
        self, reconstruction: ReconstructionResult
    ) -> ReconstructionResult:
        """Apply the online session reference without changing camera points."""
        reference = self._ground_reference
        if reference is None:
            return reconstruction
        points_ground, _ = reference.apply_to_points(reconstruction.points_ground)
        return ReconstructionResult(
            pixels_uv=reconstruction.pixels_uv,
            points_camera=reconstruction.points_camera,
            points_ground=points_ground,
            filtered=reconstruction.filtered,
        )

    def _build_central_widget(self) -> QWidget:
        central_widget = QWidget(self)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.view_stack, 1)
        self._control_panel_scroll_area = QScrollArea(central_widget)
        self._control_panel_scroll_area.setObjectName(
            "controlPanelScrollArea"
        )
        # Reserve enough logical width for the result labels and the vertical
        # scrollbar.  The panel itself follows the viewport width, so opening
        # the scrollbar cannot clip the right side of a label.
        self._control_panel_scroll_area.setMinimumWidth(320)
        self._control_panel_scroll_area.setWidgetResizable(True)
        self._control_panel_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._control_panel_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._control_panel_scroll_area.setWidget(self._build_control_panel())
        layout.addWidget(self._control_panel_scroll_area)
        return central_widget

    def _build_control_panel(self) -> QWidget:
        panel = QWidget(self)
        panel.setMinimumWidth(300)
        panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        layout = QVBoxLayout(panel)

        self.load_button = QPushButton("加载图像", panel)
        self.online_button = QPushButton("在线相机", panel)
        self.method_combo = QComboBox(panel)
        for method in AVAILABLE_METHODS:
            self.method_combo.addItem(method)
        if self._app_config is not None:
            index = self.method_combo.findText(
                self._app_config.extraction_method
            )
            if index >= 0:
                self.method_combo.setCurrentIndex(index)
        self.extract_laser_button = QPushButton("提取激光线", panel)
        self.point_cloud_button = QPushButton("三维点云", panel)
        self.point_cloud_button.setEnabled(False)
        self.section_view_button = QPushButton("截面视图", panel)
        self.section_view_button.setEnabled(False)
        self.baseline_roi_button = QPushButton("添加基准区域", panel)
        self.obstacle_roi_button = QPushButton("添加障碍物区域", panel)
        self.remove_last_roi_button = QPushButton("删除最后一个区域", panel)
        self.clear_rois_button = QPushButton("清空区域", panel)
        self.reconstruct_button = QPushButton("三维恢复并测量", panel)
        self.save_button = QPushButton("保存结果", panel)

        layout.addWidget(self.load_button)
        layout.addWidget(self.online_button)
        layout.addSpacing(12)
        layout.addWidget(QLabel("提取算法:", panel))
        layout.addWidget(self.method_combo)
        for button in self._image_action_buttons:
            layout.addWidget(button)
        layout.addSpacing(12)
        layout.addWidget(self._build_results_group(panel))
        layout.addStretch(1)
        return panel

    def _build_results_group(self, parent: QWidget) -> QGroupBox:
        group = QGroupBox("计算结果 (mm)", parent)
        layout = QVBoxLayout(group)
        reference_group = QGroupBox("公共地面基准", group)
        reference_form = QFormLayout(reference_group)
        self._result_labels: dict[str, QLabel] = {}
        for key, title in (
            ("ground", "地面基准 Zg"),
            ("ground_sigma", "地面噪声 σ"),
            ("baseline_points", "内点/总点"),
        ):
            label = QLabel(
                self._ground_extrinsic_source if key == "ground_source" else "—",
                reference_group,
            )
            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._result_labels[key] = label
            reference_form.addRow(f"{title}:", label)
        layout.addWidget(reference_group)

        session_group = QGroupBox("本次测量状态", group)
        session_form = QFormLayout(session_group)
        for key, title in (
            ("stage_a_enabled", "Stage-A 补偿"),
            ("stage_a_domain", "Stage-A 有效域"),
            ("session_ground_reference", "Session 地面基准"),
            ("ground_reference_mode", "地面参考模式"),
            ("ground_source", "ground 外参来源"),
        ):
            label = QLabel(
                self._ground_extrinsic_source
                if key == "ground_source"
                else "—",
                session_group,
            )
            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._result_labels[key] = label
            session_form.addRow(f"{title}:", label)
        layout.addWidget(session_group)
        self._obstacle_results_layout = QVBoxLayout()
        self._obstacle_result_groups: list[QGroupBox] = []
        layout.addLayout(self._obstacle_results_layout)
        return group

    @property
    def _image_action_buttons(self) -> tuple[QPushButton, ...]:
        return (
            self.extract_laser_button,
            self.point_cloud_button,
            self.section_view_button,
            self.baseline_roi_button,
            self.obstacle_roi_button,
            self.remove_last_roi_button,
            self.clear_rois_button,
            self.reconstruct_button,
            self.save_button,
        )

    def _connect_signals(self) -> None:
        self.load_button.clicked.connect(self.open_image)
        self.online_button.clicked.connect(self._open_online_window)
        self.extract_laser_button.clicked.connect(self._extract_laser_line)
        self.point_cloud_button.clicked.connect(
            lambda _checked=False: self._toggle_point_cloud_view()
        )
        self.section_view_button.clicked.connect(
            lambda _checked=False: self._toggle_section_view()
        )
        self.baseline_roi_button.clicked.connect(
            lambda _checked=False: self._request_roi_selection("baseline")
        )
        self.obstacle_roi_button.clicked.connect(
            lambda _checked=False: self._request_roi_selection("obstacle")
        )
        self.remove_last_roi_button.clicked.connect(
            lambda _checked=False: self._remove_last_roi()
        )
        self.clear_rois_button.clicked.connect(
            lambda _checked=False: self._clear_rois()
        )
        self.reconstruct_button.clicked.connect(
            lambda _checked=False: self._run_measurement()
        )
        self.save_button.clicked.connect(
            lambda _checked=False: self._save_results()
        )
        self.method_combo.currentTextChanged.connect(self._change_method)
        self.image_view.image_coordinates_changed.connect(self._show_image_coordinates)
        self.image_view.image_coordinates_cleared.connect(self._clear_image_coordinates)
        self.image_view.roi_selected.connect(self._add_roi_region)

    def _open_online_window(self) -> None:
        if self._app_config is None:
            QMessageBox.critical(self, "缺少配置", "在线相机需要有效的统一配置文件")
            return
        try:
            from online.window import OnlineCameraWindow

            if self._online_window is None:
                self._online_window = OnlineCameraWindow(self._app_config)
            self._online_window.show()
            self._online_window.raise_()
            self._online_window.activateWindow()
        except (RuntimeError, ValueError, OSError) as error:
            QMessageBox.critical(self, "在线相机启动失败", str(error))

    def _set_image_actions_enabled(self, enabled: bool) -> None:
        for button in self._image_action_buttons:
            button.setEnabled(enabled)

    def _request_roi_selection(self, roi_kind: str) -> None:
        self.image_view.begin_roi_selection(roi_kind)
        self.roi_selection_requested.emit(roi_kind)
        label = "基准区域" if roi_kind == "baseline" else "障碍物区域"
        self.statusBar().showMessage(f"请在图像中拖动框选{label}")

    def _add_roi_region(self, roi_kind: str, rectangle) -> None:
        self._roi_manager.add_region(
            roi_kind,
            rectangle.left(),
            rectangle.top(),
            rectangle.right(),
            rectangle.bottom(),
        )
        self.image_view.set_roi_regions(self._roi_manager.regions)
        self._update_roi_points()
        self.statusBar().showMessage(
            f"已添加 ROI，共 {len(self._roi_manager.regions)} 个区域 | "
            f"基准点 {len(self._baseline_points)}，障碍物点 {len(self._obstacle_points)}"
        )

    def _remove_last_roi(self) -> None:
        self.image_view.cancel_roi_selection()
        removed = self._roi_manager.remove_last()
        if removed is None:
            self.statusBar().showMessage("当前没有可删除的 ROI")
            return
        self.image_view.set_roi_regions(self._roi_manager.regions)
        self._update_roi_points()
        self.statusBar().showMessage(
            f"已删除最后一个 ROI，剩余 {len(self._roi_manager.regions)} 个 | "
            f"基准点 {len(self._baseline_points)}，障碍物点 {len(self._obstacle_points)}"
        )

    def _clear_rois(self) -> None:
        self.image_view.cancel_roi_selection()
        self._roi_manager.clear()
        self.image_view.clear_roi_regions()
        self._update_roi_points()
        self.statusBar().showMessage("已清空全部 ROI")

    def _extract_laser_line(self) -> None:
        if self._image is None or self._image_path is None:
            return

        self.extract_laser_requested.emit()
        try:
            centers = extract_laser_center(
                self._image,
                self._laser_extraction_params,
                image_offset=self._image_offset,
            )
        except LaserAlgorithmNotConfiguredError as error:
            self.statusBar().showMessage(str(error))
            QMessageBox.information(self, "算法未配置", str(error))
            return
        except (LaserExtractionError, TypeError, ValueError) as error:
            self.statusBar().showMessage("激光中心提取失败")
            QMessageBox.critical(self, "提取失败", str(error))
            return

        self._laser_centers = centers
        self._last_laser_csv_path = None
        self.image_view.set_laser_centers(centers)
        self.point_cloud_view.clear()
        self.section_view.clear()
        self._show_image_view()
        self.point_cloud_button.setEnabled(len(centers) > 0)
        self.section_view_button.setEnabled(len(centers) > 0)
        self._update_roi_points()
        self.laser_centers_extracted.emit(centers, "")
        self.statusBar().showMessage(
            f"已提取 {len(centers)} 个中心点（点击“保存结果”写入文件） | "
            f"基准点 {len(self._baseline_points)}，障碍物点 {len(self._obstacle_points)}"
        )

    def _update_roi_points(self) -> None:
        self._baseline_points, self._obstacle_points = (
            self._roi_manager.filter_points(self._laser_centers)
        )
        self._obstacle_point_groups = self._roi_manager.filter_points_by_region(
            self._laser_centers, RoiKind.OBSTACLE
        )
        self._invalidate_measurement()
        self.roi_points_changed.emit(
            self._baseline_points,
            self._obstacle_points,
        )

    def _invalidate_measurement(self) -> None:
        """点或 ROI 变化后，上一次测量结果作废。"""
        self._last_measurements = []
        self._last_reconstruction = {}
        self._last_obstacle_reconstructions = []
        self._last_full_reconstruction = None
        self._last_overlay_segments = []
        if hasattr(self, "point_cloud_view"):
            self.point_cloud_view.clear()
        if hasattr(self, "section_view"):
            self.section_view.clear()
        if hasattr(self, "view_stack"):
            self._show_image_view()
        if self.image_view.has_image:
            self.image_view.clear_measurement_overlay()
        if hasattr(self, "_result_labels"):
            for key, label in self._result_labels.items():
                label.setText(
                    self._ground_extrinsic_source if key == "ground_source" else "—"
                )
        if hasattr(self, "_obstacle_result_groups"):
            self._clear_obstacle_result_groups()

    def _extraction_params_from_config(
        self, method: str | None
    ) -> LaserExtractionParamsInput:
        if method is None:
            method = "centroid"
        if self._app_config is None:
            return create_extraction_params(method, {})
        options = self._app_config.extraction_options_by_method.get(method, {})
        try:
            return create_extraction_params(method, options)
        except ValueError:
            return LaserExtractionParams(method=method)

    def _change_method(self, method: str) -> None:
        self._laser_extraction_params = self._extraction_params_from_config(
            method
        )
        self.statusBar().showMessage(f"提取算法切换为 {method}")

    def _ensure_calibration(self) -> dict[str, Any] | None:
        """惰性加载标定；失败时弹窗并返回 None。"""
        if self._calibration is not None:
            return self._calibration
        if self._app_config is None:
            QMessageBox.critical(
                self,
                "缺少配置",
                "未加载配置文件，无法读取标定参数。\n"
                "请通过 python main.py --config <measure_tool.yaml> 启动。",
            )
            return None
        paths = self._app_config.calibration
        try:
            if paths.manifest is not None:
                self._calibration = load_calibration_package(
                    paths.manifest
                ).calibration
            else:
                self._calibration = load_calibration_files(
                    intrinsics=paths.intrinsics,
                    laser_plane=paths.laser_plane,
                    extrinsics=paths.extrinsics,
                    ground_u_compensation=paths.ground_u_compensation,
                    laser_ray_correction=paths.laser_ray_correction,
                )
        except (
            CalibrationFileNotFoundError,
            CalibrationConfigError,
            OSError,
        ) as error:
            QMessageBox.critical(self, "标定加载失败", str(error))
            return None
        return self._calibration

    def _run_measurement(self) -> None:
        """三维恢复基准线与高度线，计算高度和长度并叠加显示。"""
        self.reconstruction_requested.emit()
        if self._image is None:
            return
        if len(self._laser_centers) == 0:
            QMessageBox.information(self, "缺少数据", "请先提取激光线")
            return
        has_baseline_roi = any(
            region.kind is RoiKind.BASELINE
            for region in self._roi_manager.regions
        )
        if not self._obstacle_point_groups:
            QMessageBox.information(
                self,
                "缺少 ROI",
                "请先框选障碍物（高度线）区域，"
                "并确认区域内包含激光中心点。基准区域可不选，"
                "此时使用 Zg=0 作为固定地面基准。",
            )
            return
        empty_obstacles = [
            str(index)
            for index, points in enumerate(
                self._obstacle_point_groups, start=1
            )
            if len(points) == 0
        ]
        if empty_obstacles:
            QMessageBox.information(
                self,
                "障碍物区域无有效点",
                f"障碍物区域 {', '.join(empty_obstacles)} 中没有激光中心点。"
                "请调整或删除这些区域。",
            )
            return
        if has_baseline_roi and len(self._baseline_points) == 0:
            QMessageBox.information(
                self,
                "基准区域无有效点",
                "已选择基准区域，但区域内没有激光中心点。"
                "请调整基准区域，或删除全部基准区域后使用 Zg=0 模式。",
            )
            return
        calibration = self._ensure_calibration()
        if calibration is None:
            return

        config = self._app_config
        assert config is not None
        try:
            baseline_recon = None
            if has_baseline_roi:
                baseline_recon = self._apply_ground_reference_to_reconstruction(
                    reconstruct_uv_to_ground(
                        self._centers_in_calibration_coordinates(self._baseline_points),
                        calibration,
                        config.reconstruction,
                    )
                )
            obstacle_recons = [
                self._apply_ground_reference_to_reconstruction(
                    reconstruct_uv_to_ground(
                        self._centers_in_calibration_coordinates(points),
                        calibration,
                        config.reconstruction,
                    )
                )
                for points in self._obstacle_point_groups
            ]
            full_recon = self._apply_ground_reference_to_reconstruction(
                reconstruct_uv_to_ground(
                    self._centers_in_calibration_coordinates(self._laser_centers),
                    calibration,
                    config.reconstruction,
                )
            )
            measurements = measure_height_lines(
                (
                    baseline_recon.points_ground
                    if baseline_recon is not None
                    else None
                ),
                [recon.points_ground for recon in obstacle_recons],
                config.measurement,
            )
        except (ReconstructionInputError, MeasurementError) as error:
            QMessageBox.warning(self, "测量失败", str(error))
            return

        self._last_reconstruction = {}
        if baseline_recon is not None:
            self._last_reconstruction["baseline"] = baseline_recon
        if len(obstacle_recons) == 1:
            self._last_reconstruction["height"] = obstacle_recons[0]
        else:
            for index, recon in enumerate(obstacle_recons, start=1):
                self._last_reconstruction[f"obstacle_{index}"] = recon
        self._last_obstacle_reconstructions = obstacle_recons
        self._last_full_reconstruction = full_recon
        self._last_measurements = measurements
        self._last_overlay_segments = self._build_overlay_segments(
            measurements, calibration
        )
        self.image_view.set_measurement_overlay(self._last_overlay_segments)
        self._update_results_panel(measurements)
        first_measurement = measurements[0]
        if first_measurement.baseline_fit is not None:
            reference_status = (
                f"基准 {first_measurement.baseline_inlier_count}/"
                f"{first_measurement.baseline_point_count}"
            )
        else:
            reference_status = "固定基准 Zg=0"
        height_status = "，".join(
            self._format_height_status(index, measurement)
            for index, measurement in enumerate(measurements, start=1)
        )
        self.statusBar().showMessage(
            f"{height_status} | {reference_status} | "
            f"ground 外参 {self._ground_extrinsic_source}"
        )

    def _toggle_point_cloud_view(self) -> None:
        if self.view_stack.currentWidget() is self.point_cloud_view:
            self._show_image_view()
            self.statusBar().showMessage("已切回图像视图")
            return
        self._show_point_cloud_view()

    def _show_image_view(self) -> None:
        self.view_stack.setCurrentWidget(self.image_view)
        if hasattr(self, "point_cloud_button"):
            self.point_cloud_button.setText("三维点云")
        if hasattr(self, "section_view_button"):
            self.section_view_button.setText("截面视图")

    def _show_point_cloud_view(self) -> None:
        try:
            full_reconstruction = self._ensure_full_laser_reconstruction()
            if full_reconstruction is None:
                return
            self.point_cloud_view.set_points(
                full_reconstruction.points_ground
            )
        except (ReconstructionInputError, ValueError) as error:
            QMessageBox.warning(self, "点云生成失败", str(error))
            return

        self.view_stack.setCurrentWidget(self.point_cloud_view)
        self.point_cloud_button.setText("返回图像")
        self.section_view_button.setText("截面视图")
        self.statusBar().showMessage(
            f"三维点云：{full_reconstruction.point_count} 个点 | "
            "颜色=Zg(mm)"
        )

    def _toggle_section_view(self) -> None:
        if self.view_stack.currentWidget() is self.section_view:
            self._show_image_view()
            self.statusBar().showMessage("已切回图像视图")
            return
        self._show_section_view()

    def _show_section_view(self) -> None:
        try:
            full_reconstruction = self._ensure_full_laser_reconstruction()
            if full_reconstruction is None:
                return
            self.section_view.set_points(full_reconstruction.points_ground)
        except (ReconstructionInputError, ValueError) as error:
            QMessageBox.warning(self, "截面视图生成失败", str(error))
            return

        self.view_stack.setCurrentWidget(self.section_view)
        self.point_cloud_button.setText("三维点云")
        self.section_view_button.setText("返回图像")
        self.statusBar().showMessage(
            f"截面视图：{full_reconstruction.point_count} 个点 | "
            "横轴=S(mm)，纵轴=Zg(mm)"
        )

    def _ensure_full_laser_reconstruction(self) -> ReconstructionResult | None:
        if len(self._laser_centers) == 0:
            QMessageBox.information(self, "缺少数据", "请先提取激光线")
            return None
        calibration = self._ensure_calibration()
        if calibration is None:
            return None
        config = self._app_config
        if config is None:
            return None

        if self._last_full_reconstruction is None:
            self._last_full_reconstruction = (
                self._apply_ground_reference_to_reconstruction(
                    reconstruct_uv_to_ground(
                        self._centers_in_calibration_coordinates(self._laser_centers),
                        calibration,
                        config.reconstruction,
                    )
                )
            )
        return self._last_full_reconstruction

    def _build_overlay_segments(
        self,
        measurements: list[HeightLineMeasurement],
        calibration: dict[str, Any],
    ) -> list[tuple[str, np.ndarray]]:
        """把公共基准与各障碍物拟合线端点投影回图像。"""
        segments: list[tuple[str, np.ndarray]] = []
        first_measurement = measurements[0]
        ground_segments = [
            (f"obstacle_{index}", measurement.endpoints_ground)
            for index, measurement in enumerate(measurements, start=1)
        ]
        if first_measurement.baseline_fit is not None:
            baseline_xy = first_measurement.baseline_fit.endpoints_xy
            if first_measurement.ground_profile_fit is None:
                baseline_z = np.full(2, first_measurement.ground_baseline_zg_mm)
            else:
                baseline_z = first_measurement.ground_profile_fit.predict_z(
                    baseline_xy
                )
            baseline_endpoints = np.column_stack(
                [baseline_xy, baseline_z]
            )
            ground_segments.insert(0, ("baseline", baseline_endpoints))
        for kind, endpoints_ground in ground_segments:
            pixels = project_ground_points_to_pixels(
                endpoints_ground, calibration
            )
            if np.isfinite(pixels).all():
                # 测量叠加绘制在 ROI 局部图像上，投影坐标则属于全幅标定图像。
                pixels = pixels - np.asarray(self._image_offset, dtype=np.float64)
                segments.append((kind, pixels))
        return segments

    def _clear_obstacle_result_groups(self) -> None:
        for group in self._obstacle_result_groups:
            self._obstacle_results_layout.removeWidget(group)
            group.deleteLater()
        self._obstacle_result_groups.clear()

    def _update_results_panel(
        self, measurements: list[HeightLineMeasurement]
    ) -> None:
        self._clear_obstacle_result_groups()
        reference = measurements[0]
        ground_suffix = (
            " (固定)" if reference.ground_reference_mode == "zg_zero" else ""
        )
        self._result_labels["ground"].setText(
            f"{reference.ground_baseline_zg_mm:.3f}{ground_suffix}"
        )
        ground_sigma = reference.ground_noise_sigma_mm
        self._result_labels["ground_sigma"].setText(
            "—" if ground_sigma is None else f"{ground_sigma:.3f}"
        )
        if reference.baseline_fit is not None:
            baseline_counts = (
                f"{reference.baseline_inlier_count}/"
                f"{reference.baseline_point_count}"
            )
        else:
            baseline_counts = "固定 Zg=0"
        self._result_labels["baseline_points"].setText(baseline_counts)

        session_stage_a = self._stage_a_height_result(None)
        self._result_labels["stage_a_enabled"].setText(
            "开启" if session_stage_a.stage_a_enabled else "关闭"
        )
        self._result_labels["stage_a_domain"].setText(
            self._stage_a_domain_text()
        )
        self._result_labels["session_ground_reference"].setText(
            "VALID · 已应用" if self._ground_reference is not None else "未启用"
        )
        reference_modes = {measurement.ground_reference_mode for measurement in measurements}
        self._result_labels["ground_reference_mode"].setText(
            self._display_ground_reference_mode(
                reference.ground_reference_mode
                if len(reference_modes) == 1
                else "mixed"
            )
        )

        for index, measurement in enumerate(measurements, start=1):
            group = QGroupBox(f"障碍物 {index}")
            form = QVBoxLayout(group)
            angle = measurement.angle_with_baseline_deg
            stage_a = self._stage_a_height_result(measurement.height_mean_mm)
            raw_height = (
                "—"
                if stage_a.height_raw is None
                else f"{stage_a.height_raw:.3f} mm"
            )
            stage_a_height = (
                "—"
                if stage_a.height_stage_a is None
                else f"{stage_a.height_stage_a:.3f} mm"
            )
            rows = (
                ("原始高度 height_raw (均值)", raw_height),
                ("补偿高度 height_stage_a", stage_a_height),
                ("Stage-A 状态", self._display_stage_a_status(stage_a.stage_a_status)),
                ("高度 σ (raw)", f"{measurement.height_std_mm:.3f} mm"),
                ("高度 中位数 (raw)", f"{measurement.height_median_mm:.3f} mm"),
                ("长度", f"{measurement.length_mm:.3f}"),
                ("与基准线夹角", "—" if angle is None else f"{angle:.2f}°"),
                ("拟合 RMSE", f"{measurement.height_fit.rmse_mm:.3f}"),
                (
                    "内点/总点",
                    f"{measurement.height_inlier_count}/"
                    f"{measurement.height_point_count}",
                ),
            )
            for title, value in rows:
                label = QLabel(f"{title}: {value}", group)
                label.setWordWrap(True)
                label.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                )
                form.addWidget(label)
            self._obstacle_results_layout.addWidget(group)
            self._obstacle_result_groups.append(group)

    def _format_height_status(
        self, index: int, measurement: HeightLineMeasurement
    ) -> str:
        """Format both raw and Stage-A values without changing measurement data."""
        stage_a = self._stage_a_height_result(measurement.height_mean_mm)
        raw = "—" if stage_a.height_raw is None else f"{stage_a.height_raw:.3f}"
        corrected = (
            "—"
            if stage_a.height_stage_a is None
            else f"{stage_a.height_stage_a:.3f}"
        )
        return (
            f"障碍物{index} raw {raw} mm / stage_a {corrected} mm "
            f"({self._display_stage_a_status(stage_a.stage_a_status)})"
        )

    def _stage_a_domain_text(self) -> str:
        config = self._app_config
        stage_a_config = (
            config.correction.stage_a_height_scale
            if config is not None
            else None
        )
        if stage_a_config is None:
            return "—"
        lower, upper = stage_a_config.valid_height_mm
        return f"{lower:.1f}–{upper:.1f} mm"

    @staticmethod
    def _display_ground_reference_mode(mode: str) -> str:
        return {
            "baseline_roi_profile": "基准 ROI 地面拟合",
            "zg_zero": "固定 Zg=0",
            "mixed": "多个模式（请检查）",
        }.get(mode, mode)

    @staticmethod
    def _display_stage_a_status(status: str) -> str:
        return {
            "applied": "已应用",
            "out_of_valid_domain": "超出有效域，保留 raw",
            "disabled": "未启用",
            "unsupported_system": "非 Daheng，不适用",
            "not_configured": "未配置",
            "mode_not_stage_a": "当前模式非 Stage-A",
            "not_measured": "未测量",
            "invalid_height": "高度无效",
        }.get(status, status)

    def _save_results(self) -> None:
        """保存二维提取结果，并按当前处理阶段追加三维与测量结果。"""
        self.save_requested.emit()
        if self._image_path is None or len(self._laser_centers) == 0:
            QMessageBox.information(
                self, "无结果", "请先加载图像并提取激光线，再保存结果"
            )
            return

        config = self._app_config
        save_full_ply = (
            config is None
            or config.output is None
            or config.output.save_full_pointcloud_ply
        )
        reconstruction_error: str | None = None
        if (
            save_full_ply
            and self._last_full_reconstruction is None
            and config is not None
        ):
            try:
                full_reconstruction = self._ensure_full_laser_reconstruction()
                if full_reconstruction is None:
                    reconstruction_error = "标定不可用"
            except ReconstructionInputError as error:
                reconstruction_error = str(error)

        target_dir = next_measurement_dir(
            self._image_path, self._output_directory
        )
        payload = self._measurement_payload(self._last_measurements)
        try:
            laser_csv_path = save_laser_centers_csv(
                target_dir / "laser_center.csv",
                self._centers_in_calibration_coordinates(self._laser_centers),
            )
            self._last_laser_csv_path = laser_csv_path
            save_measurement_json(target_dir / "result.json", payload)
            if (
                self._last_measurements
                and (
                    config is None
                    or config.output is None
                    or config.output.save_pointcloud_csv
                )
            ):
                for name, recon in self._last_reconstruction.items():
                    save_reconstructed_points_csv(
                        target_dir / f"{name}_points.csv",
                        recon.pixels_uv,
                        recon.points_camera,
                        recon.points_ground,
                    )
            if config is None or config.output is None or (
                config.output.save_overlay_png
            ):
                save_image_png(
                    target_dir / "overlay.png", self._render_overlay_bgr()
                )
            if (
                self._last_full_reconstruction is not None
                and save_full_ply
            ):
                save_ground_pointcloud_ply(
                    target_dir / "full_laser_ground.ply",
                    self._last_full_reconstruction.points_ground,
                )
        except (OSError, ValueError, FileExistsError) as error:
            QMessageBox.critical(self, "保存失败", str(error))
            return
        if self._last_measurements:
            mode = "完整测量结果"
        elif self._last_full_reconstruction is not None:
            mode = "二维/三维提取结果"
        else:
            mode = "二维提取结果"
        if reconstruction_error is None:
            self.statusBar().showMessage(f"{mode}已保存到 {target_dir}")
        else:
            self.statusBar().showMessage(
                f"二维中心点已保存到 {target_dir}，PLY 未生成"
            )
            QMessageBox.warning(
                self,
                "点云未保存",
                f"二维中心点和其他可用结果已保存，但三维点云生成失败：\n"
                f"{reconstruction_error}",
            )

    def _measurement_payload(
        self, measurements: list[HeightLineMeasurement]
    ) -> dict[str, Any]:
        common = self._common_result_payload(bool(measurements))
        if not measurements:
            stage_a = self._stage_a_height_result(None)
            return {
                **common,
                **stage_a.as_dict(),
                "point_counts": {
                    "laser_centers_2d": len(self._laser_centers),
                    "full_laser_reconstructed": (
                        self._last_full_reconstruction.point_count
                        if self._last_full_reconstruction is not None
                        else 0
                    ),
                },
                "full_laser_reconstruction_filtered": (
                    self._last_full_reconstruction.filtered
                    if self._last_full_reconstruction is not None
                    else None
                ),
            }

        primary = measurements[0]
        stage_a_results = [
            self._stage_a_height_result(measurement.height_mean_mm)
            for measurement in measurements
        ]
        primary_stage_a = stage_a_results[0]
        obstacles = [
            {
                "index": index,
                "points_csv": (
                    "height_points.csv"
                    if len(measurements) == 1
                    else f"obstacle_{index}_points.csv"
                ),
                "results_mm": self._measurement_values(measurement, stage_a),
                "point_counts": {
                    "total": measurement.height_point_count,
                    "inliers": measurement.height_inlier_count,
                },
                "reconstruction_filtered": reconstruction.filtered,
            }
            for index, (measurement, reconstruction, stage_a) in enumerate(
                zip(
                    measurements,
                    self._last_obstacle_reconstructions,
                    stage_a_results,
                    strict=True,
                ),
                start=1,
            )
        ]
        return {
            **common,
            **primary_stage_a.as_dict(),
            "ground_reference_mode": primary.ground_reference_mode,
            # 兼容旧版单障碍物读取：顶层结果仍对应障碍物 1。
            "results_mm": self._measurement_values(primary, primary_stage_a),
            "obstacles": obstacles,
            "point_counts": {
                "laser_centers_2d": len(self._laser_centers),
                "full_laser_reconstructed": (
                    self._last_full_reconstruction.point_count
                    if self._last_full_reconstruction is not None
                    else 0
                ),
                "baseline_total": primary.baseline_point_count,
                "baseline_inliers": primary.baseline_inlier_count,
                "height_total": primary.height_point_count,
                "height_inliers": primary.height_inlier_count,
            },
            "reconstruction_filtered": {
                name: recon.filtered
                for name, recon in self._last_reconstruction.items()
            },
            "full_laser_reconstruction_filtered": (
                self._last_full_reconstruction.filtered
                if self._last_full_reconstruction is not None
                else None
            ),
        }

    def _stage_a_height_result(self, height_raw: float | None) -> StageAHeightResult:
        config = self._app_config
        if config is None:
            return apply_stage_a_height_scale(
                height_raw,
                system="mvs",
                enabled=False,
                correction_mode="none",
                config=None,
            )
        return apply_stage_a_height_scale(
            height_raw,
            system=self._system,
            enabled=config.correction.stage_a_height_scale_enabled,
            correction_mode=config.correction.mode,
            config=config.correction.stage_a_height_scale,
        )

    def _common_result_payload(self, measurement_performed: bool) -> dict[str, Any]:
        config = self._app_config
        payload = {
            "image": str(self._image_path),
            "config": str(config.config_path) if config else None,
            "calibration": (
                {
                    "intrinsics": str(config.calibration.intrinsics),
                    "laser_model": str(config.calibration.laser_model),
                    # 兼容旧结果读取器。
                    "laser_plane": str(config.calibration.laser_plane),
                    "extrinsics": str(config.calibration.extrinsics),
                    "ground_u_compensation": (
                        str(config.calibration.ground_u_compensation)
                        if config.calibration.ground_u_compensation
                        else None
                    ),
                }
                if config
                else None
            ),
            "extraction_method": (
                self.method_combo.currentText()
                if hasattr(self, "method_combo")
                else None
            ),
            "measurement_performed": measurement_performed,
            "ground_extrinsic_source": self._ground_extrinsic_source,
            "session_ground_reference": (
                None
                if self._ground_reference is None
                else self._ground_reference.as_dict()
            ),
            "laser_center_csv": "laser_center.csv",
            "correction": (
                {
                    "mode": config.correction.mode,
                    "stage_a_height_scale_enabled": (
                        config.correction.stage_a_height_scale_enabled
                    ),
                    "stage_a_height_scale_config": (
                        str(config.correction.stage_a_height_scale_config)
                        if config.correction.stage_a_height_scale_config
                        else None
                    ),
                }
                if config
                else {
                    "mode": "none",
                    "stage_a_height_scale_enabled": False,
                    "stage_a_height_scale_config": None,
                }
            ),
        }
        if self._image_offset != (0, 0):
            payload["image_offset"] = {
                "u": int(self._image_offset[0]),
                "v": int(self._image_offset[1]),
            }
        return payload

    def _measurement_values(
        self,
        measurement: HeightLineMeasurement,
        stage_a: StageAHeightResult,
    ) -> dict[str, Any]:
        ground_profile = None
        if measurement.ground_profile_fit is not None:
            ground_profile = {
                "model": "z_mm = slope_z_per_mm * s_mm + intercept_z_mm",
                "slope_z_per_mm": (
                    measurement.ground_profile_fit.slope_z_per_mm
                ),
                "intercept_z_mm": (
                    measurement.ground_profile_fit.intercept_z_mm
                ),
                "rmse_mm": measurement.ground_profile_fit.rmse_mm,
            }
        return {
            "height_mean": measurement.height_mean_mm,
            "height_median": measurement.height_median_mm,
            "height_std": measurement.height_std_mm,
            "height_raw": stage_a.height_raw,
            "height_stage_a": stage_a.height_stage_a,
            "stage_a_enabled": stage_a.stage_a_enabled,
            "stage_a_valid": stage_a.stage_a_valid,
            "stage_a_status": stage_a.stage_a_status,
            "length": measurement.length_mm,
            "angle_with_baseline_deg": measurement.angle_with_baseline_deg,
            "ground_baseline_zg": measurement.ground_baseline_zg_mm,
            "ground_noise_sigma": measurement.ground_noise_sigma_mm,
            "ground_reference_mode": measurement.ground_reference_mode,
            "ground_extrinsic_source": self._ground_extrinsic_source,
            "ground_profile": ground_profile,
            "height_line_fit_rmse": measurement.height_fit.rmse_mm,
            "endpoints_ground": measurement.endpoints_ground.tolist(),
        }

    def _render_overlay_bgr(self) -> np.ndarray:
        """渲染保存用叠加图：中心点、ROI 点、拟合线与结果文字。"""
        assert self._image is not None
        display = _to_uint8_display(self._image)
        canvas = cv2.cvtColor(display, cv2.COLOR_GRAY2BGR)

        def draw_points(points: np.ndarray, color: tuple[int, int, int]) -> None:
            for u, v in points:
                cv2.circle(
                    canvas,
                    (int(round(u + 0.5)), int(round(v + 0.5))),
                    1,
                    color,
                    -1,
                    lineType=cv2.LINE_AA,
                )

        draw_points(self._laser_centers, (80, 255, 0))
        draw_points(self._baseline_points, (255, 110, 40))
        draw_points(self._obstacle_points, (60, 60, 235))
        for kind, endpoints in self._last_overlay_segments:
            color = (255, 210, 0) if kind == "baseline" else (0, 170, 255)
            start = (
                int(round(endpoints[0, 0] + 0.5)),
                int(round(endpoints[0, 1] + 0.5)),
            )
            end = (
                int(round(endpoints[1, 0] + 0.5)),
                int(round(endpoints[1, 1] + 0.5)),
            )
            cv2.line(canvas, start, end, color, 2, lineType=cv2.LINE_AA)

        if self._last_measurements:
            lines = tuple(
                f"obstacle {index}: height={measurement.height_mean_mm:.3f} "
                f"+/- {measurement.height_std_mm:.3f} mm, "
                f"length={measurement.length_mm:.3f} mm"
                for index, measurement in enumerate(
                    self._last_measurements, start=1
                )
            )
            for row, text in enumerate(lines):
                cv2.putText(
                    canvas,
                    text,
                    (12, 28 + row * 26),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                    lineType=cv2.LINE_AA,
                )
        return canvas

    def _show_image_coordinates(self, x: float, y: float) -> None:
        self.statusBar().showMessage(
            f"图像坐标 x={x:.2f}, y={y:.2f} | 像素 ({int(x)}, {int(y)})"
        )

    def _clear_image_coordinates(self) -> None:
        if self._image_path is None:
            self.statusBar().showMessage("请加载灰度图像")
        else:
            self.statusBar().showMessage(f"已加载 {self._image_path.name}")
