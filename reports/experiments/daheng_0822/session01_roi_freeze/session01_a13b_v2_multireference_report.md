# Task A-13B-v2｜Session01 Manual ROI V2 + Session/Local-Baseline 多参考高度联合诊断

## Scope and provenance

本轮正式高度验证严格使用人工冻结 V2 geometry-only ROI。Session-reference 是唯一 authoritative branch；local-baseline 分支只作 diagnostic，不替换 Session Ground、不改模型、不拟合 correction。

- Frozen Steger cache: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_steger_centers.npz`；复用 600 帧，manifest `one_steger_per_frame=True`；本轮 Steger rerun=`False`。
- 每帧 reconstruction call: `1`；C0/C1/Session R/t 后的 points、q1/q2、C1 clamp 被六个 view 共享。
- V2 manual registry: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_roi_registry_manual_v2.json`；registry_ok=`True`；自动 QC 原值未改写：{'PASS': 20, 'UNCERTAIN': 10}。
- truth: `h10/h20/h30` 按 nominal `10/20/30 mm`；未发现并未猜测更精确 certified height。
- `height_shadow.csv` 仅作为 shadow-logging QC 读取，不进入正式高度、ROI 或 FOV 计算；whole-frame `v_median` 也未用于 position。

## Session PnP / Ground state

- PnP: valid=`True`, corners=`88`, reprojection RMSE=`0.2169 px`。
- Session Ground Reference: status=`VALID`, runtime status=`VALID`, slope=`0.0003`, intercept=`-0.1331 mm`, RMSE=`0.0535 mm`, valid S=`[-130.1993360105663, 121.3555919775798]`。
- support: point/inlier=`2414/2359`, source=`pnp_board_mask`。R/t 已从 `session_ground_calibration.json` 读取并用于本轮重建，不重新拟合。
- `height_shadow.csv` ground status QC counts=`{'inactive': 180}`。其中 `inactive` 是旧 shadow logger 没有接入本轮 runtime Session Ground leveled-point chain 的日志状态，不否定 JSON 中 Ground VALID；本轮没有因此重拟 Ground。

## Manual V2 review and measurement completeness

用户已声明 30/30 overlay geometry review 完成并 ACCEPT_ALL_V2。本报告将该声明作为人工冻结 provenance；自动 QC 的 UNCERTAIN 仍然保留，表示自动质量门的原始判断，不是自动 PASS。

- records=`600`; Session raw valid=`600`; local raw valid=`600`。
- baseline support counts: `{'BOTH_SIDES': 560, 'BEFORE_ONLY': 0, 'AFTER_ONLY': 40, 'NONE': 0}`。
- one-side local diagnostics: `40` frames; h30_p01 is explicitly retained as one-side/extrapolation when applicable.

## Height-ROI true spatial coverage

Position order is derived from the frozen height-ROI formal-point v median, not the whole-frame centerline median.

- `h10`: order=`p01,p02,p03,p04,p05,p06,p07,p08,p09,p10`; v=`106.0000..2846.0000`; max adjacent gap=`362.0000 px`; support counts `>2200/>2400/>2600=2/2/1`.
- `h20`: order=`p01,p02,p03,p04,p05,p06,p07,p08,p09,p10`; v=`78.5000..2870.0000`; max adjacent gap=`373.0000 px`; support counts `>2200/>2400/>2600=3/2/1`.
- `h30`: order=`p01,p02,p03,p04,p05,p06,p07,p08,p09,p10`; v=`62.0000..2874.0000`; max adjacent gap=`349.0000 px`; support counts `>2200/>2400/>2600=2/2/1`.

## Authoritative Session-reference pooled metrics

| model | n valid | Bias | MAE | RMSE | P95 | Max | repeatability std |
|---|---:|---:|---:|---:|---:|---:|---:|
|BASE|600|-0.1751|0.1751|0.1977|0.3703|0.4054|0.0920|
|H1|600|-0.0951|0.1000|0.1308|0.2907|0.3438|0.0899|
|HB2|600|-0.1081|0.1108|0.1401|0.3052|0.3357|0.0891|

## Session spatial metrics by height

| height | model | position bias range | position bias std | worst | worst P95 | worst Max |
|---|---|---:|---:|---:|---:|---:|
|h10|BASE|0.3474|0.0933|0.3543|0.3608|0.3826|
|h20|BASE|0.2961|0.0849|0.3692|0.3746|0.3772|
|h30|BASE|0.3119|0.0878|0.3999|0.4050|0.4054|
|h10|H1|0.3488|0.0937|0.3154|0.3219|0.3438|
|h20|H1|0.2973|0.0853|0.2900|0.2954|0.2981|
|h30|H1|0.3132|0.0882|0.2805|0.2857|0.2860|
|h10|HB2|0.3453|0.0934|0.3074|0.3139|0.3357|
|h20|HB2|0.2939|0.0849|0.3001|0.3055|0.3082|
|h30|HB2|0.3097|0.0878|0.3087|0.3138|0.3142|

HB2 vs H1 spatial spread: `YES`; edge-tail relation H1 better than HB2: `NO`. In the new Session01, HB2 has lower position-bias range/std at all three heights, and its v>2400/v>2600 P95/Max are lower than H1; the historical H1 edge-tail advantage is therefore not reproduced.

## Session vs local reference

local branch is same-frame paired diagnostic. `delta_reference_mm = h_local - h_session`; local H1/HB2 are marked diagnostic-only and do not authorize a baseline change.

- BASE: condition bias delta local-session median=`0.0540` mm; conditions with local P95/Max available=`30/30`.
- H1: condition bias delta local-session median=`0.0542` mm; conditions with local P95/Max available=`30/30`.
- HB2: condition bias delta local-session median=`0.0540` mm; conditions with local P95/Max available=`30/30`.

## Baseline before/after and attribution

- before/after consistency flag=`PARTIAL`; fraction |delta_before_after|≤0.1 mm=`0.7500`.
- local baseline significantly changes height=`YES`; local-vs-session raw delta median/mean abs=`0.0549` mm / `0.0700` mm.
- BASE attribution diagnostics: error_session vs local-ground residual Pearson=`0.7166` (p=`0.0000`), Spearman=`0.7079` (p=`0.0000`); `(error_session-error_local)` vs local-ground residual Pearson=`1.0000`, Spearman=`1.0000`.
- H1 attribution diagnostics: error_session vs local-ground residual Pearson=`0.6968` (p=`0.0000`), Spearman=`0.5669` (p=`0.0000`); `(error_session-error_local)` vs local-ground residual Pearson=`1.0000`, Spearman=`1.0000`.
- HB2 attribution diagnostics: error_session vs local-ground residual Pearson=`0.7197` (p=`0.0000`), Spearman=`0.6379` (p=`0.0000`); `(error_session-error_local)` vs local-ground residual Pearson=`1.0000`, Spearman=`1.0000`.

## Historical V1 false-failure audit

V1 condition metrics remain historical only and are invalidated as formal A-13B evidence because their ROI selection used the faulty V1 geometry. Key cases: `h10_p05, h10_p06, h20_p03, h30_p02, h30_p03, h30_p04`. V2 comparison is descriptive and does not use error to select ROI.

- h10_p05: V1 abs-bias range=`1.8971..1.9296` mm, V2=`0.0069..0.0378` mm; V1 height-std median/P95=`3.9275/3.9653` mm; V2=`0.0172/0.0205` mm; resolved=`True`.
- h10_p06: V1 abs-bias range=`2.0695..2.1014` mm, V2=`0.0825..0.1275` mm; V1 height-std median/P95=`3.9699/4.0360` mm; V2=`0.0230/0.0269` mm; resolved=`True`.
- h20_p03: V1 abs-bias range=`3.0263..3.0945` mm, V2=`0.1385..0.2183` mm; V1 height-std median/P95=`7.0188/7.0198` mm; V2=`0.0167/0.0215` mm; resolved=`True`.
- h30_p02: V1 abs-bias range=`4.3770..4.4799` mm, V2=`0.0357..0.1560` mm; V1 height-std median/P95=`10.5092/10.5141` mm; V2=`0.0203/0.0237` mm; resolved=`True`.
- h30_p03: V1 abs-bias range=`4.4292..4.5319` mm, V2=`0.0868..0.2070` mm; V1 height-std median/P95=`10.5274/10.5287` mm; V2=`0.0132/0.0170` mm; resolved=`True`.
- h30_p04: V1 abs-bias range=`3.3981..3.5049` mm, V2=`0.0507..0.1710` mm; V1 height-std median/P95=`9.4185/9.4190` mm; V2=`0.0177/0.0190` mm; resolved=`True`.

## Edge audit

Edge metrics are independently emitted for pooled, each height, each actual position/rank and v>2200/2400/2600. The key edge figures are in `session01_a13b_v2_edge_metrics.csv` and the two edge comparison plots.

### v_gt_2400

| branch | model | n valid | Bias | P95 | Max | >0.1 | >0.2 | Spearman residual-v |
|---|---|---:|---:|---:|---:|---:|---:|---:|
|session|BASE|120|-0.2438|0.4024|0.4054|0.8333|0.5000|-0.9735|
|session|H1|120|-0.1641|0.3161|0.3438|0.5000|0.5000|-0.7053|
|session|HB2|120|-0.1749|0.3124|0.3357|0.5000|0.5000|-0.8836|
|local_diag|BASE|120|-0.1476|0.2623|0.2655|0.6417|0.4833|-0.9656|
|local_diag|H1|120|-0.0675|0.1657|0.1992|0.5000|0.0000|-0.6018|
|local_diag|HB2|120|-0.0786|0.1712|0.1917|0.5000|0.0000|-0.9103|
### v_gt_2600

| branch | model | n valid | Bias | P95 | Max | >0.1 | >0.2 | Spearman residual-v |
|---|---|---:|---:|---:|---:|---:|---:|---:|
|session|BASE|60|-0.3745|0.4038|0.4054|1.0000|1.0000|-0.8602|
|session|H1|60|-0.2953|0.3190|0.3438|1.0000|1.0000|0.8829|
|session|HB2|60|-0.3054|0.3128|0.3357|1.0000|1.0000|-0.1392|
|local_diag|BASE|60|-0.2259|0.2628|0.2655|1.0000|0.9667|-0.7949|
|local_diag|H1|60|-0.1461|0.1703|0.1992|1.0000|0.0000|0.5002|
|local_diag|HB2|60|-0.1568|0.1725|0.1917|1.0000|0.0000|-0.3549|

## Final flags

```text
ROI_V2_HUMAN_REVIEW_COMPLETE=YES
ROI_V2_FROZEN=YES
A13B_V2_MEASUREMENT_COMPLETE=YES
A13B_V1_MM_FAILURE_CAUSED_BY_ROI=YES
V2_HEIGHT_STD_PATHOLOGY_RESOLVED=YES
SESSION_GROUND_LOCAL_RESIDUAL_SUPPORTED=YES
LOCAL_BASELINE_SIGNIFICANTLY_CHANGES_HEIGHT=YES
BASELINE_BEFORE_AFTER_CONSISTENT=PARTIAL
ONE_SIDE_BASELINE_DIAGNOSTIC_AVAILABLE=YES
SESSION_REFERENCE_FULL_FOV_ACCURACY=SUPPORTED
LOCAL_REFERENCE_FULL_FOV_ACCURACY=SUPPORTED
PREFERRED_DEPTH_BASELINE_SESSION=H1
HB2_POSITION_SPREAD_ADVANTAGE_VS_H1=YES
H1_EDGE_TAIL_ADVANTAGE_REPRODUCED=NO
TRUE_SPATIAL_RESIDUAL_AFTER_ROI_AND_GROUND_AUDIT=YES
SPATIAL_SOURCE_ATTRIBUTION_ALLOWED=YES
NEW_SPATIAL_CORRECTION_ALLOWED=NO
NEW_ACQUISITION_REQUIRED_NOW=NO
```

## Artifact boundaries

本轮复用：Frozen Steger cache、V2 candidates/overlays、frozen calibration/C1/H1/H-B2、Session PnP/Ground JSON、V1 historical CSV。新增计算：正式 V2 registry materialization、每帧一次 reconstruction、Session-reference/local diagnostic measurement、paired metrics、edge/attribution metrics、plots 和本报告。未做：Steger rerun、ROI 重选、C0/C1/Ground/H1/H-B2 refit、spatial correction、删 position、采 Session02。

Artifacts:

- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_roi_registry_manual_v2.json`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_v2_multireference_frames.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_v2_condition_metrics.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_v2_reference_comparison.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_v2_baseline_diagnostics.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_v2_edge_metrics.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_v1_vs_v2_comparison.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session_vs_local_height_error.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session_vs_local_position_bias.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\local_ground_residual_vs_v.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\height_error_vs_local_ground_residual.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\baseline_before_vs_after_residual.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\a13b_v1_vs_v2_height_std.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\a13b_v2_edge_v2400.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\a13b_v2_edge_v2600.png`
