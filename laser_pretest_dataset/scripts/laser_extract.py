"""Core extraction and metric routines for line-laser pretest images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
import yaml


@dataclass(frozen=True)
class RoiConfig:
    x: int
    y: int
    width: int | None
    height: int | None


@dataclass(frozen=True)
class GaussianConfig:
    enabled: bool
    kernel_size: int
    sigma: float


@dataclass(frozen=True)
class ExtractionConfig:
    peak_window_radius: int
    min_peak_intensity: float
    fwhm_ratio: float
    min_fwhm_px: float
    max_fwhm_px: float


@dataclass(frozen=True)
class PlotConfig:
    dpi: int
    figsize: tuple[float, float]
    display_min: float
    display_max: float | None
    line_width: float


@dataclass(frozen=True)
class AnalysisConfig:
    roi: RoiConfig
    gaussian: GaussianConfig
    extraction: ExtractionConfig
    profile_x_positions: tuple[int, ...]
    repeatability_x_positions: tuple[int, ...]
    plot: PlotConfig


@dataclass(frozen=True)
class ResolvedRoi:
    x: int
    y: int
    width: int
    height: int

    @property
    def x_end(self) -> int:
        return self.x + self.width

    @property
    def y_end(self) -> int:
        return self.y + self.height


@dataclass
class FrameResult:
    frame_name: str
    image: np.ndarray
    roi: ResolvedRoi
    x_px: np.ndarray
    peak_y_px: np.ndarray
    center_y_px: np.ndarray
    peak_intensity: np.ndarray
    fwhm_px: np.ndarray
    valid: np.ndarray


@dataclass
class RepeatabilityResult:
    x_px: np.ndarray
    center_std_px: np.ndarray
    valid_frame_count: np.ndarray


def load_config(path: str | Path) -> AnalysisConfig:
    """Load and strictly validate the YAML analysis configuration."""
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read config file: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping")

    roi_raw = _mapping(raw, "roi")
    gaussian_raw = _mapping(raw, "gaussian_filter")
    extraction_raw = _mapping(raw, "extraction")
    profiles_raw = _mapping(raw, "profiles")
    repeatability_raw = _mapping(raw, "repeatability")
    plot_raw = _mapping(raw, "plot")

    roi = RoiConfig(
        x=_nonnegative_int(roi_raw.get("x"), "roi.x"),
        y=_nonnegative_int(roi_raw.get("y"), "roi.y"),
        width=_optional_positive_int(roi_raw.get("width"), "roi.width"),
        height=_optional_positive_int(roi_raw.get("height"), "roi.height"),
    )

    enabled = gaussian_raw.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("gaussian_filter.enabled must be true or false")
    kernel_size = _positive_int(
        gaussian_raw.get("kernel_size"), "gaussian_filter.kernel_size"
    )
    if kernel_size % 2 == 0:
        raise ValueError("gaussian_filter.kernel_size must be odd")
    sigma = _nonnegative_number(gaussian_raw.get("sigma"), "gaussian_filter.sigma")
    gaussian = GaussianConfig(enabled, kernel_size, sigma)

    radius = _positive_int(
        extraction_raw.get("peak_window_radius"),
        "extraction.peak_window_radius",
    )
    min_peak = _nonnegative_number(
        extraction_raw.get("min_peak_intensity"),
        "extraction.min_peak_intensity",
    )
    ratio = _number(extraction_raw.get("fwhm_ratio"), "extraction.fwhm_ratio")
    if not 0.0 < ratio < 1.0:
        raise ValueError("extraction.fwhm_ratio must be in (0, 1)")
    min_width = _positive_number(
        extraction_raw.get("min_fwhm_px"), "extraction.min_fwhm_px"
    )
    max_width = _positive_number(
        extraction_raw.get("max_fwhm_px"), "extraction.max_fwhm_px"
    )
    if max_width <= min_width:
        raise ValueError("extraction.max_fwhm_px must exceed min_fwhm_px")
    extraction = ExtractionConfig(radius, min_peak, ratio, min_width, max_width)

    profile_positions = _position_list(
        profiles_raw.get("x_positions"), "profiles.x_positions"
    )
    repeatability_positions = _position_list(
        repeatability_raw.get("x_positions"), "repeatability.x_positions"
    )

    dpi = _positive_int(plot_raw.get("dpi"), "plot.dpi")
    figsize_raw = plot_raw.get("figsize")
    if (
        not isinstance(figsize_raw, list)
        or len(figsize_raw) != 2
        or any(not isinstance(value, (int, float)) for value in figsize_raw)
        or any(float(value) <= 0.0 for value in figsize_raw)
    ):
        raise ValueError("plot.figsize must contain two positive numbers")
    display_min = _nonnegative_number(plot_raw.get("display_min"), "plot.display_min")
    display_max_raw = plot_raw.get("display_max")
    display_max = (
        None
        if display_max_raw is None
        else _positive_number(display_max_raw, "plot.display_max")
    )
    if display_max is not None and display_max <= display_min:
        raise ValueError("plot.display_max must exceed display_min")
    line_width = _positive_number(plot_raw.get("line_width"), "plot.line_width")
    plot = PlotConfig(
        dpi=dpi,
        figsize=(float(figsize_raw[0]), float(figsize_raw[1])),
        display_min=display_min,
        display_max=display_max,
        line_width=line_width,
    )

    return AnalysisConfig(
        roi=roi,
        gaussian=gaussian,
        extraction=extraction,
        profile_x_positions=profile_positions,
        repeatability_x_positions=repeatability_positions,
        plot=plot,
    )


def read_grayscale_image(path: str | Path) -> np.ndarray:
    """Read an 8/16-bit grayscale PNG without normalization or conversion."""
    image_path = Path(path)
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    if image.ndim != 2:
        raise ValueError(f"Image must be single-channel grayscale: {image_path}")
    if image.dtype not in (np.dtype(np.uint8), np.dtype(np.uint16)):
        raise ValueError(
            f"Image must use uint8 or uint16 pixels, got {image.dtype}: {image_path}"
        )
    return image


def resolve_roi(image_shape: tuple[int, int], config: RoiConfig) -> ResolvedRoi:
    height, width = image_shape
    roi_width = width - config.x if config.width is None else config.width
    roi_height = height - config.y if config.height is None else config.height
    roi = ResolvedRoi(config.x, config.y, roi_width, roi_height)
    if roi.width <= 0 or roi.height <= 0:
        raise ValueError("ROI has no pixels")
    if roi.x_end > width or roi.y_end > height:
        raise ValueError(
            f"ROI [{roi.x}:{roi.x_end}, {roi.y}:{roi.y_end}] exceeds "
            f"image size {width}x{height}"
        )
    return roi


def validate_sample_positions(config: AnalysisConfig, roi: ResolvedRoi) -> None:
    for label, positions in (
        ("profiles.x_positions", config.profile_x_positions),
        ("repeatability.x_positions", config.repeatability_x_positions),
    ):
        outside = [x for x in positions if not roi.x <= x < roi.x_end]
        if outside:
            raise ValueError(
                f"{label} contains positions outside ROI "
                f"[{roi.x}, {roi.x_end}): {outside}"
            )


def analyze_frame(
    image: np.ndarray,
    frame_name: str,
    config: AnalysisConfig,
    roi: ResolvedRoi | None = None,
) -> FrameResult:
    """Extract a subpixel center and FWHM for each ROI column."""
    if image.ndim != 2 or image.dtype not in (np.dtype(np.uint8), np.dtype(np.uint16)):
        raise ValueError("analyze_frame expects a uint8/uint16 grayscale image")
    resolved = resolve_roi(image.shape, config.roi) if roi is None else roi
    validate_sample_positions(config, resolved)
    raw_roi = image[resolved.y : resolved.y_end, resolved.x : resolved.x_end]

    if config.gaussian.enabled:
        detection_roi = cv2.GaussianBlur(
            raw_roi,
            (config.gaussian.kernel_size, config.gaussian.kernel_size),
            config.gaussian.sigma,
        )
    else:
        detection_roi = raw_roi

    peak_rows = detection_roi.argmax(axis=0).astype(np.int64)
    columns = np.arange(resolved.width, dtype=np.int64)
    raw_peaks = raw_roi[peak_rows, columns].astype(np.float64)
    centers = np.full(resolved.width, np.nan, dtype=np.float64)
    widths = np.full(resolved.width, np.nan, dtype=np.float64)
    valid = np.zeros(resolved.width, dtype=bool)
    radius = config.extraction.peak_window_radius

    for column, peak_row in enumerate(peak_rows):
        if raw_peaks[column] < config.extraction.min_peak_intensity:
            continue
        start = int(peak_row) - radius
        end = int(peak_row) + radius + 1
        if start < 0 or end > resolved.height:
            continue

        weights = raw_roi[start:end, column].astype(np.float64, copy=False)
        weight_sum = float(weights.sum())
        if weight_sum <= 0.0:
            continue
        y_local = np.arange(start, end, dtype=np.float64)
        center_local = float(np.dot(y_local, weights) / weight_sum)
        width = _fwhm_width(
            raw_roi[:, column],
            int(peak_row),
            config.extraction.fwhm_ratio,
        )
        if not np.isfinite(width):
            continue
        if not config.extraction.min_fwhm_px <= width <= config.extraction.max_fwhm_px:
            continue

        centers[column] = center_local + resolved.y
        widths[column] = width
        valid[column] = True

    return FrameResult(
        frame_name=frame_name,
        image=image,
        roi=resolved,
        x_px=np.arange(resolved.x, resolved.x_end, dtype=np.float64),
        peak_y_px=peak_rows.astype(np.float64) + resolved.y,
        center_y_px=centers,
        peak_intensity=raw_peaks,
        fwhm_px=widths,
        valid=valid,
    )


def calculate_repeatability(results: Iterable[FrameResult]) -> RepeatabilityResult:
    frames = list(results)
    if not frames:
        raise ValueError("Repeatability requires at least one frame")
    reference_x = frames[0].x_px
    if any(
        frame.x_px.shape != reference_x.shape
        or not np.array_equal(frame.x_px, reference_x)
        for frame in frames[1:]
    ):
        raise ValueError("All frames must use the same ROI columns")

    centers = np.vstack([frame.center_y_px for frame in frames])
    valid = np.vstack([frame.valid & np.isfinite(frame.center_y_px) for frame in frames])
    counts = valid.sum(axis=0)
    std = np.full(reference_x.size, np.nan, dtype=np.float64)
    for column in np.flatnonzero(counts >= 2):
        std[column] = np.std(centers[valid[:, column], column], ddof=1)
    return RepeatabilityResult(reference_x.copy(), std, counts)


def summarize_frame(result: FrameResult) -> dict[str, int | float]:
    valid = result.valid
    summary: dict[str, int | float] = {
        "valid_column_count": int(valid.sum()),
        "column_count": int(valid.size),
        "valid_ratio": float(valid.mean()) if valid.size else 0.0,
    }
    _add_distribution(summary, "peak_intensity", result.peak_intensity[valid])
    _add_distribution(summary, "fwhm_px", result.fwhm_px[valid])
    return summary


def summarize_group(
    results: Iterable[FrameResult], repeatability: RepeatabilityResult
) -> dict[str, int | float]:
    frames = list(results)
    valid = np.concatenate([frame.valid for frame in frames])
    intensities = np.concatenate(
        [frame.peak_intensity[frame.valid] for frame in frames]
    )
    widths = np.concatenate([frame.fwhm_px[frame.valid] for frame in frames])
    repeatable = np.isfinite(repeatability.center_std_px)
    summary: dict[str, int | float] = {
        "frame_count_actual": len(frames),
        "valid_column_count": int(valid.sum()),
        "column_count": int(valid.size),
        "valid_ratio": float(valid.mean()) if valid.size else 0.0,
        "repeatable_column_count": int(repeatable.sum()),
        "repeatable_column_ratio": (
            float(repeatable.mean()) if repeatable.size else 0.0
        ),
    }
    _add_distribution(summary, "peak_intensity", intensities)
    _add_distribution(summary, "fwhm_px", widths)
    std_values = repeatability.center_std_px[repeatable]
    if std_values.size:
        summary.update(
            {
                "center_std_px_median": float(np.median(std_values)),
                "center_std_px_p95": float(np.percentile(std_values, 95.0)),
                "center_std_px_max": float(np.max(std_values)),
            }
        )
    else:
        summary.update(
            {
                "center_std_px_median": float("nan"),
                "center_std_px_p95": float("nan"),
                "center_std_px_max": float("nan"),
            }
        )
    return summary


def _fwhm_width(profile: np.ndarray, peak_row: int, ratio: float) -> float:
    values = profile.astype(np.float64, copy=False)
    peak = float(values[peak_row])
    if peak <= 0.0:
        return float("nan")
    threshold = peak * ratio

    left = peak_row
    while left > 0 and values[left] >= threshold:
        left -= 1
    if values[left] >= threshold:
        return float("nan")
    left_crossing = _linear_crossing(
        left,
        float(values[left]),
        left + 1,
        float(values[left + 1]),
        threshold,
    )

    right = peak_row
    last = values.size - 1
    while right < last and values[right] >= threshold:
        right += 1
    if values[right] >= threshold:
        return float("nan")
    right_crossing = _linear_crossing(
        right - 1,
        float(values[right - 1]),
        right,
        float(values[right]),
        threshold,
    )
    width = right_crossing - left_crossing
    return float(width) if width > 0.0 else float("nan")


def _linear_crossing(
    x0: int, y0: float, x1: int, y1: float, threshold: float
) -> float:
    if y1 == y0:
        return float(x0)
    return float(x0 + (threshold - y0) * (x1 - x0) / (y1 - y0))


def _add_distribution(
    summary: dict[str, int | float], prefix: str, values: np.ndarray
) -> None:
    finite = values[np.isfinite(values)]
    if finite.size:
        summary[f"{prefix}_mean"] = float(np.mean(finite))
        summary[f"{prefix}_median"] = float(np.median(finite))
        summary[f"{prefix}_std"] = float(np.std(finite, ddof=0))
        summary[f"{prefix}_p95"] = float(np.percentile(finite, 95.0))
    else:
        for suffix in ("mean", "median", "std", "p95"):
            summary[f"{prefix}_{suffix}"] = float("nan")


def _mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    return float(value)


def _positive_number(value: Any, label: str) -> float:
    result = _number(value, label)
    if result <= 0.0:
        raise ValueError(f"{label} must be positive")
    return result


def _nonnegative_number(value: Any, label: str) -> float:
    result = _number(value, label)
    if result < 0.0:
        raise ValueError(f"{label} must be nonnegative")
    return result


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _optional_positive_int(value: Any, label: str) -> int | None:
    return None if value is None else _positive_int(value, label)


def _position_list(value: Any, label: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty integer list")
    positions: list[int] = []
    for item in value:
        positions.append(_nonnegative_int(item, label))
    if len(set(positions)) != len(positions):
        raise ValueError(f"{label} must not contain duplicates")
    return tuple(positions)
