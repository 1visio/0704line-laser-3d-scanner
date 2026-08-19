# Ground-2 pose invariance report

## GROUND_POSE_INVARIANCE: NOT_SUPPORTED_BOARD_DEPENDENT

- CAMERA_SPACE_STRUCTURE: `NOT_SUPPORTED`
- BOARD_DEPENDENT_STRUCTURE: `SUPPORTED`
- MIXED_STRUCTURE: `NOT_SELECTED`
- Ground-3 recommendation: `BLOCK`

## Frozen Ground-1 coordinate definition

- origin_xy (mm): `[4.345466690716022, 2.878594498981755]`
- direction_xy: `[0.012883418031591754, 0.9999170053258537]`
- S formula: `S=(XY-origin_xy) dot direction_xy`.
- Ground-1 S coverage: [-147.047, 144.126] mm; 50 bins.
- No pose-specific PCA, re-centering, S redefinition, cross-pose point pooling, interpolation, spline/LUT, or height compensation was used.

## Ground-1 versus each new pose

| pose | common S bins | correlation | profile RMSE difference (mm) | median abs difference (mm) | peak offset (mm) | valley offset (mm) | frame RMSE difference (mm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| pose002 | 50 | 0.4913 | 0.0932763 | 0.0137088 | 122.293 | -5.82346 | 0.0370032 |
| pose003 | 50 | 0.563516 | 0.0788947 | 0.0137913 | 116.469 | -11.6469 | 0.0382278 |
| pose004 | 50 | 0.57591 | 0.0693062 | 0.0118305 | 122.293 | 0 | 0.0194503 |

## New-data audit

- 15 TIFFs: 002/003/004 each 5 frames; all retained in the report.
- quality summary: `{'frames': 15, 'passed': 0, 'warnings': 15, 'warning_counts': {'dynamic_range_low': 15}}`; no frame was dropped.
- exposure by pose: `{'002': [300.0], '003': [320.0], '004': [350.0]}` µs; this differs from the online config exposure of 2000 µs and is recorded as a protocol risk.
- `enable_laser_ray_correction=true`; existing frozen C1 parameters were reused and C0/C1 were not refit.
- The configured Steger search rectangle is detector search configuration only; no analytical/output ROI was applied.

## Ground-3 gate

The gate is based on raw binned residual profiles on the frozen S axis. It does not authorize fitting or deploying a new correction.
- thresholds: full correlation >= 0.8, normalized profile difference <= 0.5; low-frequency correlation >= 0.8 using a 5-bin diagnostic moving average.

## Outputs

- `ground_pose_frame_metrics.csv`
- `ground_pose_profiles.csv`
- `ground_pose_comparison.csv`
- `ground_pose_residual_overlay.png`
- `ground_pose_pairwise_difference.png`
- `ground_pose_consensus_profile.png`
- `ground_pose_invariance_report.md`
- `ground_pose_invariance_summary.json`
