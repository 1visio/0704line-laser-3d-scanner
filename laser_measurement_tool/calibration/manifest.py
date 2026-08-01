"""Runtime calibration package integrity and provenance checks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config_loader import CalibrationConfigError, load_calibration_files


class CalibrationManifestError(CalibrationConfigError):
    """The runtime package manifest is missing, unsafe, or inconsistent."""


@dataclass(frozen=True, slots=True)
class CalibrationPackage:
    manifest_path: Path
    package_id: str
    camera_model: str
    image_width: int
    image_height: int
    algorithm: str
    manifest_sha256: str
    calibration: dict[str, Any]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_calibration_package(manifest_path: str | Path) -> CalibrationPackage:
    """Validate a self-contained manifest and load its calibration arrays."""
    path = Path(manifest_path).resolve()
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise CalibrationManifestError(f"无法读取标定清单 {path}: {error}") from error
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise CalibrationManifestError("标定清单 schema_version 必须为 1")

    package_id = _required_text(document, "package_id")
    camera = document.get("camera")
    if not isinstance(camera, dict):
        raise CalibrationManifestError("标定清单缺少 camera")
    camera_model = _required_text(camera, "model")
    image_width = _positive_int(camera.get("image_width"), "camera.image_width")
    image_height = _positive_int(camera.get("image_height"), "camera.image_height")

    extractor = document.get("extractor")
    if not isinstance(extractor, dict):
        raise CalibrationManifestError("标定清单缺少 extractor")
    algorithm = _required_text(extractor, "algorithm")
    if algorithm != "shared_steger":
        raise CalibrationManifestError(
            f"生产标定包必须使用 shared_steger，实际为 {algorithm!r}"
        )

    files = document.get("files")
    required = ("intrinsics", "laser_plane", "extrinsics", "ground_u_compensation")
    if not isinstance(files, dict) or any(name not in files for name in required):
        raise CalibrationManifestError(f"标定清单 files 必须包含 {required}")
    resolved: dict[str, Path] = {}
    for name in required:
        entry = files[name]
        if not isinstance(entry, dict):
            raise CalibrationManifestError(f"files.{name} 必须是映射")
        relative = Path(_required_text(entry, "path"))
        if relative.is_absolute() or ".." in relative.parts:
            raise CalibrationManifestError(f"files.{name}.path 必须是包内相对路径")
        file_path = (path.parent / relative).resolve()
        try:
            file_path.relative_to(path.parent)
        except ValueError as error:
            raise CalibrationManifestError(f"files.{name}.path 越出标定包") from error
        expected_hash = _required_text(entry, "sha256").lower()
        if len(expected_hash) != 64:
            raise CalibrationManifestError(f"files.{name}.sha256 格式错误")
        if not file_path.is_file():
            raise CalibrationManifestError(f"标定文件不存在: {file_path}")
        actual_hash = sha256_file(file_path)
        if actual_hash != expected_hash:
            raise CalibrationManifestError(
                f"标定文件哈希不匹配: {file_path.name}\n"
                f"期望 {expected_hash}\n实际 {actual_hash}"
            )
        resolved[name] = file_path

    calibration = load_calibration_files(
        resolved["intrinsics"],
        resolved["laser_plane"],
        resolved["extrinsics"],
        resolved["ground_u_compensation"],
    )
    return CalibrationPackage(
        manifest_path=path,
        package_id=package_id,
        camera_model=camera_model,
        image_width=image_width,
        image_height=image_height,
        algorithm=algorithm,
        manifest_sha256=sha256_file(path),
        calibration=calibration,
    )


def _required_text(document: dict[str, Any], name: str) -> str:
    value = document.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CalibrationManifestError(f"{name} 必须是非空字符串")
    return value.strip()


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CalibrationManifestError(f"{name} 必须是正整数")
    return value
