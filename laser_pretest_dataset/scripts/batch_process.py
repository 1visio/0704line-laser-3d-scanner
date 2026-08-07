"""Command-line batch processor for line-laser pretest datasets."""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

from laser_extract import (
    AnalysisConfig,
    FrameResult,
    analyze_frame,
    calculate_repeatability,
    load_config,
    read_grayscale_image,
    resolve_roi,
    summarize_frame,
    summarize_group,
)
from plot_quality import (
    plot_centerline_overlay,
    plot_intensity_profiles,
    plot_line_width_distribution,
    plot_raw_with_roi,
    plot_repeatability_selected_columns,
    plot_repeatability_std_distribution,
)


METADATA_FIELDS = (
    "exp_id",
    "image_dir",
    "exposure_us",
    "gain",
    "material",
    "distance_mm",
    "baseline_mm",
    "laser_angle_deg",
    "frame_count",
    "remark",
)

METRIC_FIELDS = (
    "valid_column_count",
    "column_count",
    "valid_ratio",
    "peak_intensity_mean",
    "peak_intensity_median",
    "peak_intensity_std",
    "peak_intensity_p95",
    "fwhm_px_mean",
    "fwhm_px_median",
    "fwhm_px_std",
    "fwhm_px_p95",
    "repeatable_column_count",
    "repeatable_column_ratio",
    "center_std_px_median",
    "center_std_px_p95",
    "center_std_px_max",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline quality analysis for line-laser pretest images."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Dataset root containing metadata.csv and raw image directories.",
    )
    parser.add_argument(
        "--config", required=True, type=Path, help="YAML analysis configuration."
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="Output directory."
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        dataset = args.dataset.resolve(strict=True)
        if not dataset.is_dir():
            raise ValueError(f"Dataset path is not a directory: {dataset}")
        config = load_config(args.config)
        experiments = load_metadata(dataset / "metadata.csv")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, Any]] = []
    failed = False

    for experiment in experiments:
        exp_id = experiment["exp_id"]
        print(f"Processing {exp_id} ...")
        try:
            row = process_experiment(dataset, output, experiment, config)
            summary_rows.append(row)
            print(f"  OK: {row['frame_count_actual']} frame(s)")
        except (OSError, ValueError, RuntimeError) as exc:
            failed = True
            actual_count = _observed_frame_count(dataset, experiment["image_dir"])
            expected_count = _optional_int(experiment.get("frame_count", ""))
            error_row = dict(experiment)
            error_row.update(
                {
                    "frame_count_expected": (
                        "" if expected_count is None else expected_count
                    ),
                    "frame_count_actual": actual_count,
                    "frame_count_match": (
                        expected_count is None or expected_count == actual_count
                    ),
                    "status": "error",
                    "error": str(exc),
                }
            )
            summary_rows.append(error_row)
            print(f"  ERROR: {exc}", file=sys.stderr)

    write_metrics_csv(output / "metrics_summary.csv", summary_rows)
    print(f"Summary written to {output / 'metrics_summary.csv'}")
    return 1 if failed else 0


def load_metadata(path: str | Path) -> list[dict[str, str]]:
    metadata_path = Path(path)
    try:
        handle = metadata_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise ValueError(f"Cannot read metadata file: {metadata_path}") from exc

    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("metadata.csv has no header")
        missing = [field for field in METADATA_FIELDS if field not in reader.fieldnames]
        if missing:
            raise ValueError(f"metadata.csv is missing fields: {missing}")

        experiments: list[dict[str, str]] = []
        seen_ids: set[str] = set()
        for line_number, raw_row in enumerate(reader, start=2):
            row = {field: (raw_row.get(field) or "").strip() for field in METADATA_FIELDS}
            if not any(row.values()):
                continue
            if not row["exp_id"]:
                raise ValueError(f"metadata.csv line {line_number}: exp_id is required")
            if not row["image_dir"]:
                raise ValueError(
                    f"metadata.csv line {line_number}: image_dir is required"
                )
            if row["exp_id"] in seen_ids:
                raise ValueError(
                    f"metadata.csv line {line_number}: duplicate exp_id {row['exp_id']!r}"
                )
            _validate_metadata_numbers(row, line_number)
            seen_ids.add(row["exp_id"])
            experiments.append(row)

    if not experiments:
        raise ValueError("metadata.csv contains no experiment rows")
    return experiments


def process_experiment(
    dataset: Path,
    output: Path,
    experiment: dict[str, str],
    config: AnalysisConfig,
) -> dict[str, Any]:
    image_dir = _resolve_image_dir(dataset, experiment["image_dir"])
    frame_paths = natural_sort(image_dir.glob("frame_*.png"))
    if not frame_paths:
        raise ValueError(f"No frame_*.png images found in {image_dir}")

    images = [read_grayscale_image(path) for path in frame_paths]
    first_shape = images[0].shape
    first_dtype = images[0].dtype
    for path, image in zip(frame_paths[1:], images[1:]):
        if image.shape != first_shape:
            raise ValueError(
                f"Frame size mismatch: {path.name} is {image.shape}, "
                f"expected {first_shape}"
            )
        if image.dtype != first_dtype:
            raise ValueError(
                f"Frame dtype mismatch: {path.name} is {image.dtype}, "
                f"expected {first_dtype}"
            )

    roi = resolve_roi(first_shape, config.roi)
    results = [
        analyze_frame(image, path.name, config, roi)
        for path, image in zip(frame_paths, images)
    ]
    repeatability = calculate_repeatability(results)
    group_metrics = summarize_group(results, repeatability)

    exp_output = output / experiment["exp_id"]
    exp_output.mkdir(parents=True, exist_ok=True)
    representative = results[0]
    plot_raw_with_roi(
        representative,
        experiment,
        config,
        exp_output / "01_raw_with_roi.png",
    )
    plot_intensity_profiles(
        representative,
        experiment,
        config,
        exp_output / "02_intensity_profiles.png",
    )
    plot_line_width_distribution(
        results,
        experiment,
        config,
        exp_output / "03_line_width_distribution.png",
    )
    plot_centerline_overlay(
        representative,
        experiment,
        config,
        exp_output / "04_centerline_overlay.png",
    )
    plot_repeatability_selected_columns(
        results,
        experiment,
        config,
        exp_output / "05_repeatability_selected_columns.png",
    )
    plot_repeatability_std_distribution(
        repeatability,
        experiment,
        config,
        exp_output / "06_repeatability_std_distribution.png",
    )

    metric_rows: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        row: dict[str, Any] = dict(experiment)
        row.update(
            {
                "row_type": "FRAME",
                "frame_index": index,
                "frame_name": result.frame_name,
                "frame_count_actual": len(results),
            }
        )
        row.update(summarize_frame(result))
        metric_rows.append(row)
    summary_row: dict[str, Any] = dict(experiment)
    summary_row.update(
        {
            "row_type": "SUMMARY",
            "frame_index": "",
            "frame_name": "",
        }
    )
    summary_row.update(group_metrics)
    metric_rows.append(summary_row)
    write_metrics_csv(exp_output / "metrics.csv", metric_rows)

    expected = _optional_int(experiment.get("frame_count", ""))
    global_row: dict[str, Any] = dict(experiment)
    global_row.update(group_metrics)
    global_row.update(
        {
            "frame_count_expected": "" if expected is None else expected,
            "frame_count_match": expected is None or expected == len(results),
            "status": "ok",
            "error": "",
        }
    )
    return global_row


def write_metrics_csv(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    row_list = list(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _ordered_fieldnames(row_list)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in row_list:
            writer.writerow({key: _csv_value(row.get(key, "")) for key in fieldnames})


def natural_sort(paths: Iterable[Path]) -> list[Path]:
    def key(path: Path) -> list[int | str]:
        return [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.name)
        ]

    return sorted(paths, key=key)


def _resolve_image_dir(dataset: Path, configured: str) -> Path:
    relative = Path(configured)
    if relative.is_absolute():
        raise ValueError(f"image_dir must be relative to dataset: {configured}")
    resolved = (dataset / relative).resolve()
    try:
        resolved.relative_to(dataset)
    except ValueError as exc:
        raise ValueError(f"image_dir escapes dataset root: {configured}") from exc
    if not resolved.is_dir():
        raise ValueError(f"Image directory does not exist: {resolved}")
    return resolved


def _validate_metadata_numbers(row: dict[str, str], line_number: int) -> None:
    for field in (
        "exposure_us",
        "gain",
        "distance_mm",
        "baseline_mm",
        "laser_angle_deg",
    ):
        value = row[field]
        if not value:
            continue
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(
                f"metadata.csv line {line_number}: {field} must be numeric"
            ) from exc
        if not math.isfinite(number):
            raise ValueError(
                f"metadata.csv line {line_number}: {field} must be finite"
            )
    if row["frame_count"]:
        try:
            count = int(row["frame_count"])
        except ValueError as exc:
            raise ValueError(
                f"metadata.csv line {line_number}: frame_count must be an integer"
            ) from exc
        if count < 0:
            raise ValueError(
                f"metadata.csv line {line_number}: frame_count must be nonnegative"
            )


def _optional_int(value: str) -> int | None:
    return None if value == "" else int(value)


def _observed_frame_count(dataset: Path, configured: str) -> int:
    try:
        image_dir = _resolve_image_dir(dataset, configured)
    except ValueError:
        return 0
    return len(list(image_dir.glob("frame_*.png")))


def _ordered_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    preferred = list(METADATA_FIELDS) + [
        "row_type",
        "frame_index",
        "frame_name",
        "frame_count_expected",
        "frame_count_actual",
        "frame_count_match",
        *METRIC_FIELDS,
        "status",
        "error",
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    all_keys = {key for row in rows for key in row}
    for key in preferred:
        if key in all_keys and key not in seen:
            ordered.append(key)
            seen.add(key)
    for key in sorted(all_keys - seen):
        ordered.append(key)
    return ordered


def _csv_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


if __name__ == "__main__":
    raise SystemExit(main())
