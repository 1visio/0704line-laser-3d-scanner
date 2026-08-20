"""Experimental Daheng Stage-A height-scale correction.

Stage-A is deliberately a post-measurement height correction.  It never
changes C0/C1, lambda, reconstructed point coordinates, or Ground G(S).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any


STAGE_A_HEIGHT_SCALE_MODE = "stage_a_height_scale"
SURFACE_AWARE_MODE = "surface_aware"
NO_CORRECTION_MODE = "none"
VALID_CORRECTION_MODES = frozenset(
    {NO_CORRECTION_MODE, STAGE_A_HEIGHT_SCALE_MODE, SURFACE_AWARE_MODE}
)


class StageAConfigError(ValueError):
    """Stage-A configuration is missing, malformed, or unsafe to use."""


@dataclass(frozen=True, slots=True)
class StageAHeightScaleConfig:
    """Frozen Stage-A metadata and scale factor."""

    system: str
    status: str
    valid_height_mm: tuple[float, float]
    scale: float
    source_path: Path | None = None

    def __post_init__(self) -> None:
        system = self.system.strip().lower()
        if system != "daheng":
            raise StageAConfigError(
                "Stage-A height-scale config 仅允许 system: daheng"
            )
        if self.status != "experimental_stage_validated":
            raise StageAConfigError(
                "Stage-A height-scale config 必须保持 experimental_stage_validated"
            )
        try:
            bounds = tuple(float(value) for value in self.valid_height_mm)
        except (TypeError, ValueError) as error:
            raise StageAConfigError("valid_height_mm 必须包含两个有限数") from error
        if len(bounds) != 2 or not all(math.isfinite(value) for value in bounds):
            raise StageAConfigError("valid_height_mm 必须包含两个有限数")
        if bounds[0] > bounds[1] or bounds[0] < 0.0:
            raise StageAConfigError("valid_height_mm 必须是非负的升序范围")
        scale = float(self.scale)
        if not math.isfinite(scale) or scale <= 0.0:
            raise StageAConfigError("scale 必须是有限正数")
        object.__setattr__(self, "system", system)
        object.__setattr__(self, "valid_height_mm", bounds)
        object.__setattr__(self, "scale", scale)
        if self.source_path is not None:
            object.__setattr__(self, "source_path", Path(self.source_path).resolve())


@dataclass(frozen=True, slots=True)
class CorrectionConfig:
    """Correction mode and optional Stage-A configuration.

    ``surface_aware`` is a reserved mode only.  Its implementation is
    intentionally absent, and it cannot be enabled together with Stage-A.
    """

    mode: str = NO_CORRECTION_MODE
    stage_a_height_scale_enabled: bool = False
    stage_a_height_scale_config: Path | None = None
    stage_a_height_scale: StageAHeightScaleConfig | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, str):
            raise ValueError("correction.mode 必须是字符串")
        mode = self.mode.strip().lower()
        if mode not in VALID_CORRECTION_MODES:
            raise ValueError(
                "correction.mode 必须是 none、stage_a_height_scale 或 surface_aware"
            )
        if not isinstance(self.stage_a_height_scale_enabled, bool):
            raise ValueError("stage_a_height_scale_enabled 必须是布尔值")
        if self.stage_a_height_scale_enabled and mode != STAGE_A_HEIGHT_SCALE_MODE:
            raise ValueError(
                "stage_a_height_scale_enabled 与 correction.mode 互斥"
            )
        if mode == STAGE_A_HEIGHT_SCALE_MODE and self.stage_a_height_scale is None:
            raise ValueError(
                "correction.mode=stage_a_height_scale 必须提供 Stage-A 配置"
            )
        object.__setattr__(self, "mode", mode)
        if self.stage_a_height_scale_config is not None:
            object.__setattr__(
                self,
                "stage_a_height_scale_config",
                Path(self.stage_a_height_scale_config).resolve(),
            )


@dataclass(frozen=True, slots=True)
class StageAHeightResult:
    """Raw and post-Stage-A height values for one measured height."""

    height_raw: float | None
    height_stage_a: float | None
    stage_a_enabled: bool
    stage_a_valid: bool
    stage_a_status: str

    def as_dict(self) -> dict[str, Any]:
        """Return the stable JSON fields required by online and single-frame output."""
        return {
            "height_raw": self.height_raw,
            "height_stage_a": self.height_stage_a,
            "stage_a_enabled": self.stage_a_enabled,
            "stage_a_valid": self.stage_a_valid,
            "stage_a_status": self.stage_a_status,
        }


def load_stage_a_height_scale(path: str | Path) -> StageAHeightScaleConfig:
    """Load the independent frozen Stage-A parameter JSON."""
    config_path = Path(path)
    if not config_path.is_file():
        raise StageAConfigError(f"Stage-A 配置文件不存在: {config_path}")
    try:
        document = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StageAConfigError(
            f"无法读取 Stage-A 配置文件 {config_path}: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise StageAConfigError("Stage-A 配置根节点必须是 JSON 映射")
    if document.get("schema_version", 1) != 1:
        raise StageAConfigError("Stage-A 配置 schema_version 必须为 1")
    required = {"system", "status", "valid_height_mm", "scale"}
    missing = required - set(document)
    if missing:
        raise StageAConfigError(
            f"Stage-A 配置缺少字段: {sorted(missing)}"
        )
    try:
        return StageAHeightScaleConfig(
            system=document["system"],
            status=document["status"],
            valid_height_mm=tuple(document["valid_height_mm"]),
            scale=document["scale"],
            source_path=config_path,
        )
    except (TypeError, ValueError, KeyError) as error:
        if isinstance(error, StageAConfigError):
            raise
        raise StageAConfigError(
            f"Stage-A 配置字段非法: {config_path}: {error}"
        ) from error


def apply_stage_a_height_scale(
    height_raw: float | None,
    *,
    system: str,
    enabled: bool,
    correction_mode: str,
    config: StageAHeightScaleConfig | None,
) -> StageAHeightResult:
    """Apply Stage-A only to a final scalar height inside its valid domain.

    The valid interval is inclusive.  Disabled, unsupported, out-of-domain,
    or unmeasured values are returned unchanged (or as ``None``) and are
    explicitly labelled in ``stage_a_status``.
    """
    raw = None if height_raw is None else float(height_raw)
    mode = correction_mode.strip().lower()
    normalized_system = system.strip().lower()

    if not enabled:
        return StageAHeightResult(raw, raw, False, False, "disabled")
    if config is None:
        return StageAHeightResult(raw, raw, False, False, "not_configured")
    if mode != STAGE_A_HEIGHT_SCALE_MODE:
        return StageAHeightResult(raw, raw, False, False, "mode_not_stage_a")
    if normalized_system != config.system:
        return StageAHeightResult(raw, raw, False, False, "unsupported_system")
    if raw is None:
        return StageAHeightResult(None, None, True, False, "not_measured")
    if not math.isfinite(raw):
        return StageAHeightResult(raw, raw, True, False, "invalid_height")

    lower, upper = config.valid_height_mm
    if not lower <= raw <= upper:
        return StageAHeightResult(
            raw, raw, True, False, "out_of_valid_domain"
        )
    return StageAHeightResult(
        raw,
        config.scale * raw,
        True,
        True,
        "applied",
    )


def resolve_stage_a_height_scale(
    height_raw: float | None,
    *,
    system: str,
    correction: CorrectionConfig | None,
) -> StageAHeightResult:
    """Resolve a loaded app correction config into one height result."""
    if correction is None:
        return apply_stage_a_height_scale(
            height_raw,
            system=system,
            enabled=False,
            correction_mode=NO_CORRECTION_MODE,
            config=None,
        )
    return apply_stage_a_height_scale(
        height_raw,
        system=system,
        enabled=correction.stage_a_height_scale_enabled,
        correction_mode=correction.mode,
        config=correction.stage_a_height_scale,
    )
