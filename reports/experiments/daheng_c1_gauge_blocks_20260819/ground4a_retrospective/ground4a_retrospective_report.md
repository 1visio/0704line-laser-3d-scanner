# Ground-4A 旧量块数据四链回放（retrospective diagnostic）

## 结论

- `GS_HEIGHT_VALUE = NEUTRAL`
- `OBSTACLE_ONLY_APPROACHES_LOCAL_BASELINE = NO`
- `GROUND4A_STATUS = RETROSPECTIVE_DIAGNOSTIC_ONLY`
- 本轮不修改 C0/C1、G(S)、ROI、GUI、生产测高链路，也不构成新的 held-out engineering acceptance。

## 判定口径

- 正式指标只使用每个 height × position condition 的 repeat2–5；repeat1 仅用于冻结该 condition 的 session calibration proxy。
- `A fixed_zg_zero` 与 `D local_adjacent` 复用 frozen C1 audit 的同一帧结果；B/C 使用同一批 C1 height ROI 点和相同 XY robust height-line inlier 规则。
- B：repeat1 基准面 ROI 点 robust 拟合 `Zg=a*S+b`，随后 `Zobj-(aS+b)`；C：先拟合 `Zg-G(S)=a*S+b`，随后 `Zobj-(aS+b+G(S))`。
- `S=(XY-origin_xy)·direction_xy` 严格复用 Ground-1；G(S) 域外不外推、不 clamp，当前量块有效 ROI 点均在 frozen domain 内。

## Artifact provenance / reuse audit

- 复用：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_manual_frozen` 的 150 图像审计、150 次 Steger、C1 重建、30/30 manual-frozen geometry-only ROI、逐点 C1 XYZ 与既有 A/D 测量。
- 复用：Ground-3 freeze candidate `D:\Docs\linelaserscan\0704line-laser-3d-scanner\laser_measurement_tool\output_daheng_0811\ground_spatial_correction_ground3\ground_gs_summary.json`；模型 `cubic_bspline_3_interior_knots`，参数 hash `a6aee2d10839ca3cc2c6fb641dd82cef098c479575f39b8060c226dabd497be7`。
- 本轮新增：30 个 condition 的 repeat1 ground proxy、B/C 四链回放、repeat2–5 正式统计、全 150 帧参考行、position range、repeatability 与图表。
- 未做：Steger 重跑、C0/C1 重建或重拟合、ROI 重选、G(S) 重拟合、height linear correction、生产配置写入。
- frozen C1 config hash：`c22e463aff6dc51565679382cc766a3c7078a57f676809e7b31ee1cbe185f15f`；`enable_laser_ray_correction=true`。

## 四链正式指标（repeat2–5）

| chain | n/expected | failed | Bias | MAE | RMSE | P95 | Max | ±0.1 pass | ±0.2 pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A fixed_zg_zero | 116/120 | 4 | -0.0502 | 0.0593 | 0.0711 | 0.1355 | 0.1610 | 100/116 (86.2%) | 116/116 (100.0%) |
| B session_linear | 116/120 | 4 | -0.0539 | 0.0561 | 0.0696 | 0.1310 | 0.1723 | 100/116 (86.2%) | 116/116 (100.0%) |
| C session_linear_G | 116/120 | 4 | -0.0537 | 0.0560 | 0.0695 | 0.1311 | 0.1724 | 100/116 (86.2%) | 116/116 (100.0%) |
| D local_adjacent | 116/120 | 4 | -0.0538 | 0.0560 | 0.0693 | 0.1323 | 0.1692 | 100/116 (86.2%) | 116/116 (100.0%) |

## C-B 增量与 C-D 差距（repeat2–5）

负的 `abs_error_delta` 表示左侧链路绝对误差更小。

| comparison | n | value delta mean | value delta RMSE | abs-error delta mean | abs-error delta median | positive improvement rate |
|---|---:|---:|---:|---:|---:|---:|
| C_minus_B | 116 | 0.0002 | 0.0003 | -0.0001 | 0.0000 | 44.8% |
| C_minus_D | 116 | 0.0000 | 0.0017 | 0.0001 | -0.0003 | 56.0% |

- C 相对 B 的 MAE：`0.0561 -> 0.0560` mm；RMSE：`0.0696 -> 0.0695` mm。
- C 相对 D 的 MAE 差距（C abs error - D abs error）：`0.0001` mm。
- obstacle-only 与 D 的平均高度值差距：B=`0.0012` mm，C=`0.0013` mm；C 未缩小该差距，因此结论为 `NO`。

## Position bias range（repeat2–5 condition mean）

详表见 `ground4a_position_bias_ranges.csv`；每行是同一高度五个 position 的 condition bias 范围。

| dataset | chain | positions | bias min | bias max | range | position MAE |
|---|---|---:|---:|---:|---:|---:|
| obs_1mm | fixed_zg_zero | 5 | -0.1545 | -0.0395 | 0.1150 | 0.0978 |
| obs_1mm | local_adjacent | 5 | -0.0564 | 0.0130 | 0.0694 | 0.0300 |
| obs_1mm | session_linear | 5 | -0.0551 | 0.0131 | 0.0681 | 0.0303 |
| obs_1mm | session_linear_G | 5 | -0.0551 | 0.0132 | 0.0684 | 0.0303 |
| obs_2mm | fixed_zg_zero | 4 | -0.1359 | -0.0347 | 0.1012 | 0.0909 |
| obs_2mm | local_adjacent | 4 | -0.0579 | 0.0046 | 0.0625 | 0.0296 |
| obs_2mm | session_linear | 4 | -0.0578 | 0.0048 | 0.0626 | 0.0293 |
| obs_2mm | session_linear_G | 4 | -0.0578 | 0.0053 | 0.0631 | 0.0292 |
| obs_6mm | fixed_zg_zero | 5 | -0.0821 | -0.0006 | 0.0815 | 0.0456 |
| obs_6mm | local_adjacent | 5 | -0.0649 | 0.0059 | 0.0708 | 0.0243 |
| obs_6mm | session_linear | 5 | -0.0643 | 0.0054 | 0.0697 | 0.0240 |
| obs_6mm | session_linear_G | 5 | -0.0643 | 0.0053 | 0.0697 | 0.0238 |
| obs_10mm | fixed_zg_zero | 5 | -0.0705 | -0.0011 | 0.0694 | 0.0384 |
| obs_10mm | local_adjacent | 5 | -0.0845 | -0.0302 | 0.0544 | 0.0484 |
| obs_10mm | session_linear | 5 | -0.0838 | -0.0289 | 0.0550 | 0.0480 |
| obs_10mm | session_linear_G | 5 | -0.0839 | -0.0289 | 0.0550 | 0.0479 |
| obs_20mm | fixed_zg_zero | 5 | -0.0103 | 0.0534 | 0.0637 | 0.0278 |
| obs_20mm | local_adjacent | 5 | -0.1325 | -0.0470 | 0.0855 | 0.0878 |
| obs_20mm | session_linear | 5 | -0.1313 | -0.0491 | 0.0822 | 0.0881 |
| obs_20mm | session_linear_G | 5 | -0.1314 | -0.0489 | 0.0825 | 0.0879 |
| obs_30mm | fixed_zg_zero | 5 | -0.0833 | -0.0186 | 0.0648 | 0.0606 |
| obs_30mm | local_adjacent | 5 | -0.1672 | -0.0802 | 0.0870 | 0.1105 |
| obs_30mm | session_linear | 5 | -0.1693 | -0.0843 | 0.0849 | 0.1118 |
| obs_30mm | session_linear_G | 5 | -0.1694 | -0.0844 | 0.0850 | 0.1117 |

## Repeatability

| chain | conditions | median sigma | P95 sigma | Max sigma |
|---|---:|---:|---:|---:|
| A fixed_zg_zero | 29 | 0.0023 | 0.0041 | 0.0044 |
| B session_linear | 29 | 0.0022 | 0.0040 | 0.0043 |
| C session_linear_G | 29 | 0.0022 | 0.0040 | 0.0043 |
| D local_adjacent | 29 | 0.0025 | 0.0034 | 0.0037 |

## 文件

- `ground4a_frame_comparison.csv`：全 150 帧；repeat1 标为 in-sample calibration，repeat2–5 标为 formal evaluation。
- `ground4a_condition_comparison.csv`：30 个 condition 的 repeat2–5 汇总。
- `ground4a_four_chain_summary.csv`：四链的 repeat2–5 与 all150 统计。
- `ground4a_position_bias_ranges.csv`、`ground4a_repeatability_summary.csv`、`ground4a_chain_deltas.csv`。
- `ground4a_height_error_vs_position.png`。

## 备注

- `obs_2mm / position5` 沿用原 frozen C1 audit 的 height ROI 点数不足失败状态；没有因为本轮结果删除该 condition。
- 全 150 帧输出仅供回放追踪；任何正式结论均不把 repeat1 的 in-sample 结果混入 repeat2–5 指标。
