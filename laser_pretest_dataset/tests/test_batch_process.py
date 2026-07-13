from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
import yaml

import batch_process


def make_stripe(center: float, width: int = 64, height: int = 48) -> np.ndarray:
    rows = np.arange(height, dtype=np.float64)[:, None]
    image = 200.0 * np.exp(-0.5 * ((rows - center) / 1.7) ** 2)
    return np.repeat(np.rint(image).astype(np.uint8), width, axis=1)


def write_config(path: Path) -> None:
    config = {
        "roi": {"x": 0, "y": 0, "width": None, "height": None},
        "gaussian_filter": {"enabled": True, "kernel_size": 5, "sigma": 1.0},
        "extraction": {
            "peak_window_radius": 5,
            "min_peak_intensity": 20,
            "fwhm_ratio": 0.5,
            "min_fwhm_px": 1.0,
            "max_fwhm_px": 10.0,
        },
        "profiles": {"x_positions": [16, 32, 48]},
        "repeatability": {"x_positions": [16, 32, 48]},
        "plot": {
            "dpi": 80,
            "figsize": [6.0, 4.0],
            "display_min": 0,
            "display_max": 255,
            "line_width": 1.0,
        },
    }
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def write_metadata(path: Path, frame_count: int = 3) -> None:
    path.write_text(
        "exp_id,image_dir,exposure_us,gain,material,distance_mm,baseline_mm,laser_angle_deg,frame_count,remark\n"
        f"T001,raw/T001,2000,0,white_board,300,80,15,{frame_count},synthetic\n",
        encoding="utf-8",
    )


class BatchProcessTests(unittest.TestCase):
    def test_end_to_end_generates_six_plots_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_dir = root / "raw" / "T001"
            image_dir.mkdir(parents=True)
            write_metadata(root / "metadata.csv", frame_count=4)
            write_config(root / "config.yaml")
            for index, center in enumerate((22.2, 22.3, 22.4), start=1):
                cv2.imwrite(
                    str(image_dir / f"frame_{index:04d}.png"), make_stripe(center)
                )

            output = root / "results"
            code = batch_process.main(
                [
                    "--dataset",
                    str(root),
                    "--config",
                    str(root / "config.yaml"),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(code, 0)
            exp_output = output / "T001"
            expected = [
                "01_raw_with_roi.png",
                "02_intensity_profiles.png",
                "03_line_width_distribution.png",
                "04_centerline_overlay.png",
                "05_repeatability_selected_columns.png",
                "06_repeatability_std_distribution.png",
                "metrics.csv",
            ]
            for name in expected:
                self.assertTrue((exp_output / name).is_file(), name)
                self.assertGreater((exp_output / name).stat().st_size, 0)

            with (exp_output / "metrics.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["row_type"] for row in rows], ["FRAME"] * 3 + ["SUMMARY"])
            self.assertGreater(float(rows[-1]["valid_ratio"]), 0.99)

            with (output / "metrics_summary.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                summary = next(csv.DictReader(handle))
            self.assertEqual(summary["status"], "ok")
            self.assertEqual(summary["frame_count_actual"], "3")
            self.assertEqual(summary["frame_count_match"], "False")

    def test_empty_group_isolated_as_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "raw" / "T001").mkdir(parents=True)
            write_metadata(root / "metadata.csv")
            write_config(root / "config.yaml")
            output = root / "results"

            code = batch_process.main(
                [
                    "--dataset",
                    str(root),
                    "--config",
                    str(root / "config.yaml"),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(code, 1)
            with (output / "metrics_summary.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                summary = next(csv.DictReader(handle))
            self.assertEqual(summary["status"], "error")
            self.assertIn("No frame_*.png", summary["error"])

    def test_bad_metadata_is_global_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "metadata.csv").write_text("exp_id,image_dir\nT001,raw/T001\n")
            write_config(root / "config.yaml")
            code = batch_process.main(
                [
                    "--dataset",
                    str(root),
                    "--config",
                    str(root / "config.yaml"),
                    "--output",
                    str(root / "results"),
                ]
            )
            self.assertEqual(code, 2)

    def test_mismatched_frame_sizes_fail_only_that_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_dir = root / "raw" / "T001"
            image_dir.mkdir(parents=True)
            write_metadata(root / "metadata.csv", frame_count=2)
            write_config(root / "config.yaml")
            cv2.imwrite(str(image_dir / "frame_1.png"), make_stripe(22.0))
            cv2.imwrite(
                str(image_dir / "frame_2.png"), make_stripe(22.0, width=63)
            )

            code = batch_process.main(
                [
                    "--dataset",
                    str(root),
                    "--config",
                    str(root / "config.yaml"),
                    "--output",
                    str(root / "results"),
                ]
            )
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
