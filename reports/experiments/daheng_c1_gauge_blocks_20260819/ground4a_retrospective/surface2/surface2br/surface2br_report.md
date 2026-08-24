# Surface-2BR 低自由度 q correction feasibility audit

## 独立结论

`SURFACE_CORRECTION_FEASIBILITY=PARTIAL`  
`MORE_HEIGHT_ACQUISITION_REQUIRED=YES`

本报告是 Surface-2B 的 feasibility audit，不是 production validation，也不覆盖原报告。原结论保持：`Q2_GAP_FILLED=NO`、`Q1Q2_STATE_CONSISTENCY=PARTIAL`、`SURFACE2C_ALLOWED=NO`。

判定只在 30/36/40/46 mm development 上进行模型比较；50 mm 从未进入拟合、模型选择或阈值调整，仅用 development-all fit 做一次 strict held-out 描述。每个 height×position condition 总权重相同，拟合采用每个点的 `1 / condition_point_count` 权重；没有 random point split。

## 模型

- S0：`F(q1,q2)=a0+a1*q1+a2*q2`
- S1：`F(q1,q2)=a0+a1*q1+a2*q2+a3*q1²+a4*q1*q2+a5*q2²`
- corrected residual：`r_corrected = r - F(q1,q2)`。
- q1/q2 沿用 Frozen C0 的 Surface-2B 定义，未重新中心化、缩放或重定义。

## Provenance

| artifact | SHA256 |
|---|---|
| samples | `f2bb04053c77806ede096ba5b15d05d76f2a0f1b7465e0a189adf7f1346687c7` |
| condition statistics | `b049eb25eec2824541e36ab321d7e80bba45f0c70accd1d1ba8d7f6d79cf7a65` |
| domain statistics | `697c0742798c15e1f661069833590659d3c4e27c18c32950910c9e3eaec84d13` |
| Surface-2B summary | `07bb9295492dde995989269f70d1baf141f3ad709e7b2e3d45e6bf697df5a03f` |

## Pooled condition-balanced comparison

| CV scheme | model | conditions | raw RMSE | corrected RMSE | ΔRMSE | corrected P95 |
|---|---:|---:|---:|---:|---:|---:|
| LOHO_development | S0 | 20 | 0.11020 | 0.03334 | -0.07687 | 0.06213 |
| LOHO_development | S1 | 20 | 0.11020 | 0.04734 | -0.06287 | 0.08659 |
| LOPO_position_rank | S0 | 20 | 0.11020 | 0.03738 | -0.07282 | 0.05834 |
| LOPO_position_rank | S1 | 20 | 0.11020 | 0.05140 | -0.05880 | 0.08282 |
| strict_50mm_validation | S0 | 5 | 0.10737 | 0.02560 | -0.08177 | 0.04378 |
| strict_50mm_validation | S1 | 5 | 0.10737 | 0.03931 | -0.06806 | 0.06260 |

## Fold metrics and q-space support

`bbox_oob_rate` 是该 fold 测试点落在训练 fold q1/q2 轴对齐 bbox 外的比例；这不是自动删点，也不代表允许 extrapolation。所有预测即使越界也只作为诊断数值输出，并明确标记 unsupported。

| scheme | model | held-out group | raw RMSE | corrected RMSE | ΔRMSE | support | bbox OOB |
|---|---:|---|---:|---:|---:|---|---:|
| LOHO_development | S0 | height_30mm | 0.11627 | 0.03656 | -0.07971 | BBOX_EXTRAPOLATION | 100.0% |
| LOHO_development | S1 | height_30mm | 0.11627 | 0.06848 | -0.04779 | BBOX_EXTRAPOLATION | 100.0% |
| LOHO_development | S0 | height_36mm | 0.10855 | 0.02861 | -0.07993 | IN_DOMAIN | 0.0% |
| LOHO_development | S1 | height_36mm | 0.10855 | 0.02906 | -0.07949 | IN_DOMAIN | 0.0% |
| LOHO_development | S0 | height_40mm | 0.09597 | 0.02707 | -0.06890 | IN_DOMAIN | 0.0% |
| LOHO_development | S1 | height_40mm | 0.09597 | 0.01976 | -0.07621 | IN_DOMAIN | 0.0% |
| LOHO_development | S0 | height_46mm | 0.11861 | 0.03947 | -0.07914 | BBOX_EXTRAPOLATION | 100.0% |
| LOHO_development | S1 | height_46mm | 0.11861 | 0.05512 | -0.06349 | BBOX_EXTRAPOLATION | 100.0% |
| LOPO_position_rank | S0 | rank_1 | 0.09937 | 0.02261 | -0.07676 | BBOX_EXTRAPOLATION | 100.0% |
| LOPO_position_rank | S1 | rank_1 | 0.09937 | 0.06969 | -0.02968 | BBOX_EXTRAPOLATION | 100.0% |
| LOPO_position_rank | S0 | rank_2 | 0.11874 | 0.03040 | -0.08834 | HULL_EXTRAPOLATION | 0.0% |
| LOPO_position_rank | S1 | rank_2 | 0.11874 | 0.04529 | -0.07345 | HULL_EXTRAPOLATION | 0.0% |
| LOPO_position_rank | S0 | rank_3 | 0.08201 | 0.03682 | -0.04519 | HULL_EXTRAPOLATION | 0.0% |
| LOPO_position_rank | S1 | rank_3 | 0.08201 | 0.02774 | -0.05427 | HULL_EXTRAPOLATION | 0.0% |
| LOPO_position_rank | S0 | rank_4 | 0.09765 | 0.03047 | -0.06718 | IN_DOMAIN | 0.0% |
| LOPO_position_rank | S1 | rank_4 | 0.09765 | 0.02937 | -0.06828 | IN_DOMAIN | 0.0% |
| LOPO_position_rank | S0 | rank_5 | 0.14315 | 0.05717 | -0.08598 | BBOX_EXTRAPOLATION | 100.0% |
| LOPO_position_rank | S1 | rank_5 | 0.14315 | 0.06835 | -0.07480 | BBOX_EXTRAPOLATION | 100.0% |
| strict_50mm_validation | S0 | height_50mm_strict_heldout | 0.10737 | 0.02560 | -0.08177 | BBOX_EXTRAPOLATION | 100.0% |
| strict_50mm_validation | S1 | height_50mm_strict_heldout | 0.10737 | 0.03931 | -0.06806 | BBOX_EXTRAPOLATION | 100.0% |

### S0 各 held-out fold 完整指标

| scheme | held-out group | raw Bias | corrected Bias | raw abs(Bias) | corrected abs(Bias) | raw RMSE | corrected RMSE | raw P95 | corrected P95 | raw Max | corrected Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LOHO_development | height_30mm | -0.11177 | -0.02086 | 0.11177 | 0.02086 | 0.11627 | 0.03656 | 0.16008 | 0.06193 | 0.16927 | 0.06787 |
| LOHO_development | height_36mm | -0.10377 | 0.00305 | 0.10377 | 0.00305 | 0.10855 | 0.02861 | 0.14050 | 0.04344 | 0.14548 | 0.04673 |
| LOHO_development | height_40mm | -0.09309 | 0.01791 | 0.09309 | 0.01791 | 0.09597 | 0.02707 | 0.12812 | 0.04079 | 0.13745 | 0.04183 |
| LOHO_development | height_46mm | -0.11795 | -0.03027 | 0.11795 | 0.03027 | 0.11861 | 0.03947 | 0.13434 | 0.06153 | 0.13567 | 0.06183 |
| LOPO_position_rank | rank_1 | -0.09732 | -0.00927 | 0.09732 | 0.00927 | 0.09937 | 0.02261 | 0.12417 | 0.03778 | 0.12899 | 0.04186 |
| LOPO_position_rank | rank_2 | -0.11760 | -0.02630 | 0.11760 | 0.02630 | 0.11874 | 0.03040 | 0.13382 | 0.04148 | 0.13567 | 0.04334 |
| LOPO_position_rank | rank_3 | -0.08041 | 0.03347 | 0.08041 | 0.03347 | 0.08201 | 0.03682 | 0.10106 | 0.05054 | 0.10401 | 0.05291 |
| LOPO_position_rank | rank_4 | -0.09607 | 0.02533 | 0.09607 | 0.02533 | 0.09765 | 0.03047 | 0.11702 | 0.04349 | 0.11897 | 0.04460 |
| LOPO_position_rank | rank_5 | -0.14183 | -0.05121 | 0.14183 | 0.05121 | 0.14315 | 0.05717 | 0.16571 | 0.08257 | 0.16927 | 0.08712 |
| strict_50mm_validation | height_50mm_strict_heldout | -0.10423 | 0.00592 | 0.10423 | 0.00592 | 0.10737 | 0.02560 | 0.13150 | 0.04378 | 0.13319 | 0.04703 |

## Coefficient stability

| scheme | model | parameter | mean | std | range | range/abs(mean) | sign consistent |
|---|---:|---|---:|---:|---:|---:|---:|
| LOHO_development | S0 | intercept | -0.102673 | 0.00485506 | 0.0126848 | 0.124 | True |
| LOHO_development | S0 | q1 | -0.00739847 | 0.00317873 | 0.00798729 | 1.08 | True |
| LOHO_development | S0 | q2 | 0.0060132 | 0.0250636 | 0.0696734 | 11.6 | False |
| LOHO_development | S1 | intercept | -0.0860181 | 0.00684185 | 0.0180319 | 0.21 | True |
| LOHO_development | S1 | q1 | -0.00950219 | 0.00638758 | 0.0161883 | 1.7 | True |
| LOHO_development | S1 | q2 | -0.0459402 | 0.0553994 | 0.14611 | 3.18 | False |
| LOHO_development | S1 | q1_sq | -0.0111531 | 0.000971534 | 0.00240498 | 0.216 | True |
| LOHO_development | S1 | q1_q2 | -0.0272795 | 0.030808 | 0.0871167 | 3.19 | False |
| LOHO_development | S1 | q2_sq | -0.119541 | 0.171166 | 0.467989 | 3.91 | False |
| LOPO_position_rank | S0 | intercept | -0.103307 | 0.00652965 | 0.0177841 | 0.172 | True |
| LOPO_position_rank | S0 | q1 | -0.00697654 | 0.00559611 | 0.0146482 | 2.1 | False |
| LOPO_position_rank | S0 | q2 | 0.00763503 | 0.00886199 | 0.025192 | 3.3 | False |
| LOPO_position_rank | S1 | intercept | -0.0832139 | 0.0100212 | 0.0305605 | 0.367 | True |
| LOPO_position_rank | S1 | q1 | -0.00189399 | 0.00992647 | 0.0248705 | 13.1 | False |
| LOPO_position_rank | S1 | q2 | -0.0183383 | 0.0195626 | 0.0528922 | 2.88 | False |
| LOPO_position_rank | S1 | q1_sq | -0.0108734 | 0.00908665 | 0.0267192 | 2.46 | False |
| LOPO_position_rank | S1 | q1_q2 | -0.0228611 | 0.0099314 | 0.0290459 | 1.27 | True |
| LOPO_position_rank | S1 | q2_sq | -0.126338 | 0.0562468 | 0.163478 | 1.29 | True |

## 判定依据

- S0 development LOHO 所有折的无 q2 overlap 外推折数：`2` / 4。
- S0 development LOPO 的 rank5 fold RMSE Δ：`-0.085980 mm`；rank5 bbox OOB rate：`100.00%`。
- S0 development folds 中 MAE 与 RMSE 同时改善的折数：`9` / `9`。
- S0 development folds 中所有 abs(Bias)/MAE/RMSE/P95/Max 均未恶化的折数：`9` / `9`。
- S0 development pooled RMSE Δ：`-0.076867 mm`。
- S0 development 系数出现 sign flip 的项：`LOHO_development:S0:q2, LOPO_position_rank:S0:q1, LOPO_position_rank:S0:q2`；这些系数不应被视为已冻结参数。
- S1 仅作同协议二次项对照，不因为 50 mm 结果选择或调参。

当前 q2 band 仍没有提供跨高度共同 support；即使 S0 在部分外推折上改善，也不能把 q-space extrapolation 当成 Surface-2C 的泛化证据。因此本轮建议 `YES`：若要继续，应优先补采 33/38/43/48 mm，并重新进行独立 grouped feasibility audit。

## 约束确认

- 未修改 C0/C1、ROI、Frozen q1/q2 定义。
- 未使用 50 mm 拟合、模型选择或参数调整。
- 未使用 spline、RF、MLP 或其他高自由度模型。
- 未把本轮结果包装为 production validation。

## 输出

- `surface2br_cv_metrics.csv`：逐 fold LOHO/LOPO/50 strict 指标。
- `surface2br_loho_metrics.csv`、`surface2br_lopo_metrics.csv`：独立 LOHO/LOPO 指标。
- `surface2br_model_comparison.csv`：按 CV scheme 的 condition-balanced 汇总。
- `surface2br_condition_predictions.csv`：逐 condition raw/predicted/corrected 结果及 support 标记。
- `surface2br_coefficients.csv`、`surface2br_coefficient_stability.csv`：逐 fold 系数和稳定性。
- `surface2br_raw_vs_corrected.png`：raw/S0/S1 对比图。
- `surface2br_summary.json`：机器可读结论、provenance 与判定字段。
