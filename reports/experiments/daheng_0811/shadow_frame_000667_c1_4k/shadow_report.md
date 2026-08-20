# Daheng C1_4k single-frame shadow report

## SHADOW_INTEGRATION: PASS

本轮只验证集成链路；20 mm 单帧高度误差只作记录，不参与 PASS 判定。

- 输入图像：D:\Docs\linelaserscan\0704line-laser-3d-scanner\data\tif\frame_000667.png
- 输入 metadata：D:\Docs\linelaserscan\0704line-laser-3d-scanner\data\tif\frame_000667.json
- Steger 中心提取：同一张图只执行一次，C0/C1 使用同一 centers_full。
- C1 数学：复用 frozen JSON evaluator；s_used 是 clamp 后的 s_eval，不做 spline extrapolation。

## Point-set alignment

| C0 valid | C1 valid | common | C0-only | C1-only |
|---:|---:|---:|---:|---:|
| 1801 | 1801 | 1801 | 0 | 0 |

- extracted centers: 1847
- exact valid-set equality: True
- valid-set difference explanation: True

Difference reason pairs (C0 reason -> C1 reason):

- none

## C1 diagnostics

- clamp count/rate over all centers: 2 / 0.001083
- clamp count/rate over C1-valid centers: 0 / 0.000000
- clamp count/rate over common centers: 0 / 0.000000
- delta_lambda all centers: count=1847, min=-0.148929 mm, mean=0.000290 mm, P95=0.140025 mm, max=0.231422 mm
- delta_lambda C1-valid centers: count=1801, min=-0.148929 mm, mean=-0.004983 mm, P95=0.111679 mm, max=0.172908 mm
- delta_lambda common centers: count=1801, min=-0.148929 mm, mean=-0.004983 mm, P95=0.111679 mm, max=0.172908 mm

Coordinate delta statistics on common points (C1 - C0, mm):

- camera norm: count=1801, min=0.000014 mm, mean=0.040034 mm, P95=0.133150 mm, max=0.176199 mm
- ground norm: count=1801, min=0.000014 mm, mean=0.040034 mm, P95=0.133150 mm, max=0.176199 mm
- ground X: count=1801, min=-0.007234 mm, mean=-0.000213 mm, P95=0.005927 mm, max=0.009207 mm
- ground Y: count=1801, min=-0.006034 mm, mean=0.003822 mm, P95=0.025254 mm, max=0.035277 mm
- ground Z: count=1801, min=-0.172385 mm, mean=0.005009 mm, P95=0.098363 mm, max=0.148997 mm

## 20 mm height measurements

| Model | Baseline | Status | Height mm | Error mm |
|---|---|---|---:|---:|
| c0 | local_adjacent | success | 19.841610 | -0.158390 |
| c0 | all_non_height | success | 19.835130 | -0.164870 |
| c0 | fixed_zg_zero | success | 19.935864 | -0.064136 |
| c1 | local_adjacent | success | 19.840459 | -0.159541 |
| c1 | all_non_height | success | 19.830133 | -0.169867 |
| c1 | fixed_zg_zero | success | 19.927702 | -0.072298 |

Height results are reported for local_adjacent, all_non_height, and fixed_zg_zero using each branch's own valid points. They are not a shadow PASS criterion.

## Shadow conditions

- same_centers_used_for_c0_and_c1: True
- c0_has_valid_points: True
- c1_has_valid_points: True
- common_points_present: True
- valid_coordinates_are_finite: True
- c1_correction_actually_nonzero: True
- clamp_rate_not_abnormal_le_5_percent: True
- valid_set_same_or_difference_explained: True
- all_six_height_measurements_succeeded: True

## Artifacts

- c1_diagnostics.csv
- point_set_summary.json
- height_measurements.csv
- c0_points.csv
- c1_points.csv
- c0_ground.ply
- c1_ground.ply
- pointwise_comparison.csv
- laser_centers_local.csv
- laser_centers_full.csv
- provenance.json
- shadow_report.md
