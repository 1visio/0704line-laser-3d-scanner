# Session01 A-13B Frozen ROI 正式全 FOV 验证

本报告是 validation-only replay。没有重新运行 Steger、没有读取 `height_shadow.csv` 做正式高度/FOV 计算、没有重新拟合 C0/C1/Ground/H1/H-B2，也没有新增 correction。

## Final flags

```text
A13B_REPLAY_PROVENANCE_MATCH=YES
A13B_MEASUREMENT_COMPLETE=YES
BASE_FULL_FOV_VALID=SUPPORTED
H1_FULL_FOV_VALID=SUPPORTED
HB2_FULL_FOV_VALID=PARTIAL
EDGE_V2400_FAILURE_REPRODUCED=YES
EDGE_V2600_FAILURE_REPRODUCED=YES
EDGE_BASELINE_CLIPPING_EFFECT=WEAK
HB2_POSITION_SPREAD_ADVANTAGE_REPRODUCED=PARTIAL
HB2_EDGE_TAIL_PENALTY_REPRODUCED=YES
PREFERRED_DEPTH_BASELINE_AFTER_SESSION01=H1
SPATIAL_RESIDUAL_REPRODUCED_IN_NEW_SESSION=YES
SPATIAL_SOURCE_ATTRIBUTION_ALLOWED=YES
NEW_SPATIAL_CORRECTION_ALLOWED=NO
SECOND_SESSION_REQUIRED_BEFORE_MODEL_CHANGE=YES
```

## Provenance / reuse lock

- Dataset root: `D:\Docs\linelaserscan\calibration_tool\projects\daheng\outputs\0822\session01`; PNG source identity checked: `600/600` SHA256 matches.
- Frozen cache: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_steger_centers.npz`; frames `600`; concatenated centers `1672465`; `one_steger_per_frame=True`.
- Actual cache manifest field `reused_existing_cache=False`. A-13A report/cache-reuse display discrepancy is retained as a note; A-13B used the immutable manifest and NPZ, and did not rewrite either.
- Frozen manifest SHA256: `240c6ea407dbb3d46dd3287467cd8e9e1b92ca9a179fe22a94df2a4983eb2f90`; cache protocol SHA256: `240c6ea407dbb3d46dd3287467cd8e9e1b92ca9a179fe22a94df2a4983eb2f90`; match `YES`.
- Current formal config SHA256: `dced8a4f558f2b77ad8a1cfd8716c59de7e31edd19fb399f6bd8e3f1e581af11`; semantic lock values: depth `630–715 mm`, model margin `2 mm`, C1 enabled, measurement minimum baseline/height `20/20`.
- Frozen C0/C1/H1/H-B2 artifact hashes are recorded in `session01_a13b_provenance_audit.json`: `{"frozen_intrinsics": {"path": "D:\\Docs\\linelaserscan\\0704line-laser-3d-scanner\\laser_measurement_tool\\configs\\calibration_daheng_0811\\calibration_result.yaml", "sha256": "0d2b17c3e43aea548088e9cd54b70f3a46350a5c53ea9ee27a4705d85e8fc9b4"}, "frozen_c0_laser_model": {"path": "D:\\Docs\\linelaserscan\\0704line-laser-3d-scanner\\laser_measurement_tool\\configs\\calibration_daheng_0811\\quadratic_graph.yaml", "sha256": "113d3c1b8f92d5a734a2bf612b82a4bd59c0436a89664b5e565e7dd1034bab27"}, "frozen_reference_extrinsics": {"path": "D:\\Docs\\linelaserscan\\0704line-laser-3d-scanner\\laser_measurement_tool\\configs\\calibration_daheng_0811\\camera_ground_extrinsics.yaml", "sha256": "55eaa9cddb3e94f767d918f447393464a9cf9c183955e62b5f24384431962569"}, "frozen_c1": {"path": "D:\\Docs\\linelaserscan\\0704line-laser-3d-scanner\\laser_measurement_tool\\configs\\calibration_daheng_0811\\frozen_c1_4k.json", "sha256": "32717a3688905b237b0acbfb54e3290e112bc816c9be1133825d255196801ae3"}, "frozen_h1": {"path": "D:\\Docs\\linelaserscan\\0704line-laser-3d-scanner\\laser_measurement_tool\\configs\\calibration_daheng_0811\\stage_a_height_scale.json", "sha256": "3d41b5c3b4035f8568574f7a3599bb20a841267b6ebd34c617385027b6612811"}, "frozen_hb2": {"path": "D:\\Docs\\linelaserscan\\0704line-laser-3d-scanner\\laser_measurement_tool\\configs\\calibration_daheng_0811\\hb2_height_correction.json", "sha256": "203916caf8ec3ba3633ca7a7407a5de8f5c353a5be0729dc74a38eb2c04ddaac"}}`; none were modified or refit.
- Frozen registry: `30` entries; manual confirmed/frozen/geometry-only lock `YES`; edge baseline-clipped entries `6`.
- No whole-frame v median, truth height, residual, q1/q2 or correction output was used to select/alter any ROI. Formal coordinate is `height_roi_center_v`.

## Session PnP / Ground provenance

- `session_ground_calibration.json`: top `status=VALID`, `valid=True`; PnP `pnp_valid=YES`, corners `88`, reprojection RMSE `0.216905 px`.
- PnP reference R: `[[0.9989971277915087, 0.0003664569910963127, 0.0447728084174941], [5.421010862427523e-20, -0.9999665061143105, 0.008184537222028755], [0.044774308083050864, -0.00817632917710942, -0.9989636674959064]]`; t (mm): `[-31.89361181346621, -5.830200567232144, 711.6051137507399]`.
- Session R: `[[0.999011111566454, 0.00036355970827463415, 0.04445972099661178], [0.0, -0.9999665677003052, 0.008177009335376075], [0.04446120743702361, -0.008168923185423322, -0.9989777123275737]]`; t (mm): `[-31.67126115868773, -5.824962288392667, 711.6302871366686]`; PnP/session delta: `{"translation_mm": 0.2238324208079244, "rotation_deg": 0.01796240817613262}`.
- Session Ground Reference: status `VALID`, source `pnp_board_mask`, support `pnp_board_mask`, slope/intercept `0.000255503` / `-0.133124972`, RMSE `0.053502 mm`, valid S `[-130.1993360105663, 121.3555919775798]`, support points `2414/2359`.
- Formal replay chain: cached Frozen Steger full-sensor `(u,v)` → Frozen C0 → Frozen C1 → Session R/t → saved Session Ground Reference → GUI `measure_height_line` with `ground_correction_mode=session_reference`.
- `session_ground_calibration.json` 中 Ground VALID 与 `height_shadow.csv` 的 `ground_reference_status=inactive` 不矛盾：后者是独立 shadow-logging 路径的当时应用状态；本轮没有使用该文件，也没有因 inactive 重拟或修改 Ground。

## ROI / spatial coverage reuse

- 30 个 frozen geometry-only entries，位置坐标只使用 `height_roi_center_v`；全局 v 范围 `47.5–2897.5`，最大相邻 gap `380.0` px。
- v>2200 `True`；v>2400 `True`；v>2600 `True`。六个 edge baseline clipped entry 保留原 ROI，没有删除或重尺寸。
- h10/h20/h30 仅按 nominal truth 10/20/30 mm 计算 residual；未发现/未使用 certified height，因此结果不是标准件认证声明。

## Frame status audit

- Measurement rows: `600`; invalid status: `{"NONE": 600}`.
- q2 hard gate: `{"True": 260, "False": 340}`; H-B2 status: `{"applied": 260, "HB2_Q2_OOD": 340}`. H-B2 OOD rows are rejected, never clamped.
- C1 clamp: full cached centerline `{"MIXED": 600}`; height ROI formal points `{"IN_DOMAIN": 600}`.
- Session Ground: full centerline `{"PARTIAL_OUT_OF_VALID_S_DOMAIN": 600}`; formal baseline+height `{"PARTIAL_OUT_OF_VALID_S_DOMAIN": 180, "VALID": 420}`; height ROI `{"PARTIAL_OUT_OF_VALID_S_DOMAIN": 20, "VALID": 480, "OUT_OF_VALID_S_DOMAIN": 100}`. Ground-OOD points remain raw per the frozen `apply_to_points` contract and are explicitly counted; no extrapolation is performed.

## Condition-level metrics

|height|model|conditions|valid frames|Bias (mm)|MAE|RMSE|P95|Max|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|h10|BASE|10|200|-0.5854|0.5854|0.9628|2.1088|2.2121|
|h10|H1|10|200|-0.5474|0.5474|0.9427|2.0770|2.1807|
|h10|HB2|10|100|-0.2316|0.2316|0.4344|1.4620|1.6654|
|h20|BASE|10|200|-0.8417|0.8417|1.3580|3.0947|3.1022|
|h20|H1|10|200|-0.7644|0.7644|1.3150|3.0266|3.0341|
|h20|HB2|10|80|-0.1235|0.1235|0.1604|0.3030|0.3050|
|h30|BASE|10|200|-2.4156|2.4156|2.9181|4.5319|4.5362|
|h30|H1|10|200|-2.3044|2.3044|2.8305|4.4291|4.4335|
|h30|HB2|10|80|-0.8120|0.8120|1.5175|3.0688|3.1406|

## Height spatial metrics

|height|model|valid positions|Bias range|Bias std|worst |Bias||worst P95|worst Max|
|---|---:|---:|---:|---:|---:|---:|---:|
|h10|BASE|10|2.0275|0.7312|-2.1014 (p06)|2.2108 (p06)|2.2121 (p06)|
|h10|H1|10|2.0357|0.7341|-2.0695 (p06)|2.1794 (p06)|2.1807 (p06)|
|h10|HB2|5|0.5307|0.1921|-0.5601 (p07)|1.5743 (p07)|1.6654 (p07)|
|h20|BASE|10|2.9759|1.0657|-3.0945 (p03)|3.0989 (p03)|3.1022 (p03)|
|h20|H1|10|2.9880|1.0700|-3.0263 (p03)|3.0307 (p03)|3.0341 (p03)|
|h20|HB2|4|0.2479|0.1023|-0.2997 (p10)|0.3048 (p10)|0.3050 (p10)|
|h30|BASE|10|4.3780|1.6371|-4.5319 (p03)|4.5359 (p03)|4.5362 (p03)|
|h30|H1|10|4.3957|1.6437|-4.4292 (p03)|4.4331 (p03)|4.4335 (p03)|
|h30|HB2|4|2.9667|1.2817|-3.0320 (p10)|3.1081 (p10)|3.1406 (p10)|

## Edge audit

Edge regions use `height_roi_center_v`, not whole-frame v median. `edge_metrics.csv` includes pooled, per-height, and per-position scopes.

|region|scope|model|n valid|P95|Max|>|0.1|>|0.2|rho(v,residual)|worst condition|
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
|v_gt_2400|pooled|BASE|120|3.1224|3.2256|0.833|0.500|-0.978|h30_p10|
|v_gt_2400|pooled|H1|120|3.0140|3.1176|0.500|0.500|-0.805|h30_p10|
|v_gt_2400|pooled|HB2|120|3.0372|3.1406|0.500|0.500|-0.930|h30_p10|
|v_gt_2400|height:h10|BASE|40|0.3691|0.3843|0.500|0.500|-0.866|h10_p10|
|v_gt_2400|height:h10|H1|40|0.3303|0.3455|0.500|0.500|-0.866|h10_p10|
|v_gt_2400|height:h10|HB2|40|0.3222|0.3374|0.500|0.500|-0.866|h10_p10|
|v_gt_2400|height:h20|BASE|40|0.3736|0.3741|1.000|0.500|-0.866|h20_p10|
|v_gt_2400|height:h20|H1|40|0.2944|0.2949|0.500|0.500|-0.866|h20_p10|
|v_gt_2400|height:h20|HB2|40|0.3045|0.3050|0.500|0.500|-0.866|h20_p10|
|v_gt_2400|height:h30|BASE|40|3.1604|3.2256|1.000|0.500|-0.866|h30_p10|
|v_gt_2400|height:h30|H1|40|3.0521|3.1176|0.500|0.500|-0.866|h30_p10|
|v_gt_2400|height:h30|HB2|40|3.0753|3.1406|0.500|0.500|-0.866|h30_p10|
|v_gt_2600|pooled|BASE|60|3.1575|3.2256|1.000|1.000|-0.875|h30_p10|
|v_gt_2600|pooled|H1|60|3.0492|3.1176|1.000|1.000|-0.471|h30_p10|
|v_gt_2600|pooled|HB2|60|3.0724|3.1406|1.000|1.000|-0.471|h30_p10|
|v_gt_2600|height:h10|BASE|20|0.3769|0.3843|1.000|1.000|—|h10_p10|
|v_gt_2600|height:h10|H1|20|0.3381|0.3455|1.000|1.000|—|h10_p10|
|v_gt_2600|height:h10|HB2|20|0.3300|0.3374|1.000|1.000|—|h10_p10|
|v_gt_2600|height:h20|BASE|20|0.3739|0.3741|1.000|1.000|—|h20_p10|
|v_gt_2600|height:h20|H1|20|0.2948|0.2949|1.000|1.000|—|h20_p10|
|v_gt_2600|height:h20|HB2|20|0.3048|0.3050|1.000|1.000|—|h20_p10|
|v_gt_2600|height:h30|BASE|20|3.1932|3.2256|1.000|1.000|—|h30_p10|
|v_gt_2600|height:h30|H1|20|3.0850|3.1176|1.000|1.000|—|h30_p10|
|v_gt_2600|height:h30|HB2|20|3.1081|3.1406|1.000|1.000|—|h30_p10|

## Paired H1 vs H-B2

- Pairing is same processed frame. `abs_error_delta_hb2_minus_h1 < 0` means H-B2 is better; the condition rows also contain Bias/P95/Max differences and squared-error differences.

- Paired condition rows: `30`; condition mean |error| delta (pooled mean): `0.0111 mm`; squared-error delta: `0.0112 mm²`.
- H-B2 position spread: `PARTIAL`; detail `[{"height": "h10", "comparable": true, "common_position_count": 5, "hb2_full_height_coverage": false, "common_positions": ["p01", "p07", "p08", "p09", "p10"], "range_hb2_lower": true, "std_hb2_lower": true, "h1_range": 0.5309510450644405, "hb2_range": 0.5306522543026604, "h1_std": 0.19254681297118084, "hb2_std": 0.19207274879985783}, {"height": "h20", "comparable": true, "common_position_count": 4, "hb2_full_height_coverage": false, "common_positions": ["p07", "p08", "p09", "p10"], "range_hb2_lower": true, "std_hb2_lower": true, "h1_range": 0.2512544166239355, "hb2_range": 0.24793103434051977, "h1_std": 0.10396378297735019, "hb2_std": 0.10234738615734386}, {"height": "h30", "comparable": true, "common_position_count": 4, "hb2_full_height_coverage": false, "common_positions": ["p07", "p08", "p09", "p10"], "range_hb2_lower": true, "std_hb2_lower": true, "h1_range": 2.975214526248213, "hb2_range": 2.9667362793707888, "h1_std": 1.285305648929592, "hb2_std": 1.2817316280850661}]`.
- H-B2 edge tail: `YES`; detail `[{"region": "v_gt_2400", "height": "h10", "comparable": true, "hb2_p95_worse": false, "hb2_max_worse": false, "h1_p95": 0.3302800280977847, "hb2_p95": 0.3222454920391512, "h1_max": 0.3454801893307913, "hb2_max": 0.33739302509481206}, {"region": "v_gt_2400", "height": "h20", "comparable": true, "hb2_p95_worse": true, "hb2_max_worse": true, "h1_p95": 0.2944224353015882, "hb2_p95": 0.30452238965452966, "h1_max": 0.29491455704084757, "hb2_max": 0.3050035295931366}, {"region": "v_gt_2400", "height": "h30", "comparable": true, "hb2_p95_worse": true, "hb2_max_worse": true, "h1_p95": 3.0521165134911263, "hb2_p95": 3.075276672925374, "h1_max": 3.1176059783544368, "hb2_max": 3.1406484070718683}, {"region": "v_gt_2600", "height": "h10", "comparable": true, "hb2_p95_worse": false, "hb2_max_worse": false, "h1_p95": 0.3380932343491804, "hb2_p95": 0.3300295723658667, "h1_max": 0.3454801893307913, "hb2_max": 0.33739302509481206}, {"region": "v_gt_2600", "height": "h20", "comparable": true, "hb2_p95_worse": true, "hb2_max_worse": true, "h1_p95": 0.29475864460024753, "hb2_p95": 0.3048426573760574, "h1_max": 0.29491455704084757, "hb2_max": 0.3050035295931366}, {"region": "v_gt_2600", "height": "h30", "comparable": true, "hb2_p95_worse": true, "hb2_max_worse": true, "h1_p95": 3.085046301103885, "hb2_p95": 3.1081470343882343, "h1_max": 3.1176059783544368, "hb2_max": 3.1406484070718683}]`.
- Historical A-11 relation is therefore judged from the frozen same-frame results: H-B2 spread advantage and H1 edge-tail advantage are not assumed; the flags above state whether each relation reappears.

## Baseline clipping audit

Clipping is an A-13A frozen geometry property, not a reason to delete or resize an ROI.

|group|scope|model|n|Bias|P95|Max|
|---|---|---:|---:|---:|---:|---:|
|clipped|pooled|BASE|120|-1.6157|3.3293|3.3342|
|clipped|pooled|H1|120|-1.5416|3.2218|3.2266|
|clipped|pooled|HB2|80|-0.9582|3.0688|3.1406|
|normal|pooled|BASE|480|-1.1972|4.4818|4.5362|
|normal|pooled|H1|480|-1.1213|4.3789|4.4335|
|normal|pooled|HB2|180|-0.1186|0.0916|1.6654|

## Artifacts

- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_frame_measurements.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_condition_metrics.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_height_spatial_metrics.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_edge_metrics.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_clipped_vs_normal_metrics.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_paired_h1_hb2.csv`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_position_bias_by_height.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_residual_vs_v.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_h1_vs_hb2_paired_delta.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_edge_v2400.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_edge_v2600.png`
- `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_a13b_clipped_baseline_audit.png`

## Interpretation boundary

`SPATIAL_SOURCE_ATTRIBUTION_ALLOWED` 仅表示可以把新 session 中的 residual-v / position spread 作为 frozen stack 的空间残差现象进行诊断归因；不表示已经允许拟合或部署 spatial correction。`NEW_SPATIAL_CORRECTION_ALLOWED=NO`，且本轮没有删 position、改 ROI、改 Ground 或改 H1/H-B2。

`SECOND_SESSION_REQUIRED_BEFORE_MODEL_CHANGE=YES`：Session01 可完成跨 session validation，但在模型变更或新 spatial correction 前仍需另一独立 session。
