# Daheng C1 量块工程精度验收报告

- 生成时间（UTC）：2026-08-19T06:31:46.590967+00:00
- 数据根目录：D:\Docs\linelaserscan\calibration_tool\projects\daheng\data
- 生产配置（只读）：D:\Docs\linelaserscan\0704line-laser-3d-scanner\laser_measurement_tool\configs\measure_tool_daheng_0811.yaml
- 数据协议：6 高度 × 5 v 位置（laser001~005）× 5 重复
- 真值：obs_1mm = 1.001 mm；其余为独立 truth 配置中的标称值

## 结论

- SYSTEM_HEIGHT_ACCURACY：False （主判据：C1 + local_adjacent，150 个单帧）
- C1_ENGINEERING_STATUS：FAIL
- 状态说明：one or more audit or accuracy gates failed
- 验收阈值：绝对高度误差不超过 0.2 mm。

## Provenance 与审计

- 复用：仓库现有 Steger backend、Daheng 0811 配置解析、quadratic C0 重建、Frozen C1 correction loader/evaluator。
- 本轮新增：150 张 TIFF 的尺寸/dtype/offset/SHA/重复审计、150 次 Steger、30 个 geometry-only ROI、C0/C1 双分支重建、全部统计和图表。
- 不复用：历史单帧/旧 PNG ROI、历史量块测量值、任何依据 C0/C1 结果调节的 ROI。
- 图像数：150/150；Steger 调用：150/150；重复 SHA 组：0。
- 每行 CSV 都记录 steger_called_once；height_measurements.csv 还记录 same_roi_c0_c1。

## 输入组审计

| 数据组 | 25 张 | 5 pose × 5 repeat | shape/dtype/offset | manifest quality |
|---|---:|---:|---|---|
| obs_1mm | 25/25 | yes | yes ([(0, 0)]) | frames quality=['False']; warnings=['dynamic_range_low']; manifest=completed |
| obs_2mm | 25/25 | yes | yes ([(0, 0)]) | frames quality=['False']; warnings=['dynamic_range_low']; manifest=completed |
| obs_6mm | 25/25 | yes | yes ([(0, 0)]) | frames quality=['False']; warnings=['dynamic_range_low']; manifest=completed |
| obs_10mm | 25/25 | yes | yes ([(0, 0)]) | frames quality=['False']; warnings=['dynamic_range_low']; manifest=completed |
| obs_20mm | 25/25 | yes | yes ([(0, 0)]) | frames quality=['False']; warnings=['dynamic_range_low']; manifest=completed |
| obs_30mm | 25/25 | yes | yes ([(0, 0)]) | frames quality=['False']; warnings=['dynamic_range_low']; manifest=completed |

## Geometry-only ROI registry

本报告使用 30/30 人工确认后冻结的 v-axis ROI；自动候选仅作为边界差异对照保留。
ROI 没有读取或计算 C0/C1 高度来选取；每个位置使用固定 height window 与相邻两侧 baseline window。

| 高度 | position | pose | v_center | height_v_range | baseline_before | baseline_after |
|---|---:|---|---:|---|---|---|
| obs_1mm | 1 | 001 | 245.0 | [205, 284] | [6, 79] | [308, 484] |
| obs_1mm | 2 | 002 | 1067.5 | [1036, 1100] | [717, 871] | [1131, 1296] |
| obs_1mm | 3 | 003 | 1515.0 | [1478, 1548] | [1154, 1332] | [1573, 1749] |
| obs_1mm | 4 | 004 | 2157.5 | [2125, 2188] | [1798, 1970] | [2215, 2383] |
| obs_1mm | 5 | 005 | 2825.0 | [2792, 2858] | [2475, 2635] | [2880, 2974] |
| obs_2mm | 1 | 005 | 252.5 | [219, 285] | [16, 69] | [314, 470] |
| obs_2mm | 2 | 004 | 942.5 | [908, 977] | [594, 751] | [1003, 1164] |
| obs_2mm | 3 | 003 | 1760.0 | [1730, 1791] | [1411, 1592] | [1827, 1992] |
| obs_2mm | 4 | 002 | 2407.5 | [2374, 2441] | [2048, 2213] | [2472, 2622] |
| obs_2mm | 5 | 001 | 2817.5 | [2777, 2860] | [2472, 2617] | [2874, 2985] |
| obs_6mm | 1 | 001 | 300.0 | [269, 332] | [13, 130] | [366, 523] |
| obs_6mm | 2 | 002 | 1125.0 | [1093, 1156] | [777, 925] | [1189, 1349] |
| obs_6mm | 3 | 003 | 1532.5 | [1502, 1565] | [1184, 1355] | [1603, 1761] |
| obs_6mm | 4 | 004 | 2392.5 | [2360, 2427] | [2022, 2177] | [2462, 2754] |
| obs_6mm | 5 | 005 | 2840.0 | [2808, 2872] | [2479, 2620] | [2902, 2983] |
| obs_10mm | 1 | 005 | 300.0 | [265, 333] | [22, 129] | [367, 527] |
| obs_10mm | 2 | 004 | 1130.0 | [1099, 1160] | [789, 955] | [1199, 1361] |
| obs_10mm | 3 | 003 | 1980.0 | [1947, 2013] | [1618, 1758] | [2046, 2181] |
| obs_10mm | 4 | 002 | 2400.0 | [2369, 2429] | [2032, 2176] | [2467, 2599] |
| obs_10mm | 5 | 001 | 2825.0 | [2797, 2856] | [2481, 2613] | [2892, 2975] |
| obs_20mm | 1 | 005 | 252.5 | [217, 291] | [16, 122] | [368, 531] |
| obs_20mm | 2 | 004 | 1112.5 | [1074, 1148] | [755, 907] | [1186, 1336] |
| obs_20mm | 3 | 003 | 1945.0 | [1909, 1978] | [1589, 1730] | [2018, 2144] |
| obs_20mm | 4 | 002 | 2365.0 | [2333, 2394] | [2004, 2144] | [2430, 2562] |
| obs_20mm | 5 | 001 | 2787.5 | [2757, 2819] | [2438, 2560] | [2858, 2979] |
| obs_30mm | 1 | 001 | 257.5 | [227, 292] | [19, 123] | [367, 511] |
| obs_30mm | 2 | 002 | 1110.0 | [1077, 1145] | [785, 938] | [1184, 1357] |
| obs_30mm | 3 | 003 | 1972.5 | [1936, 2009] | [1612, 1749] | [2047, 2169] |
| obs_30mm | 4 | 004 | 2397.5 | [2358, 2435] | [2031, 2171] | [2478, 2691] |
| obs_30mm | 5 | 005 | 2842.5 | [2807, 2880] | [2504, 2603] | [2915, 2994] |

- ROI source：manual_frozen；人工确认标记：complete。
- 预览：figures/roi_registry_overview.png 与 overlays/ 下每个高度×pose 一张图。

## 缺失条件诊断

本轮没有缺失的 height × position × model × mode 条件。

## 30 个 height × position 条件（local_adjacent）

| 高度 | pos | v_center | truth | C0 mean | C0 err | C0 pass | C1 mean | C1 err | C1 pass |
|---|---:|---:|---:|---:|---:|:---:|---:|---:|:---:|
| obs_1mm | 1 | 245.0 | 1.001 | 0.9888 | -0.0122 | PASS | 1.0092 | 0.0082 | PASS |
| obs_1mm | 2 | 1067.5 | 1.001 | 0.9621 | -0.0389 | PASS | 0.9640 | -0.0370 | PASS |
| obs_1mm | 3 | 1515.0 | 1.001 | 1.0164 | 0.0154 | PASS | 1.0145 | 0.0135 | PASS |
| obs_1mm | 4 | 2157.5 | 1.001 | 0.9479 | -0.0531 | PASS | 0.9454 | -0.0556 | PASS |
| obs_1mm | 5 | 2825.0 | 1.001 | 0.9809 | -0.0201 | PASS | 0.9662 | -0.0348 | PASS |
| obs_2mm | 1 | 252.5 | 2.000 | 1.9879 | -0.0121 | PASS | 2.0049 | 0.0049 | PASS |
| obs_2mm | 2 | 942.5 | 2.000 | 1.9578 | -0.0422 | PASS | 1.9654 | -0.0346 | PASS |
| obs_2mm | 3 | 1760.0 | 2.000 | 1.9423 | -0.0577 | PASS | 1.9418 | -0.0582 | PASS |
| obs_2mm | 4 | 2407.5 | 2.000 | 1.9821 | -0.0179 | PASS | 1.9765 | -0.0235 | PASS |
| obs_2mm | 5 | 2817.5 | 2.000 | 1.9734 | -0.0266 | PASS | 1.9577 | -0.0423 | PASS |
| obs_6mm | 1 | 300.0 | 6.000 | 5.9779 | -0.0221 | PASS | 5.9942 | -0.0058 | PASS |
| obs_6mm | 2 | 1125.0 | 6.000 | 5.9637 | -0.0363 | PASS | 5.9645 | -0.0355 | PASS |
| obs_6mm | 3 | 1532.5 | 6.000 | 5.9921 | -0.0079 | PASS | 5.9899 | -0.0101 | PASS |
| obs_6mm | 4 | 2392.5 | 6.000 | 6.0130 | 0.0130 | PASS | 6.0055 | 0.0055 | PASS |
| obs_6mm | 5 | 2840.0 | 6.000 | 5.9491 | -0.0509 | PASS | 5.9350 | -0.0650 | PASS |
| obs_10mm | 1 | 300.0 | 10.000 | 9.9578 | -0.0422 | PASS | 9.9698 | -0.0302 | PASS |
| obs_10mm | 2 | 1130.0 | 10.000 | 9.9532 | -0.0468 | PASS | 9.9524 | -0.0476 | PASS |
| obs_10mm | 3 | 1980.0 | 10.000 | 9.9706 | -0.0294 | PASS | 9.9696 | -0.0304 | PASS |
| obs_10mm | 4 | 2400.0 | 10.000 | 9.9569 | -0.0431 | PASS | 9.9515 | -0.0485 | PASS |
| obs_10mm | 5 | 2825.0 | 10.000 | 9.9291 | -0.0709 | PASS | 9.9172 | -0.0828 | PASS |
| obs_20mm | 1 | 252.5 | 20.000 | 19.9499 | -0.0501 | PASS | 19.9526 | -0.0474 | PASS |
| obs_20mm | 2 | 1112.5 | 20.000 | 19.9177 | -0.0823 | PASS | 19.9192 | -0.0808 | PASS |
| obs_20mm | 3 | 1945.0 | 20.000 | 19.9259 | -0.0741 | PASS | 19.9253 | -0.0747 | PASS |
| obs_20mm | 4 | 2365.0 | 20.000 | 19.9007 | -0.0993 | PASS | 19.8966 | -0.1034 | PASS |
| obs_20mm | 5 | 2787.5 | 20.000 | 19.8791 | -0.1209 | PASS | 19.8674 | -0.1326 | PASS |
| obs_30mm | 1 | 257.5 | 30.000 | 29.9108 | -0.0892 | PASS | 29.9042 | -0.0958 | PASS |
| obs_30mm | 2 | 1110.0 | 30.000 | 29.8735 | -0.1265 | PASS | 29.8747 | -0.1253 | PASS |
| obs_30mm | 3 | 1972.5 | 30.000 | 29.9163 | -0.0837 | PASS | 29.9156 | -0.0844 | PASS |
| obs_30mm | 4 | 2397.5 | 30.000 | 29.9233 | -0.0767 | PASS | 29.9194 | -0.0806 | PASS |
| obs_30mm | 5 | 2842.5 | 30.000 | 29.8357 | -0.1643 | PASS | 29.8331 | -0.1669 | PASS |

## 六个高度的 position bias range（local_adjacent）

| 高度 | truth | C0 range | C1 range | C0 position MAE | C1 position MAE |
|---|---:|---:|---:|---:|---:|
| obs_1mm | 1.001 | 0.0686 | 0.0691 | 0.0280 | 0.0298 |
| obs_2mm | 2.000 | 0.0456 | 0.0631 | 0.0313 | 0.0327 |
| obs_6mm | 6.000 | 0.0639 | 0.0705 | 0.0260 | 0.0244 |
| obs_10mm | 10.000 | 0.0415 | 0.0526 | 0.0465 | 0.0479 |
| obs_20mm | 20.000 | 0.0708 | 0.0853 | 0.0853 | 0.0878 |
| obs_30mm | 30.000 | 0.0876 | 0.0863 | 0.1081 | 0.1106 |

## 四层 Bias / MAE / RMSE / P95 / Max

Bias 为 signed error 的均值；MAE、RMSE、P95、Max 均以绝对误差作为幅值口径。

| layer | height/position | model | mode | n | failed | Bias | MAE | RMSE | P95 | Max | pass |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single_frame |  | C0 | local_adjacent | 146 | 4 | -0.0530 | 0.0549 | 0.0668 | 0.1261 | 0.1661 | 146/146 |
| global |  | C0 | local_adjacent | 30 | 0 | -0.0523 | 0.0542 | 0.0660 | 0.1240 | 0.1643 | 30/30 |
| height_position | obs_1mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.0122 | 0.0122 | 0.0124 | 0.0154 | 0.0160 | 5/5 |
| height_position | obs_1mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.0389 | 0.0389 | 0.0390 | 0.0427 | 0.0435 | 5/5 |
| height_position | obs_1mm/position_3 | C0 | local_adjacent | 5 | 0 | 0.0154 | 0.0154 | 0.0155 | 0.0170 | 0.0173 | 5/5 |
| height_position | obs_1mm/position_4 | C0 | local_adjacent | 5 | 0 | -0.0531 | 0.0531 | 0.0532 | 0.0556 | 0.0562 | 5/5 |
| height_position | obs_1mm/position_5 | C0 | local_adjacent | 5 | 0 | -0.0201 | 0.0201 | 0.0202 | 0.0212 | 0.0213 | 5/5 |
| height_position | obs_2mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.0121 | 0.0121 | 0.0122 | 0.0142 | 0.0146 | 5/5 |
| height_position | obs_2mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.0422 | 0.0422 | 0.0422 | 0.0445 | 0.0448 | 5/5 |
| height_position | obs_2mm/position_3 | C0 | local_adjacent | 5 | 0 | -0.0577 | 0.0577 | 0.0577 | 0.0591 | 0.0593 | 5/5 |
| height_position | obs_2mm/position_4 | C0 | local_adjacent | 5 | 0 | -0.0179 | 0.0179 | 0.0182 | 0.0223 | 0.0231 | 5/5 |
| height_position | obs_2mm/position_5 | C0 | local_adjacent | 1 | 4 | -0.0266 | 0.0266 | 0.0266 | 0.0266 | 0.0266 | 1/1 |
| height_position | obs_6mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.0221 | 0.0221 | 0.0222 | 0.0246 | 0.0248 | 5/5 |
| height_position | obs_6mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.0363 | 0.0363 | 0.0363 | 0.0391 | 0.0395 | 5/5 |
| height_position | obs_6mm/position_3 | C0 | local_adjacent | 5 | 0 | -0.0079 | 0.0079 | 0.0082 | 0.0107 | 0.0109 | 5/5 |
| height_position | obs_6mm/position_4 | C0 | local_adjacent | 5 | 0 | 0.0130 | 0.0130 | 0.0135 | 0.0185 | 0.0198 | 5/5 |
| height_position | obs_6mm/position_5 | C0 | local_adjacent | 5 | 0 | -0.0509 | 0.0509 | 0.0510 | 0.0550 | 0.0559 | 5/5 |
| height_position | obs_10mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.0422 | 0.0422 | 0.0422 | 0.0443 | 0.0446 | 5/5 |
| height_position | obs_10mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.0468 | 0.0468 | 0.0469 | 0.0505 | 0.0515 | 5/5 |
| height_position | obs_10mm/position_3 | C0 | local_adjacent | 5 | 0 | -0.0294 | 0.0294 | 0.0295 | 0.0312 | 0.0313 | 5/5 |
| height_position | obs_10mm/position_4 | C0 | local_adjacent | 5 | 0 | -0.0431 | 0.0431 | 0.0431 | 0.0457 | 0.0457 | 5/5 |
| height_position | obs_10mm/position_5 | C0 | local_adjacent | 5 | 0 | -0.0709 | 0.0709 | 0.0711 | 0.0754 | 0.0758 | 5/5 |
| height_position | obs_20mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.0501 | 0.0501 | 0.0501 | 0.0519 | 0.0520 | 5/5 |
| height_position | obs_20mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.0823 | 0.0823 | 0.0823 | 0.0853 | 0.0854 | 5/5 |
| height_position | obs_20mm/position_3 | C0 | local_adjacent | 5 | 0 | -0.0741 | 0.0741 | 0.0741 | 0.0779 | 0.0789 | 5/5 |
| height_position | obs_20mm/position_4 | C0 | local_adjacent | 5 | 0 | -0.0993 | 0.0993 | 0.0993 | 0.1005 | 0.1007 | 5/5 |
| height_position | obs_20mm/position_5 | C0 | local_adjacent | 5 | 0 | -0.1209 | 0.1209 | 0.1209 | 0.1241 | 0.1248 | 5/5 |
| height_position | obs_30mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.0892 | 0.0892 | 0.0892 | 0.0906 | 0.0908 | 5/5 |
| height_position | obs_30mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.1265 | 0.1265 | 0.1265 | 0.1280 | 0.1282 | 5/5 |
| height_position | obs_30mm/position_3 | C0 | local_adjacent | 5 | 0 | -0.0837 | 0.0837 | 0.0837 | 0.0864 | 0.0867 | 5/5 |
| height_position | obs_30mm/position_4 | C0 | local_adjacent | 5 | 0 | -0.0767 | 0.0767 | 0.0768 | 0.0809 | 0.0813 | 5/5 |
| height_position | obs_30mm/position_5 | C0 | local_adjacent | 5 | 0 | -0.1643 | 0.1643 | 0.1643 | 0.1660 | 0.1661 | 5/5 |
| single_frame |  | C0 | all_non_height | 146 | 4 | -0.0491 | 0.0831 | 0.1015 | 0.2053 | 0.2684 | 137/146 |
| global |  | C0 | all_non_height | 30 | 0 | -0.0497 | 0.0827 | 0.1005 | 0.1848 | 0.2503 | 28/30 |
| height_position | obs_1mm/position_1 | C0 | all_non_height | 5 | 0 | 0.1052 | 0.1052 | 0.1052 | 0.1092 | 0.1101 | 5/5 |
| height_position | obs_1mm/position_2 | C0 | all_non_height | 5 | 0 | -0.0932 | 0.0932 | 0.0933 | 0.0971 | 0.0980 | 5/5 |
| height_position | obs_1mm/position_3 | C0 | all_non_height | 5 | 0 | 0.0046 | 0.0046 | 0.0051 | 0.0072 | 0.0073 | 5/5 |
| height_position | obs_1mm/position_4 | C0 | all_non_height | 5 | 0 | -0.0477 | 0.0477 | 0.0478 | 0.0502 | 0.0508 | 5/5 |
| height_position | obs_1mm/position_5 | C0 | all_non_height | 5 | 0 | -0.0716 | 0.0716 | 0.0716 | 0.0725 | 0.0725 | 5/5 |
| height_position | obs_2mm/position_1 | C0 | all_non_height | 5 | 0 | 0.0945 | 0.0945 | 0.0945 | 0.0962 | 0.0964 | 5/5 |
| height_position | obs_2mm/position_2 | C0 | all_non_height | 5 | 0 | -0.1344 | 0.1344 | 0.1344 | 0.1371 | 0.1377 | 5/5 |
| height_position | obs_2mm/position_3 | C0 | all_non_height | 5 | 0 | -0.0625 | 0.0625 | 0.0625 | 0.0641 | 0.0643 | 5/5 |
| height_position | obs_2mm/position_4 | C0 | all_non_height | 5 | 0 | 0.0253 | 0.0253 | 0.0255 | 0.0297 | 0.0304 | 5/5 |
| height_position | obs_2mm/position_5 | C0 | all_non_height | 1 | 4 | -0.0694 | 0.0694 | 0.0694 | 0.0694 | 0.0694 | 1/1 |
| height_position | obs_6mm/position_1 | C0 | all_non_height | 5 | 0 | 0.0582 | 0.0582 | 0.0584 | 0.0636 | 0.0641 | 5/5 |
| height_position | obs_6mm/position_2 | C0 | all_non_height | 5 | 0 | -0.0621 | 0.0621 | 0.0622 | 0.0659 | 0.0663 | 5/5 |
| height_position | obs_6mm/position_3 | C0 | all_non_height | 5 | 0 | -0.0314 | 0.0314 | 0.0315 | 0.0335 | 0.0336 | 5/5 |
| height_position | obs_6mm/position_4 | C0 | all_non_height | 5 | 0 | 0.0254 | 0.0254 | 0.0256 | 0.0306 | 0.0318 | 5/5 |
| height_position | obs_6mm/position_5 | C0 | all_non_height | 5 | 0 | -0.1274 | 0.1274 | 0.1274 | 0.1305 | 0.1307 | 5/5 |
| height_position | obs_10mm/position_1 | C0 | all_non_height | 5 | 0 | 0.0855 | 0.0855 | 0.0855 | 0.0873 | 0.0873 | 5/5 |
| height_position | obs_10mm/position_2 | C0 | all_non_height | 5 | 0 | -0.0259 | 0.0259 | 0.0262 | 0.0316 | 0.0332 | 5/5 |
| height_position | obs_10mm/position_3 | C0 | all_non_height | 5 | 0 | -0.0371 | 0.0371 | 0.0372 | 0.0392 | 0.0394 | 5/5 |
| height_position | obs_10mm/position_4 | C0 | all_non_height | 5 | 0 | -0.0135 | 0.0135 | 0.0166 | 0.0277 | 0.0305 | 5/5 |
| height_position | obs_10mm/position_5 | C0 | all_non_height | 5 | 0 | -0.1205 | 0.1205 | 0.1206 | 0.1238 | 0.1239 | 5/5 |
| height_position | obs_20mm/position_1 | C0 | all_non_height | 5 | 0 | 0.0697 | 0.0697 | 0.0697 | 0.0705 | 0.0705 | 5/5 |
| height_position | obs_20mm/position_2 | C0 | all_non_height | 5 | 0 | -0.1304 | 0.1304 | 0.1319 | 0.1484 | 0.1489 | 5/5 |
| height_position | obs_20mm/position_3 | C0 | all_non_height | 5 | 0 | -0.2503 | 0.2503 | 0.2521 | 0.2678 | 0.2684 | 1/5 |
| height_position | obs_20mm/position_4 | C0 | all_non_height | 5 | 0 | -0.0361 | 0.0361 | 0.0361 | 0.0375 | 0.0379 | 5/5 |
| height_position | obs_20mm/position_5 | C0 | all_non_height | 5 | 0 | -0.1529 | 0.1529 | 0.1529 | 0.1557 | 0.1561 | 5/5 |
| height_position | obs_30mm/position_1 | C0 | all_non_height | 5 | 0 | 0.0268 | 0.0268 | 0.0268 | 0.0280 | 0.0283 | 5/5 |
| height_position | obs_30mm/position_2 | C0 | all_non_height | 5 | 0 | -0.1583 | 0.1583 | 0.1583 | 0.1611 | 0.1614 | 5/5 |
| height_position | obs_30mm/position_3 | C0 | all_non_height | 5 | 0 | -0.0978 | 0.0978 | 0.0978 | 0.1006 | 0.1006 | 5/5 |
| height_position | obs_30mm/position_4 | C0 | all_non_height | 5 | 0 | -0.0567 | 0.0567 | 0.0568 | 0.0601 | 0.0602 | 5/5 |
| height_position | obs_30mm/position_5 | C0 | all_non_height | 5 | 0 | -0.2065 | 0.2065 | 0.2065 | 0.2084 | 0.2088 | 0/5 |
| single_frame |  | C0 | fixed_zg_zero | 146 | 4 | -0.0505 | 0.0625 | 0.0822 | 0.1762 | 0.1882 | 146/146 |
| global |  | C0 | fixed_zg_zero | 30 | 0 | -0.0514 | 0.0631 | 0.0823 | 0.1635 | 0.1809 | 30/30 |
| height_position | obs_1mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -0.0104 | 0.0104 | 0.0107 | 0.0135 | 0.0140 | 5/5 |
| height_position | obs_1mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -0.1809 | 0.1809 | 0.1810 | 0.1872 | 0.1882 | 5/5 |
| height_position | obs_1mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -0.0921 | 0.0921 | 0.0921 | 0.0939 | 0.0940 | 5/5 |
| height_position | obs_1mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -0.1042 | 0.1042 | 0.1042 | 0.1073 | 0.1079 | 5/5 |
| height_position | obs_1mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -0.1029 | 0.1029 | 0.1029 | 0.1038 | 0.1038 | 5/5 |
| height_position | obs_2mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -0.0048 | 0.0048 | 0.0052 | 0.0078 | 0.0088 | 5/5 |
| height_position | obs_2mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -0.1771 | 0.1771 | 0.1771 | 0.1800 | 0.1806 | 5/5 |
| height_position | obs_2mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -0.1153 | 0.1153 | 0.1153 | 0.1167 | 0.1169 | 5/5 |
| height_position | obs_2mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -0.0249 | 0.0249 | 0.0251 | 0.0298 | 0.0307 | 5/5 |
| height_position | obs_2mm/position_5 | C0 | fixed_zg_zero | 1 | 4 | -0.0855 | 0.0855 | 0.0855 | 0.0855 | 0.0855 | 1/1 |
| height_position | obs_6mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -0.0028 | 0.0028 | 0.0036 | 0.0049 | 0.0050 | 5/5 |
| height_position | obs_6mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -0.1036 | 0.1036 | 0.1036 | 0.1080 | 0.1086 | 5/5 |
| height_position | obs_6mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -0.0662 | 0.0662 | 0.0662 | 0.0688 | 0.0689 | 5/5 |
| height_position | obs_6mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | 0.0107 | 0.0107 | 0.0114 | 0.0163 | 0.0177 | 5/5 |
| height_position | obs_6mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -0.1009 | 0.1009 | 0.1010 | 0.1053 | 0.1057 | 5/5 |
| height_position | obs_10mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -0.0043 | 0.0043 | 0.0047 | 0.0067 | 0.0070 | 5/5 |
| height_position | obs_10mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -0.0749 | 0.0749 | 0.0749 | 0.0786 | 0.0795 | 5/5 |
| height_position | obs_10mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -0.0564 | 0.0564 | 0.0564 | 0.0591 | 0.0592 | 5/5 |
| height_position | obs_10mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | 0.0104 | 0.0104 | 0.0105 | 0.0124 | 0.0126 | 5/5 |
| height_position | obs_10mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -0.0820 | 0.0820 | 0.0822 | 0.0862 | 0.0865 | 5/5 |
| height_position | obs_20mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | 0.0789 | 0.0789 | 0.0790 | 0.0810 | 0.0813 | 5/5 |
| height_position | obs_20mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | 0.0011 | 0.0025 | 0.0027 | 0.0036 | 0.0037 | 5/5 |
| height_position | obs_20mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | 0.0040 | 0.0041 | 0.0046 | 0.0058 | 0.0060 | 5/5 |
| height_position | obs_20mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | 0.0665 | 0.0665 | 0.0665 | 0.0673 | 0.0673 | 5/5 |
| height_position | obs_20mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -0.0154 | 0.0154 | 0.0156 | 0.0182 | 0.0185 | 5/5 |
| height_position | obs_30mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | 0.0030 | 0.0030 | 0.0032 | 0.0041 | 0.0041 | 5/5 |
| height_position | obs_30mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -0.1065 | 0.1065 | 0.1065 | 0.1081 | 0.1084 | 5/5 |
| height_position | obs_30mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -0.0532 | 0.0532 | 0.0532 | 0.0554 | 0.0555 | 5/5 |
| height_position | obs_30mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -0.0064 | 0.0064 | 0.0074 | 0.0105 | 0.0106 | 5/5 |
| height_position | obs_30mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -0.1469 | 0.1469 | 0.1469 | 0.1503 | 0.1508 | 5/5 |
| single_frame |  | C1 | local_adjacent | 146 | 4 | -0.0537 | 0.0559 | 0.0691 | 0.1327 | 0.1692 | 146/146 |
| global |  | C1 | local_adjacent | 30 | 0 | -0.0534 | 0.0555 | 0.0685 | 0.1293 | 0.1669 | 30/30 |
| height_position | obs_1mm/position_1 | C1 | local_adjacent | 5 | 0 | 0.0082 | 0.0082 | 0.0086 | 0.0112 | 0.0118 | 5/5 |
| height_position | obs_1mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.0370 | 0.0370 | 0.0371 | 0.0407 | 0.0414 | 5/5 |
| height_position | obs_1mm/position_3 | C1 | local_adjacent | 5 | 0 | 0.0135 | 0.0135 | 0.0135 | 0.0148 | 0.0151 | 5/5 |
| height_position | obs_1mm/position_4 | C1 | local_adjacent | 5 | 0 | -0.0556 | 0.0556 | 0.0556 | 0.0582 | 0.0589 | 5/5 |
| height_position | obs_1mm/position_5 | C1 | local_adjacent | 5 | 0 | -0.0348 | 0.0348 | 0.0348 | 0.0361 | 0.0362 | 5/5 |
| height_position | obs_2mm/position_1 | C1 | local_adjacent | 5 | 0 | 0.0049 | 0.0049 | 0.0051 | 0.0060 | 0.0060 | 5/5 |
| height_position | obs_2mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.0346 | 0.0346 | 0.0347 | 0.0371 | 0.0376 | 5/5 |
| height_position | obs_2mm/position_3 | C1 | local_adjacent | 5 | 0 | -0.0582 | 0.0582 | 0.0583 | 0.0595 | 0.0597 | 5/5 |
| height_position | obs_2mm/position_4 | C1 | local_adjacent | 5 | 0 | -0.0235 | 0.0235 | 0.0237 | 0.0278 | 0.0285 | 5/5 |
| height_position | obs_2mm/position_5 | C1 | local_adjacent | 1 | 4 | -0.0423 | 0.0423 | 0.0423 | 0.0423 | 0.0423 | 1/1 |
| height_position | obs_6mm/position_1 | C1 | local_adjacent | 5 | 0 | -0.0058 | 0.0058 | 0.0062 | 0.0082 | 0.0084 | 5/5 |
| height_position | obs_6mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.0355 | 0.0355 | 0.0356 | 0.0378 | 0.0380 | 5/5 |
| height_position | obs_6mm/position_3 | C1 | local_adjacent | 5 | 0 | -0.0101 | 0.0101 | 0.0104 | 0.0131 | 0.0134 | 5/5 |
| height_position | obs_6mm/position_4 | C1 | local_adjacent | 5 | 0 | 0.0055 | 0.0055 | 0.0065 | 0.0107 | 0.0120 | 5/5 |
| height_position | obs_6mm/position_5 | C1 | local_adjacent | 5 | 0 | -0.0650 | 0.0650 | 0.0650 | 0.0693 | 0.0703 | 5/5 |
| height_position | obs_10mm/position_1 | C1 | local_adjacent | 5 | 0 | -0.0302 | 0.0302 | 0.0302 | 0.0323 | 0.0327 | 5/5 |
| height_position | obs_10mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.0476 | 0.0476 | 0.0477 | 0.0512 | 0.0522 | 5/5 |
| height_position | obs_10mm/position_3 | C1 | local_adjacent | 5 | 0 | -0.0304 | 0.0304 | 0.0305 | 0.0323 | 0.0326 | 5/5 |
| height_position | obs_10mm/position_4 | C1 | local_adjacent | 5 | 0 | -0.0485 | 0.0485 | 0.0486 | 0.0513 | 0.0515 | 5/5 |
| height_position | obs_10mm/position_5 | C1 | local_adjacent | 5 | 0 | -0.0828 | 0.0828 | 0.0829 | 0.0875 | 0.0879 | 5/5 |
| height_position | obs_20mm/position_1 | C1 | local_adjacent | 5 | 0 | -0.0474 | 0.0474 | 0.0474 | 0.0494 | 0.0496 | 5/5 |
| height_position | obs_20mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.0808 | 0.0808 | 0.0809 | 0.0839 | 0.0840 | 5/5 |
| height_position | obs_20mm/position_3 | C1 | local_adjacent | 5 | 0 | -0.0747 | 0.0747 | 0.0747 | 0.0784 | 0.0794 | 5/5 |
| height_position | obs_20mm/position_4 | C1 | local_adjacent | 5 | 0 | -0.1034 | 0.1034 | 0.1034 | 0.1044 | 0.1045 | 5/5 |
| height_position | obs_20mm/position_5 | C1 | local_adjacent | 5 | 0 | -0.1326 | 0.1326 | 0.1326 | 0.1356 | 0.1362 | 5/5 |
| height_position | obs_30mm/position_1 | C1 | local_adjacent | 5 | 0 | -0.0958 | 0.0958 | 0.0958 | 0.0971 | 0.0972 | 5/5 |
| height_position | obs_30mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.1253 | 0.1253 | 0.1253 | 0.1266 | 0.1268 | 5/5 |
| height_position | obs_30mm/position_3 | C1 | local_adjacent | 5 | 0 | -0.0844 | 0.0844 | 0.0845 | 0.0874 | 0.0876 | 5/5 |
| height_position | obs_30mm/position_4 | C1 | local_adjacent | 5 | 0 | -0.0806 | 0.0806 | 0.0807 | 0.0831 | 0.0832 | 5/5 |
| height_position | obs_30mm/position_5 | C1 | local_adjacent | 5 | 0 | -0.1669 | 0.1669 | 0.1669 | 0.1690 | 0.1692 | 5/5 |
| single_frame |  | C1 | all_non_height | 146 | 4 | -0.0544 | 0.0630 | 0.0840 | 0.1551 | 0.2880 | 141/146 |
| global |  | C1 | all_non_height | 30 | 0 | -0.0539 | 0.0622 | 0.0830 | 0.1443 | 0.2787 | 29/30 |
| height_position | obs_1mm/position_1 | C1 | all_non_height | 5 | 0 | 0.0544 | 0.0544 | 0.0545 | 0.0575 | 0.0579 | 5/5 |
| height_position | obs_1mm/position_2 | C1 | all_non_height | 5 | 0 | -0.0534 | 0.0534 | 0.0535 | 0.0569 | 0.0575 | 5/5 |
| height_position | obs_1mm/position_3 | C1 | all_non_height | 5 | 0 | -0.0008 | 0.0011 | 0.0014 | 0.0022 | 0.0023 | 5/5 |
| height_position | obs_1mm/position_4 | C1 | all_non_height | 5 | 0 | -0.0659 | 0.0659 | 0.0660 | 0.0682 | 0.0687 | 5/5 |
| height_position | obs_1mm/position_5 | C1 | all_non_height | 5 | 0 | -0.0305 | 0.0305 | 0.0306 | 0.0317 | 0.0319 | 5/5 |
| height_position | obs_2mm/position_1 | C1 | all_non_height | 5 | 0 | 0.0272 | 0.0272 | 0.0273 | 0.0294 | 0.0296 | 5/5 |
| height_position | obs_2mm/position_2 | C1 | all_non_height | 5 | 0 | -0.0680 | 0.0680 | 0.0681 | 0.0715 | 0.0721 | 5/5 |
| height_position | obs_2mm/position_3 | C1 | all_non_height | 5 | 0 | -0.0792 | 0.0792 | 0.0793 | 0.0806 | 0.0808 | 5/5 |
| height_position | obs_2mm/position_4 | C1 | all_non_height | 5 | 0 | -0.0089 | 0.0089 | 0.0095 | 0.0132 | 0.0138 | 5/5 |
| height_position | obs_2mm/position_5 | C1 | all_non_height | 1 | 4 | -0.0348 | 0.0348 | 0.0348 | 0.0348 | 0.0348 | 1/1 |
| height_position | obs_6mm/position_1 | C1 | all_non_height | 5 | 0 | 0.0225 | 0.0225 | 0.0226 | 0.0254 | 0.0254 | 5/5 |
| height_position | obs_6mm/position_2 | C1 | all_non_height | 5 | 0 | -0.0508 | 0.0508 | 0.0510 | 0.0560 | 0.0567 | 5/5 |
| height_position | obs_6mm/position_3 | C1 | all_non_height | 5 | 0 | -0.0413 | 0.0413 | 0.0414 | 0.0429 | 0.0430 | 5/5 |
| height_position | obs_6mm/position_4 | C1 | all_non_height | 5 | 0 | 0.0196 | 0.0196 | 0.0199 | 0.0251 | 0.0264 | 5/5 |
| height_position | obs_6mm/position_5 | C1 | all_non_height | 5 | 0 | -0.0569 | 0.0569 | 0.0570 | 0.0608 | 0.0615 | 5/5 |
| height_position | obs_10mm/position_1 | C1 | all_non_height | 5 | 0 | 0.0016 | 0.0021 | 0.0023 | 0.0035 | 0.0036 | 5/5 |
| height_position | obs_10mm/position_2 | C1 | all_non_height | 5 | 0 | -0.0070 | 0.0070 | 0.0075 | 0.0108 | 0.0118 | 5/5 |
| height_position | obs_10mm/position_3 | C1 | all_non_height | 5 | 0 | -0.0728 | 0.0728 | 0.0729 | 0.0752 | 0.0753 | 5/5 |
| height_position | obs_10mm/position_4 | C1 | all_non_height | 5 | 0 | -0.0307 | 0.0307 | 0.0308 | 0.0333 | 0.0334 | 5/5 |
| height_position | obs_10mm/position_5 | C1 | all_non_height | 5 | 0 | -0.0773 | 0.0773 | 0.0774 | 0.0818 | 0.0822 | 5/5 |
| height_position | obs_20mm/position_1 | C1 | all_non_height | 5 | 0 | -0.0327 | 0.0327 | 0.0328 | 0.0342 | 0.0344 | 5/5 |
| height_position | obs_20mm/position_2 | C1 | all_non_height | 5 | 0 | -0.0226 | 0.0226 | 0.0228 | 0.0262 | 0.0263 | 5/5 |
| height_position | obs_20mm/position_3 | C1 | all_non_height | 5 | 0 | -0.2787 | 0.2787 | 0.2791 | 0.2876 | 0.2880 | 0/5 |
| height_position | obs_20mm/position_4 | C1 | all_non_height | 5 | 0 | -0.0741 | 0.0741 | 0.0741 | 0.0751 | 0.0754 | 5/5 |
| height_position | obs_20mm/position_5 | C1 | all_non_height | 5 | 0 | -0.1307 | 0.1307 | 0.1307 | 0.1336 | 0.1342 | 5/5 |
| height_position | obs_30mm/position_1 | C1 | all_non_height | 5 | 0 | -0.0728 | 0.0728 | 0.0728 | 0.0738 | 0.0740 | 5/5 |
| height_position | obs_30mm/position_2 | C1 | all_non_height | 5 | 0 | -0.1143 | 0.1143 | 0.1143 | 0.1154 | 0.1154 | 5/5 |
| height_position | obs_30mm/position_3 | C1 | all_non_height | 5 | 0 | -0.1155 | 0.1155 | 0.1155 | 0.1175 | 0.1176 | 5/5 |
| height_position | obs_30mm/position_4 | C1 | all_non_height | 5 | 0 | -0.0661 | 0.0661 | 0.0662 | 0.0696 | 0.0696 | 5/5 |
| height_position | obs_30mm/position_5 | C1 | all_non_height | 5 | 0 | -0.1554 | 0.1554 | 0.1554 | 0.1570 | 0.1572 | 5/5 |
| single_frame |  | C1 | fixed_zg_zero | 146 | 4 | -0.0501 | 0.0590 | 0.0709 | 0.1358 | 0.1610 | 146/146 |
| global |  | C1 | fixed_zg_zero | 30 | 0 | -0.0494 | 0.0580 | 0.0700 | 0.1318 | 0.1537 | 30/30 |
| height_position | obs_1mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -0.0772 | 0.0772 | 0.0772 | 0.0804 | 0.0809 | 5/5 |
| height_position | obs_1mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -0.1537 | 0.1537 | 0.1538 | 0.1600 | 0.1610 | 5/5 |
| height_position | obs_1mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.0968 | 0.0968 | 0.0968 | 0.0985 | 0.0987 | 5/5 |
| height_position | obs_1mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -0.1207 | 0.1207 | 0.1207 | 0.1238 | 0.1243 | 5/5 |
| height_position | obs_1mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -0.0394 | 0.0394 | 0.0394 | 0.0405 | 0.0406 | 5/5 |
| height_position | obs_2mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -0.0674 | 0.0674 | 0.0674 | 0.0698 | 0.0705 | 5/5 |
| height_position | obs_2mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -0.1368 | 0.1368 | 0.1368 | 0.1397 | 0.1403 | 5/5 |
| height_position | obs_2mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.1257 | 0.1257 | 0.1257 | 0.1270 | 0.1272 | 5/5 |
| height_position | obs_2mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -0.0361 | 0.0361 | 0.0363 | 0.0410 | 0.0420 | 5/5 |
| height_position | obs_2mm/position_5 | C1 | fixed_zg_zero | 1 | 4 | -0.0267 | 0.0267 | 0.0267 | 0.0267 | 0.0267 | 1/1 |
| height_position | obs_6mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -0.0417 | 0.0417 | 0.0418 | 0.0438 | 0.0439 | 5/5 |
| height_position | obs_6mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -0.0825 | 0.0825 | 0.0826 | 0.0869 | 0.0875 | 5/5 |
| height_position | obs_6mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.0715 | 0.0715 | 0.0715 | 0.0741 | 0.0743 | 5/5 |
| height_position | obs_6mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -0.0009 | 0.0034 | 0.0039 | 0.0059 | 0.0062 | 5/5 |
| height_position | obs_6mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -0.0326 | 0.0326 | 0.0328 | 0.0369 | 0.0378 | 5/5 |
| height_position | obs_10mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -0.0444 | 0.0444 | 0.0444 | 0.0464 | 0.0466 | 5/5 |
| height_position | obs_10mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -0.0542 | 0.0542 | 0.0543 | 0.0579 | 0.0588 | 5/5 |
| height_position | obs_10mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.0711 | 0.0711 | 0.0711 | 0.0738 | 0.0739 | 5/5 |
| height_position | obs_10mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -0.0011 | 0.0017 | 0.0020 | 0.0031 | 0.0031 | 5/5 |
| height_position | obs_10mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -0.0194 | 0.0194 | 0.0198 | 0.0235 | 0.0238 | 5/5 |
| height_position | obs_20mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | 0.0177 | 0.0177 | 0.0178 | 0.0202 | 0.0207 | 5/5 |
| height_position | obs_20mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | 0.0235 | 0.0235 | 0.0236 | 0.0260 | 0.0261 | 5/5 |
| height_position | obs_20mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.0100 | 0.0100 | 0.0102 | 0.0133 | 0.0142 | 5/5 |
| height_position | obs_20mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | 0.0536 | 0.0536 | 0.0536 | 0.0544 | 0.0545 | 5/5 |
| height_position | obs_20mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | 0.0340 | 0.0340 | 0.0341 | 0.0373 | 0.0379 | 5/5 |
| height_position | obs_30mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -0.0557 | 0.0557 | 0.0557 | 0.0569 | 0.0571 | 5/5 |
| height_position | obs_30mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -0.0838 | 0.0838 | 0.0838 | 0.0855 | 0.0857 | 5/5 |
| height_position | obs_30mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.0678 | 0.0678 | 0.0678 | 0.0700 | 0.0701 | 5/5 |
| height_position | obs_30mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -0.0179 | 0.0179 | 0.0183 | 0.0221 | 0.0222 | 5/5 |
| height_position | obs_30mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -0.0770 | 0.0770 | 0.0770 | 0.0803 | 0.0807 | 5/5 |

## Repeatability

repeatability 是每个 height × position 条件内五次重复高度均值的样本标准差（ddof=1）；不是单帧 height_std_mm。

| model | mode | condition n | median sigma | P95 sigma | max sigma |
|---|---|---:|---:|---:|---:|
| C0 | local_adjacent | 29 | 0.0025 | 0.0040 | 0.0048 |
| C0 | all_non_height | 29 | 0.0028 | 0.0180 | 0.0336 |
| C0 | fixed_zg_zero | 29 | 0.0026 | 0.0046 | 0.0048 |
| C1 | local_adjacent | 29 | 0.0027 | 0.0038 | 0.0049 |
| C1 | all_non_height | 29 | 0.0025 | 0.0046 | 0.0168 |
| C1 | fixed_zg_zero | 29 | 0.0026 | 0.0044 | 0.0047 |

## Adjacent-height-difference MAE

| model | mode | n | Bias | MAE | RMSE | P95 | Max |
|---|---|---:|---:|---:|---:|---:|---:|
| C0 | local_adjacent | 25 | -0.0173 | 0.0288 | 0.0348 | 0.0562 | 0.0731 |
| C0 | all_non_height | 25 | -0.0156 | 0.0477 | 0.0674 | 0.1429 | 0.2132 |
| C0 | fixed_zg_zero | 25 | 0.0072 | 0.0461 | 0.0583 | 0.1027 | 0.1315 |
| C1 | local_adjacent | 25 | -0.0179 | 0.0286 | 0.0343 | 0.0547 | 0.0717 |
| C1 | all_non_height | 25 | -0.0171 | 0.0456 | 0.0650 | 0.1489 | 0.2058 |
| C1 | fixed_zg_zero | 25 | 0.0074 | 0.0441 | 0.0546 | 0.1027 | 0.1110 |

## C0/C1 配对

配对 condition 行数：90；每个 mode 期望 30 行。
两模型复用同一 Steger center array 与同一固定 ROI；详细结果见 paired_comparison.csv。

## 输出文件

- input_audit.csv / audit_summary.json
- roi_registry.json / roi_candidates.csv / figures/roi_registry_overview.png / overlays/*.png
- frame_metrics.csv / pointwise_diagnostics.csv
- height_measurements.csv / condition_measurements.csv
- stats_summary.csv / position_bias_ranges.csv / repeatability_summary.csv
- adjacent_height_difference.csv / adjacent_height_difference_summary.csv / paired_comparison.csv
- truth_config.json / provenance.json / acceptance_status.json / evaluation_summary.json
- figures/*.png
