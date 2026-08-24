# Ground-5A｜Frozen Factory Ground Profile 同 Session Held-out 验证

数据集：`chessboard_0821`；本轮生成时间：`2026-08-21T14:52:51+0800`。

## 最终结论

- `GROUND_POINT_SELECTION = PASS`
- `RECOMMENDED_COORDINATE = full_v`
- `FACTORY_PROFILE_FIT_STABILITY = PASS`
- `HELDOUT_FACTORY_PROFILE = FAIL`
- `SESSION_LINEAR_NEEDED = YES`

## Protocol lock

- Fit poses: `001–005`; held-out poses: `006–007`; no validation value was read for coordinate/model selection.
- Full-sensor image coordinates are retained. `full_v` is raw sensor row `v`; `c1_s` is Frozen C1 raw PCA ray coordinate `s_raw`.
- PnP: existing Session PnP implementation with board pattern `[11, 8]`, square size `20 mm`.
- Mask: existing `pnp_board_mask/full_board_physical`; selection is polygon-only and uses no Z residual.
- Reconstruction: same cached centers to frozen C0 and frozen C1; per-pose PnP `R,t` is used as camera-to-ground transform.
- H1/Stage-A: disabled for analysis; Session Ground Reference: not fitted/applied; Ground-3 G(S) parameters: not reused.
- Factory profile target: frame-detrended `r=Zg-(a*x+b)`, cubic B-spline candidates with 1/2/3 interior knots, equal pose weighting, no extrapolation and no clamp.

## Artifact provenance / reuse audit

### Reused implementation (not reused results)

- Existing Steger adapter and full-sensor reconstruction entry points.
- Existing Session PnP and checkerboard physical-board mask.
- Existing robust linear ground-profile kernel through a one-dimensional adapter.
- Ground-3 frame-median/pose-median bin aggregation and spline-basis construction as code framework only.

### Reused artifacts

- `chessboard_0821` manifest/frame split, source TIFFs and their recorded SHA-256 values.
- Frozen Daheng C0/C1 calibration package and its provenance; no C0/C1 refit.
- On reruns, the local one-Steger cache is reused only when source SHA, extraction options and config SHA match.

### This generation

- Per-pose PnP, board-mask selections, PnP-ground C0/C1 points.
- Steger centers were loaded from the protocol-compatible cache; no Steger rerun was needed for this final generation.
- Fit-only coordinate comparison, frozen coordinate decision, fit-only Factory candidates and final profile.
- Held-out A/B/C metrics and plots for 006/007.

## PnP and point selection

| split | pose | chess PnP RMSE (px) | detection | selected frames | min selected points |
|---|---:|---:|---|---:|---:|
| fit | 001 | 0.174936 | SB | 5 | 2445 |
| fit | 002 | 0.17672 | SB | 5 | 2157 |
| fit | 003 | 0.197037 | SB | 5 | 2215 |
| fit | 004 | 0.194134 | SB | 5 | 2489 |
| fit | 005 | 0.193861 | SB | 5 | 2510 |
| validation | 006 | 0.193258 | SB | 5 | 2492 |
| validation | 007 | 0.202651 | SB | 5 | 2451 |

## Fit-only coordinate comparison

| coordinate | common coverage | cross-pose corr | low-frequency corr | profile RMSE diff (mm) | frame repeatability RMSE (mm) | selected |
|---|---:|---:|---:|---:|---:|---|
| full_v | 0.85 | 0.918749 | 0.971492 | 0.0224416 | 0.00166506 | YES |
| c1_s | 0.85 | 0.919135 | 0.971486 | 0.0223979 | 0.00161051 | NO |

Selection was frozen after this table was produced from 001–005 only; `006/007` did not enter any coordinate or Factory candidate rule.

## Factory Profile candidate

- Coordinate: `full_v`
- Fit support domain: `[566, 2137.65]`
- Support bins: `34/40`
- Selected interior knots: `3`
- Fit-only leave-one-pose-out RMSE: `0.0469812 mm`
- Model selection: minimum fit-only leave-one-pose-out RMSE; tie goes to lower knot count.
- Unsupported coordinates are rejected/marked unsupported; no interpolation, extrapolation or clamp is used by Factory F(x).

| candidate knots | fit RMSE (mm) | fit-pose LPO CV RMSE (mm) | selected |
|---:|---:|---:|---|
| 1 | 0.0466961 | 0.0469817 | NO |
| 2 | 0.0466969 | 0.0469825 | NO |
| 3 | 0.0466957 | 0.0469812 | YES |

## Held-out A/B/C

RMSE/P95 improvements are relative reductions on the same strict Factory support domain.

| pose | A RMSE | B RMSE | C RMSE | B vs A | C vs B | A P95 | B P95 | C P95 | B vs A P95 | C vs B P95 | B support | detrended-shape corr |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 006 | 0.249444 | 0.235846 | 0.0503646 | 0.0545133 | 0.786451 | 0.38303 | 0.34963 | 0.0912235 | 0.0872005 | 0.739086 | 0.623044 | 0.48485 |
| 007 | 0.249454 | 0.236403 | 0.0536241 | 0.0523182 | 0.773167 | 0.369853 | 0.339317 | 0.101297 | 0.082563 | 0.701469 | 0.628711 | 0.313578 |

A and B are compared on the same strict Factory support domain. C's `a,b` are fitted separately for each held-out pose using only that pose's supported laser ground points; they are not fed back into F(x).

## Interpretation

- Absolute profile prediction: see A→B RMSE/P95 deltas above and `absolute_profile_overlay.png`. The Factory model is a detrended spatial profile, so pose zero/tilt remains visible in B when present.
- Nonlinear detrended shape: pose006 correlation `0.48485`, pose007 correlation `0.313578` against frozen F(x).
- Session linear diagnostic: C→B improvement is reported per held-out pose; classification uses predeclared thresholds `0.1` / `0.05`.

## Outputs

- `ground5a_report.md`
- `frame_metrics.csv`
- `pose_metrics.csv`
- `coordinate_comparison.csv`
- `fit_profile_by_pose.csv`
- `validation_abc_comparison.csv`
- `factory_profile_candidate.json`
- `coordinate_freeze.json`
- `absolute_profile_overlay.png`
- `detrended_profile_overlay.png`
- `heldout_abc_comparison.png`
- `heldout_abc_residual_overlay.png`
- `steger_geometry_cache.json`
- `pose001_board_mask_overlay.png`
- `pose002_board_mask_overlay.png`
- `pose003_board_mask_overlay.png`
- `pose004_board_mask_overlay.png`
- `pose005_board_mask_overlay.png`
- `pose006_board_mask_overlay.png`
- `pose007_board_mask_overlay.png`
