# Surface-1A 激光曲面坐标 + 局部 Jacobian 残差归因

- `SURFACE_COORDINATE_EXPLANATORY_POWER = PARTIAL`
- `JACOBIAN_DEPENDENCE = SUPPORTED`
- `HEIGHT_ONLY_MODEL = INSUFFICIENT`
- `SURFACE_AWARE_CORRECTION_RECOMMENDED = YES_DIAGNOSTIC_ONLY`

本轮只做点级归因诊断；未重新拟合 C0/C1/G(S)/H1，也未生成或写入新的补偿函数。50 mm 全程保持 held-out 身份。

## Provenance / reuse audit

- 复用 Ground-4A manual-frozen 150 帧逐点 C1：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_manual_frozen\pointwise_diagnostics.csv`，SHA-256 `3c63dc9d115d714d9b78747db06c5016bfd863592c6b959c31301e1a6cd67487`。
- 复用 Ground-4A repeat-1 `session_linear` proxy：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\ground4a_session_calibration.csv`，不重新拟合永久参数。
- 复用 50 mm one-pass center cache、人工 geometry-only ROI 和既有 repeat-1 proxy；50 mm formal 为 20 帧、5 position。
- Frozen config `enable_laser_ray_correction=true`；config SHA-256 `c22e463aff6dc51565679382cc766a3c7078a57f676809e7b31ee1cbe185f15f`。
- 本轮新增：50 mm 点级 C0/C1 几何补全、统一 q1/q2、中心差分 Jacobian、height residual 字段、解释性统计和图表。

## 统一 surface intrinsic coordinates

- Frozen C0 `dependent_axis=X`，`independent_axes=['Y', 'Z']`。
- 对每个 C0 交点 `P_c0`，定义 `q1=(P_c0[independent_axis_1]-center_1)/scale_1`、`q2=(P_c0[independent_axis_2]-center_2)/scale_2`；center/scale 直接来自 Frozen Quadratic C0。
- q1/q2 是全数据共用的无量纲坐标；不按 height、position 或 held-out 数据重新 PCA、平移、缩放或定义坐标。CSV 同时保留 `q1_mm/q2_mm`。
- `height_residual = Zg - (a*S+b) - true_height`；a/b 使用同一 position 的 repeat-1 ground proxy，point-level metrics 仅使用与原 height line 相同的 XY robust inlier。
- Jacobian 为最终 C1 lambda/Zg 对原始像素 u/v 的中心差分，epsilon=`0.01` px；导数单位分别为 mm/px。

## Surface domain / held-out 检查

- development formal q bbox：q1 `-1.73130`–`2.11623`，q2 `0.16223`–`1.46051`。
- 50 mm q bbox：q1 `-1.57193`–`1.82884`，q2 `-0.66432`–`-0.58517`。
- 50 mm formal points 落在 development q bbox 内的比例：`0.0%`。50 mm 不参与 q/尺度/阈值或任何模型拟合；该比例仅作为 held-out 的事后 domain-coverage 诊断，并影响跨域支持级别的解释。
- 相近 q 条件对（固定 max(|Δq1|,|Δq2|)≤0.05）：`1` 对；median residual difference `0.00423` mm。

## Development formal point-pooled explanatory metrics

OLS 仅作为描述性解释量，不是补偿拟合；`within_condition_r2` 先去除每个完整 height×position condition 的均值，用于检查 surface/Jacobian 是否解释 condition 内空间结构。

| model | features | R² | OLS RMSE | Pearson/Spearman | within-condition R² |
|---|---|---:|---:|---:|---:|
| height | true_height_mm | 0.55796 | 0.03294 | -0.74697/-0.72731 | MISSING |
| v | v | 0.14823 | 0.04572 | -0.38500/-0.34801 | 0.02812 |
| C1_s | C1_s | 0.14844 | 0.04572 | -0.38529/-0.34903 | 0.02812 |
| (q1,q2) | q1+q2 | 0.64269 | 0.02961 | — | 0.86812 |
| J_Zg_norm | jacobian_Zg_norm_mm_per_px | 0.57180 | 0.03242 | 0.75617/0.75865 | 0.75315 |
| J_lambda_norm | jacobian_lambda_norm_mm_per_px | 0.58504 | 0.03191 | 0.76488/0.76530 | 0.59265 |
| Jacobian | d_lambda_du+d_lambda_dv+d_Zg_du+d_Zg_dv | 0.71114 | 0.02663 | — | 0.95609 |
| v+C1_s | v+C1_s | 0.51696 | 0.03443 | — | 0.02814 |
| height+q1+q2 | true_height_mm+q1+q2 | 0.75998 | 0.02427 | — | 0.86812 |
| q1+q2+Jacobian | q1+q2+d_lambda_du+d_lambda_dv+d_Zg_du+d_Zg_dv | 0.71584 | 0.02641 | — | 0.96031 |

## Height × position condition summaries

development formal：

| height | position | points | mean residual | median | RMSE | q1 mean | q2 mean | JZ norm mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1mm | laser001 | 315 | 0.00923 | 0.00993 | 0.02575 | -1.67386 | 1.45762 | 0.31269 |
| 1mm | laser002 | 196 | -0.03935 | -0.03919 | 0.04173 | -0.47758 | 1.43538 | 0.31256 |
| 1mm | laser003 | 271 | 0.01306 | 0.01642 | 0.02322 | 0.16559 | 1.41609 | 0.31230 |
| 1mm | laser004 | 236 | -0.05516 | -0.05482 | 0.05789 | 1.09622 | 1.39432 | 0.31202 |
| 1mm | laser005 | 196 | -0.03487 | -0.03625 | 0.03847 | 2.06604 | 1.37137 | 0.31165 |
| 2mm | laser001 | 234 | 0.00500 | 0.00522 | 0.01793 | -1.65958 | 1.41535 | 0.31181 |
| 2mm | laser002 | 211 | -0.03295 | -0.03218 | 0.03895 | -0.66066 | 1.39792 | 0.31174 |
| 2mm | laser003 | 186 | -0.05771 | -0.05855 | 0.05931 | 0.51923 | 1.36681 | 0.31134 |
| 2mm | laser004 | 200 | -0.02153 | -0.02193 | 0.02742 | 1.45062 | 1.34082 | 0.31096 |
| 6mm | laser001 | 225 | -0.00608 | -0.00656 | 0.01899 | -1.57768 | 1.24622 | 0.30831 |
| 6mm | laser002 | 222 | -0.03492 | -0.03375 | 0.03729 | -0.39169 | 1.22132 | 0.30811 |
| 6mm | laser003 | 233 | -0.00980 | -0.00923 | 0.02105 | 0.19337 | 1.20563 | 0.30791 |
| 6mm | laser004 | 247 | 0.00490 | 0.00434 | 0.02287 | 1.42872 | 1.17292 | 0.30745 |
| 6mm | laser005 | 238 | -0.06435 | -0.06143 | 0.06756 | 2.07018 | 1.16248 | 0.30730 |
| 10mm | laser001 | 269 | -0.03188 | -0.02991 | 0.04046 | -1.57111 | 1.07916 | 0.30484 |
| 10mm | laser002 | 202 | -0.04713 | -0.05190 | 0.05151 | -0.38408 | 1.05296 | 0.30461 |
| 10mm | laser003 | 166 | -0.02868 | -0.02757 | 0.03351 | 0.83166 | 1.02287 | 0.30424 |
| 10mm | laser004 | 226 | -0.04794 | -0.04553 | 0.05151 | 1.42762 | 1.00595 | 0.30399 |
| 10mm | laser005 | 180 | -0.08394 | -0.08272 | 0.08561 | 2.03896 | 0.99551 | 0.30384 |
| 20mm | laser001 | 250 | -0.04917 | -0.04830 | 0.05060 | -1.60946 | 0.65912 | 0.29619 |
| 20mm | laser002 | 269 | -0.08027 | -0.08247 | 0.08267 | -0.39885 | 0.63267 | 0.29597 |
| 20mm | laser003 | 244 | -0.07495 | -0.07005 | 0.07913 | 0.76983 | 0.60438 | 0.29563 |
| 20mm | laser004 | 203 | -0.10497 | -0.10590 | 0.10569 | 1.36310 | 0.58766 | 0.29539 |
| 20mm | laser005 | 236 | -0.13118 | -0.12930 | 0.13344 | 1.95768 | 0.57704 | 0.29525 |
| 30mm | laser001 | 261 | -0.09686 | -0.09583 | 0.09743 | -1.57661 | 0.24401 | 0.28778 |
| 30mm | laser002 | 264 | -0.12332 | -0.12450 | 0.12418 | -0.39443 | 0.21953 | 0.28758 |
| 30mm | laser003 | 248 | -0.08429 | -0.08478 | 0.08486 | 0.80336 | 0.18844 | 0.28720 |
| 30mm | laser004 | 284 | -0.08511 | -0.08495 | 0.08708 | 1.38728 | 0.17265 | 0.28699 |
| 30mm | laser005 | 290 | -0.16927 | -0.16876 | 0.17002 | 2.00957 | 0.16387 | 0.28689 |

50 mm held-out formal：

| height | position | points | mean residual | median | RMSE | q1 mean | q2 mean | JZ norm mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 50mm | laser001 | 221 | -0.12473 | -0.12484 | 0.12521 | 1.78755 | -0.66324 | 0.27048 |
| 50mm | laser002 | 218 | -0.11225 | -0.11383 | 0.11317 | 1.19595 | -0.65040 | 0.27063 |
| 50mm | laser003 | 190 | -0.06233 | -0.06151 | 0.06350 | 0.01896 | -0.62320 | 0.27093 |
| 50mm | laser004 | 237 | -0.13319 | -0.13376 | 0.13391 | -0.86375 | -0.59354 | 0.27133 |
| 50mm | laser005 | 234 | -0.08862 | -0.08861 | 0.08962 | -1.53145 | -0.58667 | 0.27129 |

## 结论解释

- `SURFACE_COORDINATE_EXPLANATORY_POWER = PARTIAL`：q1/q2 的统一定义和跨组比较已完成；该状态只表示诊断性解释能力，不代表可以直接把 q1/q2 变成 correction LUT。
- `JACOBIAN_DEPENDENCE = SUPPORTED`：使用最终 C1 的 `d_lambda/du,d_lambda/dv,d_Zg/du,d_Zg/dv` 及其 norm；50 mm 只做独立描述。
- `HEIGHT_ONLY_MODEL = INSUFFICIENT`：height-only 仅作为基线解释，不把高度相关性误认为 surface 充分性。
- `SURFACE_AWARE_CORRECTION_RECOMMENDED = YES_DIAGNOSTIC_ONLY`：即使为 YES，也仅建议进入下一轮 held-out 诊断/候选设计；本轮不拟合、不冻结、不接生产链路。
- 若 q 相近条件仍有明显 residual 差异，则 q1/q2 不是充分统计量；若 Jacobian 在相近 q 区域显著变化，则应优先考虑局部灵敏度/数值稳定性而非简单 height 或 v 补偿。

## 输出

- `surface1a_points.csv`：所有成功 C1 顶部点，含 u/v、C0/C1 lambda、P、Zg、q1/q2、height residual 与局部 Jacobian。
- `surface_coordinate_definition.json`：唯一 q 定义、Frozen 参数、residual/Jacobian 口径与 provenance。
- `surface1a_explanatory_metrics.csv`：point-pooled/condition-balanced 的描述性解释指标。
- `residual_vs_surface_coordinate.png`、`surface_residual_map_q1_q2.png`、`residual_vs_jacobian.png`。
