# Height-1 高度尺度补偿交叉验证

- `HEIGHT_LINEAR_STATUS=PASS`
- `SELECTED_MODEL=H1`
- `ALLOW_NEW_HELD_OUT_VALIDATION=YES`
- 本轮仅为诊断，不修改 C0/C1、Ground-3 G(S)、GUI 或生产配置。

## Provenance / reuse audit

- 输入：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_c1_gauge_blocks_20260819_ground4a\ground4a_condition_comparison.csv`，SHA-256 `f069020d7ff84b7189b0c386cd4c2a93bd55ac6753957e48d77b1966ecd47b68`。
- 复用 Ground-4A B `session_linear` 的正式 repeat2–5 condition mean，共 29 个成功 height×position condition。
- `obs_2mm/position5` 的缺失 condition 未补零、未删除；它不进入成功 condition 数值拟合。
- 本轮新增仅为 H0/H1/H2 的 condition-level 完整分组 CV；无随机 point split、无随机抽样、无高阶模型。

## 模型定义

- H0：`h_corr=h`，B `session_linear` raw height。
- H1：训练 condition 上拟合 `h_corr=k*h`。
- H2：训练 condition 上拟合 `h_corr=a*h+b`。
- 所有参数均只由训练组拟合；Leave-One-Height-Out 完整剔除一个高度的所有 position，Leave-One-Position-Out 完整剔除一个 position 的所有高度。
- 每个 condition 等权；condition 内使用 Ground-4A 已汇总的 repeat2–5 `measured_mean_mm`，不重新展开 repeat。

## Pooled out-of-fold metrics

| CV | model | n | raw Bias | raw MAE | raw RMSE | raw P95 | raw Max | corrected Bias | corrected MAE | corrected RMSE | corrected P95 | corrected Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Leave-One-Height-Out | H0 | 29 | -0.05390 | 0.05614 | 0.06954 | 0.12808 | 0.16929 | -0.05390 | 0.05614 | 0.06954 | 0.12808 | 0.16929 |
| Leave-One-Height-Out | H1 | 29 | -0.05390 | 0.05614 | 0.06954 | 0.12808 | 0.16929 | -0.00449 | 0.02566 | 0.03033 | 0.05118 | 0.05408 |
| Leave-One-Height-Out | H2 | 29 | -0.05390 | 0.05614 | 0.06954 | 0.12808 | 0.16929 | 0.00055 | 0.02354 | 0.02788 | 0.04717 | 0.05309 |
| Leave-One-Position-Out | H0 | 29 | -0.05390 | 0.05614 | 0.06954 | 0.12808 | 0.16929 | -0.05390 | 0.05614 | 0.06954 | 0.12808 | 0.16929 |
| Leave-One-Position-Out | H1 | 29 | -0.05390 | 0.05614 | 0.06954 | 0.12808 | 0.16929 | -0.00636 | 0.02678 | 0.03205 | 0.05777 | 0.06553 |
| Leave-One-Position-Out | H2 | 29 | -0.05390 | 0.05614 | 0.06954 | 0.12808 | 0.16929 | 0.00018 | 0.02656 | 0.03155 | 0.05432 | 0.07048 |

## Held-out group metrics

`height_linear_cv_metrics.csv` 保留每个 held-out group 的完整 Bias/MAE/RMSE/P95/Max；下面按模型逐行摘录 corrected 指标。H0 的 corrected 即 raw。

| CV | held-out group | model | n | Bias | MAE | RMSE | P95 | Max |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Leave-One-Height-Out | obs_1mm | H0 | 5 | -0.02146 | 0.03035 | 0.03484 | 0.05200 | 0.05509 |
| Leave-One-Height-Out | obs_1mm | H1 | 5 | -0.01752 | 0.02966 | 0.03266 | 0.04818 | 0.05128 |
| Leave-One-Height-Out | obs_1mm | H2 | 5 | -0.00553 | 0.02725 | 0.02810 | 0.03724 | 0.03928 |
| Leave-One-Height-Out | obs_2mm | H0 | 4 | -0.02687 | 0.02926 | 0.03504 | 0.05405 | 0.05778 |
| Leave-One-Height-Out | obs_2mm | H1 | 4 | -0.01895 | 0.02536 | 0.02948 | 0.04624 | 0.04998 |
| Leave-One-Height-Out | obs_2mm | H2 | 4 | -0.00763 | 0.01969 | 0.02382 | 0.03647 | 0.03865 |
| Leave-One-Height-Out | obs_6mm | H0 | 5 | -0.02182 | 0.02399 | 0.03317 | 0.05839 | 0.06427 |
| Leave-One-Height-Out | obs_6mm | H1 | 5 | 0.00236 | 0.02275 | 0.02519 | 0.03816 | 0.04027 |
| Leave-One-Height-Out | obs_6mm | H2 | 5 | 0.01649 | 0.02693 | 0.03000 | 0.04157 | 0.04383 |
| Leave-One-Height-Out | obs_10mm | H0 | 5 | -0.04798 | 0.04798 | 0.05181 | 0.07666 | 0.08382 |
| Leave-One-Height-Out | obs_10mm | H1 | 5 | -0.00842 | 0.01582 | 0.02135 | 0.03767 | 0.04440 |
| Leave-One-Height-Out | obs_10mm | H2 | 5 | -0.00018 | 0.01436 | 0.01961 | 0.03271 | 0.03614 |
| Leave-One-Height-Out | obs_20mm | H0 | 5 | -0.08808 | 0.08808 | 0.09241 | 0.12601 | 0.13127 |
| Leave-One-Height-Out | obs_20mm | H1 | 5 | -0.01072 | 0.02314 | 0.03005 | 0.04895 | 0.05408 |
| Leave-One-Height-Out | obs_20mm | H2 | 5 | -0.00976 | 0.02293 | 0.02970 | 0.04834 | 0.05309 |
| Leave-One-Height-Out | obs_30mm | H0 | 5 | -0.11181 | 0.11181 | 0.11630 | 0.16009 | 0.16929 |
| Leave-One-Height-Out | obs_30mm | H1 | 5 | 0.02343 | 0.03715 | 0.03977 | 0.05083 | 0.05101 |
| Leave-One-Height-Out | obs_30mm | H2 | 5 | 0.00828 | 0.02934 | 0.03316 | 0.04669 | 0.04941 |
| Leave-One-Position-Out | 1 | H0 | 6 | -0.02828 | 0.03293 | 0.04645 | 0.08491 | 0.09686 |
| Leave-One-Position-Out | 1 | H1 | 6 | 0.02115 | 0.02115 | 0.02334 | 0.03566 | 0.03688 |
| Leave-One-Position-Out | 1 | H2 | 6 | 0.03106 | 0.03106 | 0.03167 | 0.03736 | 0.03793 |
| Leave-One-Position-Out | 2 | H0 | 6 | -0.05972 | 0.05972 | 0.06801 | 0.11253 | 0.12329 |
| Leave-One-Position-Out | 2 | H1 | 6 | -0.01417 | 0.01417 | 0.01878 | 0.03315 | 0.03582 |
| Leave-One-Position-Out | 2 | H2 | 6 | -0.00876 | 0.00876 | 0.01225 | 0.02193 | 0.02446 |
| Leave-One-Position-Out | 3 | H0 | 6 | -0.04039 | 0.04474 | 0.05345 | 0.08196 | 0.08435 |
| Leave-One-Position-Out | 3 | H1 | 6 | 0.00848 | 0.02498 | 0.02934 | 0.04793 | 0.04950 |
| Leave-One-Position-Out | 3 | H2 | 6 | 0.01565 | 0.02736 | 0.02875 | 0.03613 | 0.03646 |
| Leave-One-Position-Out | 4 | H0 | 6 | -0.05158 | 0.05339 | 0.06341 | 0.10005 | 0.10498 |
| Leave-One-Position-Out | 4 | H1 | 6 | -0.00421 | 0.02713 | 0.03098 | 0.04801 | 0.05118 |
| Leave-One-Position-Out | 4 | H2 | 6 | 0.00148 | 0.02264 | 0.02787 | 0.03922 | 0.03923 |
| Leave-One-Position-Out | 5 | H0 | 5 | -0.09668 | 0.09668 | 0.10794 | 0.16169 | 0.16929 |
| Leave-One-Position-Out | 5 | H1 | 5 | -0.05041 | 0.05041 | 0.05192 | 0.06486 | 0.06553 |
| Leave-One-Position-Out | 5 | H2 | 5 | -0.04628 | 0.04628 | 0.04964 | 0.06871 | 0.07048 |

## Fold parameter stability

| CV | model | parameter | mean | std | min | max | range | relative range |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Leave-One-Height-Out | H0 | k | 1.0000000 | 0.0000000 | 1.0000000 | 1.0000000 | 0.0000000 | 0.0000000 |
| Leave-One-Height-Out | H1 | k | 1.0040776 | 0.0002065 | 1.0038851 | 1.0045248 | 0.0006397 | 0.0006371 |
| Leave-One-Height-Out | H2 | a | 1.0033597 | 0.0001366 | 1.0031813 | 1.0035751 | 0.0003938 | 0.0003925 |
| Leave-One-Height-Out | H2 | b | 0.0144402 | 0.0023238 | 0.0124713 | 0.0192919 | 0.0068206 | 0.4723344 |
| Leave-One-Position-Out | H0 | k | 1.0000000 | 0.0000000 | 1.0000000 | 1.0000000 | 0.0000000 | 0.0000000 |
| Leave-One-Position-Out | H1 | k | 1.0040342 | 0.0003003 | 1.0034784 | 1.0043088 | 0.0008304 | 0.0008270 |
| Leave-One-Position-Out | H2 | a | 1.0033304 | 0.0002226 | 1.0029290 | 1.0035382 | 0.0006092 | 0.0006071 |
| Leave-One-Position-Out | H2 | b | 0.0147289 | 0.0039099 | 0.0114398 | 0.0219208 | 0.0104810 | 0.7115909 |

## Model selection

- 选择 `H1`：H1 scale-only 在两个 CV 方向上每个 fold 的 MAE/RMSE/P95/Max 均优于 H0，且 k 的 relative range 为 0.0006371, 0.0008270，低于稳定性门槛 0.005。
- H2 affine 相对 H1 的 mean-fold MAE 额外改善：LHO-height 8.70%、LHO-position 1.26%；H2 并非每个 held-out fold 都优于 H1，因此按最简单稳定原则不选 H2。
- 这只是进入新量块 held-out validation 的候选资格，不是生产参数冻结，也不等同于新的工程验收。

## 输出

- `height_linear_cv_metrics.csv`：每个 height/position held-out fold 的 raw/corrected 指标。
- `height_linear_model_comparison.csv`：两个 CV 方案的 pooled out-of-fold 模型比较。
- `height_linear_fold_parameters.csv`：每个 fold 的 k/a/b。
- `height_error_before_after.png`：held-out MAE/RMSE 前后对比。
