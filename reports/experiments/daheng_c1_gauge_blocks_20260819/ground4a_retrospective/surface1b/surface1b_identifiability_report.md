# Surface-1B Surface/Jacobian 特征可辨识性审计

- `SURFACE_FEATURE_IDENTIFIABILITY = PARTIAL`
- `HEIGHT_Q2_REDUNDANCY = SUPPORTED`
- `JACOBIAN_ADDS_INDEPENDENT_INFORMATION = NOT_SUPPORTED`
- `RECOMMENDED_MINIMAL_FEATURE_SET = q1+q2`
- `SURFACE2_ACQUISITION_PRIORITY = 40mm > 35mm > 45mm；资源允许时三者全部采集`

本轮是 development-only 可辨识性诊断。未重新拟合 C0/C1/G(S)/H1，未生成补偿函数，未修改生产配置。50 mm 仅保留为 held-out 描述，未参与 SVD、VIF、候选特征选择或任何模型参数拟合。

## Provenance / reuse audit

- 复用输入：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\surface1a\surface1a_points.csv`，Surface-1A 已冻结的 q 定义：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\surface1a\surface_coordinate_definition.json`。
- 复用 Surface-1A summary/metrics 做 split 与数值一致性核对：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\surface1a\surface1a_summary.json`、`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\surface1a\surface1a_explanatory_metrics.csv`。
- development formal：6802 个分析点、29 个 height×position condition。
- 50 mm held-out descriptive：1100 个分析点、5 个 condition；未进入模型选择/拟合。
- formal 过滤：`split_role` 为 repeat2–5 formal，同时 `height_measurement_inlier=True`、`jacobian_valid=True`；禁止随机 point split。
- condition-level 采用每个完整 height×position condition 的点均值，每个 condition 等权；point-level 仅作描述性参考。

## Correlation / redundancy

下表同时给出 point-level 与 condition-level 的 feature↔residual 相关性；相关性不等于因果或可部署补偿。

| feature | point Pearson/Spearman | condition Pearson/Spearman |
|---|---:|---:|
| height | -0.7470/-0.7273 | -0.7893/-0.7375 |
| q1 | -0.3834/-0.3534 | -0.3968/-0.3591 |
| q2 | 0.7632/0.7667 | 0.8086/0.8084 |
| d_lambda_du | 0.7647/0.7655 | 0.8102/0.8049 |
| d_lambda_dv | 0.4462/0.4543 | 0.4618/0.4970 |
| d_Zg_du | -0.7558/-0.7585 | -0.8001/-0.7980 |
| d_Zg_dv | -0.4529/-0.4600 | -0.4690/-0.4970 |
| J_lambda_norm | 0.7649/0.7653 | 0.8104/0.8049 |
| J_Z_norm | 0.7562/0.7587 | 0.8005/0.7980 |

关键共线性对：

| pair | point Pearson/Spearman | condition Pearson/Spearman |
|---|---:|---:|
| height ↔ q2 | -0.9977/-0.9769 | -0.9976/-0.9751 |
| q1 ↔ q2 | -0.1866/-0.3382 | -0.1559/-0.2946 |
| q2 ↔ J_lambda_norm | 1.0000/0.9997 | 1.0000/0.9995 |
| q2 ↔ J_Z_norm | 0.9996/0.9983 | 0.9996/0.9985 |
| d_lambda_du ↔ d_lambda_dv | 0.2740/0.4457 | 0.2450/0.4232 |
| d_Zg_du ↔ d_Zg_dv | 0.2508/0.4348 | 0.2207/0.4030 |

height↔q2 的最小绝对 Pearson/Spearman 相关系数为 `0.9751`，因此其独立可辨识性受到高度-表面几何共线性限制。

## Standardized SVD / PCA / VIF（development condition-level）

PCA/SVD 只作为数值诊断，不改写 frozen q1/q2 定义。J 表示四个带符号的局部导数：`d_lambda_du,d_lambda_dv,d_Zg_du,d_Zg_dv`。

| feature set | rank | SVD condition no. | correlation condition no. | max VIF | mean VIF |
|---|---:|---:|---:|---:|---:|
| q1 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| q1+q2 | 2.00 | 1.17 | 1.37 | 1.02 | 1.02 |
| q1+J | 5.00 | 10110.61 | 102224365.33 | 15765110.21 | 7525989.88 |
| q1+q2+J | 6.00 | 11057.21 | 122261790.67 | 16686962.74 | 6594651.23 |
| height+q1+q2 | 3.00 | 357.27 | 127642.62 | 31684.60 | 20996.72 |

## Candidate feature-set comparison

OLS 仅为 explanatory nested-model comparison；不代表将系数冻结为 correction。所有候选模型使用同一 development observation table。

| feature set | condition in-sample R² | condition RMSE | point within-condition R² | LOHO median RMSE | LOPO median RMSE |
|---|---:|---:|---:|---:|---:|
| q1 | 0.1575 | 0.0403 | -0.0080 | 0.0434 | 0.0390 |
| q1+q2 | 0.7290 | 0.0229 | -0.0127 | 0.0230 | 0.0303 |
| q1+J | 0.8127 | 0.0190 | -0.0271 | 0.0246 | 0.0331 |
| q1+q2+J | 0.8163 | 0.0188 | -0.0292 | 0.0253 | 0.0317 |
| height+q1+q2 | 0.8016 | 0.0196 | 0.4504 | 0.0211 | 0.0274 |

q1+q2+J 相对 q1+q2 的 condition-level in-sample ΔR²=`0.0874`；LOHO/LOPO grouped RMSE 中位改善分别为 `-0.00321, -0.00397` mm。
因此 `JACOBIAN_ADDS_INDEPENDENT_INFORMATION = NOT_SUPPORTED`；即使 J 能解释部分 residual，也必须结合 VIF 和 grouped 稳定性，不能把高 in-sample R² 当作单个参数可辨识。

## Grouped sensitivity

LOHO=leave-one-height-out，LOPO=leave-one-position-out；每个 fold 完整留出对应 height 或 position 的全部 condition，训练/评估均在 development 内完成。

| fold type | feature set | median RMSE | median MAE | median P95 | median max | fold count |
|---|---|---:|---:|---:|---:|---:|
| LOHO | q1 | 0.0434 | 0.0385 | 0.0640 | 0.0682 | 6 |
| LOHO | q1+q2 | 0.0230 | 0.0188 | 0.0342 | 0.0371 | 6 |
| LOHO | q1+J | 0.0246 | 0.0184 | 0.0407 | 0.0418 | 6 |
| LOHO | q1+q2+J | 0.0253 | 0.0197 | 0.0412 | 0.0435 | 6 |
| LOHO | height+q1+q2 | 0.0211 | 0.0151 | 0.0363 | 0.0392 | 6 |
| LOPO | q1 | 0.0390 | 0.0310 | 0.0743 | 0.0829 | 5 |
| LOPO | q1+q2 | 0.0303 | 0.0292 | 0.0387 | 0.0408 | 5 |
| LOPO | q1+J | 0.0331 | 0.0300 | 0.0505 | 0.0520 | 5 |
| LOPO | q1+q2+J | 0.0317 | 0.0292 | 0.0451 | 0.0474 | 5 |
| LOPO | height+q1+q2 | 0.0274 | 0.0225 | 0.0390 | 0.0395 | 5 |

## Surface-2 采集优先级（仅 development 规划）

development-only q2~height slope=`-0.042086` q2/mm；该趋势只用于采集规划，不是 height correction。development formal q2 范围为 `0.1625`–`1.4605`。
50 mm q2 范围 `-0.6643`–`-0.5854` 仅作 held-out domain context，未参与上述趋势拟合。

| target height | development-only predicted q2 | position-wise predicted q2 range |
|---:|---:|---:|
| 35 mm | -0.0163 | -0.0458–0.0331 |
| 40 mm | -0.2267 | -0.2541–-0.1762 |
| 45 mm | -0.4371 | -0.4624–-0.3856 |

建议顺序：40 mm（中段 gap）、35 mm（development 上界转折）、45 mm（接近 50 mm 高端）。若资源允许，优先一次性采集完整 `35/40/45 mm × 5 positions`，每个高度保持 repeat1 proxy + repeat2–5 formal protocol。

## 结论与限制

- `SURFACE_FEATURE_IDENTIFIABILITY = PARTIAL`：q1/q2 在当前 development 域可做稳定的表面坐标诊断，但 height、q2、Jacobian 之间存在不同程度共线性；不能据此声称各物理因素已完全分离。
- `HEIGHT_Q2_REDUNDANCY = SUPPORTED`：height 与 q2 的高度趋势在当前设计中高度重叠，height+q1+q2 的解释增益不能单独归因于 surface。
- `JACOBIAN_ADDS_INDEPENDENT_INFORMATION = NOT_SUPPORTED`：J 的增益必须以 grouped sensitivity 和 VIF 共同判断；当前没有把 J 变成补偿函数。
- `RECOMMENDED_MINIMAL_FEATURE_SET = q1+q2`：这是后续诊断建模的最小候选集，不是生产参数。
- 50 mm 保持 held-out 身份；本轮不使用其结果调整 feature set、PCA/VIF、阈值或采集规则。

## Outputs

- `surface1b_feature_correlation.csv`：point-level / condition-level 的 Pearson/Spearman 长表。
- `surface1b_vif_svd.csv`：development-only 各候选集的标准化 SVD/PCA、condition number、VIF。
- `surface1b_feature_set_comparison.csv`：候选集 explanatory OLS 与 LOHO/LOPO grouped sensitivity。
- `surface1b_correlation_heatmap.png`、本报告以及 machine-readable `surface1b_summary.json`。
