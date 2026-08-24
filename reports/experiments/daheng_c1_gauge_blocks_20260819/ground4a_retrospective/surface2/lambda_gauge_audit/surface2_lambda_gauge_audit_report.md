# Surface lambda gauge audit

## Decision

LAMBDA_INTERCEPT_IDENTIFIABILITY=SUPPORTED

ANCHORED_LAMBDA_LAYER_VALIDITY=NOT_SUPPORTED

FINAL_CORRECTION_LAYER=HEIGHT

STOP_LAMBDA_ROUTE=YES

The historical conclusions remain unchanged:
SELECTED_SURFACE_MODEL=B2, Q1_RETAINED=NO, Q2_GAP_FILLED=NO,
SURFACE2C_ALLOWED=NO. This is a diagnostic audit, not production validation.

## Protocol and provenance

- L0-B2 is delta_lambda=b2*q2 with b0 fixed exactly to zero.
- The same correction is applied to repeat1 ground points and repeat2-5 formal
  points. Every fold refits the session-linear ground proxy after correcting
  repeat1, before evaluating formal residuals.
- Current H-B2 and free L-B2 comparison rows are a fresh strict-50-excluded
  replay under the same fold definitions as L0-B2. The previous H-B2/L-B2
  result files are preserved as frozen historical artifacts and are included
  in the comparison CSV without modification.
- LOHO, LOPO and LOBO are development grouped CV. No random point split is
  used. 50 mm is evaluated only in the separate strict diagnostic fold and is
  not used for development fitting, selection, or threshold adjustment.
- Frozen C0 SHA256: 113d3c1b8f92d5a734a2bf612b82a4bd59c0436a89664b5e565e7dd1034bab27
- Frozen C1 SHA256: 32717a3688905b237b0acbfb54e3290e112bc816c9be1133825d255196801ae3
- Config SHA256: f24b23f95f9cf3fe55afb07e369c41d916a7e266aaa24492f80fada716272e78
- q2 remains the Frozen-C0 intrinsic coordinate. C0, C1, ROI, Steger and the
  ground protocol were not changed.
- Maximum raw residual replay difference: 0.0000000000 mm.

## Provenance audit of the previous artifact

The previous result files were not overwritten. Their hashes are recorded in
the summary JSON. The previous fold audit records development train counts
[30, 34, 39, 40, 44, 45]; this indicates that
the old development folds included the 50 mm conditions. Because the present
request requires strict 50 mm held-out status, this report uses a new
50-excluded H/free replay for the direct comparison. The old H/free numbers
remain available under source=previous_frozen_artifact.

The previous artifact recorded config SHA256
d71dd6e9ac5919c0a6ef220ed40a8f3b517c31bfc98fcbb6a6ff6a8cbcd9d47c, while this replay used
f24b23f95f9cf3fe55afb07e369c41d916a7e266aaa24492f80fada716272e78; config_sha256_matches_previous_artifact=
False. C0 and C1 hashes
remain explicitly recorded above. The current strict-dev-only replay is therefore
the comparison authority for this audit; the previous H/free rows are retained
historical references only.

## Grouped metrics: current strict-50-excluded replay

| scheme | layer | conditions | Bias | MAE | RMSE | P95 | Max | worst condition |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LOHO_height | RAW | 44 | -0.07131 | 0.07277 | 0.08468 | 0.13718 | 0.16927 | 0.16927 |
| LOHO_height | H-B2 | 44 | 0.00111 | 0.02405 | 0.02955 | 0.04682 | 0.08107 | 0.08107 |
| LOHO_height | L-B2 | 44 | -0.05041 | 0.05240 | 0.06234 | 0.11282 | 0.14657 | 0.14657 |
| LOHO_height | L0-B2 | 44 | -0.00769 | 0.02768 | 0.03391 | 0.05496 | 0.08665 | 0.08665 |
| LOPO_position_rank | RAW | 44 | -0.07131 | 0.07277 | 0.08468 | 0.13718 | 0.16927 | 0.16927 |
| LOPO_position_rank | H-B2 | 44 | 0.00021 | 0.02578 | 0.03139 | 0.04922 | 0.08525 | 0.08525 |
| LOPO_position_rank | L-B2 | 44 | -0.06220 | 0.06389 | 0.07600 | 0.13651 | 0.16927 | 0.16927 |
| LOPO_position_rank | L0-B2 | 44 | -0.00866 | 0.02757 | 0.03418 | 0.05677 | 0.08994 | 0.08994 |
| LOBO_height_band | RAW | 44 | -0.07131 | 0.07277 | 0.08468 | 0.13718 | 0.16927 | 0.16927 |
| LOBO_height_band | H-B2 | 44 | 0.03001 | 0.04332 | 0.05059 | 0.08396 | 0.08736 | 0.08736 |
| LOBO_height_band | L-B2 | 44 | -0.04674 | 0.04909 | 0.05894 | 0.10671 | 0.13534 | 0.13534 |
| LOBO_height_band | L0-B2 | 44 | 0.00539 | 0.03837 | 0.04761 | 0.08657 | 0.09048 | 0.09048 |
| strict_50mm_validation | RAW | 5 | -0.10423 | 0.10423 | 0.10737 | 0.13150 | 0.13319 | 0.13319 |
| strict_50mm_validation | H-B2 | 5 | 0.02967 | 0.03003 | 0.03914 | 0.06591 | 0.07156 | 0.07156 |
| strict_50mm_validation | L-B2 | 5 | NA | NA | NA | NA | NA | NA |
| strict_50mm_validation | L0-B2 | 5 | 0.04059 | 0.04059 | 0.04811 | 0.07729 | 0.08258 | 0.08258 |

## Anchored L0 relative to H-B2

Negative deltas mean anchored L0-B2 is smaller.

| scheme | heldout group | delta RMSE L0-H | delta P95 L0-H | delta worst L0-H | delta RMSE L0-free-L | L0 not worse in all three |
|---|---|---:|---:|---:|---:|---|
| LOBO_height_band | ALL_FOLDS | -0.00298 | 0.00261 | 0.00312 | -0.01133 | False |
| LOHO_height | ALL_FOLDS | 0.00436 | 0.00814 | 0.00557 | -0.02843 | False |
| LOPO_position_rank | ALL_FOLDS | 0.00279 | 0.00756 | 0.00470 | -0.04182 | False |
| strict_50mm_validation | ALL_FOLDS | 0.00897 | 0.01138 | 0.01103 | NA | False |

## Gauge interpretation

- Previous free L-B2 b0 mean/std/range: -28.388777 /
  7.139347 / 30.964194 mm.
- Previous free L-B2 b2 mean/std/range: 0.00807941 /
  0.00785610 / 0.03212964.
- Previous free-L maximum development absolute delta lambda:
  30.962645 mm; induced
  absolute delta Zg: 30.990993 mm.
- Previous free-L design condition number maximum:
  31932.80.
- Free b0 is consistent with a common-mode/gauge direction: its magnitude is tens of millimetres, the design is ill-conditioned, and free b2 changes sign across development folds.
- Anchored b2 relative fold range:
  0.472107; sign consistent:
  True.

The evidence therefore classifies the free intercept as a common-mode/gauge
direction only when the anchored coefficient and physical audit are considered
together; it does not make a physically large lambda correction acceptable.

## Anchored lambda physical and numerical audit

- Development status: SUPPORTED
- All-fold status including strict diagnostic: SUPPORTED
- Development new formal invalid points: 0
- Development new baseline invalid points: 0
- All-fold new invalid points: 0
- C1 clamp state changes: 0
- Development max absolute delta lambda: 0.145419 mm
- Development max P95 absolute delta lambda: 0.144845 mm
- Development max absolute induced delta Zg: 0.144983 mm
- All-fold max absolute delta lambda: 0.145419 mm
- All-fold max absolute induced delta Zg: 0.144983 mm
- Maximum absolute corrected-proxy slope change:
  0.00006497 mm/mm
- Maximum absolute corrected-proxy intercept change:
  0.143148 mm
- Maximum corrected-proxy RMSE:
  0.032356 mm
- Thresholds: max absolute delta lambda <= 2 mm, P95 absolute delta lambda
  <= 1 mm, absolute induced delta Zg <= 2 mm, b2 relative range <= 1.

## Coefficient stability

| source | layer | parameter | mean | std | range | relative range | sign consistent |
|---|---|---|---:|---:|---:|---:|---|
| previous_frozen_artifact | L-B2 | b0 | -28.3887768 | 7.1393470 | 30.9641943 | 1.0907 | True |
| previous_frozen_artifact | L-B2 | b2 | 0.0080794 | 0.0078561 | 0.0321296 | 3.9767 | False |
| strict_dev_only_replay | L-B2 | b0 | -32.8630565 | 8.8195134 | 45.1113706 | 1.3727 | True |
| strict_dev_only_replay | L-B2 | b2 | -0.0008466 | 0.0049885 | 0.0198067 | 23.3945 | False |
| strict_dev_only_replay | L0-B2 | b0 | 0.0000000 | 0.0000000 | 0.0000000 | 0.0000 | True |
| strict_dev_only_replay | L0-B2 | b2 | 0.0708597 | 0.0071187 | 0.0334534 | 0.4721 | True |
| anchored_l0_replay | L0-B2 | b0 | 0.0000000 | 0.0000000 | 0.0000000 | 0.0000 | True |
| anchored_l0_replay | L0-B2 | b2 | 0.0708597 | 0.0071187 | 0.0334534 | 0.4721 | True |

## Final interpretation

The anchored model is accepted as a lambda-layer candidate only if it is
non-inferior to H-B2 in RMSE, P95 and worst-condition error for every
development LOHO/LOPO/LOBO pooled fold and passes the independent physical
audit. A large free b0 by itself is not evidence to deploy lambda correction.
If the anchored model fails either criterion, lambda complexity is stopped and
the frozen height-layer route remains the final candidate. The 50 mm result
shown in the CSV and plot is strict diagnostic only.
