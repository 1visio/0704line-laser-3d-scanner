from __future__ import annotations

import unittest

import numpy as np

from line_laser_static.metrics import summarize_profile_quality
from line_laser_static.models import StripeProfile


class SummarizeProfileQualityTests(unittest.TestCase):
    def test_counts_distribution_saturation_and_center_step(self) -> None:
        # 第 3 列(索引 2)无效，且第 2 与第 3 列之间存在列号断档(u 从 2 跳到 4)，
        # 用来验证相邻列掩码只统计既有效又列号连续的相邻对。
        profile = StripeProfile(
            u_px=np.array([0.0, 1.0, 2.0, 4.0, 5.0]),
            v_px=np.array([10.0, 12.0, 15.0, 100.0, 105.0]),
            intensity=np.array([50.0, 60.0, 70.0, 80.0, 90.0]),
            confidence=np.array([0.9, 0.9, 0.1, 0.9, 0.9]),
            valid=np.array([True, True, False, True, True]),
            contrast=np.array([1.0, 2.0, 3.0, 4.0, np.nan]),
            saturated=np.array([False, False, False, True, False]),
        )

        summary = summarize_profile_quality(profile)

        self.assertEqual(summary["point_count"], 5)
        self.assertEqual(summary["valid_count"], 4)
        self.assertAlmostEqual(summary["valid_ratio"], 0.8)

        self.assertEqual(summary["saturated_count"], 1)
        self.assertAlmostEqual(summary["saturated_ratio"], 0.2)

        # NaN 应被剔除后再统计分布。
        self.assertAlmostEqual(summary["contrast_median"], 2.5)
        self.assertAlmostEqual(summary["contrast_p05"], 1.15)
        self.assertAlmostEqual(summary["contrast_p95"], 3.85)

        # 仅 (0,1) 与 (4,5) 两对既有效又相邻，步长为 2 和 5。
        self.assertAlmostEqual(summary["center_step_abs_px_p95"], 4.85)

        # 未提供的可选字段不应出现在摘要里。
        self.assertNotIn("snr_median", summary)
        self.assertNotIn("fwhm_px_median", summary)

    def test_empty_valid_and_missing_optionals(self) -> None:
        profile = StripeProfile(
            u_px=np.array([0.0, 1.0, 2.0]),
            v_px=np.array([np.nan, np.nan, np.nan]),
            intensity=np.array([0.0, 0.0, 0.0]),
            confidence=np.array([0.0, 0.0, 0.0]),
            valid=np.array([False, False, False]),
        )

        summary = summarize_profile_quality(profile)

        self.assertEqual(summary["point_count"], 3)
        self.assertEqual(summary["valid_count"], 0)
        self.assertAlmostEqual(summary["valid_ratio"], 0.0)
        # 没有有效的相邻对，也没有可选字段，相关键都应缺省。
        self.assertNotIn("center_step_abs_px_p95", summary)
        self.assertNotIn("contrast_median", summary)
        self.assertNotIn("saturated_count", summary)


if __name__ == "__main__":
    unittest.main()
