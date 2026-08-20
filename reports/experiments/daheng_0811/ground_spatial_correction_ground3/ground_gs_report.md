# Ground-3 cross-pose consensus Ground Spatial Correction

## GROUND_GS_STATUS: PASS

- selected model: `cubic_bspline_3_interior_knots`
- allow next held-out block validation: `True`

## Four-pose and frozen-S protocol

- Four equal-weight pose groups: Ground-1 A, pose002, pose003, pose004; each pose weight is 1/4.
- Within each pose: per-frame per-bin residual median, then median across frames. No point pooling is used to define a pose profile.
- Frozen S: `S=(XY-Ground1_origin_xy) dot Ground1_direction_xy`; no PCA, origin/direction, or C0/C1 refit.
- Frozen S domain: [-147.047, 144.126] mm; 50 frozen bins.
- `raw` = existing detrended residual r; `corrected` = r - G(S). This is not a C1 toggle or production height correction.

## Candidate family

- Candidates are cubic B-splines with 3/4/5 interior knots only.
- Knot locations are fixed and evenly spaced in the frozen S domain.
- Fit uses SciPy `least_squares(loss='soft_l1')` and fixed curvature smoothness penalty lambda=0.001.
- Leave-one-pose-out training uses three pose profiles with equal pose weights; each fold is scored only in strict common support.
- Extrapolation, interpolation, and clamping are not performed; unsupported bins are recorded and omitted.

## Leave-one-pose-out CV

| knots | held-out pose | common bins | raw RMSE | corrected RMSE | RMSE improvement | raw P95 | corrected P95 | P95 improvement | raw P2P | corrected P2P | P2P improvement |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | ground1 | 48 | 0.0568267 | 0.053623 | 0.00320372 | 0.137022 | 0.126121 | 0.0109005 | 0.232586 | 0.232227 | 0.00035887 |
| 3 | 002 | 48 | 0.0420932 | 0.0402249 | 0.00186826 | 0.0938457 | 0.0784286 | 0.0154172 | 0.166815 | 0.165649 | 0.00116669 |
| 3 | 003 | 48 | 0.0446432 | 0.0420637 | 0.00257952 | 0.103173 | 0.0889596 | 0.0142132 | 0.171462 | 0.169467 | 0.00199495 |
| 3 | 004 | 48 | 0.0448045 | 0.0430819 | 0.00172254 | 0.0933523 | 0.0826954 | 0.0106569 | 0.175912 | 0.173175 | 0.0027374 |

## Candidate comparison

| knots | basis | mean RMSE improvement | mean P95 improvement | mean P2P improvement | min-fold RMSE improvement | stable candidate | selected |
|---:|---:|---:|---:|---:|---:|---|---|
| 3 | 7 | 0.00234351 | 0.0127969 | 0.00156448 | 0.00172254 | True | True |
| 4 | 8 | 0.00228185 | 0.012535 | 0.00138174 | 0.00168949 | True | False |
| 5 | 9 | 0.00231355 | 0.0126207 | 0.00140469 | 0.00171316 | True | False |

## Freeze candidate and gate

- `G(S)` freeze candidate: `cubic_bspline_3_interior_knots`; coefficients are in `ground_gs_candidate_coefficients.csv`.
- The candidate is not written to C1, GUI, production configuration, or the height-measurement chain.
- All CV folds no extrapolation: `True`; no clamp: `True`.
- Unsupported bins were omitted rather than extrapolated; maximum unsupported bins in a fold: `2`.

## Data caveat

- Ground-1 quality summary: `{'frames': 20, 'passed': 0, 'warnings': 20, 'warning_counts': {'dynamic_range_low': 20}}`.
- Ground-2R quality summary: `{'frames': 15, 'passed': 0, 'warnings': 15, 'warning_counts': {'dynamic_range_low': 15}}`.
- Ground-2R exposure by pose: `{'002': [300.0], '003': [320.0], '004': [350.0]}` µs; this remains a protocol caveat.

## Reuse versus new computation

- Reused: Ground-1 frozen origin/direction/50 bin edges and frame residual CSV; Ground-2R image-geometry mask, one-Steger cache, pose grouping, and C1-enabled reconstruction package.
- Newly computed: Ground-2R frame residual arrays from cached centers, four-pose balanced profiles, cubic B-spline candidates, held-out-pose CV, freeze candidate, and diagnostic plots/report.

## Outputs

- `ground_gs_frame_metrics.csv`
- `ground_gs_frame_residuals.csv`
- `ground_gs_pose_profiles.csv`
- `ground_gs_cv_metrics.csv`
- `ground_gs_model_comparison.csv`
- `ground_gs_candidate_coefficients.csv`
- `ground_gs_profile_candidates.png`
- `ground_gs_cv_improvement.png`
- `ground_gs_selected_cv_residuals.png`
- `ground_gs_summary.json`
- `ground_gs_report.md`
