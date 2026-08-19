# Ground reference report

## GROUND_LINEAR_MODEL: REVIEW_REQUIRED_SPATIAL_STRUCTURE

Model: `Zg = a*S + b`; the values below are diagnostic freeze candidates only.

- frame-balanced pooled `a`: -0.000237628710669 mm/mm
- frame-balanced pooled `b`: -0.0066927158093 mm
- pooled RMSE / P95 / Max: 0.066317 / 0.141844 / 0.665654 mm
- frame count / pooled point count: 20 / 58813

## GROUND_PROFILE_STABILITY: STABLE_SPATIAL_STRUCTURE

- a mean / median / std / range: -0.000237908 / -0.000237726 / 1.28008e-05 / 4.19809e-05 mm/mm
- b mean / median / std / range: -0.00671263 / -0.00661112 / 0.00109929 / 0.00372705 mm
- residual-vs-S check: stable_spatial_structure_candidate
- residual profile RMS / peak-to-peak: 0.055807394774195995 / 0.23258605170974875 mm
- cross-frame bin-median repeatability sigma / structure ratio: 0.0015022604907416366 / 37.14894661620567.

## Shared coordinate definition

- origin_xy (mm): `[4.345466690716022, 2.878594498981755]`
- direction_xy: `[0.012883418031591754, 0.9999170053258537]`
- Every frame uses `S=(XY-origin_xy) dot direction_xy`; no frame-local re-centering or re-orientation.

## Protocol and provenance

- 20 source TIFFs were processed; each frame ran Steger once.
- The same centers were passed to the C0 base and C1-enabled reconstruction calls; C1-valid points are the ground points used below.
- No analytical ROI, reconstruction image ROI, black-cell interpolation, spline/LUT, or height compensation was used.
- The configured Steger search rectangle is recorded as a detector search window only; it is not a post-extraction point-selection ROI.
- `enable_laser_ray_correction`: `True`.
- Dataset quality summary: `{'frames': 20, 'passed': 0, 'warnings': 20, 'warning_counts': {'dynamic_range_low': 20}}`. The low dynamic-range warning was retained and not used to drop frames.

## Outputs

- `ground_frame_metrics.csv`
- `ground_residuals.csv`
- `ground_profile_pooled.csv`
- `ground_reference_summary.json`
- `ground_profile_all_frames.png`
- `ground_detrended_residual_vs_s.png`
- `ground_ab_stability.png`
- `ground_reference_report.md`

The report is a diagnostic and parameter-freeze candidate; it does not modify GUI or production height-measurement behavior.
