# Surface-2 B2(q2-only) vs S0(q1+q2) model selection

## 结论

`SELECTED_SURFACE_MODEL=B2`  
`Q1_RETAINED=NO`  
`Q2_ONLY_CORRECTION_RECOMMENDED=YES`  
`MORE_HEIGHT_ACQUISITION_REQUIRED=YES`

历史结论原样保留：`Q2_GAP_FILLED=NO`、`SURFACE2C_ALLOWED=NO`。本轮没有因 q2 gap 阻塞 B2/S0 比较；上述选择仅是 development grouped-CV 的诊断性模型结构选择，不是 production validation，也不等于允许直接接入 correction 链路。

判断规则：S0 只有在 LOHO、LOPO、LOBO 三个 development scheme 中都同时满足 pooled RMSE/P95 改善，并且 P95 与 worst-condition 的 fold improvement 为多数时，才保留 q1；否则在 B2 相对 B0 的 q2 增益稳定时选择更简单的 B2。50 mm 不参与任何选择。

## Provenance / 复用边界

- 复用 canonical Surface-2BR2 的 condition table、CV metrics、condition predictions、coefficients 和 coefficient stability；输入 SHA 已写入 `surface2_model_selection_summary.json`。
- development：1/2/6/10/20/30/36/40/46 mm，44 conditions、11160 analysis points。
- strict held-out：50 mm，5 conditions、1100 analysis points；仅本报告末尾诊断。
- condition 等权；沿用既有点级拟合权重 `1 / condition_point_count`；没有 random point split。
- Frozen C0/C1、manual ROI、session-linear ground proxy、q1/q2 定义全部由既有 artifact 继承；未重拟 C0/C1、未修改 ROI/q、未拟合新 correction。

## Pooled condition metrics

| CV scheme | model | conditions | Bias | MAE | RMSE | P95 | Max |
|---|---|---:|---:|---:|---:|---:|---:|
| LOHO_height | B2 | 44 | 0.00111 | 0.02405 | 0.02955 | 0.04682 | 0.08107 |
| LOHO_height | S0 | 44 | 0.00093 | 0.02252 | 0.02723 | 0.04991 | 0.06447 |
| LOPO_position_rank | B2 | 44 | 0.00021 | 0.02578 | 0.03139 | 0.04922 | 0.08525 |
| LOPO_position_rank | S0 | 44 | -0.00237 | 0.02566 | 0.03109 | 0.05888 | 0.07953 |
| LOBO_height_band | B2 | 44 | 0.03001 | 0.04332 | 0.05059 | 0.08396 | 0.08736 |
| LOBO_height_band | S0 | 44 | 0.02750 | 0.03973 | 0.04649 | 0.07418 | 0.09488 |
| strict_50mm_validation | B2 | 5 | 0.02967 | 0.03003 | 0.03914 | 0.06591 | 0.07156 |
| strict_50mm_validation | S0 | 5 | 0.02835 | 0.03293 | 0.03821 | 0.06179 | 0.06927 |

## S0 相对 B2 incremental

负值代表 S0 优于 B2。

| CV scheme | ΔBias | ΔMAE | ΔRMSE | ΔP95 | ΔMax |
|---|---:|---:|---:|---:|---:|
| LOHO_height | -0.00018 | -0.00153 | -0.00232 | 0.00309 | -0.01660 |
| LOPO_position_rank | -0.00259 | -0.00013 | -0.00030 | 0.00966 | -0.00572 |
| LOBO_height_band | -0.00251 | -0.00359 | -0.00410 | -0.00978 | 0.00752 |
| strict_50mm_validation | -0.00132 | 0.00291 | -0.00092 | -0.00412 | -0.00229 |

### Fold improvement rate

| CV scheme | RMSE improved | P95 improved | worst-condition improved |
|---|---:|---:|---:|
| LOHO_height | 8/9 (88.9%) | 6/9 (66.7%) | 6/9 (66.7%) |
| LOPO_position_rank | 3/5 (60.0%) | 3/5 (60.0%) | 3/5 (60.0%) |
| LOBO_height_band | 3/3 (100.0%) | 2/3 (66.7%) | 2/3 (66.7%) |

- `LOHO_height`：ΔRMSE=-0.00232 mm，ΔP95=0.00309 mm；P95 fold=66.7%，worst-condition fold=66.7%。
- `LOPO_position_rank`：ΔRMSE=-0.00030 mm，ΔP95=0.00966 mm；P95 fold=60.0%，worst-condition fold=60.0%。
- `LOBO_height_band`：ΔRMSE=-0.00410 mm，ΔP95=-0.00978 mm；P95 fold=66.7%，worst-condition fold=66.7%。

LOHO 与 LOPO 的 pooled P95 分别没有改善，因而 S0 没有达到“跨三个 scheme 稳定额外收益”的门槛；q1 即使符号稳定，也没有足够稳定的工程收益。

## q-space support 分层

support 分类沿用每个 frozen fold 的 `IN_DOMAIN / HULL_EXTRAPOLATION / BBOX_EXTRAPOLATION`，extrapolation 改善不被解释为域内泛化。

| CV scheme | support | conditions | B2 RMSE | S0 RMSE | ΔRMSE | B2 P95 | S0 P95 | ΔP95 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LOHO_height | IN_DOMAIN | 32 | 0.02853 | 0.02611 | -0.00242 | 0.04595 | 0.04944 | 0.00349 |
| LOHO_height | HULL_EXTRAPOLATION | 3 | 0.04944 | 0.03936 | -0.01008 | 0.07567 | 0.05993 | -0.01574 |
| LOHO_height | BBOX_EXTRAPOLATION | 9 | 0.02369 | 0.02617 | 0.00248 | 0.03769 | 0.03741 | -0.00028 |
| LOPO_position_rank | IN_DOMAIN | 25 | 0.02636 | 0.03074 | 0.00438 | 0.04428 | 0.04987 | 0.00559 |
| LOPO_position_rank | HULL_EXTRAPOLATION | 2 | 0.02380 | 0.02828 | 0.00449 | 0.02812 | 0.02850 | 0.00038 |
| LOPO_position_rank | BBOX_EXTRAPOLATION | 17 | 0.03824 | 0.03191 | -0.00633 | 0.07180 | 0.06625 | -0.00555 |
| LOBO_height_band | IN_DOMAIN | 9 | 0.03143 | 0.02921 | -0.00223 | 0.05713 | 0.05085 | -0.00628 |
| LOBO_height_band | HULL_EXTRAPOLATION | 1 | 0.08445 | 0.07104 | -0.01342 | 0.08445 | 0.07104 | -0.01342 |
| LOBO_height_band | BBOX_EXTRAPOLATION | 34 | 0.05330 | 0.04922 | -0.00408 | 0.08321 | 0.07842 | -0.00479 |
| strict_50mm_validation | BBOX_EXTRAPOLATION | 5 | 0.03914 | 0.03821 | -0.00092 | 0.06591 | 0.06179 | -0.00412 |

## Worst-condition

| CV scheme | folds | mean B2 worst | mean S0 worst | S0 improved folds | mean condition error improvement rate |
|---|---:|---:|---:|---:|---:|
| LOHO_height | 9 | 0.04588 | 0.04324 | 6/9 | 0.567 |
| LOPO_position_rank | 5 | 0.05083 | 0.05249 | 3/5 | 0.508 |
| LOBO_height_band | 3 | 0.08242 | 0.08022 | 2/3 | 0.587 |
| strict_50mm_validation | 1 | 0.07156 | 0.06927 | 1/1 | 0.400 |

对应明细写入 `surface2_model_selection_worst_conditions.csv`；每个 fold 的 worst condition 是该 fold condition mean 的最大绝对 corrected bias，不是点级最大值。

## Coefficient stability

| CV scheme | model | parameter | mean | std | range | range/abs(mean) | sign consistent |
|---|---|---|---:|---:|---:|---:|---|
| LOBO_height_band | B2 | intercept | -0.109283 | 0.016136 | 0.038168 | 0.349 | True |
| LOBO_height_band | B2 | q2 | 0.050723 | 0.024583 | 0.060215 | 1.187 | True |
| LOBO_height_band | S0 | intercept | -0.105754 | 0.013588 | 0.032306 | 0.305 | True |
| LOBO_height_band | S0 | q1 | -0.008886 | 0.001131 | 0.002611 | 0.294 | True |
| LOBO_height_band | S0 | q2 | 0.049698 | 0.022407 | 0.054835 | 1.103 | True |
| LOHO_height | B2 | intercept | -0.100868 | 0.002599 | 0.009494 | 0.094 | True |
| LOHO_height | B2 | q2 | 0.053377 | 0.002274 | 0.007674 | 0.144 | True |
| LOHO_height | S0 | intercept | -0.098485 | 0.002217 | 0.008504 | 0.086 | True |
| LOHO_height | S0 | q1 | -0.009376 | 0.000927 | 0.003602 | 0.384 | True |
| LOHO_height | S0 | q2 | 0.053164 | 0.002089 | 0.007295 | 0.137 | True |
| LOPO_position_rank | B2 | intercept | -0.100674 | 0.004870 | 0.014172 | 0.141 | True |
| LOPO_position_rank | B2 | q2 | 0.053172 | 0.002539 | 0.006756 | 0.127 | True |
| LOPO_position_rank | S0 | intercept | -0.097856 | 0.004911 | 0.011791 | 0.120 | True |
| LOPO_position_rank | S0 | q1 | -0.009035 | 0.003390 | 0.009280 | 1.027 | True |
| LOPO_position_rank | S0 | q2 | 0.052923 | 0.002015 | 0.005488 | 0.104 | True |
| strict_50mm_validation | B2 | intercept | -0.100688 | 0.000000 | 0.000000 | 0.000 | True |
| strict_50mm_validation | B2 | q2 | 0.053274 | 0.000000 | 0.000000 | 0.000 | True |
| strict_50mm_validation | S0 | intercept | -0.098337 | 0.000000 | 0.000000 | 0.000 | True |
| strict_50mm_validation | S0 | q1 | -0.009397 | 0.000000 | 0.000000 | 0.000 | True |
| strict_50mm_validation | S0 | q2 | 0.053092 | 0.000000 | 0.000000 | 0.000 | True |

S0 q1 在 development scheme 中符号一致：`True`；幅值 relative range 为 `{'LOBO_height_band': 0.29377573275194624, 'LOHO_height': 0.384202126345683, 'LOPO_position_rank': 1.027066190673536}`。符号一致不能抵消 LOHO/LOPO P95 与 worst-condition 额外收益不稳定这一事实。

## Strict 50 mm（只作最终诊断）

strict_50mm_validation 0.03914→0.03821 RMSE, Δ=-0.00092; 0.06591→0.06179 P95, Δ=-0.00412

50 mm 所有 fold 均为 q-space `BBOX_EXTRAPOLATION`，因此不用于模型选择、阈值或参数调整；它不能把 S0 的微小 RMSE/P95 改善升级为开发域泛化证据。

## B2(q2-only) 的后续含义

B2 相对公共 offset B0 在三个 development grouped schemes 的 pooled RMSE 与 P95 均改善，因此本轮推荐 `Q2_ONLY_CORRECTION_RECOMMENDED=YES`，但仅作为 1D q2 correction 的诊断候选。现有 q2 domain gap 和低 IN_DOMAIN 支持仍使后续高度补采保持必要；这不覆盖原 Surface-2B/2BR2 结论。

## 输出

- `surface2_model_selection_cv_metrics.csv`
- `surface2_model_selection_support_metrics.csv`
- `surface2_model_selection_incremental_comparison.csv`
- `surface2_model_selection_coefficients.csv`
- `surface2_model_selection_coefficient_stability.csv`
- `surface2_model_selection_worst_conditions.csv`
- `surface2_model_selection_worst_condition.png`
- `surface2_model_selection_coefficient_stability.png`
- `surface2_model_selection_summary.json`
