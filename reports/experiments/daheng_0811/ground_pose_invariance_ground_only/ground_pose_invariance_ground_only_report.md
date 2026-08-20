# Ground-2R ground-only pose invariance report

## GROUND_POSE_INVARIANCE: SUPPORTED

- CAMERA_SPACE_STRUCTURE: `SUPPORTED`
- BOARD_DEPENDENT_STRUCTURE: `NOT_SUPPORTED`
- MIXED_STRUCTURE: `NOT_SELECTED`
- Ground-3 recommendation: `ALLOW`

## Geometry-only selection protocol

- Ground-only ranges were selected once per pose from the pose median image and Steger overlay, then shared by all five frames in that pose.
- Selection basis is image geometry only: outer board edge/frame/protrusion exclusion. No residual value, residual threshold, or residual ranking was used.
- The preview cache records one Steger run per source frame; analysis reuses those cached centers and does not run Steger again.
- The exact range/mask definition is in `ground_only_ranges.yaml`; the corresponding overlay/median images are listed below.

## Frozen Ground-1 S definition

- origin_xy: `[4.345466690716022, 2.878594498981755]`
- direction_xy: `[0.012883418031591754, 0.9999170053258537]`
- Formula: `S=(XY-origin_xy) dot direction_xy`.
- 50 frozen bins: [-147.047, 144.126] mm.
- No new PCA, S origin/direction, C0/C1 fit, spline/LUT, height compensation, black-cell interpolation, or cross-pose point pooling.

## Ground-1 versus ground-only pose profiles

| pose | common bins | correlation | low-frequency correlation | profile RMSE difference (mm) | median abs difference (mm) | peak S offset (mm) | valley S offset (mm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| pose002 | 49 | 0.935864 | 0.958973 | 0.0233299 | 0.0137847 | 5.82346 | -5.82346 |
| pose003 | 48 | 0.960799 | 0.975449 | 0.0187701 | 0.0144364 | -5.82346 | -11.6469 |
| pose004 | 49 | 0.93421 | 0.935503 | 0.0226549 | 0.0114605 | 5.82346 | 0 |

## Pose-level image geometry ranges

- pose002: `v` in [110, 3000] px; shared by all five frames.
- pose003: `v` in [170, 3000] px; shared by all five frames.
- pose004: `v` in [70, 3000] px; shared by all five frames.

## Provenance and protocol caveat

- New frames: `{'002': 5, '003': 5, '004': 5}`; all retained.
- New dataset quality summary: `{'frames': 15, 'passed': 0, 'warnings': 15, 'warning_counts': {'dynamic_range_low': 15}}`.
- Exposure by pose: `{'002': [300.0], '003': [320.0], '004': [350.0]}` µs; this remains a Ground-1/new-data protocol difference.
- `enable_laser_ray_correction=true`; Ground-1 frozen C1 calibration is reused.
- This is a diagnostic attribution result only; it does not authorize a new correction model.

## Outputs

- `ground_only_ranges.yaml`
- `ground_pose_geometry_cache.json`
- `pose002_median_image.png`
- `pose002_median_steger_overlay.png`
- `pose002_steger_geometry.png`
- `pose002_ground_only_mask_overlay.png`
- `pose003_median_image.png`
- `pose003_median_steger_overlay.png`
- `pose003_steger_geometry.png`
- `pose003_ground_only_mask_overlay.png`
- `pose004_median_image.png`
- `pose004_median_steger_overlay.png`
- `pose004_steger_geometry.png`
- `pose004_ground_only_mask_overlay.png`
- `ground_pose_frame_metrics_ground_only.csv`
- `ground_pose_profiles_ground_only.csv`
- `ground_pose_comparison_ground_only.csv`
- `ground_pose_residual_overlay_ground_only.png`
- `ground_pose_pairwise_difference_ground_only.png`
- `ground_pose_invariance_ground_only_report.md`
- `ground_pose_invariance_ground_only_summary.json`
