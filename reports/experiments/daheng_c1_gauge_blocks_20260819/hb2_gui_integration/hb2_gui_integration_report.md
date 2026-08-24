# A-12 Frozen H-B2 GUI integration report

## Status

`H1_BACKWARD_COMPATIBILITY=PASS`  
`HB2_RUNTIME_SEMANTICS_MATCH=PASS`  
`H1_HB2_MUTUALLY_EXCLUSIVE=YES`  
`HB2_Q2_OOD_GATE=PASS`  
`SHADOW_LOGGING_READY=YES`  
`HB2_PRODUCTION_DEFAULT=NO`  
`NEXT_STEP=NEW_SESSION_FULL_FOV_PAIRED_VALIDATION`

## Scope and provenance

- Replay input is the reused A-11 pointwise artifact: `outputs\daheng_c1_gauge_blocks_20260819_height_depth_baseline_spatial_audit\pointwise_base_h1_hb2.csv`.
- Replay input SHA256: `8f09763cea1bbe6e5828ddd0684a3c61902461d2001da02d16da24f29c9fab88`.
- Runtime config: `laser_measurement_tool\configs\measure_tool_daheng_0811.yaml`.
- Frozen H-B2 config SHA256: `203916caf8ec3ba3633ca7a7407a5de8f5c353a5be0729dc74a38eb2c04ddaac`.
- No C0, C1, Ground Reference, Steger, ROI, fitting, or model search was rerun.
- A-11 artifacts are reused for provenance and deterministic numeric replay only; no new model selection is made here.

## Runtime call chain

`Frozen C0 -> Frozen C1 -> session-linear Ground Reference -> raw height -> one active mode (none/h1/hb2)`

The existing H1 entry point remains the final scalar-height stage.  The H-B2
entry point is the same scalar stage and is selected through the GUI mode combo.
The point reconstruction remains unchanged.  H1 and H-B2 are both evaluated
for shadow logging, but only `active_height_correction` is used for display.
Online `FrameResult`/export JSON contains the shadow fields, and an active raw
frame recording writes the accepted processed rows to `height_shadow.csv`
alongside `frames.csv`.

For H-B2, q2 is computed from Frozen-C0 `P_c0=lambda_c0*[xn,yn,1]` and the
quadratic model's independent-axis normalization.  The runtime aggregation for
one GUI height ROI is the arithmetic mean q2 over accepted reconstruction
points, while `q2_in_domain` is an all-points gate; an OOD point cannot be
hidden by an in-domain mean.

## Frozen H-B2 semantics

`h_hb2 = h_raw - (a0 + a2*q2)`  
`a0 = -0.10068827127712787 mm`  
`a2 = 0.053274373969597236 mm/q2`  
`q2 domain = [-0.50189189917236998, 1.4605125871893883]`

The default OOD policy is reject with explicit `HB2_Q2_OOD`; no silent
unbounded extrapolation is permitted.  `clamp_diagnostic` is a separate,
explicit diagnostic policy and is flagged in the output.

## Replay result

The CSV contains the pointwise H1/H-B2 equality checks, `none` raw preservation,
mode exclusivity, and both OOD sides.  The maximum absolute replay deltas are
`H1=0.000e+00 mm` and `H-B2=0.000e+00 mm`.

For H1, the replay expectation uses the existing Stage-A inclusive 1--30 mm
gate: values outside that height domain remain raw.  This is why the H1
compatibility check is against the old GUI/Stage-A runtime semantics rather
than against the ungated diagnostic `h_h1_mm` column in the A-11 pointwise
artifact.

## Engineering conclusion

The current configuration keeps H1 as the Daheng default for backward
compatibility.  H-B2 is available as an independent selectable mode, with H1
preserved as a shadow comparison.  This integration does not establish a
production default or add a spatial correction; the required next experiment
is a new-session paired full-FOV validation.
