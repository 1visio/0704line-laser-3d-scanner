# H1 vs H-B2 全视场位置一致性专项审计

## 最终判定

- `HISTORICAL_DATA_COVERS_V_GT_2400=PARTIAL`
- `EDGE_V_GT_2400_FAILURE_REPRODUCED=YES`
- `H1_REDUCES_SPATIAL_BIAS=NO`
- `HB2_REDUCES_SPATIAL_BIAS=YES`
- `PREFERRED_DEPTH_BASELINE=HB2`
- `SPATIAL_RESIDUAL_SUPPORTED=YES`
- `NEW_SPATIAL_CORRECTION_REQUIRED=YES`

结论只描述本轮历史数据的诊断证据；本轮没有拟合或写入新的 spatial correction，也不改变生产配置。

## 1. Provenance / reuse audit

| 项目 | 本轮处理 |
|---|---|
| 图像 / Steger | 复用历史一次 Steger / frame 的冻结产物；未重新运行 |
| ROI | 复用 `roi_registry_manual.json` 的 30/30 frozen manual ROI；未修改 |
| formal points | 复用 Surface-1A `surface1a_points.csv` 的 `development_formal_repeat2_5`，并严格保留 `height_measurement_inlier=True` 且 `jacobian_valid=True` 的有效点集合 |
| Base | Frozen C0 + Frozen C1 + 同一 session-linear Ground Reference；`height_value_mm` / `height_residual_mm` 原样复用 |
| H1 | 复用 frozen scale `h_H1 = 1.00403395913372 * h_raw`；未重新拟合 |
| H-B2 | 复用 frozen `a0=-0.100688271277128 mm`, `a2=0.053274373969597 mm/q2`；`h_HB2=h_raw-(a0+a2*q2)`；未重新拟合 |
| 新增计算 | 仅 deterministic pointwise transform、coverage/metrics、edge audit、诊断图和本报告 |
| 禁止项 | 未重跑模型搜索、未改 q2/ROI/Steger/ground proxy、未按模型结果删点 |
| 输出目录 | `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_height_depth_baseline_spatial_audit` |


输入文件 SHA-256：

- `roi_registry`: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819\roi_registry_manual.json` — `4550eb7cf653c44f7dc64738f75db9c99239bc98fae65249b4eebfac791a3c9f`
- `pointwise_diagnostics`: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_manual_frozen\pointwise_diagnostics.csv` — `3c63dc9d115d714d9b78747db06c5016bfd863592c6b959c31301e1a6cd67487`
- `surface1a_points`: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\surface1a\surface1a_points.csv` — `0a325ea20c8b250ea94553cd6c9c78c198ce49f48a27925697a34eabf9fd4c9a`
- `stage_a_scale`: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\laser_measurement_tool\configs\calibration_daheng_0811\stage_a_height_scale.json` — `3d41b5c3b4035f8568574f7a3599bb20a841267b6ebd34c617385027b6612811`
- `hb2_parameters`: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\surface2\surface3_hb2_candidate\surface3_hb2_parameters.json` — `f77fc5224d35ab7bb14e63a530e2c413a23e0e90b4ff048e79486d862886c829`
- `hb2_candidate`: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\surface2\surface3_hb2_candidate\surface3_hb2_candidate.json` — `c5534b4086b82cd3d18a068f02eae762cff5027b608da9976db7eb56515d23ae`
- `height_linear_summary`: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\height_linear_summary.json` — `2f075ad220744662ec06b600fcf2330139309a7a7527d1de0c58a643132e107b`

历史 artifact 中，`height_linear_summary.json` 与 `surface3_hb2_candidate.json` 仅作 frozen 参数/候选 provenance 核对，不复用其 pooled/condition-level 数值来替代本轮 pointwise 计算。

## 2. 历史 5 个位置的真实 v 覆盖

`position_rank` 是 ROI registry 原有 rank；`v_order_rank` 是本审计按每个高度的 raw formal-row `v_median` 从小到大生成，仅用于本审计。任何跨高度结论均不把 pose_id 当作统一空间坐标。
`historical_position_v_coverage.csv` 同时保留 raw formal 与 effective formal 两套 v 范围：报告下面各行的 `v_min–v_max` 是 raw formal rows；`n_eff`/`edge` 来自 effective set，effective 的 P05/median/P95/min/max 在 CSV 的 `effective_*` 列。`height_v_range` 是 frozen manual ROI 的 height 条带，`baseline_v_ranges` 是同一 registry 中的两个 baseline 条带，均为 image-v 像素闭区间。

raw formal candidate 有 30 个 height×position 条件；effective formal point set 共 6802 个点。详细范围见 `historical_position_v_coverage.csv`。
实际 raw formal rows 中有 10/30 个条件的最大 v 超过 2400；冻结 effective set 中有 9/30 个条件实际留下 v>2400 点，覆盖高度为 obs_10mm, obs_1mm, obs_20mm, obs_2mm, obs_30mm, obs_6mm，覆盖 v_order_rank 为 [4, 5]。

关键覆盖观察：

- `obs_1mm`: p1/rank1/pose001: 205–284 (n_eff=315, edge=0); p2/rank2/pose002: 1036–1100 (n_eff=196, edge=0); p3/rank3/pose003: 1478–1548 (n_eff=271, edge=0); p4/rank4/pose004: 2125–2188 (n_eff=236, edge=0); p5/rank5/pose005: 2792–2858 (n_eff=196, edge=196)
- `obs_2mm`: p1/rank1/pose005: 219–285 (n_eff=234, edge=0); p2/rank2/pose004: 908–977 (n_eff=211, edge=0); p3/rank3/pose003: 1730–1791 (n_eff=186, edge=0); p4/rank4/pose002: 2374–2441 (n_eff=200, edge=102); p5/rank5/pose001: 2789–2848 (n_eff=0, edge=0)
- `obs_6mm`: p1/rank1/pose001: 269–332 (n_eff=225, edge=0); p2/rank2/pose002: 1093–1156 (n_eff=222, edge=0); p3/rank3/pose003: 1502–1565 (n_eff=233, edge=0); p4/rank4/pose004: 2360–2427 (n_eff=247, edge=95); p5/rank5/pose005: 2808–2872 (n_eff=238, edge=238)
- `obs_10mm`: p1/rank1/pose005: 265–333 (n_eff=269, edge=0); p2/rank2/pose004: 1099–1160 (n_eff=202, edge=0); p3/rank3/pose003: 1947–2012 (n_eff=166, edge=0); p4/rank4/pose002: 2369–2429 (n_eff=226, edge=100); p5/rank5/pose001: 2797–2856 (n_eff=180, edge=180)
- `obs_20mm`: p1/rank1/pose005: 217–291 (n_eff=250, edge=0); p2/rank2/pose004: 1074–1148 (n_eff=269, edge=0); p3/rank3/pose003: 1909–1978 (n_eff=244, edge=0); p4/rank4/pose002: 2333–2394 (n_eff=203, edge=0); p5/rank5/pose001: 2757–2819 (n_eff=236, edge=236)
- `obs_30mm`: p1/rank1/pose001: 227–292 (n_eff=261, edge=0); p2/rank2/pose002: 1077–1145 (n_eff=264, edge=0); p3/rank3/pose003: 1936–2009 (n_eff=248, edge=0); p4/rank4/pose004: 2358–2435 (n_eff=284, edge=124); p5/rank5/pose005: 2807–2880 (n_eff=290, edge=290)

`obs_2mm` 的 `position_rank=5` 原始 formal rows 存在，但 Base 冻结规则中全部为 `height_measurement_inlier=False`（历史 height fit `too_few_points`），因此 effective point count 为 0；本轮不补点、不把它伪装成可比较 condition。

因此历史数据确实触及 v>2400，但不是完整五位置均匀覆盖：edge 支持主要来自每个高度的高 v 位置（尤其 v_order_rank 5，部分高度 rank 4），且存在 2mm rank5 的 effective 缺口；最终标记为 `PARTIAL`。五个位置之间还存在明显空档，不能追加连续 v band 统计。

## 3. 三条同点测量链

所有 pointwise 行均来自同一 frozen formal effective set；H1/H-B2 只生成新的高度与 residual 列：

```text
h_raw = height_value_mm
Base = h_raw  (residual = h_raw - truth)
H1   = 1.00403395913372 * h_raw
H-B2 = h_raw - (-0.100688271277128 + 0.053274373969597 * q2)
```

输出 `pointwise_base_h1_hb2.csv` 保留了 point identity、frame/repeat、u/v、q2、h_raw 和三条链的高度/residual；不存在因 H1/H-B2 结果较差而重筛点。

## 4. Position consistency（主要评价单位）

position-level 指标是每个 height×position 的 pointwise 指标；height summary 对可用 position 的 Bias 等权汇总，2mm 只有 4 个 effective positions。pooled 行仅作上下文，不作为位置一致性结论。完整结果见 `position_consistency_metrics.csv`。

| height | model | positions | Bias range | Bias std | worst | worst P95 | worst Max | status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1mm | Base | 5 | 0.0682 | 0.0275 | 0.0552 | 0.0864 | 0.1011 | OK |
| 1mm | H1 | 5 | 0.0685 | 0.0276 | 0.0513 | 0.0827 | 0.0974 | OK |
| 1mm | H-B2 | 5 | 0.0671 | 0.0266 | 0.0383 | 0.0652 | 0.0792 | OK |
| 2mm | Base | 4 | 0.0627 | 0.0225 | 0.0577 | 0.0798 | 0.0901 | PARTIAL_POSITION_SUPPORT |
| 2mm | H1 | 4 | 0.0630 | 0.0226 | 0.0499 | 0.0720 | 0.0824 | PARTIAL_POSITION_SUPPORT |
| 2mm | H-B2 | 4 | 0.0601 | 0.0219 | 0.0303 | 0.0566 | 0.0781 | PARTIAL_POSITION_SUPPORT |
| 6mm | Base | 5 | 0.0692 | 0.0248 | 0.0643 | 0.1012 | 0.1172 | OK |
| 6mm | H1 | 5 | 0.0695 | 0.0249 | 0.0404 | 0.0774 | 0.0934 | OK |
| 6mm | H-B2 | 5 | 0.0687 | 0.0243 | 0.0431 | 0.0780 | 0.0915 | OK |
| 10mm | Base | 5 | 0.0553 | 0.0196 | 0.0839 | 0.1113 | 0.1243 | OK |
| 10mm | H1 | 5 | 0.0555 | 0.0197 | 0.0439 | 0.0714 | 0.0845 | OK |
| 10mm | H-B2 | 5 | 0.0538 | 0.0186 | 0.0363 | 0.0637 | 0.0768 | OK |
| 20mm | Base | 5 | 0.0820 | 0.0279 | 0.1312 | 0.1716 | 0.1792 | OK |
| 20mm | H1 | 5 | 0.0823 | 0.0280 | 0.0510 | 0.0916 | 0.0992 | OK |
| 20mm | H-B2 | 5 | 0.0776 | 0.0264 | 0.0612 | 0.1017 | 0.1093 | OK |
| 30mm | Base | 5 | 0.0850 | 0.0320 | 0.1693 | 0.1951 | 0.2074 | OK |
| 30mm | H1 | 5 | 0.0853 | 0.0322 | 0.0489 | 0.0749 | 0.0872 | OK |
| 30mm | H-B2 | 5 | 0.0837 | 0.0316 | 0.0773 | 0.1032 | 0.1155 | OK |

position spread 改善判定规则：同一模型的 Bias range 与 Bias std 在至少 4/6 个高度同时下降才标 `YES`；有部分但未达此稳定门槛标 `PARTIAL`。该规则只用于解释 H1/H-B2 的 spatial benefit，不是重新拟合。

## 5. 独立 v>2400 edge audit

edge 直接从同一 effective formal points 按 `v_px > 2400` 筛选；不要求组成独立完整 position。

| model | n | covered heights | covered poses | covered ranks | Bias | MAE | RMSE | P95 | Max | >0.1 | >0.2 | v-Bias Spearman | ROI boundary <=10px |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Base | 1561 | ["obs_10mm","obs_1mm","obs_20mm","obs_2mm","obs_30mm","obs_6mm"] | ["001","002","004","005"] | [4,5] | -0.0852 | 0.0883 | 0.1034 | 0.1810 | 0.2074 | 0.382 | 0.003 | -0.328 | 0.358 |
| H1 | 1561 | ["obs_10mm","obs_1mm","obs_20mm","obs_2mm","obs_30mm","obs_6mm"] | ["001","002","004","005"] | [4,5] | -0.0278 | 0.0400 | 0.0451 | 0.0770 | 0.0992 | 0.000 | 0.000 | -0.463 | 0.358 |
| H-B2 | 1561 | ["obs_10mm","obs_1mm","obs_20mm","obs_2mm","obs_30mm","obs_6mm"] | ["001","002","004","005"] | [4,5] | -0.0281 | 0.0408 | 0.0503 | 0.0944 | 0.1155 | 0.026 | 0.000 | -0.447 | 0.358 |

跨高度/pose/position 的 edge 分解、阈值比例和每个 height×position 结果见 `edge_v_gt_2400_metrics.csv`。

failure 诊断：

- Base 在达到 edge support 的高度中，满足 edge P95≥0.1 mm 或 >0.1 比例≥0.1 的高度为 `obs_10mm, obs_20mm, obs_30mm`。
- Base edge 点在 ROI 边界 10 px 内比例为 `0.358`；这用于区分“仅少量 ROI 边界异常”与连续/跨高度现象。
- Base 的上述 failure 实际涉及 pose `001, 004, 005`，不是单一 pose；pose-level 与 height×position 细节见 CSV，本轮不以 pooled 指标掩盖局部失败。
- residual-v 图使用 raw v 排序 rolling median 仅作诊断，不拟合 correction；图中保留 v=2400 分界。

Pose-level edge 分解（完整数值也保留在 `edge_v_gt_2400_metrics.csv` 的 `row_type=pose` 行）：

| pose_id | Base n / >0.1 | H1 n / >0.1 | H-B2 n / >0.1 |
|---|---:|---:|---:|
| 001 | 416 / 0.615 | 416 / 0.000 | 416 / 0.048 |
| 002 | 202 / 0.000 | 202 / 0.000 | 202 / 0.000 |
| 003 | 0 / NA | 0 / NA | 0 / NA |
| 004 | 219 / 0.174 | 219 / 0.000 | 219 / 0.000 |
| 005 | 724 / 0.419 | 724 / 0.000 | 724 / 0.029 |

## 6. H1 / H-B2 的真实收益与选择

- `H1`: position Bias range 改善 0/6，高度 Bias std 改善 0/6，同时改善 0/6；分类 `NO`。
  edge 相对 Base：|Bias|=↓, P95=↓, Max=↓；edge P95/Max 同时逐高度改善 6/6。
- `H-B2`: position Bias range 改善 6/6，高度 Bias std 改善 6/6，同时改善 6/6；分类 `YES`。
  edge 相对 Base：|Bias|=↓, P95=↓, Max=↓；edge P95/Max 同时逐高度改善 6/6。

次级 absolute-error preference score（每个 position-spread、worst-position、edge 指标低者得 1 分）为 `{'H1': 3, 'H-B2': 3}`；首选仍按稳定性主规则判定：HB2 meets the primary stability rule: position Bias range/std and edge P95/Max improve in at least 4 heights; H1 does not meet the position-spread rule. 因此 `PREFERRED_DEPTH_BASELINE=HB2`。这是本历史工作域的诊断优先级，不是生产冻结。

本轮 H1 与 H-B2 都明显降低 edge 的 common depth bias；但 H1 没有降低跨位置 spread，H-B2 在六个高度同时降低 position spread 与 edge P95/Max，因此位置一致性专项优先 H-B2。二者都没有建立新的 spatial correction，且仍需注意 2mm rank5 无 effective support。

## 7. 是否追加连续 v band

不追加 `v_band_metrics.csv`：五个历史位置是离散 acquisition bands，position 之间有明显未覆盖空档，且并非所有 height×position 都有 effective formal points。按任务约束，不能把离散五位置强行解释成连续 v 覆盖或固定五等分。

## 8. 产物

- `historical_position_v_coverage.csv`
- `pointwise_base_h1_hb2.csv`
- `position_consistency_metrics.csv`
- `edge_v_gt_2400_metrics.csv`
- `audit_provenance.json`
- `historical_position_v_coverage.png`
- `residual_vs_v_base_h1_hb2.png`
- `position_bias_comparison_by_height.png`
- `edge_v_gt_2400_error_comparison.png`

本报告由 `tools/audit_height_depth_baseline_spatial.py` 生成；脚本只执行复用产物上的确定性审计，不调用模型搜索或数据采集。
