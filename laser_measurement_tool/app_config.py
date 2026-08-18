"""测量工具的统一 YAML 配置入口。

所有可调项集中在一个 YAML 文件（默认 ``configs/measure_tool.yaml``）：
标定文件路径、提取算法及参数、重建约束、测量参数、输出目录。
配置里的相对路径一律相对于配置文件所在目录解析，因此整个仓库
移动位置后配置仍然有效。字段说明见 docs/USAGE_CONFIG.md。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any

import yaml

from measurement.height_measure import MeasurementParams
from reconstruction.reconstructor import ReconstructionParams


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "configs" / "measure_tool.yaml"


class AppConfigError(ValueError):
    """配置文件缺失、格式错误或数值非法。"""


@dataclass(frozen=True, slots=True)
class CalibrationPaths:
    """相机内参、激光表面模型、外参与可选补偿文件的绝对路径。

    为兼容旧代码，成员名仍保留为 ``laser_plane``；文件内容现在可以是
    global_plane、quadratic_graph 或 circular_cone。推荐使用配置键
    ``calibration.laser_model``，旧键 ``calibration.laser_plane`` 仍可读取。
    """

    intrinsics: Path
    laser_plane: Path
    extrinsics: Path
    ground_u_compensation: Path | None = None
    laser_ray_correction: Path | None = None
    manifest: Path | None = None

    @property
    def laser_model(self) -> Path:
        """激光表面模型文件路径（新名称）。"""
        return self.laser_plane


@dataclass(frozen=True, slots=True)
class OutputConfig:
    """结果输出目录与开关。"""

    directory: Path
    save_pointcloud_csv: bool = True
    save_overlay_png: bool = True
    save_full_pointcloud_ply: bool = True


@dataclass(frozen=True, slots=True)
class CameraStartupConfig:
    """在线相机启动参数；配置未声明 camera 段时保持原有界面默认值。"""

    exposure_us: float = 600.0
    gain_db: float = 0.0
    pixel_format: str = "Mono8"
    offset_x: int = 0
    offset_y: int = 880
    width: int = 2448
    height: int = 300
    timeout_ms: int = 2000

    def __post_init__(self) -> None:
        if self.exposure_us <= 0 or not math.isfinite(self.exposure_us):
            raise ValueError("exposure_us 必须是有限正数")
        if not math.isfinite(self.gain_db):
            raise ValueError("gain_db 必须是有限数")
        if self.pixel_format not in {"Mono8", "Mono12"}:
            raise ValueError("pixel_format 必须是 Mono8 或 Mono12")
        if min(self.offset_x, self.offset_y) < 0:
            raise ValueError("ROI 偏移不能为负数")
        if min(self.width, self.height, self.timeout_ms) <= 0:
            raise ValueError("ROI 尺寸和 timeout_ms 必须为正数")


@dataclass(frozen=True, slots=True)
class AppConfig:
    """加载并校验后的应用配置。"""

    config_path: Path
    calibration: CalibrationPaths
    extraction_method: str
    extraction_options: dict[str, Any] = field(default_factory=dict)
    extraction_options_by_method: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )
    reconstruction: ReconstructionParams = field(
        default_factory=ReconstructionParams
    )
    measurement: MeasurementParams = field(default_factory=MeasurementParams)
    output: OutputConfig | None = None
    camera: CameraStartupConfig | None = None


def load_app_config(config_path: str | Path | None = None) -> AppConfig:
    """读取并校验配置文件；``None`` 表示使用默认路径。"""
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    if not path.is_file():
        raise AppConfigError(f"配置文件不存在: {path}")
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise AppConfigError(f"无法读取配置文件 {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise AppConfigError(f"{path} 的顶层必须是 YAML 映射")

    base_dir = path.resolve().parent

    calibration = _parse_calibration(document, base_dir, path)
    method, options, options_by_method = _parse_extraction(document, path)
    reconstruction = _build_dataclass(
        document.get("reconstruction"), ReconstructionParams, "reconstruction"
    )
    measurement = _build_dataclass(
        document.get("measurement"), MeasurementParams, "measurement"
    )
    output = _parse_output(document, base_dir)
    camera = (
        None
        if document.get("camera") is None
        else _build_dataclass(
            document.get("camera"), CameraStartupConfig, "camera"
        )
    )

    return AppConfig(
        config_path=path.resolve(),
        calibration=calibration,
        extraction_method=method,
        extraction_options=options,
        extraction_options_by_method=options_by_method,
        reconstruction=reconstruction,
        measurement=measurement,
        output=output,
        camera=camera,
    )


def _resolve_path(value: Any, base_dir: Path, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise AppConfigError(f"{name} 必须是非空路径字符串")
    raw = Path(value)
    return raw if raw.is_absolute() else (base_dir / raw).resolve()


def _parse_calibration(
    document: Mapping[str, Any], base_dir: Path, path: Path
) -> CalibrationPaths:
    section = document.get("calibration")
    if not isinstance(section, Mapping):
        raise AppConfigError(f"{path} 缺少 calibration 段")
    ground_u_value = section.get("ground_u_compensation")
    laser_ray_correction_value = section.get("laser_ray_correction")
    manifest_value = section.get("manifest")
    laser_model_value = section.get("laser_model")
    legacy_laser_plane_value = section.get("laser_plane")
    if (
        laser_model_value not in (None, "")
        and legacy_laser_plane_value not in (None, "")
        and str(laser_model_value).strip()
        != str(legacy_laser_plane_value).strip()
    ):
        raise AppConfigError(
            "calibration.laser_model 与 calibration.laser_plane 同时存在且不一致；"
            "请只保留一个"
        )
    selected_laser_model = (
        laser_model_value
        if laser_model_value not in (None, "")
        else legacy_laser_plane_value
    )
    return CalibrationPaths(
        intrinsics=_resolve_path(
            section.get("intrinsics"), base_dir, "calibration.intrinsics"
        ),
        laser_plane=_resolve_path(
            selected_laser_model, base_dir, "calibration.laser_model"
        ),
        extrinsics=_resolve_path(
            section.get("extrinsics"), base_dir, "calibration.extrinsics"
        ),
        ground_u_compensation=(
            None
            if ground_u_value in (None, "")
            else _resolve_path(
                ground_u_value, base_dir, "calibration.ground_u_compensation"
            )
        ),
        laser_ray_correction=(
            None
            if laser_ray_correction_value in (None, "")
            else _resolve_path(
                laser_ray_correction_value,
                base_dir,
                "calibration.laser_ray_correction",
            )
        ),
        manifest=(
            None
            if manifest_value in (None, "")
            else _resolve_path(manifest_value, base_dir, "calibration.manifest")
        ),
    )


def _parse_extraction(
    document: Mapping[str, Any], path: Path
) -> tuple[str, dict[str, Any], dict[str, dict[str, Any]]]:
    section = document.get("extraction")
    if not isinstance(section, Mapping):
        raise AppConfigError(f"{path} 缺少 extraction 段")
    method = section.get("method")
    if not isinstance(method, str) or not method.strip():
        raise AppConfigError("extraction.method 必须是非空字符串")
    method = method.strip()

    options_by_method: dict[str, dict[str, Any]] = {}
    profile_options: dict[str, Any] = {}
    profile_value = section.get("profile")
    if profile_value not in (None, ""):
        if not isinstance(profile_value, str):
            raise AppConfigError("extraction.profile 必须是路径字符串")
        profile_path = (path.resolve().parent / profile_value).resolve()
        try:
            profile_document = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        except (OSError, UnicodeError, yaml.YAMLError) as error:
            raise AppConfigError(f"无法读取 extraction.profile {profile_path}: {error}") from error
        if not isinstance(profile_document, Mapping):
            raise AppConfigError(f"extraction.profile 根节点必须是映射: {profile_path}")
        profile_options = profile_document.get("steger", profile_document.get("options", {}))
        if not isinstance(profile_options, Mapping):
            raise AppConfigError(f"extraction.profile 缺少 steger 映射: {profile_path}")
        profile_options = dict(profile_options)

    for key, value in section.items():
        if key in {"method", "profile"}:
            continue
        if value is None:
            options_by_method[str(key)] = {}
        elif isinstance(value, Mapping):
            options_by_method[str(key)] = dict(value)
        else:
            raise AppConfigError(f"extraction.{key} 必须是参数映射")

    if profile_options:
        merged = dict(profile_options)
        merged.update(options_by_method.get("steger", {}))
        options_by_method["steger"] = merged

        # ``shared_steger`` 是旧名称。存在 profile 时强制把它归一化为
        # 同一组实时参数，旧配置中的 sigma_px 仍可作为 sigma 覆盖项。
        shared_inline = options_by_method.get("shared_steger", {})
        shared = dict(profile_options)
        for key, value in shared_inline.items():
            canonical = "sigma" if key == "sigma_px" else key
            if canonical in profile_options:
                shared[canonical] = value
        options_by_method["shared_steger"] = shared

    options = options_by_method.get(method, {})
    return method, dict(options), options_by_method


def _build_dataclass(section: Any, cls: type[Any], name: str) -> Any:
    if section is None:
        return cls()
    if not isinstance(section, Mapping):
        raise AppConfigError(f"{name} 段必须是映射")
    valid_fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    unknown = set(section) - valid_fields
    if unknown:
        raise AppConfigError(f"{name} 段包含未知参数: {sorted(unknown)}")
    try:
        return cls(**dict(section))
    except (TypeError, ValueError) as error:
        raise AppConfigError(f"{name} 段参数非法: {error}") from error


def _parse_output(
    document: Mapping[str, Any], base_dir: Path
) -> OutputConfig | None:
    section = document.get("output")
    if section is None:
        return None
    if not isinstance(section, Mapping):
        raise AppConfigError("output 段必须是映射")
    directory = _resolve_path(section.get("dir"), base_dir, "output.dir")
    return OutputConfig(
        directory=directory,
        save_pointcloud_csv=bool(section.get("save_pointcloud_csv", True)),
        save_overlay_png=bool(section.get("save_overlay_png", True)),
        save_full_pointcloud_ply=bool(
            section.get("save_full_pointcloud_ply", True)
        ),
    )
