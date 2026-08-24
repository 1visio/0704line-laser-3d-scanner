# Surface-2BR2 Baseline Decomposition

## 结论

`Q_DEPENDENT_SIGNAL=PARTIAL`  
`HEIGHT_GAP_ACQUISITION_STILL_JUSTIFIED=YES`

原 Surface-2B/2BR 结论保持不变：`Q2_GAP_FILLED=NO`、`SURFACE2C_ALLOWED=NO`。本轮只判断 q1/q2 相对于公共 residual offset 的新增诊断价值，不生成或冻结 correction 参数，也不是 production validation。

## 数据与协议

- development：1/2/6/10/20/30/36/40/46 mm，共 `44` 个 condition、`11160` 个 analysis points；2 mm 缺少 rank5，因此为 44 个而非 45 个 condition。
- 50 mm：`5` 个 strict held-out condition、`1100` 个 analysis points；未进入任何拟合、模型选择或阈值调整。
- 每个 height×position condition 等权；点级拟合权重为 `1 / condition_point_count`，评价先按 condition mean，再跨 condition 汇总。
- singleton LOHO：每个精确高度独立留出；新增探索性 leave-one-height-band-out：`low={1,2,6,10}`、`mid={20,30}`、`high={36,40,46}`。band 不是仓库既有冻结协议，已单独标明。
- q1/q2、Frozen C0/C1、manual ROI、session-linear ground proxy 全部复用；50 mm strict held-out 只做最终诊断。

## 公共 residual offset

| nominal height mm | condition count | raw Bias | raw MAE | raw RMSE | raw P95 | raw Max |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | -0.02142 | 0.03033 | 0.03482 | 0.05200 | 0.05516 |
| 2 | 4 | -0.02680 | 0.02930 | 0.03502 | 0.05399 | 0.05771 |
| 6 | 5 | -0.02205 | 0.02401 | 0.03322 | 0.05846 | 0.06435 |
| 10 | 5 | -0.04791 | 0.04791 | 0.05178 | 0.07674 | 0.08394 |
| 20 | 5 | -0.08811 | 0.08811 | 0.09242 | 0.12594 | 0.13118 |
| 30 | 5 | -0.11177 | 0.11177 | 0.11627 | 0.16008 | 0.16927 |
| 36 | 5 | -0.10377 | 0.10377 | 0.10855 | 0.14050 | 0.14548 |
| 40 | 5 | -0.09309 | 0.09309 | 0.09597 | 0.12812 | 0.13745 |
| 46 | 5 | -0.11795 | 0.11795 | 0.11861 | 0.13434 | 0.13567 |
| 50 | 5 | -0.10423 | 0.10423 | 0.10737 | 0.13150 | 0.13319 |

development raw Bias 的范围为 `-0.11795` 至 `-0.02142 mm`，range=`0.09653 mm`；50 mm strict raw Bias=`-0.10423 mm`。这用于判断约 `-0.1 mm` 的公共 offset，但 50 mm 数值不参与模型选择。

## Nested model

- B0：`F=a0`
- B1：`F=a0+a1*q1`
- B2：`F=a0+a2*q2`
- S0：`F=a0+a1*q1+a2*q2`
- corrected residual：`r_corrected=r-F`。

## 相对于 B0 的 pooled incremental comparison

| CV scheme | model | conditions | B0 RMSE | candidate RMSE | ΔRMSE | B0 P95 | candidate P95 | ΔP95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LOBO_height_band | B0 | 44 | 0.06544 | 0.06544 | 0.00000 | 0.10793 | 0.10793 | 0.00000 |
| LOBO_height_band | B1 | 44 | 0.06544 | 0.06516 | -0.00028 | 0.10793 | 0.10014 | -0.00779 |
| LOBO_height_band | B2 | 44 | 0.06544 | 0.05059 | -0.01485 | 0.10793 | 0.08396 | -0.02396 |
| LOBO_height_band | S0 | 44 | 0.06544 | 0.04649 | -0.01895 | 0.10793 | 0.07418 | -0.03374 |
| LOHO_height | B0 | 44 | 0.04967 | 0.04967 | 0.00000 | 0.08627 | 0.08627 | 0.00000 |
| LOHO_height | B1 | 44 | 0.04967 | 0.04853 | -0.00114 | 0.08627 | 0.08675 | 0.00048 |
| LOHO_height | B2 | 44 | 0.04967 | 0.02955 | -0.02012 | 0.08627 | 0.04682 | -0.03945 |
| LOHO_height | S0 | 44 | 0.04967 | 0.02723 | -0.02244 | 0.08627 | 0.04991 | -0.03637 |
| LOPO_position_rank | B0 | 44 | 0.04811 | 0.04811 | 0.00000 | 0.08524 | 0.08524 | 0.00000 |
| LOPO_position_rank | B1 | 44 | 0.04811 | 0.04869 | 0.00058 | 0.08524 | 0.08784 | 0.00260 |
| LOPO_position_rank | B2 | 44 | 0.04811 | 0.03139 | -0.01672 | 0.08524 | 0.04922 | -0.03603 |
| LOPO_position_rank | S0 | 44 | 0.04811 | 0.03109 | -0.01702 | 0.08524 | 0.05888 | -0.02636 |
| strict_50mm_validation | B0 | 5 | 0.04181 | 0.04181 | 0.00000 | 0.06019 | 0.06019 | 0.00000 |
| strict_50mm_validation | B1 | 5 | 0.04181 | 0.04238 | 0.00057 | 0.06019 | 0.06575 | 0.00555 |
| strict_50mm_validation | B2 | 5 | 0.04181 | 0.03914 | -0.00267 | 0.06019 | 0.06591 | 0.00572 |
| strict_50mm_validation | S0 | 5 | 0.04181 | 0.03821 | -0.00360 | 0.06019 | 0.06179 | 0.00160 |

负的 Δ 表示 q 项在公共 offset 之外带来改善。正式 development 判断只看 LOHO、LOPO 和 LOBO 三类；50 mm strict 行仅作为参考。

## Fold metrics / q-space support

| CV scheme | held-out group | model | B0 RMSE | candidate RMSE | ΔRMSE | B0 P95 | candidate P95 | ΔP95 | support |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| LOHO_height | height_1mm | B0 | 0.06263 | 0.06263 | 0.00000 | 0.09000 | 0.09000 | 0.00000 | BBOX_EXTRAPOLATION |
| LOHO_height | height_1mm | B1 | 0.06263 | 0.06067 | -0.00196 | 0.09000 | 0.08587 | -0.00413 | BBOX_EXTRAPOLATION |
| LOHO_height | height_1mm | B2 | 0.06263 | 0.02723 | -0.03540 | 0.09000 | 0.03889 | -0.05111 | BBOX_EXTRAPOLATION |
| LOHO_height | height_1mm | S0 | 0.06263 | 0.02333 | -0.03930 | 0.09000 | 0.03556 | -0.05443 | BBOX_EXTRAPOLATION |
| LOHO_height | height_2mm | B0 | 0.05390 | 0.05390 | 0.00000 | 0.07678 | 0.07678 | 0.00000 | IN_DOMAIN |
| LOHO_height | height_2mm | B1 | 0.05390 | 0.04964 | -0.00426 | 0.07678 | 0.06441 | -0.01237 | IN_DOMAIN |
| LOHO_height | height_2mm | B2 | 0.05390 | 0.02187 | -0.03203 | 0.07678 | 0.03034 | -0.04645 | IN_DOMAIN |
| LOHO_height | height_2mm | S0 | 0.05390 | 0.01941 | -0.03449 | 0.07678 | 0.02642 | -0.05036 | IN_DOMAIN |
| LOHO_height | height_6mm | B0 | 0.06087 | 0.06087 | 0.00000 | 0.08033 | 0.08033 | 0.00000 | BBOX_EXTRAPOLATION |
| LOHO_height | height_6mm | B1 | 0.06087 | 0.06123 | 0.00035 | 0.08033 | 0.08955 | 0.00922 | BBOX_EXTRAPOLATION |
| LOHO_height | height_6mm | B2 | 0.06087 | 0.03071 | -0.03016 | 0.08033 | 0.04421 | -0.03612 | BBOX_EXTRAPOLATION |
| LOHO_height | height_6mm | S0 | 0.06087 | 0.03064 | -0.03023 | 0.08033 | 0.05362 | -0.02671 | BBOX_EXTRAPOLATION |
| LOHO_height | height_10mm | B0 | 0.03289 | 0.03289 | 0.00000 | 0.04499 | 0.04499 | 0.00000 | IN_DOMAIN |
| LOHO_height | height_10mm | B1 | 0.03289 | 0.03262 | -0.00027 | 0.04499 | 0.04933 | 0.00435 | IN_DOMAIN |
| LOHO_height | height_10mm | B2 | 0.03289 | 0.01880 | -0.01409 | 0.04499 | 0.03277 | -0.01222 | IN_DOMAIN |
| LOHO_height | height_10mm | S0 | 0.03289 | 0.01496 | -0.01793 | 0.04499 | 0.02241 | -0.02257 | IN_DOMAIN |
| LOHO_height | height_20mm | B0 | 0.03372 | 0.03372 | 0.00000 | 0.05679 | 0.05679 | 0.00000 | IN_DOMAIN |
| LOHO_height | height_20mm | B1 | 0.03372 | 0.02564 | -0.00808 | 0.05679 | 0.04364 | -0.01315 | IN_DOMAIN |
| LOHO_height | height_20mm | B2 | 0.03372 | 0.03479 | 0.00107 | 0.05679 | 0.05868 | 0.00189 | IN_DOMAIN |
| LOHO_height | height_20mm | S0 | 0.03372 | 0.02760 | -0.00613 | 0.05679 | 0.04589 | -0.01089 | IN_DOMAIN |
| LOHO_height | height_30mm | B0 | 0.05576 | 0.05576 | 0.00000 | 0.09396 | 0.09396 | 0.00000 | HULL_EXTRAPOLATION |
| LOHO_height | height_30mm | B1 | 0.05576 | 0.05276 | -0.00300 | 0.09396 | 0.08207 | -0.01190 | HULL_EXTRAPOLATION |
| LOHO_height | height_30mm | B2 | 0.05576 | 0.04047 | -0.01529 | 0.09396 | 0.07245 | -0.02151 | HULL_EXTRAPOLATION |
| LOHO_height | height_30mm | S0 | 0.05576 | 0.03782 | -0.01794 | 0.09396 | 0.06028 | -0.03368 | HULL_EXTRAPOLATION |
| LOHO_height | height_36mm | B0 | 0.04853 | 0.04853 | 0.00000 | 0.07336 | 0.07336 | 0.00000 | IN_DOMAIN |
| LOHO_height | height_36mm | B1 | 0.04853 | 0.04578 | -0.00275 | 0.07336 | 0.06346 | -0.00990 | IN_DOMAIN |
| LOHO_height | height_36mm | B2 | 0.04853 | 0.03101 | -0.01752 | 0.07336 | 0.04249 | -0.03087 | IN_DOMAIN |
| LOHO_height | height_36mm | S0 | 0.04853 | 0.02616 | -0.02237 | 0.07336 | 0.03878 | -0.03458 | IN_DOMAIN |
| LOHO_height | height_40mm | B0 | 0.03390 | 0.03390 | 0.00000 | 0.05961 | 0.05961 | 0.00000 | IN_DOMAIN |
| LOHO_height | height_40mm | B1 | 0.03390 | 0.03383 | -0.00007 | 0.05961 | 0.05073 | -0.00888 | IN_DOMAIN |
| LOHO_height | height_40mm | B2 | 0.03390 | 0.03357 | -0.00033 | 0.05961 | 0.04487 | -0.01474 | IN_DOMAIN |
| LOHO_height | height_40mm | S0 | 0.03390 | 0.02926 | -0.00464 | 0.05961 | 0.04709 | -0.01252 | IN_DOMAIN |
| LOHO_height | height_46mm | B0 | 0.05409 | 0.05409 | 0.00000 | 0.06901 | 0.06901 | 0.00000 | BBOX_EXTRAPOLATION |
| LOHO_height | height_46mm | B1 | 0.05409 | 0.05985 | 0.00577 | 0.06901 | 0.08560 | 0.01659 | BBOX_EXTRAPOLATION |
| LOHO_height | height_46mm | B2 | 0.05409 | 0.01810 | -0.03599 | 0.06901 | 0.02565 | -0.04336 | BBOX_EXTRAPOLATION |
| LOHO_height | height_46mm | S0 | 0.05409 | 0.02802 | -0.02606 | 0.06901 | 0.03405 | -0.03496 | BBOX_EXTRAPOLATION |
| LOPO_position_rank | rank_1 | B0 | 0.05271 | 0.05271 | 0.00000 | 0.08398 | 0.08398 | 0.00000 | BBOX_EXTRAPOLATION |
| LOPO_position_rank | rank_1 | B1 | 0.05271 | 0.04662 | -0.00609 | 0.08398 | 0.06898 | -0.01500 | BBOX_EXTRAPOLATION |
| LOPO_position_rank | rank_1 | B2 | 0.05271 | 0.02683 | -0.02588 | 0.08398 | 0.03940 | -0.04458 | BBOX_EXTRAPOLATION |
| LOPO_position_rank | rank_1 | S0 | 0.05271 | 0.01576 | -0.03696 | 0.08398 | 0.02702 | -0.05696 | BBOX_EXTRAPOLATION |
| LOPO_position_rank | rank_2 | B0 | 0.03999 | 0.03999 | 0.00000 | 0.06123 | 0.06123 | 0.00000 | HULL_EXTRAPOLATION |
| LOPO_position_rank | rank_2 | B1 | 0.03999 | 0.04594 | 0.00595 | 0.06123 | 0.07621 | 0.01498 | HULL_EXTRAPOLATION |
| LOPO_position_rank | rank_2 | B2 | 0.03999 | 0.01814 | -0.02185 | 0.06123 | 0.03051 | -0.03072 | HULL_EXTRAPOLATION |
| LOPO_position_rank | rank_2 | S0 | 0.03999 | 0.02725 | -0.01275 | 0.06123 | 0.04221 | -0.01902 | HULL_EXTRAPOLATION |
| LOPO_position_rank | rank_3 | B0 | 0.04214 | 0.04214 | 0.00000 | 0.07986 | 0.07986 | 0.00000 | HULL_EXTRAPOLATION |
| LOPO_position_rank | rank_3 | B1 | 0.04214 | 0.04294 | 0.00080 | 0.07986 | 0.07960 | -0.00026 | HULL_EXTRAPOLATION |
| LOPO_position_rank | rank_3 | B2 | 0.04214 | 0.03175 | -0.01040 | 0.07986 | 0.04745 | -0.03240 | HULL_EXTRAPOLATION |
| LOPO_position_rank | rank_3 | S0 | 0.04214 | 0.03147 | -0.01068 | 0.07986 | 0.04515 | -0.03471 | HULL_EXTRAPOLATION |
| LOPO_position_rank | rank_4 | B0 | 0.03939 | 0.03939 | 0.00000 | 0.06657 | 0.06657 | 0.00000 | IN_DOMAIN |
| LOPO_position_rank | rank_4 | B1 | 0.03939 | 0.04556 | 0.00617 | 0.06657 | 0.08540 | 0.01883 | IN_DOMAIN |
| LOPO_position_rank | rank_4 | B2 | 0.03939 | 0.02681 | -0.01258 | 0.06657 | 0.04218 | -0.02439 | IN_DOMAIN |
| LOPO_position_rank | rank_4 | S0 | 0.03939 | 0.03271 | -0.00669 | 0.06657 | 0.05636 | -0.01022 | IN_DOMAIN |
| LOPO_position_rank | rank_5 | B0 | 0.06373 | 0.06373 | 0.00000 | 0.09829 | 0.09829 | 0.00000 | BBOX_EXTRAPOLATION |
| LOPO_position_rank | rank_5 | B1 | 0.06373 | 0.06174 | -0.00199 | 0.09829 | 0.09548 | -0.00281 | BBOX_EXTRAPOLATION |
| LOPO_position_rank | rank_5 | B2 | 0.06373 | 0.04793 | -0.01581 | 0.09829 | 0.07937 | -0.01892 | BBOX_EXTRAPOLATION |
| LOPO_position_rank | rank_5 | S0 | 0.06373 | 0.04341 | -0.02032 | 0.09829 | 0.07372 | -0.02457 | BBOX_EXTRAPOLATION |
| LOBO_height_band | low_1_2_6_10 | B0 | 0.07783 | 0.07783 | 0.00000 | 0.11255 | 0.11255 | 0.00000 | BBOX_EXTRAPOLATION |
| LOBO_height_band | low_1_2_6_10 | B1 | 0.07783 | 0.07695 | -0.00088 | 0.11255 | 0.11583 | 0.00327 | BBOX_EXTRAPOLATION |
| LOBO_height_band | low_1_2_6_10 | B2 | 0.07783 | 0.05418 | -0.02365 | 0.11255 | 0.08451 | -0.02804 | BBOX_EXTRAPOLATION |
| LOBO_height_band | low_1_2_6_10 | S0 | 0.07783 | 0.05178 | -0.02605 | 0.11255 | 0.08622 | -0.02633 | BBOX_EXTRAPOLATION |
| LOBO_height_band | mid_20_30 | B0 | 0.04914 | 0.04914 | 0.00000 | 0.08925 | 0.08925 | 0.00000 | HULL_EXTRAPOLATION |
| LOBO_height_band | mid_20_30 | B1 | 0.04914 | 0.04512 | -0.00402 | 0.08925 | 0.08054 | -0.00871 | HULL_EXTRAPOLATION |
| LOBO_height_band | mid_20_30 | B2 | 0.04914 | 0.04003 | -0.00911 | 0.08925 | 0.07678 | -0.01247 | HULL_EXTRAPOLATION |
| LOBO_height_band | mid_20_30 | S0 | 0.04914 | 0.03567 | -0.01347 | 0.08925 | 0.06356 | -0.02569 | HULL_EXTRAPOLATION |
| LOBO_height_band | high_36_40_46 | B0 | 0.05726 | 0.05726 | 0.00000 | 0.08595 | 0.08595 | 0.00000 | BBOX_EXTRAPOLATION |
| LOBO_height_band | high_36_40_46 | B1 | 0.05726 | 0.05999 | 0.00272 | 0.08595 | 0.09897 | 0.01302 | BBOX_EXTRAPOLATION |
| LOBO_height_band | high_36_40_46 | B2 | 0.05726 | 0.05217 | -0.00509 | 0.08595 | 0.07522 | -0.01073 | BBOX_EXTRAPOLATION |
| LOBO_height_band | high_36_40_46 | S0 | 0.05726 | 0.04578 | -0.01148 | 0.08595 | 0.07063 | -0.01531 | BBOX_EXTRAPOLATION |
| strict_50mm_validation | height_50mm_strict_heldout | B0 | 0.04181 | 0.04181 | 0.00000 | 0.06019 | 0.06019 | 0.00000 | BBOX_EXTRAPOLATION |
| strict_50mm_validation | height_50mm_strict_heldout | B1 | 0.04181 | 0.04238 | 0.00057 | 0.06019 | 0.06575 | 0.00555 | BBOX_EXTRAPOLATION |
| strict_50mm_validation | height_50mm_strict_heldout | B2 | 0.04181 | 0.03914 | -0.00267 | 0.06019 | 0.06591 | 0.00572 | BBOX_EXTRAPOLATION |
| strict_50mm_validation | height_50mm_strict_heldout | S0 | 0.04181 | 0.03821 | -0.00360 | 0.06019 | 0.06179 | 0.00160 | BBOX_EXTRAPOLATION |

`support` 按该 fold 训练样本的 q1/q2 bbox 与 2D convex hull 标记；越界预测只作诊断，不代表允许 extrapolation。

## Coefficient stability

| CV scheme | model | parameter | mean | std | range | range/abs(mean) | sign consistent |
|---|---:|---|---:|---:|---:|---:|---:|
| LOBO_height_band | B0 | intercept | -0.0732457 | 0.0213128 | 0.0490252 | 0.669 | True |
| LOBO_height_band | B1 | intercept | -0.0706628 | 0.0218249 | 0.051111 | 0.723 | True |
| LOBO_height_band | B1 | q1 | -0.0100511 | 0.00268329 | 0.00654759 | 0.651 | True |
| LOBO_height_band | B2 | intercept | -0.109283 | 0.0161363 | 0.0381676 | 0.349 | True |
| LOBO_height_band | B2 | q2 | 0.0507235 | 0.0245832 | 0.0602154 | 1.19 | True |
| LOBO_height_band | S0 | intercept | -0.105754 | 0.0135878 | 0.0323063 | 0.305 | True |
| LOBO_height_band | S0 | q1 | -0.00888629 | 0.00113128 | 0.00261058 | 0.294 | True |
| LOBO_height_band | S0 | q2 | 0.049698 | 0.0224073 | 0.0548353 | 1.1 | True |
| LOHO_height | B0 | intercept | -0.0712948 | 0.00473792 | 0.012376 | 0.174 | True |
| LOHO_height | B1 | intercept | -0.068967 | 0.0048241 | 0.0132299 | 0.192 | True |
| LOHO_height | B1 | q1 | -0.00970313 | 0.00114014 | 0.00410783 | 0.423 | True |
| LOHO_height | B2 | intercept | -0.100868 | 0.00259866 | 0.00949394 | 0.0941 | True |
| LOHO_height | B2 | q2 | 0.0533771 | 0.00227439 | 0.00767426 | 0.144 | True |
| LOHO_height | S0 | intercept | -0.0984853 | 0.00221717 | 0.00850418 | 0.0863 | True |
| LOHO_height | S0 | q1 | -0.00937609 | 0.000927043 | 0.00360231 | 0.384 | True |
| LOHO_height | S0 | q2 | 0.0531645 | 0.00208908 | 0.00729539 | 0.137 | True |
| LOPO_position_rank | B0 | intercept | -0.0713568 | 0.00503253 | 0.013776 | 0.193 | True |
| LOPO_position_rank | B1 | intercept | -0.0687861 | 0.00456937 | 0.0110458 | 0.161 | True |
| LOPO_position_rank | B1 | q1 | -0.00895688 | 0.0042448 | 0.0116144 | 1.3 | True |
| LOPO_position_rank | B2 | intercept | -0.100674 | 0.00486964 | 0.0141716 | 0.141 | True |
| LOPO_position_rank | B2 | q2 | 0.0531718 | 0.00253942 | 0.00675635 | 0.127 | True |
| LOPO_position_rank | S0 | intercept | -0.0978559 | 0.0049112 | 0.0117907 | 0.12 | True |
| LOPO_position_rank | S0 | q1 | -0.00903529 | 0.00339003 | 0.00927984 | 1.03 | True |
| LOPO_position_rank | S0 | q2 | 0.0529234 | 0.00201457 | 0.00548771 | 0.104 | True |

S0 相对于 B0 的正向 fold 数为 `17/17`；其中同时改善 RMSE 与 P95 的 fold 数为 `17`。B1 q1 的 pooled incremental RMSE 为 `-0.000276 mm`，B2 q2 为 `-0.017229 mm`，S0 为 `-0.019469 mm`，S0 相对于 B2 的额外增益为 `-0.002241 mm`。B1 在三个 development scheme 上是否均改善：`False`。

S0 fold 的 q-space 为 IN_DOMAIN 的数量为 `6/17`，其余 `11` 个 fold 存在 bbox 或 convex-hull extrapolation；IN_DOMAIN rate=`0.353`。因此，即使数值误差在 extrapolation fold 中下降，也不能把它等同于完整域内泛化。

## 判断

`Q_DEPENDENT_SIGNAL` 只根据 1–46 mm development grouped CV 决定：S0 需相对 B0 有跨 scheme 的 pooled 改善，并检查 fold 方向、P95、q-space support 与系数符号稳定性；若要判为 SUPPORTED，还要求 q1 单变量在三个 scheme 均改善且至少 75% 的 S0 fold 为 IN_DOMAIN。本轮 q2 的改善稳定，但 q1 单变量不满足该条件，且 q-space 支持率不足，因此判定不升级为完整 SUPPORTED。50 mm strict held-out 不参与该状态判断。

当前判定为 `PARTIAL`。补采建议为 `YES`；若继续补采，目标高度为 33/38/43/48 mm，以填补原 Surface-2B 的 q2 gaps。

## Provenance / constraints

- Surface-1A points SHA256：`0a325ea20c8b250ea94553cd6c9c78c198ce49f48a27925697a34eabf9fd4c9a`。
- Surface-2B samples SHA256：`f2bb04053c77806ede096ba5b15d05d76f2a0f1b7465e0a189adf7f1346687c7`。
- Frozen C0 SHA256：`113d3c1b8f92d5a734a2bf612b82a4bd59c0436a89664b5e565e7dd1034bab27`；Frozen C1 SHA256：`32717a3688905b237b0acbfb54e3290e112bc816c9be1133825d255196801ae3`。
- q definition match：`True`；manual ROI、C0/C1 与 session-linear proxy 均未修改。
- 未使用二次项、spline、RF、MLP；未使用 50 mm 训练或调参；未修改原 Surface-2B/2BR 结论。

## 输出

- `surface2br2_condition_table.csv`
- `surface2br2_height_bias.csv`
- `surface2br2_cv_metrics.csv`
- `surface2br2_incremental_comparison.csv`
- `surface2br2_coefficients.csv`
- `surface2br2_coefficient_stability.csv`
- `surface2br2_raw_vs_nested.png`
- `surface2br2_summary.json`
