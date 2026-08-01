"""统一读取并校验测量工具使用的标定 YAML。"""

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import yaml


_CAMERA_FILE = "camera_intrinsics.yaml"
_LASER_PLANE_FILE = "laser_plane.yaml"
_EXTRINSICS_FILE = "camera_ground_extrinsics.yaml"
_GROUND_U_FILE = "ground_u_compensation.yaml"
_DISTORTION_LENGTHS = frozenset({4, 5, 8, 12, 14})
_UNIT_ALIASES = {
    "px": "px",
    "pixel": "px",
    "pixels": "px",
    "mm": "mm",
    "millimeter": "mm",
    "millimeters": "mm",
    "1": "dimensionless",
    "dimensionless": "dimensionless",
    "unitless": "dimensionless",
}


class CalibrationConfigError(ValueError):
    """标定文件内容无效。"""


class CalibrationFileNotFoundError(FileNotFoundError):
    """必需标定文件不存在。"""


class CalibrationDimensionError(CalibrationConfigError):
    """标定参数维度错误。"""


class CalibrationUnitError(CalibrationConfigError):
    """标定参数单位错误。"""


def load_calibration(config_dir: str | Path) -> dict[str, Any]:
    """读取标定目录（固定文件名），返回统一使用 NumPy 数组的标定字典。"""
    directory = Path(config_dir)
    if not directory.is_dir():
        raise CalibrationFileNotFoundError(f"标定目录不存在: {directory}")

    return load_calibration_files(
        intrinsics=directory / _CAMERA_FILE,
        laser_plane=directory / _LASER_PLANE_FILE,
        extrinsics=directory / _EXTRINSICS_FILE,
        ground_u_compensation=directory / _GROUND_U_FILE,
        ground_u_optional=True,
    )


def load_calibration_files(
    intrinsics: str | Path,
    laser_plane: str | Path,
    extrinsics: str | Path,
    ground_u_compensation: str | Path | None = None,
    *,
    ground_u_optional: bool = False,
) -> dict[str, Any]:
    """按显式路径读取三个（外加可选 U 补偿）标定文件。

    这是换新标定时推荐使用的接口：文件可以放在任意位置、使用任意文件名，
    只要内容格式满足本模块的校验规则（见 docs/USAGE_CONFIG.md）。
    返回字典固定包含 ``K``、``D``、``plane_abcd``、``R``、``t``、
    ``ground_u_compensation``。
    """
    camera = _load_camera_intrinsics(Path(intrinsics))
    plane = _load_laser_plane(Path(laser_plane))
    pose = _load_camera_ground_extrinsics(Path(extrinsics))

    ground_u: dict[str, Any] | None = None
    if ground_u_compensation is not None:
        ground_u_path = Path(ground_u_compensation)
        if not ground_u_path.exists() and not ground_u_optional:
            raise CalibrationFileNotFoundError(
                f"标定文件不存在: {ground_u_path}"
            )
        ground_u = _load_optional_ground_u(ground_u_path)

    return {
        "K": camera["K"],
        "D": camera["D"],
        "plane_abcd": plane,
        "R": pose["R"],
        "t": pose["t"],
        "ground_u_compensation": ground_u,
    }


def _load_camera_intrinsics(path: Path) -> dict[str, np.ndarray]:
    document = _load_required_yaml(path)
    _validate_units(document, path, ("units", "pixel_unit"), {"px"})

    matrix = _required_value(document, ("K", "camera_matrix"), path, "K")
    distortion = _required_value(document, ("D", "dist_coeffs"), path, "D")
    K = _matrix(matrix, (3, 3), path, "K")
    D = _vector(distortion, path, "D")
    if len(D) not in _DISTORTION_LENGTHS:
        allowed = ", ".join(str(length) for length in sorted(_DISTORTION_LENGTHS))
        raise CalibrationDimensionError(
            f"{path.name} 的 D 长度为 {len(D)}，应为 {allowed} 之一"
        )
    return {"K": K, "D": D}


def _load_laser_plane(path: Path) -> np.ndarray:
    document = _load_required_yaml(path)
    _validate_units(document, path, ("units", "coordinate_unit"), {"mm"})

    coordinate_system = document.get("coordinate_system")
    if coordinate_system is not None and str(coordinate_system).lower() != "camera":
        raise CalibrationConfigError(
            f"{path.name} 的 coordinate_system 必须为 camera"
        )

    if "plane_abcd" in document:
        raw_plane = document["plane_abcd"]
    elif isinstance(document.get("plane"), Mapping) or isinstance(
        document.get("coefficients"), Mapping
    ):
        plane = document.get("plane") or document["coefficients"]
        raw_plane = [
            _required_value(plane, (name,), path, f"plane.{name}")
            for name in ("a", "b", "c", "d")
        ]
    else:
        raise CalibrationConfigError(
            f"{path.name} 缺少 plane_abcd / plane / coefficients"
        )

    plane_abcd = _vector(raw_plane, path, "plane_abcd", expected_length=4)
    if np.linalg.norm(plane_abcd[:3]) <= np.finfo(np.float64).eps:
        raise CalibrationConfigError(f"{path.name} 的平面法向量不能为零")
    return plane_abcd


def _load_camera_ground_extrinsics(path: Path) -> dict[str, np.ndarray]:
    document = _load_required_yaml(path)
    _validate_units(
        document,
        path,
        ("units", "translation_unit", "coordinate_unit"),
        {"mm"},
    )
    _validate_units(
        document,
        path,
        ("rotation_unit",),
        {"dimensionless"},
    )

    if "R" in document or "t" in document:
        rotation = _required_value(document, ("R",), path, "R")
        translation = _required_value(document, ("t",), path, "t")
        R = _matrix(rotation, (3, 3), path, "R")
        t = _vector(translation, path, "t", expected_length=3)
    elif "T_ground_from_camera" in document:
        transform = _matrix(
            document["T_ground_from_camera"],
            (4, 4),
            path,
            "T_ground_from_camera",
        )
        if not np.allclose(transform[3], [0.0, 0.0, 0.0, 1.0], atol=1.0e-9):
            raise CalibrationConfigError(
                f"{path.name} 的 T_ground_from_camera 最后一行必须为 [0, 0, 0, 1]"
            )
        R = np.ascontiguousarray(transform[:3, :3])
        t = np.ascontiguousarray(transform[:3, 3])
    else:
        raise CalibrationConfigError(
            f"{path.name} 缺少 R/t 或 T_ground_from_camera"
        )

    orthogonality_error = float(np.linalg.norm(R.T @ R - np.eye(3), ord="fro"))
    determinant = float(np.linalg.det(R))
    if orthogonality_error > 1.0e-6 or abs(determinant - 1.0) > 1.0e-6:
        raise CalibrationConfigError(
            f"{path.name} 的旋转矩阵无效：正交误差={orthogonality_error:.3e}，"
            f"det={determinant:.9f}"
        )
    return {"R": R, "t": t}


def _load_optional_ground_u(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.suffix.lower() == ".csv":
        return _load_ground_u_csv(path)
    if path.suffix.lower() == ".npy":
        return _load_ground_u_npy(path)

    document = _load_required_yaml(path)
    _validate_units(
        document,
        path,
        ("units", "coordinate_unit"),
        {"px", "mm"},
    )
    converted = _convert_numeric_sequences(document)
    if "sample_table" in converted:
        table = _numeric_array(converted["sample_table"], path, "sample_table")
        if table.ndim != 2 or table.shape[1] != 2:
            raise CalibrationDimensionError(
                f"{path.name} 的 sample_table 维度为 {table.shape}，应为 (N, 2)"
            )
        converted["column_u_px"] = table[:, 0]
        converted["bias_mm"] = table[:, 1]

    if "column_u_px" not in converted or "bias_mm" not in converted:
        raise CalibrationConfigError(
            f"{path.name} 缺少 column_u_px/bias_mm 或 sample_table"
        )
    columns, bias = _validate_ground_u_table(
        converted["column_u_px"], converted["bias_mm"], path
    )
    converted["column_u_px"] = columns
    converted["bias_mm"] = bias
    z_offset = _ground_u_z_offset(converted, path)
    if z_offset is not None:
        converted["z_offset_mm"] = z_offset
    converted["source_path"] = str(path.resolve())
    return converted


def _load_ground_u_npy(path: Path) -> dict[str, Any]:
    try:
        loaded = np.load(path, allow_pickle=True)
    except (OSError, ValueError) as error:
        raise CalibrationConfigError(f"Unable to read {path.name}: {error}") from error

    if isinstance(loaded, np.ndarray) and loaded.shape == ():
        loaded = loaded.item()

    if isinstance(loaded, Mapping):
        converted = dict(loaded)
        if "column_u_px" not in converted and "columns" in converted:
            converted["column_u_px"] = converted["columns"]
    elif isinstance(loaded, np.ndarray) and loaded.dtype.names is not None:
        converted = {name: loaded[name] for name in loaded.dtype.names}
        if "column_u_px" not in converted and "columns" in converted:
            converted["column_u_px"] = converted["columns"]
    else:
        table = _numeric_array(loaded, path, "ground_u_compensation")
        if table.ndim != 2 or table.shape[1] != 2:
            raise CalibrationDimensionError(
                f"{path.name} must be a dict/structured array or an (N, 2) table"
            )
        converted = {"column_u_px": table[:, 0], "bias_mm": table[:, 1]}

    if "column_u_px" not in converted or "bias_mm" not in converted:
        raise CalibrationConfigError(
            f"{path.name} must contain column_u_px/bias_mm or columns/bias_mm"
        )
    columns, bias = _validate_ground_u_table(
        converted["column_u_px"], converted["bias_mm"], path
    )
    converted["column_u_px"] = columns
    converted["bias_mm"] = bias
    z_offset = _ground_u_z_offset(converted, path)
    if z_offset is not None:
        converted["z_offset_mm"] = z_offset
    converted["source_path"] = str(path.resolve())
    return converted


def _load_ground_u_csv(path: Path) -> dict[str, Any]:
    """读取 ground_bias_validation_results_v2 输出的逐列补偿表。"""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"column_u_px", "bias_mm"}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise CalibrationConfigError(
                    f"{path.name} 必须包含列 column_u_px 和 bias_mm"
                )
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise CalibrationConfigError(f"无法读取 {path.name}: {error}") from error

    try:
        columns = np.asarray([row["column_u_px"] for row in rows], dtype=np.float64)
        bias = np.asarray([row["bias_mm"] for row in rows], dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise CalibrationConfigError(
            f"{path.name} 的 column_u_px/bias_mm 必须是数值"
        ) from error

    columns, bias = _validate_ground_u_table(columns, bias, path)
    return {
        "column_u_px": columns,
        "bias_mm": bias,
        "source_path": str(path.resolve()),
    }


def _validate_ground_u_table(
    columns: Any, bias: Any, path: Path
) -> tuple[np.ndarray, np.ndarray]:
    columns_array = _vector(columns, path, "column_u_px")
    bias_array = _vector(bias, path, "bias_mm")
    if len(columns_array) == 0:
        raise CalibrationConfigError(f"{path.name} 的补偿表不能为空")
    if len(columns_array) != len(bias_array):
        raise CalibrationDimensionError(
            f"{path.name} 的 column_u_px 与 bias_mm 长度不一致"
        )
    if np.any(np.diff(columns_array) <= 0.0):
        raise CalibrationConfigError(
            f"{path.name} 的 column_u_px 必须严格递增且不能重复"
        )
    return columns_array, bias_array


def _ground_u_z_offset(document: Mapping[str, Any], path: Path) -> float | None:
    if "z_offset_mm" in document:
        return _numeric_scalar(document["z_offset_mm"], path, "z_offset_mm")
    if "ground_z_offset_mm" in document:
        return _numeric_scalar(
            document["ground_z_offset_mm"], path, "ground_z_offset_mm"
        )
    return None


def _numeric_scalar(value: Any, path: Path, name: str) -> float:
    array = _numeric_array(value, path, name)
    if array.size != 1:
        raise CalibrationDimensionError(
            f"{path.name} 的 {name} 维度为 {array.shape}，应为单个数值"
        )
    return float(array.reshape(-1)[0])


def _load_required_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CalibrationFileNotFoundError(f"标定文件不存在: {path}")
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise CalibrationConfigError(f"无法读取 {path.name}: {error}") from error
    if not isinstance(document, Mapping):
        raise CalibrationConfigError(f"{path.name} 的顶层必须是 YAML 映射")
    return dict(document)


def _required_value(
    document: Mapping[str, Any],
    aliases: tuple[str, ...],
    path: Path,
    display_name: str,
) -> Any:
    for key in aliases:
        if key in document:
            return document[key]
    raise CalibrationConfigError(f"{path.name} 缺少参数 {display_name}")


def _matrix(
    value: Any,
    expected_shape: tuple[int, int],
    path: Path,
    name: str,
) -> np.ndarray:
    array = _numeric_array(value, path, name)
    if array.shape != expected_shape:
        raise CalibrationDimensionError(
            f"{path.name} 的 {name} 维度为 {array.shape}，应为 {expected_shape}"
        )
    return np.ascontiguousarray(array)


def _vector(
    value: Any,
    path: Path,
    name: str,
    *,
    expected_length: int | None = None,
) -> np.ndarray:
    array = _numeric_array(value, path, name)
    if array.ndim == 1:
        vector = array
    elif array.ndim == 2 and 1 in array.shape:
        vector = array.reshape(-1)
    else:
        raise CalibrationDimensionError(
            f"{path.name} 的 {name} 维度为 {array.shape}，应为一维向量"
        )
    if expected_length is not None and len(vector) != expected_length:
        raise CalibrationDimensionError(
            f"{path.name} 的 {name} 长度为 {len(vector)}，应为 {expected_length}"
        )
    return np.ascontiguousarray(vector)


def _numeric_array(value: Any, path: Path, name: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise CalibrationConfigError(
            f"{path.name} 的 {name} 必须由数值组成"
        ) from error
    if not np.isfinite(array).all():
        raise CalibrationConfigError(f"{path.name} 的 {name} 包含 NaN 或无穷值")
    return array


def _validate_units(
    document: Mapping[str, Any],
    path: Path,
    keys: tuple[str, ...],
    allowed: set[str],
) -> None:
    declared_units: set[str] = set()
    for key in keys:
        if key not in document:
            continue
        raw_unit = document[key]
        if not isinstance(raw_unit, str):
            raise CalibrationUnitError(f"{path.name} 的 {key} 必须是单位字符串")
        canonical = _UNIT_ALIASES.get(raw_unit.strip().lower())
        if canonical not in allowed:
            expected = " 或 ".join(sorted(allowed))
            raise CalibrationUnitError(
                f"{path.name} 的 {key}={raw_unit!r}，应为 {expected}"
            )
        declared_units.add(canonical)
    if len(declared_units) > 1:
        raise CalibrationUnitError(f"{path.name} 声明了相互冲突的单位")


def _convert_numeric_sequences(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _convert_numeric_sequences(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        try:
            array = np.asarray(value, dtype=np.float64)
        except (TypeError, ValueError):
            return [_convert_numeric_sequences(item) for item in value]
        if np.isfinite(array).all():
            return np.ascontiguousarray(array)
        raise CalibrationConfigError("ground_u_compensation 包含 NaN 或无穷值")
    return value
