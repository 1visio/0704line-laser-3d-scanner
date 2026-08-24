# Daheng C1 量块工程精度验收报告

- 生成时间（UTC）：2026-08-19T01:44:23.364025+00:00
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

ROI 由首次重复的图像空间中心线残差候选、五 pose 最小间距约束和全部重复的 v_center 中位数确定；没有读取或计算 C0/C1 高度来选 ROI。每个位置使用固定 height window 与相邻两侧 baseline window。

| 高度 | position | pose | v_center | height_v_range | baseline_before | baseline_after |
|---|---:|---|---:|---|---|---|
| obs_1mm | 1 | 001 | 267.0 | [222, 312] | [2, 202] | [332, 532] |
| obs_1mm | 2 | 002 | 1087.0 | [1042, 1132] | [822, 1022] | [1152, 1352] |
| obs_1mm | 3 | 003 | 1533.0 | [1488, 1578] | [1268, 1468] | [1598, 1798] |
| obs_1mm | 4 | 004 | 2177.0 | [2132, 2222] | [1912, 2112] | [2242, 2442] |
| obs_1mm | 5 | 005 | 2843.0 | [2798, 2888] | [2578, 2778] | [2908, 2999] |
| obs_2mm | 1 | 005 | 273.0 | [228, 318] | [8, 208] | [338, 538] |
| obs_2mm | 2 | 004 | 963.5 | [918, 1008] | [698, 898] | [1028, 1228] |
| obs_2mm | 3 | 003 | 1765.0 | [1722, 1812] | [1502, 1702] | [1832, 2032] |
| obs_2mm | 4 | 002 | 2439.0 | [2392, 2482] | [2172, 2372] | [2502, 2702] |
| obs_2mm | 5 | 001 | 2854.0 | [2792, 2882] | [2572, 2772] | [2902, 2999] |
| obs_6mm | 1 | 001 | 321.5 | [278, 368] | [58, 258] | [388, 588] |
| obs_6mm | 2 | 002 | 1141.5 | [1098, 1188] | [878, 1078] | [1208, 1408] |
| obs_6mm | 3 | 003 | 1534.0 | [1482, 1572] | [1262, 1462] | [1592, 1792] |
| obs_6mm | 4 | 004 | 2412.0 | [2368, 2458] | [2148, 2348] | [2478, 2678] |
| obs_6mm | 5 | 005 | 2844.0 | [2802, 2892] | [2582, 2782] | [2912, 2999] |
| obs_10mm | 1 | 005 | 319.0 | [278, 368] | [58, 258] | [388, 588] |
| obs_10mm | 2 | 004 | 1148.0 | [1108, 1198] | [888, 1088] | [1218, 1418] |
| obs_10mm | 3 | 003 | 1993.0 | [1952, 2042] | [1732, 1932] | [2062, 2262] |
| obs_10mm | 4 | 002 | 2416.0 | [2372, 2462] | [2152, 2352] | [2482, 2682] |
| obs_10mm | 5 | 001 | 2843.0 | [2802, 2892] | [2582, 2782] | [2912, 2999] |
| obs_20mm | 1 | 005 | 272.5 | [238, 328] | [18, 218] | [348, 548] |
| obs_20mm | 2 | 004 | 1131.0 | [1088, 1178] | [868, 1068] | [1198, 1398] |
| obs_20mm | 3 | 003 | 1960.5 | [1918, 2008] | [1698, 1898] | [2028, 2228] |
| obs_20mm | 4 | 002 | 2376.0 | [2332, 2422] | [2112, 2312] | [2442, 2642] |
| obs_20mm | 5 | 001 | 2801.0 | [2758, 2848] | [2538, 2738] | [2868, 2999] |
| obs_30mm | 1 | 001 | 268.0 | [232, 322] | [12, 212] | [342, 542] |
| obs_30mm | 2 | 002 | 1119.0 | [1078, 1168] | [858, 1058] | [1188, 1388] |
| obs_30mm | 3 | 003 | 1984.0 | [1942, 2032] | [1722, 1922] | [2052, 2252] |
| obs_30mm | 4 | 004 | 2415.0 | [2372, 2462] | [2152, 2352] | [2482, 2682] |
| obs_30mm | 5 | 005 | 2860.0 | [2818, 2908] | [2598, 2798] | [2928, 2999] |

- ROI 人工确认标记：REQUIRED。
- 预览：figures/roi_registry_overview.png 与 overlays/ 下每个高度×pose 一张图。

## 30 个 height × position 条件（local_adjacent）

| 高度 | pos | v_center | truth | C0 mean | C0 err | C0 pass | C1 mean | C1 err | C1 pass |
|---|---:|---:|---:|---:|---:|:---:|---:|---:|:---:|
| obs_1mm | 1 | 267.0 | 1.001 | 0.7629 | -0.2381 | FAIL | 0.7839 | -0.2171 | FAIL |
| obs_1mm | 2 | 1087.0 | 1.001 | 0.7972 | -0.2038 | FAIL | 0.7973 | -0.2037 | FAIL |
| obs_1mm | 3 | 1533.0 | 1.001 | 0.8172 | -0.1838 | PASS | 0.8154 | -0.1856 | PASS |
| obs_1mm | 4 | 2177.0 | 1.001 | 0.7730 | -0.2280 | FAIL | 0.7703 | -0.2307 | FAIL |
| obs_1mm | 5 | 2843.0 | 1.001 | 0.7479 | -0.2531 | FAIL | 0.7324 | -0.2686 | FAIL |
| obs_2mm | 1 | 273.0 | 2.000 | 1.6323 | -0.3677 | FAIL | 1.6493 | -0.3507 | FAIL |
| obs_2mm | 2 | 963.5 | 2.000 | 1.5642 | -0.4358 | FAIL | 1.5688 | -0.4312 | FAIL |
| obs_2mm | 3 | 1765.0 | 2.000 | 1.9502 | -0.0498 | PASS | 1.9500 | -0.0500 | PASS |
| obs_2mm | 4 | 2439.0 | 2.000 | 1.4098 | -0.5902 | FAIL | 1.4044 | -0.5956 | FAIL |
| obs_2mm | 5 | 2854.0 | 2.000 | 0.7125 | -1.2875 | FAIL | 0.6978 | -1.3022 | FAIL |
| obs_6mm | 1 | 321.5 | 6.000 | 4.6639 | -1.3361 | FAIL | 4.6864 | -1.3136 | FAIL |
| obs_6mm | 2 | 1141.5 | 6.000 | 5.0169 | -0.9831 | FAIL | 5.0160 | -0.9840 | FAIL |
| obs_6mm | 3 | 1534.0 | 6.000 | 5.9837 | -0.0163 | PASS | 5.9819 | -0.0181 | PASS |
| obs_6mm | 4 | 2412.0 | 6.000 | 5.0011 | -0.9989 | FAIL | 4.9958 | -1.0042 | FAIL |
| obs_6mm | 5 | 2844.0 | 6.000 | 5.9390 | -0.0610 | PASS | 5.9262 | -0.0738 | PASS |
| obs_10mm | 1 | 319.0 | 10.000 | 8.3415 | -1.6585 | FAIL | 8.3160 | -1.6840 | FAIL |
| obs_10mm | 2 | 1148.0 | 10.000 | 7.9782 | -2.0218 | FAIL | 7.9758 | -2.0242 | FAIL |
| obs_10mm | 3 | 1993.0 | 10.000 | 8.1878 | -1.8122 | FAIL | 8.1867 | -1.8133 | FAIL |
| obs_10mm | 4 | 2416.0 | 10.000 | 8.3827 | -1.6173 | FAIL | 8.3787 | -1.6213 | FAIL |
| obs_10mm | 5 | 2843.0 | 10.000 | 7.7502 | -2.2498 | FAIL | 7.7431 | -2.2569 | FAIL |
| obs_20mm | 1 | 272.5 | 20.000 | 19.5873 | -0.4127 | FAIL | 19.5908 | -0.4092 | FAIL |
| obs_20mm | 2 | 1131.0 | 20.000 | 15.5439 | -4.4561 | FAIL | 15.5397 | -4.4603 | FAIL |
| obs_20mm | 3 | 1960.5 | 20.000 | 16.9283 | -3.0717 | FAIL | 16.9264 | -3.0736 | FAIL |
| obs_20mm | 4 | 2376.0 | 20.000 | 17.6739 | -2.3261 | FAIL | 17.6720 | -2.3280 | FAIL |
| obs_20mm | 5 | 2801.0 | 20.000 | 17.5508 | -2.4492 | FAIL | 17.5593 | -2.4407 | FAIL |
| obs_30mm | 1 | 268.0 | 30.000 | 29.6550 | -0.3450 | FAIL | 29.6486 | -0.3514 | FAIL |
| obs_30mm | 2 | 1119.0 | 30.000 | 27.7868 | -2.2132 | FAIL | 27.7653 | -2.2347 | FAIL |
| obs_30mm | 3 | 1984.0 | 30.000 | 27.4852 | -2.5148 | FAIL | 27.4823 | -2.5177 | FAIL |
| obs_30mm | 4 | 2415.0 | 30.000 | 25.9854 | -4.0146 | FAIL | 26.0139 | -3.9861 | FAIL |
| obs_30mm | 5 | 2860.0 | 30.000 | 25.3229 | -4.6771 | FAIL | 25.3741 | -4.6259 | FAIL |

## 六个高度的 position bias range（local_adjacent）

| 高度 | truth | C0 range | C1 range | C0 position MAE | C1 position MAE |
|---|---:|---:|---:|---:|---:|
| obs_1mm | 1.001 | 0.0693 | 0.0830 | 0.2213 | 0.2211 |
| obs_2mm | 2.000 | 1.2377 | 1.2522 | 0.5462 | 0.5459 |
| obs_6mm | 6.000 | 1.3198 | 1.2955 | 0.6791 | 0.6787 |
| obs_10mm | 10.000 | 0.6325 | 0.6356 | 1.8719 | 1.8799 |
| obs_20mm | 20.000 | 4.0434 | 4.0511 | 2.5432 | 2.5424 |
| obs_30mm | 30.000 | 4.3321 | 4.2746 | 2.7530 | 2.7432 |

## 四层 Bias / MAE / RMSE / P95 / Max

Bias 为 signed error 的均值；MAE、RMSE、P95、Max 均以绝对误差作为幅值口径。

| layer | height/position | model | mode | n | failed | Bias | MAE | RMSE | P95 | Max | pass |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single_frame |  | C0 | local_adjacent | 150 | 0 | -1.4358 | 1.4358 | 1.9525 | 4.4382 | 4.8158 | 20/150 |
| global |  | C0 | local_adjacent | 30 | 0 | -1.4358 | 1.4358 | 1.9523 | 4.2574 | 4.6771 | 4/30 |
| height_position | obs_1mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.2381 | 0.2381 | 0.2381 | 0.2394 | 0.2394 | 0/5 |
| height_position | obs_1mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.2038 | 0.2038 | 0.2038 | 0.2053 | 0.2057 | 0/5 |
| height_position | obs_1mm/position_3 | C0 | local_adjacent | 5 | 0 | -0.1838 | 0.1838 | 0.1838 | 0.1855 | 0.1856 | 5/5 |
| height_position | obs_1mm/position_4 | C0 | local_adjacent | 5 | 0 | -0.2280 | 0.2280 | 0.2280 | 0.2319 | 0.2328 | 0/5 |
| height_position | obs_1mm/position_5 | C0 | local_adjacent | 5 | 0 | -0.2531 | 0.2531 | 0.2531 | 0.2585 | 0.2596 | 0/5 |
| height_position | obs_2mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.3677 | 0.3677 | 0.3677 | 0.3696 | 0.3696 | 0/5 |
| height_position | obs_2mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.4358 | 0.4358 | 0.4359 | 0.4425 | 0.4432 | 0/5 |
| height_position | obs_2mm/position_3 | C0 | local_adjacent | 5 | 0 | -0.0498 | 0.0498 | 0.0498 | 0.0517 | 0.0519 | 5/5 |
| height_position | obs_2mm/position_4 | C0 | local_adjacent | 5 | 0 | -0.5902 | 0.5902 | 0.5904 | 0.6070 | 0.6085 | 0/5 |
| height_position | obs_2mm/position_5 | C0 | local_adjacent | 5 | 0 | -1.2875 | 1.2875 | 1.2883 | 1.3251 | 1.3253 | 0/5 |
| height_position | obs_6mm/position_1 | C0 | local_adjacent | 5 | 0 | -1.3361 | 1.3361 | 1.3361 | 1.3381 | 1.3384 | 0/5 |
| height_position | obs_6mm/position_2 | C0 | local_adjacent | 5 | 0 | -0.9831 | 0.9831 | 0.9831 | 0.9848 | 0.9850 | 0/5 |
| height_position | obs_6mm/position_3 | C0 | local_adjacent | 5 | 0 | -0.0163 | 0.0163 | 0.0165 | 0.0197 | 0.0202 | 5/5 |
| height_position | obs_6mm/position_4 | C0 | local_adjacent | 5 | 0 | -0.9989 | 0.9989 | 0.9989 | 1.0079 | 1.0081 | 0/5 |
| height_position | obs_6mm/position_5 | C0 | local_adjacent | 5 | 0 | -0.0610 | 0.0610 | 0.0611 | 0.0651 | 0.0657 | 5/5 |
| height_position | obs_10mm/position_1 | C0 | local_adjacent | 5 | 0 | -1.6585 | 1.6585 | 1.6590 | 1.7196 | 1.7373 | 0/5 |
| height_position | obs_10mm/position_2 | C0 | local_adjacent | 5 | 0 | -2.0218 | 2.0218 | 2.0221 | 2.0693 | 2.0748 | 0/5 |
| height_position | obs_10mm/position_3 | C0 | local_adjacent | 5 | 0 | -1.8122 | 1.8122 | 1.8122 | 1.8138 | 1.8139 | 0/5 |
| height_position | obs_10mm/position_4 | C0 | local_adjacent | 5 | 0 | -1.6173 | 1.6173 | 1.6174 | 1.6286 | 1.6317 | 0/5 |
| height_position | obs_10mm/position_5 | C0 | local_adjacent | 5 | 0 | -2.2498 | 2.2498 | 2.2511 | 2.3531 | 2.3739 | 0/5 |
| height_position | obs_20mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.4127 | 0.4127 | 0.4127 | 0.4141 | 0.4141 | 0/5 |
| height_position | obs_20mm/position_2 | C0 | local_adjacent | 5 | 0 | -4.4561 | 4.4561 | 4.4562 | 4.4858 | 4.4864 | 0/5 |
| height_position | obs_20mm/position_3 | C0 | local_adjacent | 5 | 0 | -3.0717 | 3.0717 | 3.0717 | 3.0772 | 3.0784 | 0/5 |
| height_position | obs_20mm/position_4 | C0 | local_adjacent | 5 | 0 | -2.3261 | 2.3261 | 2.3261 | 2.3303 | 2.3309 | 0/5 |
| height_position | obs_20mm/position_5 | C0 | local_adjacent | 5 | 0 | -2.4492 | 2.4492 | 2.4492 | 2.4557 | 2.4560 | 0/5 |
| height_position | obs_30mm/position_1 | C0 | local_adjacent | 5 | 0 | -0.3450 | 0.3450 | 0.3450 | 0.3465 | 0.3465 | 0/5 |
| height_position | obs_30mm/position_2 | C0 | local_adjacent | 5 | 0 | -2.2132 | 2.2132 | 2.2132 | 2.2146 | 2.2146 | 0/5 |
| height_position | obs_30mm/position_3 | C0 | local_adjacent | 5 | 0 | -2.5148 | 2.5148 | 2.5148 | 2.5333 | 2.5335 | 0/5 |
| height_position | obs_30mm/position_4 | C0 | local_adjacent | 5 | 0 | -4.0146 | 4.0146 | 4.0147 | 4.0383 | 4.0457 | 0/5 |
| height_position | obs_30mm/position_5 | C0 | local_adjacent | 5 | 0 | -4.6771 | 4.6771 | 4.6784 | 4.8051 | 4.8158 | 0/5 |
| single_frame |  | C0 | all_non_height | 150 | 0 | -1.4131 | 1.4184 | 1.9556 | 4.3364 | 4.8323 | 35/150 |
| global |  | C0 | all_non_height | 30 | 0 | -1.4131 | 1.4184 | 1.9555 | 4.1216 | 4.7773 | 7/30 |
| height_position | obs_1mm/position_1 | C0 | all_non_height | 5 | 0 | -0.1315 | 0.1315 | 0.1315 | 0.1333 | 0.1336 | 5/5 |
| height_position | obs_1mm/position_2 | C0 | all_non_height | 5 | 0 | -0.2557 | 0.2557 | 0.2557 | 0.2571 | 0.2573 | 0/5 |
| height_position | obs_1mm/position_3 | C0 | all_non_height | 5 | 0 | -0.1898 | 0.1898 | 0.1899 | 0.1917 | 0.1917 | 5/5 |
| height_position | obs_1mm/position_4 | C0 | all_non_height | 5 | 0 | -0.2231 | 0.2231 | 0.2231 | 0.2269 | 0.2279 | 0/5 |
| height_position | obs_1mm/position_5 | C0 | all_non_height | 5 | 0 | -0.3032 | 0.3032 | 0.3032 | 0.3079 | 0.3084 | 0/5 |
| height_position | obs_2mm/position_1 | C0 | all_non_height | 5 | 0 | -0.2699 | 0.2699 | 0.2699 | 0.2721 | 0.2722 | 0/5 |
| height_position | obs_2mm/position_2 | C0 | all_non_height | 5 | 0 | -0.5394 | 0.5394 | 0.5394 | 0.5463 | 0.5471 | 0/5 |
| height_position | obs_2mm/position_3 | C0 | all_non_height | 5 | 0 | -0.0604 | 0.0604 | 0.0604 | 0.0619 | 0.0620 | 5/5 |
| height_position | obs_2mm/position_4 | C0 | all_non_height | 5 | 0 | -0.5432 | 0.5432 | 0.5433 | 0.5602 | 0.5620 | 0/5 |
| height_position | obs_2mm/position_5 | C0 | all_non_height | 5 | 0 | -1.3393 | 1.3393 | 1.3401 | 1.3773 | 1.3773 | 0/5 |
| height_position | obs_6mm/position_1 | C0 | all_non_height | 5 | 0 | -1.2639 | 1.2639 | 1.2639 | 1.2650 | 1.2651 | 0/5 |
| height_position | obs_6mm/position_2 | C0 | all_non_height | 5 | 0 | -0.9970 | 0.9970 | 0.9970 | 0.9982 | 0.9982 | 0/5 |
| height_position | obs_6mm/position_3 | C0 | all_non_height | 5 | 0 | -0.0286 | 0.0286 | 0.0287 | 0.0317 | 0.0321 | 5/5 |
| height_position | obs_6mm/position_4 | C0 | all_non_height | 5 | 0 | -0.9787 | 0.9787 | 0.9787 | 0.9880 | 0.9882 | 0/5 |
| height_position | obs_6mm/position_5 | C0 | all_non_height | 5 | 0 | -0.1108 | 0.1108 | 0.1108 | 0.1145 | 0.1150 | 5/5 |
| height_position | obs_10mm/position_1 | C0 | all_non_height | 5 | 0 | -1.5308 | 1.5308 | 1.5313 | 1.5926 | 1.6107 | 0/5 |
| height_position | obs_10mm/position_2 | C0 | all_non_height | 5 | 0 | -1.9844 | 1.9844 | 1.9848 | 2.0328 | 2.0385 | 0/5 |
| height_position | obs_10mm/position_3 | C0 | all_non_height | 5 | 0 | -1.8170 | 1.8170 | 1.8170 | 1.8188 | 1.8190 | 0/5 |
| height_position | obs_10mm/position_4 | C0 | all_non_height | 5 | 0 | -1.5739 | 1.5739 | 1.5739 | 1.5851 | 1.5881 | 0/5 |
| height_position | obs_10mm/position_5 | C0 | all_non_height | 5 | 0 | -2.3099 | 2.3099 | 2.3112 | 2.4163 | 2.4381 | 0/5 |
| height_position | obs_20mm/position_1 | C0 | all_non_height | 5 | 0 | 0.0582 | 0.0582 | 0.0582 | 0.0606 | 0.0610 | 5/5 |
| height_position | obs_20mm/position_2 | C0 | all_non_height | 5 | 0 | -4.3552 | 4.3552 | 4.3552 | 4.3857 | 4.3861 | 0/5 |
| height_position | obs_20mm/position_3 | C0 | all_non_height | 5 | 0 | -3.1696 | 3.1696 | 3.1696 | 3.1720 | 3.1724 | 0/5 |
| height_position | obs_20mm/position_4 | C0 | all_non_height | 5 | 0 | -2.5584 | 2.5584 | 2.5584 | 2.5622 | 2.5628 | 0/5 |
| height_position | obs_20mm/position_5 | C0 | all_non_height | 5 | 0 | -2.4545 | 2.4545 | 2.4545 | 2.4614 | 2.4617 | 0/5 |
| height_position | obs_30mm/position_1 | C0 | all_non_height | 5 | 0 | 0.0215 | 0.0215 | 0.0216 | 0.0234 | 0.0237 | 5/5 |
| height_position | obs_30mm/position_2 | C0 | all_non_height | 5 | 0 | -2.2741 | 2.2741 | 2.2741 | 2.2759 | 2.2761 | 0/5 |
| height_position | obs_30mm/position_3 | C0 | all_non_height | 5 | 0 | -2.5975 | 2.5975 | 2.5978 | 2.6441 | 2.6511 | 0/5 |
| height_position | obs_30mm/position_4 | C0 | all_non_height | 5 | 0 | -3.8361 | 3.8361 | 3.8361 | 3.8623 | 3.8707 | 0/5 |
| height_position | obs_30mm/position_5 | C0 | all_non_height | 5 | 0 | -4.7773 | 4.7773 | 4.7774 | 4.8218 | 4.8323 | 0/5 |
| single_frame |  | C0 | fixed_zg_zero | 150 | 0 | -1.4128 | 1.4174 | 1.9193 | 4.3038 | 4.7751 | 25/150 |
| global |  | C0 | fixed_zg_zero | 30 | 0 | -1.4128 | 1.4174 | 1.9192 | 4.0831 | 4.7191 | 5/30 |
| height_position | obs_1mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -0.2495 | 0.2495 | 0.2495 | 0.2510 | 0.2511 | 0/5 |
| height_position | obs_1mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -0.3418 | 0.3418 | 0.3418 | 0.3456 | 0.3460 | 0/5 |
| height_position | obs_1mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -0.2878 | 0.2878 | 0.2878 | 0.2892 | 0.2892 | 0/5 |
| height_position | obs_1mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -0.2782 | 0.2782 | 0.2782 | 0.2822 | 0.2830 | 0/5 |
| height_position | obs_1mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -0.3291 | 0.3291 | 0.3292 | 0.3345 | 0.3353 | 0/5 |
| height_position | obs_2mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -0.3712 | 0.3712 | 0.3712 | 0.3741 | 0.3743 | 0/5 |
| height_position | obs_2mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -0.5817 | 0.5817 | 0.5817 | 0.5887 | 0.5894 | 0/5 |
| height_position | obs_2mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -0.1133 | 0.1133 | 0.1133 | 0.1150 | 0.1151 | 5/5 |
| height_position | obs_2mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -0.5940 | 0.5940 | 0.5941 | 0.6108 | 0.6123 | 0/5 |
| height_position | obs_2mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -1.3500 | 1.3500 | 1.3508 | 1.3883 | 1.3885 | 0/5 |
| height_position | obs_6mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -1.3175 | 1.3175 | 1.3175 | 1.3191 | 1.3195 | 0/5 |
| height_position | obs_6mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -1.0476 | 1.0476 | 1.0476 | 1.0504 | 1.0507 | 0/5 |
| height_position | obs_6mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -0.0703 | 0.0703 | 0.0704 | 0.0736 | 0.0741 | 5/5 |
| height_position | obs_6mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -0.9938 | 0.9938 | 0.9938 | 1.0029 | 1.0030 | 0/5 |
| height_position | obs_6mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -0.1058 | 0.1058 | 0.1059 | 0.1099 | 0.1104 | 5/5 |
| height_position | obs_10mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -1.6212 | 1.6212 | 1.6217 | 1.6824 | 1.7005 | 0/5 |
| height_position | obs_10mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -2.0471 | 2.0471 | 2.0474 | 2.0954 | 2.1011 | 0/5 |
| height_position | obs_10mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -1.8364 | 1.8364 | 1.8364 | 1.8386 | 1.8390 | 0/5 |
| height_position | obs_10mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -1.5696 | 1.5696 | 1.5696 | 1.5806 | 1.5838 | 0/5 |
| height_position | obs_10mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -2.2586 | 2.2586 | 2.2599 | 2.3625 | 2.3834 | 0/5 |
| height_position | obs_20mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | 0.0682 | 0.0682 | 0.0683 | 0.0706 | 0.0709 | 5/5 |
| height_position | obs_20mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -4.3228 | 4.3228 | 4.3229 | 4.3537 | 4.3541 | 0/5 |
| height_position | obs_20mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -2.9995 | 2.9995 | 2.9995 | 3.0014 | 3.0016 | 0/5 |
| height_position | obs_20mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -2.1711 | 2.1711 | 2.1711 | 2.1754 | 2.1761 | 0/5 |
| height_position | obs_20mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -2.3145 | 2.3145 | 2.3145 | 2.3220 | 2.3226 | 0/5 |
| height_position | obs_30mm/position_1 | C0 | fixed_zg_zero | 5 | 0 | -0.0020 | 0.0020 | 0.0023 | 0.0034 | 0.0034 | 5/5 |
| height_position | obs_30mm/position_2 | C0 | fixed_zg_zero | 5 | 0 | -2.2761 | 2.2761 | 2.2761 | 2.2787 | 2.2792 | 0/5 |
| height_position | obs_30mm/position_3 | C0 | fixed_zg_zero | 5 | 0 | -2.4934 | 2.4934 | 2.4935 | 2.5118 | 2.5118 | 0/5 |
| height_position | obs_30mm/position_4 | C0 | fixed_zg_zero | 5 | 0 | -3.7901 | 3.7901 | 3.7902 | 3.8171 | 3.8256 | 0/5 |
| height_position | obs_30mm/position_5 | C0 | fixed_zg_zero | 5 | 0 | -4.7191 | 4.7191 | 4.7192 | 4.7647 | 4.7751 | 0/5 |
| single_frame |  | C1 | local_adjacent | 150 | 0 | -1.4352 | 1.4352 | 1.9487 | 4.4422 | 4.7847 | 20/150 |
| global |  | C1 | local_adjacent | 30 | 0 | -1.4352 | 1.4352 | 1.9484 | 4.2469 | 4.6259 | 4/30 |
| height_position | obs_1mm/position_1 | C1 | local_adjacent | 5 | 0 | -0.2171 | 0.2171 | 0.2171 | 0.2185 | 0.2186 | 0/5 |
| height_position | obs_1mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.2037 | 0.2037 | 0.2037 | 0.2051 | 0.2055 | 0/5 |
| height_position | obs_1mm/position_3 | C1 | local_adjacent | 5 | 0 | -0.1856 | 0.1856 | 0.1856 | 0.1872 | 0.1873 | 5/5 |
| height_position | obs_1mm/position_4 | C1 | local_adjacent | 5 | 0 | -0.2307 | 0.2307 | 0.2307 | 0.2349 | 0.2360 | 0/5 |
| height_position | obs_1mm/position_5 | C1 | local_adjacent | 5 | 0 | -0.2686 | 0.2686 | 0.2686 | 0.2746 | 0.2755 | 0/5 |
| height_position | obs_2mm/position_1 | C1 | local_adjacent | 5 | 0 | -0.3507 | 0.3507 | 0.3507 | 0.3525 | 0.3525 | 0/5 |
| height_position | obs_2mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.4312 | 0.4312 | 0.4313 | 0.4380 | 0.4387 | 0/5 |
| height_position | obs_2mm/position_3 | C1 | local_adjacent | 5 | 0 | -0.0500 | 0.0500 | 0.0501 | 0.0519 | 0.0521 | 5/5 |
| height_position | obs_2mm/position_4 | C1 | local_adjacent | 5 | 0 | -0.5956 | 0.5956 | 0.5957 | 0.6121 | 0.6137 | 0/5 |
| height_position | obs_2mm/position_5 | C1 | local_adjacent | 5 | 0 | -1.3022 | 1.3022 | 1.3030 | 1.3396 | 1.3397 | 0/5 |
| height_position | obs_6mm/position_1 | C1 | local_adjacent | 5 | 0 | -1.3136 | 1.3136 | 1.3136 | 1.3162 | 1.3168 | 0/5 |
| height_position | obs_6mm/position_2 | C1 | local_adjacent | 5 | 0 | -0.9840 | 0.9840 | 0.9840 | 0.9860 | 0.9860 | 0/5 |
| height_position | obs_6mm/position_3 | C1 | local_adjacent | 5 | 0 | -0.0181 | 0.0181 | 0.0182 | 0.0210 | 0.0214 | 5/5 |
| height_position | obs_6mm/position_4 | C1 | local_adjacent | 5 | 0 | -1.0042 | 1.0042 | 1.0043 | 1.0132 | 1.0133 | 0/5 |
| height_position | obs_6mm/position_5 | C1 | local_adjacent | 5 | 0 | -0.0738 | 0.0738 | 0.0739 | 0.0779 | 0.0786 | 5/5 |
| height_position | obs_10mm/position_1 | C1 | local_adjacent | 5 | 0 | -1.6840 | 1.6840 | 1.6845 | 1.7470 | 1.7651 | 0/5 |
| height_position | obs_10mm/position_2 | C1 | local_adjacent | 5 | 0 | -2.0242 | 2.0242 | 2.0245 | 2.0719 | 2.0775 | 0/5 |
| height_position | obs_10mm/position_3 | C1 | local_adjacent | 5 | 0 | -1.8133 | 1.8133 | 1.8133 | 1.8149 | 1.8150 | 0/5 |
| height_position | obs_10mm/position_4 | C1 | local_adjacent | 5 | 0 | -1.6213 | 1.6213 | 1.6213 | 1.6327 | 1.6357 | 0/5 |
| height_position | obs_10mm/position_5 | C1 | local_adjacent | 5 | 0 | -2.2569 | 2.2569 | 2.2582 | 2.3605 | 2.3814 | 0/5 |
| height_position | obs_20mm/position_1 | C1 | local_adjacent | 5 | 0 | -0.4092 | 0.4092 | 0.4092 | 0.4105 | 0.4105 | 0/5 |
| height_position | obs_20mm/position_2 | C1 | local_adjacent | 5 | 0 | -4.4603 | 4.4603 | 4.4603 | 4.4898 | 4.4904 | 0/5 |
| height_position | obs_20mm/position_3 | C1 | local_adjacent | 5 | 0 | -3.0736 | 3.0736 | 3.0736 | 3.0790 | 3.0801 | 0/5 |
| height_position | obs_20mm/position_4 | C1 | local_adjacent | 5 | 0 | -2.3280 | 2.3280 | 2.3280 | 2.3320 | 2.3326 | 0/5 |
| height_position | obs_20mm/position_5 | C1 | local_adjacent | 5 | 0 | -2.4407 | 2.4407 | 2.4407 | 2.4482 | 2.4485 | 0/5 |
| height_position | obs_30mm/position_1 | C1 | local_adjacent | 5 | 0 | -0.3514 | 0.3514 | 0.3514 | 0.3528 | 0.3528 | 0/5 |
| height_position | obs_30mm/position_2 | C1 | local_adjacent | 5 | 0 | -2.2347 | 2.2347 | 2.2347 | 2.2364 | 2.2367 | 0/5 |
| height_position | obs_30mm/position_3 | C1 | local_adjacent | 5 | 0 | -2.5177 | 2.5177 | 2.5177 | 2.5362 | 2.5364 | 0/5 |
| height_position | obs_30mm/position_4 | C1 | local_adjacent | 5 | 0 | -3.9861 | 3.9861 | 3.9861 | 4.0099 | 4.0176 | 0/5 |
| height_position | obs_30mm/position_5 | C1 | local_adjacent | 5 | 0 | -4.6259 | 4.6259 | 4.6279 | 4.7739 | 4.7847 | 0/5 |
| single_frame |  | C1 | all_non_height | 150 | 0 | -1.4063 | 1.4063 | 1.9364 | 4.3239 | 4.7714 | 35/150 |
| global |  | C1 | all_non_height | 30 | 0 | -1.4063 | 1.4063 | 1.9362 | 4.1190 | 4.7163 | 7/30 |
| height_position | obs_1mm/position_1 | C1 | all_non_height | 5 | 0 | -0.1716 | 0.1716 | 0.1716 | 0.1729 | 0.1730 | 5/5 |
| height_position | obs_1mm/position_2 | C1 | all_non_height | 5 | 0 | -0.2170 | 0.2170 | 0.2170 | 0.2186 | 0.2189 | 0/5 |
| height_position | obs_1mm/position_3 | C1 | all_non_height | 5 | 0 | -0.1986 | 0.1986 | 0.1986 | 0.1997 | 0.1997 | 5/5 |
| height_position | obs_1mm/position_4 | C1 | all_non_height | 5 | 0 | -0.2417 | 0.2417 | 0.2417 | 0.2452 | 0.2459 | 0/5 |
| height_position | obs_1mm/position_5 | C1 | all_non_height | 5 | 0 | -0.2527 | 0.2527 | 0.2527 | 0.2575 | 0.2582 | 0/5 |
| height_position | obs_2mm/position_1 | C1 | all_non_height | 5 | 0 | -0.3067 | 0.3067 | 0.3068 | 0.3088 | 0.3091 | 0/5 |
| height_position | obs_2mm/position_2 | C1 | all_non_height | 5 | 0 | -0.4763 | 0.4763 | 0.4763 | 0.4836 | 0.4844 | 0/5 |
| height_position | obs_2mm/position_3 | C1 | all_non_height | 5 | 0 | -0.0771 | 0.0771 | 0.0771 | 0.0788 | 0.0790 | 5/5 |
| height_position | obs_2mm/position_4 | C1 | all_non_height | 5 | 0 | -0.5769 | 0.5769 | 0.5771 | 0.5939 | 0.5957 | 0/5 |
| height_position | obs_2mm/position_5 | C1 | all_non_height | 5 | 0 | -1.2887 | 1.2887 | 1.2895 | 1.3262 | 1.3263 | 0/5 |
| height_position | obs_6mm/position_1 | C1 | all_non_height | 5 | 0 | -1.2838 | 1.2838 | 1.2838 | 1.2852 | 1.2854 | 0/5 |
| height_position | obs_6mm/position_2 | C1 | all_non_height | 5 | 0 | -0.9819 | 0.9819 | 0.9819 | 0.9841 | 0.9841 | 0/5 |
| height_position | obs_6mm/position_3 | C1 | all_non_height | 5 | 0 | -0.0401 | 0.0401 | 0.0401 | 0.0433 | 0.0436 | 5/5 |
| height_position | obs_6mm/position_4 | C1 | all_non_height | 5 | 0 | -0.9835 | 0.9835 | 0.9835 | 0.9930 | 0.9932 | 0/5 |
| height_position | obs_6mm/position_5 | C1 | all_non_height | 5 | 0 | -0.0615 | 0.0615 | 0.0615 | 0.0650 | 0.0656 | 5/5 |
| height_position | obs_10mm/position_1 | C1 | all_non_height | 5 | 0 | -1.6068 | 1.6068 | 1.6073 | 1.6684 | 1.6864 | 0/5 |
| height_position | obs_10mm/position_2 | C1 | all_non_height | 5 | 0 | -1.9797 | 1.9797 | 1.9800 | 2.0277 | 2.0332 | 0/5 |
| height_position | obs_10mm/position_3 | C1 | all_non_height | 5 | 0 | -1.8533 | 1.8533 | 1.8533 | 1.8553 | 1.8556 | 0/5 |
| height_position | obs_10mm/position_4 | C1 | all_non_height | 5 | 0 | -1.6096 | 1.6096 | 1.6096 | 1.6210 | 1.6240 | 0/5 |
| height_position | obs_10mm/position_5 | C1 | all_non_height | 5 | 0 | -2.2493 | 2.2493 | 2.2506 | 2.3534 | 2.3745 | 0/5 |
| height_position | obs_20mm/position_1 | C1 | all_non_height | 5 | 0 | -0.0357 | 0.0357 | 0.0357 | 0.0374 | 0.0374 | 5/5 |
| height_position | obs_20mm/position_2 | C1 | all_non_height | 5 | 0 | -4.3421 | 4.3421 | 4.3422 | 4.3724 | 4.3729 | 0/5 |
| height_position | obs_20mm/position_3 | C1 | all_non_height | 5 | 0 | -3.1441 | 3.1441 | 3.1441 | 3.1496 | 3.1509 | 0/5 |
| height_position | obs_20mm/position_4 | C1 | all_non_height | 5 | 0 | -2.3094 | 2.3094 | 2.3094 | 2.3135 | 2.3143 | 0/5 |
| height_position | obs_20mm/position_5 | C1 | all_non_height | 5 | 0 | -2.4251 | 2.4251 | 2.4251 | 2.4320 | 2.4324 | 0/5 |
| height_position | obs_30mm/position_1 | C1 | all_non_height | 5 | 0 | -0.0746 | 0.0746 | 0.0746 | 0.0757 | 0.0758 | 5/5 |
| height_position | obs_30mm/position_2 | C1 | all_non_height | 5 | 0 | -2.2810 | 2.2810 | 2.2810 | 2.2828 | 2.2831 | 0/5 |
| height_position | obs_30mm/position_3 | C1 | all_non_height | 5 | 0 | -2.5572 | 2.5572 | 2.5572 | 2.5764 | 2.5766 | 0/5 |
| height_position | obs_30mm/position_4 | C1 | all_non_height | 5 | 0 | -3.8463 | 3.8463 | 3.8464 | 3.8725 | 3.8809 | 0/5 |
| height_position | obs_30mm/position_5 | C1 | all_non_height | 5 | 0 | -4.7163 | 4.7163 | 4.7165 | 4.7609 | 4.7714 | 0/5 |
| single_frame |  | C1 | fixed_zg_zero | 150 | 0 | -1.4081 | 1.4091 | 1.9081 | 4.2835 | 4.6979 | 25/150 |
| global |  | C1 | fixed_zg_zero | 30 | 0 | -1.4081 | 1.4091 | 1.9080 | 4.0766 | 4.6419 | 5/30 |
| height_position | obs_1mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -0.3050 | 0.3050 | 0.3051 | 0.3066 | 0.3067 | 0/5 |
| height_position | obs_1mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -0.3165 | 0.3165 | 0.3165 | 0.3204 | 0.3208 | 0/5 |
| height_position | obs_1mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.2931 | 0.2931 | 0.2931 | 0.2944 | 0.2945 | 0/5 |
| height_position | obs_1mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -0.2946 | 0.2946 | 0.2946 | 0.2986 | 0.2994 | 0/5 |
| height_position | obs_1mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -0.2594 | 0.2594 | 0.2595 | 0.2648 | 0.2656 | 0/5 |
| height_position | obs_2mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -0.4239 | 0.4239 | 0.4239 | 0.4267 | 0.4269 | 0/5 |
| height_position | obs_2mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -0.5434 | 0.5434 | 0.5434 | 0.5504 | 0.5511 | 0/5 |
| height_position | obs_2mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.1238 | 0.1238 | 0.1238 | 0.1255 | 0.1256 | 5/5 |
| height_position | obs_2mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -0.6033 | 0.6033 | 0.6034 | 0.6201 | 0.6215 | 0/5 |
| height_position | obs_2mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -1.2775 | 1.2775 | 1.2783 | 1.3153 | 1.3156 | 0/5 |
| height_position | obs_6mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -1.3480 | 1.3480 | 1.3480 | 1.3497 | 1.3500 | 0/5 |
| height_position | obs_6mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -1.0282 | 1.0282 | 1.0282 | 1.0310 | 1.0313 | 0/5 |
| height_position | obs_6mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -0.0757 | 0.0757 | 0.0758 | 0.0790 | 0.0795 | 5/5 |
| height_position | obs_6mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -1.0045 | 1.0045 | 1.0045 | 1.0136 | 1.0137 | 0/5 |
| height_position | obs_6mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -0.0366 | 0.0366 | 0.0367 | 0.0405 | 0.0412 | 5/5 |
| height_position | obs_10mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -1.6525 | 1.6525 | 1.6530 | 1.7136 | 1.7316 | 0/5 |
| height_position | obs_10mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -2.0287 | 2.0287 | 2.0290 | 2.0770 | 2.0827 | 0/5 |
| height_position | obs_10mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -1.8513 | 1.8513 | 1.8513 | 1.8535 | 1.8539 | 0/5 |
| height_position | obs_10mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -1.5801 | 1.5801 | 1.5802 | 1.5911 | 1.5943 | 0/5 |
| height_position | obs_10mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -2.1885 | 2.1885 | 2.1899 | 2.2929 | 2.3139 | 0/5 |
| height_position | obs_20mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | 0.0151 | 0.0151 | 0.0152 | 0.0169 | 0.0171 | 5/5 |
| height_position | obs_20mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -4.3024 | 4.3024 | 4.3025 | 4.3333 | 4.3337 | 0/5 |
| height_position | obs_20mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -3.0139 | 3.0139 | 3.0139 | 3.0157 | 3.0160 | 0/5 |
| height_position | obs_20mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -2.1835 | 2.1835 | 2.1835 | 2.1877 | 2.1884 | 0/5 |
| height_position | obs_20mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -2.2602 | 2.2602 | 2.2602 | 2.2677 | 2.2683 | 0/5 |
| height_position | obs_30mm/position_1 | C1 | fixed_zg_zero | 5 | 0 | -0.0573 | 0.0573 | 0.0574 | 0.0587 | 0.0587 | 5/5 |
| height_position | obs_30mm/position_2 | C1 | fixed_zg_zero | 5 | 0 | -2.2545 | 2.2545 | 2.2545 | 2.2570 | 2.2576 | 0/5 |
| height_position | obs_30mm/position_3 | C1 | fixed_zg_zero | 5 | 0 | -2.5082 | 2.5082 | 2.5082 | 2.5265 | 2.5265 | 0/5 |
| height_position | obs_30mm/position_4 | C1 | fixed_zg_zero | 5 | 0 | -3.8007 | 3.8007 | 3.8007 | 3.8276 | 3.8361 | 0/5 |
| height_position | obs_30mm/position_5 | C1 | fixed_zg_zero | 5 | 0 | -4.6419 | 4.6419 | 4.6420 | 4.6876 | 4.6979 | 0/5 |

## Repeatability

repeatability 是每个 height × position 条件内五次重复高度均值的样本标准差（ddof=1）；不是单帧 height_std_mm。

| model | mode | condition n | median sigma | P95 sigma | max sigma |
|---|---|---:|---:|---:|---:|
| C0 | local_adjacent | 30 | 0.0038 | 0.0697 | 0.1221 |
| C0 | all_non_height | 30 | 0.0033 | 0.0486 | 0.0875 |
| C0 | fixed_zg_zero | 30 | 0.0035 | 0.0484 | 0.0857 |
| C1 | local_adjacent | 30 | 0.0038 | 0.0698 | 0.1499 |
| C1 | all_non_height | 30 | 0.0039 | 0.0480 | 0.0858 |
| C1 | fixed_zg_zero | 30 | 0.0035 | 0.0478 | 0.0860 |

## Adjacent-height-difference MAE

| model | mode | n | Bias | MAE | RMSE | P95 | Max |
|---|---|---:|---:|---:|---:|---:|---:|
| C0 | local_adjacent | 25 | -0.5063 | 0.9469 | 1.2091 | 2.2399 | 2.4343 |
| C0 | all_non_height | 25 | -0.4944 | 0.9450 | 1.2046 | 2.2981 | 2.3707 |
| C0 | fixed_zg_zero | 25 | -0.4718 | 0.9281 | 1.1975 | 2.2511 | 2.4046 |
| C1 | local_adjacent | 25 | -0.5044 | 0.9452 | 1.2043 | 2.2175 | 2.4361 |
| C1 | all_non_height | 25 | -0.4958 | 0.9441 | 1.2030 | 2.2706 | 2.3625 |
| C1 | fixed_zg_zero | 25 | -0.4718 | 0.9261 | 1.1940 | 2.2494 | 2.3817 |

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
