from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from laser_extract import (
    AnalysisConfig,
    ExtractionConfig,
    GaussianConfig,
    PlotConfig,
    RoiConfig,
    analyze_frame,
    calculate_repeatability,
    read_grayscale_image,
)


def make_config(
    *,
    gaussian_enabled: bool = False,
    min_peak: float = 20.0,
    min_width: float = 1.0,
    max_width: float = 20.0,
) -> AnalysisConfig:
    return AnalysisConfig(
        roi=RoiConfig(0, 0, None, None),
        gaussian=GaussianConfig(gaussian_enabled, 5, 1.0),
        extraction=ExtractionConfig(5, min_peak, 0.5, min_width, max_width),
        profile_x_positions=(8, 16, 24),
        repeatability_x_positions=(8, 16, 24),
        plot=PlotConfig(100, (6.0, 4.0), 0.0, None, 1.0),
    )


def stripe_image(
    *,
    width: int = 32,
    height: int = 40,
    center: float = 18.35,
    sigma: float = 1.8,
    amplitude: float = 180.0,
    dtype: type[np.unsignedinteger] = np.uint8,
) -> np.ndarray:
    rows = np.arange(height, dtype=np.float64)[:, None]
    columns = np.arange(width, dtype=np.float64)[None, :]
    centers = center + 0.01 * (columns - (width - 1) / 2.0)
    image = amplitude * np.exp(-0.5 * ((rows - centers) / sigma) ** 2)
    return np.rint(image).astype(dtype)


class ExtractionTests(unittest.TestCase):
    def test_subpixel_center_and_fwhm_are_accurate(self) -> None:
        image = stripe_image()
        result = analyze_frame(image, "frame_0001.png", make_config())

        expected_center = 18.35 + 0.01 * (
            np.arange(image.shape[1]) - (image.shape[1] - 1) / 2.0
        )
        self.assertTrue(bool(result.valid.all()))
        self.assertLess(
            float(np.max(np.abs(result.center_y_px - expected_center))), 0.08
        )
        self.assertAlmostEqual(float(np.median(result.fwhm_px)), 4.24, delta=0.2)

    def test_uint16_peak_uses_raw_dn_with_gaussian_detection(self) -> None:
        image = stripe_image(amplitude=3200.0, dtype=np.uint16)
        result = analyze_frame(
            image,
            "frame_0001.png",
            make_config(gaussian_enabled=True, min_peak=500.0),
        )

        local_columns = np.arange(image.shape[1])
        peak_rows = result.peak_y_px.astype(int)
        expected_raw_peaks = image[peak_rows, local_columns]
        np.testing.assert_array_equal(result.peak_intensity, expected_raw_peaks)
        self.assertEqual(result.image.dtype, np.uint16)
        self.assertGreater(float(np.median(result.peak_intensity)), 3000.0)

    def test_weak_edge_and_abnormal_width_columns_are_invalid(self) -> None:
        weak = stripe_image(amplitude=5.0)
        edge = stripe_image(center=2.0)
        broad = stripe_image(sigma=4.0)

        self.assertFalse(
            bool(analyze_frame(weak, "weak.png", make_config(min_peak=20.0)).valid.any())
        )
        self.assertFalse(bool(analyze_frame(edge, "edge.png", make_config()).valid.any()))
        broad_result = analyze_frame(
            broad, "broad.png", make_config(max_width=5.0)
        )
        self.assertFalse(bool(broad_result.valid.any()))
        self.assertTrue(bool(np.isnan(broad_result.fwhm_px).all()))

    def test_missing_fwhm_crossing_and_outside_sample_are_rejected(self) -> None:
        no_crossing = np.full((40, 32), 60, dtype=np.uint8)
        no_crossing[18, :] = 100
        no_crossing_result = analyze_frame(
            no_crossing, "no_crossing.png", make_config()
        )
        self.assertFalse(bool(no_crossing_result.valid.any()))

        config = make_config()
        config = AnalysisConfig(
            roi=config.roi,
            gaussian=config.gaussian,
            extraction=config.extraction,
            profile_x_positions=(8, 40),
            repeatability_x_positions=config.repeatability_x_positions,
            plot=config.plot,
        )
        with self.assertRaisesRegex(ValueError, "outside ROI"):
            analyze_frame(stripe_image(), "outside.png", config)

    def test_repeatability_uses_sample_standard_deviation(self) -> None:
        frames = []
        for index, offset in enumerate((-0.1, 0.0, 0.1)):
            image = stripe_image(center=18.35 + offset)
            frames.append(analyze_frame(image, f"frame_{index}.png", make_config()))

        repeatability = calculate_repeatability(frames)
        self.assertTrue(bool(np.isfinite(repeatability.center_std_px).all()))
        self.assertAlmostEqual(
            float(np.median(repeatability.center_std_px)), 0.1, delta=0.02
        )
        np.testing.assert_array_equal(repeatability.valid_frame_count, 3)

    def test_image_reader_preserves_depth_and_rejects_color(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mono_path = root / "mono.png"
            color_path = root / "color.png"
            mono = stripe_image(amplitude=3200.0, dtype=np.uint16)
            color = np.zeros((12, 16, 3), dtype=np.uint8)
            self.assertTrue(cv2.imwrite(str(mono_path), mono))
            self.assertTrue(cv2.imwrite(str(color_path), color))

            loaded = read_grayscale_image(mono_path)
            self.assertEqual(loaded.dtype, np.uint16)
            np.testing.assert_array_equal(loaded, mono)
            with self.assertRaisesRegex(ValueError, "single-channel grayscale"):
                read_grayscale_image(color_path)


if __name__ == "__main__":
    unittest.main()
