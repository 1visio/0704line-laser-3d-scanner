"""Publication-style plots for line-laser pretest quality analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from laser_extract import AnalysisConfig, FrameResult, RepeatabilityResult


def configure_plot_style() -> None:
    plt.rcParams.update(
        {
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.alpha": 0.25,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def experiment_title(metadata: Mapping[str, object]) -> str:
    fields = (
        ("exp_id", "exp"),
        ("exposure_us", "exposure"),
        ("gain", "gain"),
        ("material", "material"),
        ("distance_mm", "distance"),
        ("baseline_mm", "baseline"),
        ("laser_angle_deg", "angle"),
    )
    parts: list[str] = []
    for key, label in fields:
        value = metadata.get(key, "")
        if value not in (None, ""):
            suffix = {
                "exposure_us": " us",
                "distance_mm": " mm",
                "baseline_mm": " mm",
                "laser_angle_deg": " deg",
            }.get(key, "")
            parts.append(f"{label}={value}{suffix}")
    return " | ".join(parts)


def plot_raw_with_roi(
    result: FrameResult,
    metadata: Mapping[str, object],
    config: AnalysisConfig,
    output_path: str | Path,
) -> None:
    fig, ax = _figure(config)
    vmin, vmax = _display_limits(result.image, config)
    image_artist = ax.imshow(result.image, cmap="gray", vmin=vmin, vmax=vmax)
    roi = result.roi
    ax.add_patch(
        Rectangle(
            (roi.x - 0.5, roi.y - 0.5),
            roi.width,
            roi.height,
            fill=False,
            edgecolor="#ff3b30",
            linewidth=2.0,
            label="Analysis ROI",
        )
    )
    ax.set_title(f"Raw image with ROI\n{experiment_title(metadata)}")
    ax.set_xlabel("x [px]")
    ax.set_ylabel("y [px]")
    ax.legend(loc="upper right")
    fig.colorbar(image_artist, ax=ax, label="Intensity [DN]")
    _save(fig, output_path, config)


def plot_intensity_profiles(
    result: FrameResult,
    metadata: Mapping[str, object],
    config: AnalysisConfig,
    output_path: str | Path,
) -> None:
    fig, ax = _figure(config)
    y = np.arange(result.roi.y, result.roi.y_end)
    for x in config.profile_x_positions:
        profile = result.image[result.roi.y : result.roi.y_end, x]
        ax.plot(
            y,
            profile,
            linewidth=config.plot.line_width,
            label=f"x={x} px",
        )
    ax.set_title(f"Vertical intensity profiles\n{experiment_title(metadata)}")
    ax.set_xlabel("y [px]")
    ax.set_ylabel("Intensity [DN]")
    ax.set_ylim(bottom=result.roi.y, top=result.roi.y_end - 1)
    ax.legend(ncol=2)
    _save(fig, output_path, config)


def plot_line_width_distribution(
    results: Sequence[FrameResult],
    metadata: Mapping[str, object],
    config: AnalysisConfig,
    output_path: str | Path,
) -> None:
    fig, ax = _figure(config)
    width_stack = np.vstack([result.fwhm_px for result in results])
    for result in results:
        ax.plot(
            result.x_px,
            result.fwhm_px,
            color="#8da0cb",
            alpha=0.22,
            linewidth=0.8,
        )
    finite = np.isfinite(width_stack)
    counts = finite.sum(axis=0)
    mean_width = np.full(width_stack.shape[1], np.nan, dtype=np.float64)
    columns_with_data = counts > 0
    mean_width[columns_with_data] = (
        np.nansum(width_stack[:, columns_with_data], axis=0)
        / counts[columns_with_data]
    )
    ax.plot(
        results[0].x_px,
        mean_width,
        color="#d62728",
        linewidth=max(1.8, config.plot.line_width),
        label="Mean across frames",
    )
    ax.axhline(
        config.extraction.min_fwhm_px,
        color="#2ca02c",
        linestyle="--",
        linewidth=1.0,
        label="Configured limits",
    )
    ax.axhline(
        config.extraction.max_fwhm_px,
        color="#2ca02c",
        linestyle="--",
        linewidth=1.0,
    )
    ax.set_title(f"FWHM line-width distribution\n{experiment_title(metadata)}")
    ax.set_xlabel("x [px]")
    ax.set_ylabel("FWHM [px]")
    ax.legend()
    _save(fig, output_path, config)


def plot_centerline_overlay(
    result: FrameResult,
    metadata: Mapping[str, object],
    config: AnalysisConfig,
    output_path: str | Path,
) -> None:
    fig, ax = _figure(config)
    vmin, vmax = _display_limits(result.image, config)
    image_artist = ax.imshow(result.image, cmap="gray", vmin=vmin, vmax=vmax)
    ax.plot(
        result.x_px[result.valid],
        result.center_y_px[result.valid],
        color="#00e5ff",
        linewidth=max(1.2, config.plot.line_width),
        label="Valid subpixel centerline",
    )
    ax.set_xlim(result.roi.x - 0.5, result.roi.x_end - 0.5)
    ax.set_ylim(result.roi.y_end - 0.5, result.roi.y - 0.5)
    ax.set_title(f"Laser centerline overlay\n{experiment_title(metadata)}")
    ax.set_xlabel("x [px]")
    ax.set_ylabel("y [px]")
    ax.legend(loc="upper right")
    fig.colorbar(image_artist, ax=ax, label="Intensity [DN]")
    _save(fig, output_path, config)


def plot_repeatability_selected_columns(
    results: Sequence[FrameResult],
    metadata: Mapping[str, object],
    config: AnalysisConfig,
    output_path: str | Path,
) -> None:
    fig, ax = _figure(config)
    frame_indices = np.arange(len(results))
    roi_x = results[0].roi.x
    for x in config.repeatability_x_positions:
        local_x = x - roi_x
        values = np.array(
            [
                result.center_y_px[local_x] if result.valid[local_x] else np.nan
                for result in results
            ],
            dtype=np.float64,
        )
        ax.plot(
            frame_indices,
            values,
            marker="o",
            markersize=3.5,
            linewidth=config.plot.line_width,
            label=f"x={x} px",
        )
    ax.set_title(
        f"Center repeatability at selected columns\n{experiment_title(metadata)}"
    )
    ax.set_xlabel("Frame index")
    ax.set_ylabel("Subpixel center y [px]")
    ax.set_xticks(frame_indices)
    ax.legend(ncol=2)
    _save(fig, output_path, config)


def plot_repeatability_std_distribution(
    repeatability: RepeatabilityResult,
    metadata: Mapping[str, object],
    config: AnalysisConfig,
    output_path: str | Path,
) -> None:
    fig, ax = _figure(config)
    ax.plot(
        repeatability.x_px,
        repeatability.center_std_px,
        color="#9467bd",
        linewidth=config.plot.line_width,
        label="Sample standard deviation",
    )
    ax.set_title(
        f"Center repeatability standard deviation\n{experiment_title(metadata)}"
    )
    ax.set_xlabel("x [px]")
    ax.set_ylabel("Center y standard deviation [px]")
    ax.set_ylim(bottom=0.0)
    ax.legend()
    _save(fig, output_path, config)


def _figure(config: AnalysisConfig) -> tuple[plt.Figure, plt.Axes]:
    configure_plot_style()
    return plt.subplots(figsize=config.plot.figsize)


def _display_limits(
    image: np.ndarray, config: AnalysisConfig
) -> tuple[float, float]:
    if config.plot.display_max is not None:
        maximum = config.plot.display_max
    else:
        maximum = float(np.iinfo(image.dtype).max)
    return config.plot.display_min, maximum


def _save(fig: plt.Figure, output_path: str | Path, config: AnalysisConfig) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=config.plot.dpi, bbox_inches="tight")
    plt.close(fig)
