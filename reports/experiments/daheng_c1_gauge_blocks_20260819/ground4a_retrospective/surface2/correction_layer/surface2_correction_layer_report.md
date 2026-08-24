# Surface correction layer replay

## Decision

SELECTED_CORRECTION_LAYER=HEIGHT

LAMBDA_LAYER_PHYSICAL_VALIDITY=NOT_SUPPORTED

DEVELOPMENT_LAMBDA_LAYER_PHYSICAL_VALIDITY=PARTIAL

Q2_ONLY_CORRECTION_CANDIDATE=YES

MORE_DATA_REQUIRED_BEFORE_NEXT_ANALYSIS=YES

The historical conclusion is preserved: SELECTED_SURFACE_MODEL=B2,
Q1_RETAINED=NO, Q2_GAP_FILLED=NO,
SURFACE2C_ALLOWED=NO.  This report is
diagnostic and is not production validation.

## Protocol and provenance

- H-B2 is a0+a2*q2 applied to the final height residual.
- L-B2 is b0+b2*q2 added to lambda_C1 before camera-point construction.
- L-B2 applies the same lambda change to repeat1 ground points and formal points.
  Each fold refits the session-linear ground proxy from the corrected repeat1
  baseline before evaluating formal residuals.
- Development conditions are condition-balanced; there is no random point split.
- LOHO, LOPO and LOBO are selection folds.  50 mm is a strict diagnostic only
  and is not used for fitting, selection, or threshold adjustment.
- Frozen C0 SHA256: 113d3c1b8f92d5a734a2bf612b82a4bd59c0436a89664b5e565e7dd1034bab27
- Frozen C1 SHA256: 32717a3688905b237b0acbfb54e3290e112bc816c9be1133825d255196801ae3
- Config SHA256: d71dd6e9ac5919c0a6ef220ed40a8f3b517c31bfc98fcbb6a6ff6a8cbcd9d47c
- q2 is the existing Frozen-C0 intrinsic coordinate; no q redefinition.
- Maximum raw replay difference against the existing formal residual column:
  0.00000000 mm.

## Grouped metrics

These are metrics over condition means, so each height x position condition has
equal weight.

| scheme | layer | conditions | Bias | MAE | RMSE | P95 | Max | worst condition |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LOHO_height | RAW | 44 | -0.07131 | 0.07277 | 0.08468 | 0.13718 | 0.16927 | 0.16927 |
| LOHO_height | H-B2 | 44 | -0.00201 | 0.02361 | 0.02955 | 0.04865 | 0.08528 | 0.08528 |
| LOHO_height | L-B2 | 44 | -0.04988 | 0.05175 | 0.06179 | 0.10923 | 0.13666 | 0.13666 |
| LOPO_position_rank | RAW | 49 | -0.07467 | 0.07598 | 0.08726 | 0.13674 | 0.16927 | 0.16927 |
| LOPO_position_rank | H-B2 | 49 | 0.00021 | 0.02595 | 0.03226 | 0.06378 | 0.08921 | 0.08921 |
| LOPO_position_rank | L-B2 | 49 | -0.05680 | 0.05867 | 0.07290 | 0.13494 | 0.16927 | 0.16927 |
| LOBO_height_band | RAW | 44 | -0.07131 | 0.07277 | 0.08468 | 0.13718 | 0.16927 | 0.16927 |
| LOBO_height_band | H-B2 | 44 | 0.01766 | 0.03840 | 0.04654 | 0.08971 | 0.09463 | 0.09463 |
| LOBO_height_band | L-B2 | 44 | -0.04969 | 0.05156 | 0.06010 | 0.10325 | 0.12747 | 0.12747 |
| strict_50mm_validation | RAW | 5 | -0.10423 | 0.10423 | 0.10737 | 0.13150 | 0.13319 | 0.13319 |
| strict_50mm_validation | H-B2 | 5 | 0.02967 | 0.03003 | 0.03914 | 0.06591 | 0.07156 | 0.07156 |
| strict_50mm_validation | L-B2 | 5 | NA | NA | NA | NA | NA | NA |

## Support stratification

Support is inherited from the frozen Surface-2BR2 B2 q-space protocol.  It is
reported separately so an extrapolation improvement is not treated as
in-domain generalization.

| scheme | support state | layer | conditions | RMSE | P95 | worst condition |
|---|---|---|---:|---:|---:|---:|
| LOBO_height_band | IN_DOMAIN | H-B2 | 9 | 0.03319 | 0.05964 | 0.06947 |
| LOBO_height_band | HULL_EXTRAPOLATION | H-B2 | 1 | 0.08826 | 0.08826 | 0.08826 |
| LOBO_height_band | BBOX_EXTRAPOLATION | H-B2 | 34 | 0.04778 | 0.09005 | 0.09463 |
| LOBO_height_band | IN_DOMAIN | L-B2 | 9 | 0.06420 | 0.09606 | 0.10376 |
| LOBO_height_band | HULL_EXTRAPOLATION | L-B2 | 1 | 0.12747 | 0.12747 | 0.12747 |
| LOBO_height_band | BBOX_EXTRAPOLATION | L-B2 | 34 | 0.05573 | 0.09809 | 0.11214 |
| LOHO_height | IN_DOMAIN | H-B2 | 32 | 0.02838 | 0.04818 | 0.06602 |
| LOHO_height | HULL_EXTRAPOLATION | H-B2 | 3 | 0.05106 | 0.07909 | 0.08528 |
| LOHO_height | BBOX_EXTRAPOLATION | H-B2 | 9 | 0.02313 | 0.04159 | 0.04388 |
| LOHO_height | IN_DOMAIN | L-B2 | 32 | 0.05401 | 0.09699 | 0.10849 |
| LOHO_height | HULL_EXTRAPOLATION | L-B2 | 3 | 0.08712 | 0.12842 | 0.13666 |
| LOHO_height | BBOX_EXTRAPOLATION | L-B2 | 9 | 0.07591 | 0.11277 | 0.11505 |
| LOPO_position_rank | IN_DOMAIN | H-B2 | 27 | 0.02851 | 0.04419 | 0.07082 |
| LOPO_position_rank | HULL_EXTRAPOLATION | H-B2 | 3 | 0.01727 | 0.02058 | 0.02112 |
| LOPO_position_rank | BBOX_EXTRAPOLATION | H-B2 | 19 | 0.03850 | 0.07224 | 0.08921 |
| LOPO_position_rank | IN_DOMAIN | L-B2 | 27 | 0.06549 | 0.11476 | 0.11968 |
| LOPO_position_rank | HULL_EXTRAPOLATION | L-B2 | 3 | 0.06193 | 0.07868 | 0.08091 |
| LOPO_position_rank | BBOX_EXTRAPOLATION | L-B2 | 19 | 0.08369 | 0.14786 | 0.16927 |

## L-B2 relative to H-B2

Negative values mean L-B2 is smaller.

| scheme | delta RMSE L-H | delta P95 L-H | delta worst L-H | L not worse |
|---|---:|---:|---:|---|
| LOBO_height_band | 0.01356 | 0.01355 | 0.03283 | False |
| LOHO_height | 0.03224 | 0.06058 | 0.05137 | False |
| LOPO_position_rank | 0.04064 | 0.07116 | 0.08007 | False |
| strict_50mm_validation | NA | NA | NA | False |

## Lambda physical and numerical audit

- New invalid final points across development plus strict-50 diagnostic folds: 1100
- Development-only new invalid final points: 0
- Development-only physical status: PARTIAL
- C1 clamp-state changes: 0
- Maximum absolute delta lambda: 34.75828 mm
- Maximum P95 absolute delta lambda: 34.75828 mm
- Maximum absolute induced delta Zg: 34.79810 mm
- Maximum lambda coefficient relative fold range: 3.977
- Physical thresholds used: abs delta lambda <= 2 mm, P95 abs delta lambda <= 1 mm,
  abs induced delta Zg <= 2 mm, coefficient relative range <= 1.
- C1 clamp is evaluated before the layer correction and is therefore expected
  to remain unchanged.  Any new final-depth invalid point would fail the
  physical validity check.
- The strict-50 invalid count contributes only to the diagnostic
  LAMBDA_LAYER_PHYSICAL_VALIDITY flag; it is not used to fit either layer,
  choose a fold, or adjust a threshold.  Development already fails the
  lambda physical-magnitude limits independently.

## Coefficient stability

| layer | parameter | mean | std | range | relative range | sign consistent |
|---|---|---:|---:|---:|---:|---|
| H-B2 | a0 | -0.094980 | 0.003693 | 0.014207 | 0.150 | True |
| H-B2 | a2 | 0.045120 | 0.007857 | 0.036301 | 0.805 | True |
| L-B2 | b0 | -28.388777 | 7.139347 | 30.964194 | 1.091 | True |
| L-B2 | b2 | 0.008079 | 0.007856 | 0.032130 | 3.977 | False |

## Interpretation

The layer decision is based on development grouped CV only.  L-B2 must be no
worse than H-B2 simultaneously in RMSE, P95 and worst-condition error for
LOHO, LOPO and LOBO, and must pass the independent physical audit.  Lambda is
not preferred merely because it is more physical.  The strict 50 mm rows are
shown in the table only as an unselected diagnostic.

No C0/C1, ROI, q2, Steger, GUI, Ground G(S), H1, or online production
configuration was modified.  Existing Q2_GAP_FILLED=NO and
SURFACE2C_ALLOWED=NO remain historical conclusions.
