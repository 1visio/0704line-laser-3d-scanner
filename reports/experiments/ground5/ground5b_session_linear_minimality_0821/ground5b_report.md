# Ground-5B｜Session Linear Minimality Audit

数据集：`chessboard_0821`；生成时间：`2026-08-21T15:26:06+0800`。

## 最终结论

- `SESSION_LINEAR_EFFECT = STRONG`
- `FACTORY_PROFILE_INCREMENT_AFTER_SESSION_LINEAR = NEUTRAL`
- `RECOMMENDED_SESSION_COORDINATE = physical_S`
- `PRODUCTION_GROUND_CHAIN = PnP -> Frozen C0+C1 -> Session Linear in physical_S; omit Factory Profile`

## Protocol lock / provenance

- Fit poses remain `001–005`; held-out poses are `006–007`.
- Ground-5A PnP, physical-board mask, cached centers, Frozen C0/C1 and Factory candidate are reused.
- Ground-5B reads the existing Steger cache in read-only mode and refuses cache miss; no Steger extraction is performed.
- No C0/C1 refit, H1, Session Ground Reference or Ground-3 numeric parameter reuse.
- The Factory candidate is loaded from Ground-5A JSON; it is not refit or retuned.
- Ground-5A Factory coordinate/domain: `full_v`, `[566, 2137.65]`.

### Frozen physical S

`S = (XY - origin_xy) dot direction_xy`, with `origin_xy=[4.345466690716022, 2.878594498981755]` mm and `direction_xy=[0.012883418031591754, 0.9999170053258537]`.
This is the Ground-1/4A global physical along-stripe coordinate, not a height-measurement obstacle-local axis.

## Session Linear parameters

D-v and D-S parameters are fitted independently for each held-out pose using all board-mask-selected points, with equal total frame weight. C uses only the common Factory support, matching Ground-5A.

| pose | chain | coordinate | fit scope | a | b | fit points |
|---:|---|---|---|---:|---:|---:|
| 006 | C | full_v | common_factory_support | 0.000105274 | -0.3682957 | 7765 |
| 006 | D-v | full_v | all_board_points | 8.739524e-05 | -0.3604446 | 12463 |
| 006 | D-S | physical_S | all_board_points | -0.0009007711 | -0.2308163 | 12463 |
| 007 | C | full_v | common_factory_support | 8.065262e-05 | -0.3364916 | 7708 |
| 007 | D-v | full_v | all_board_points | 8.366785e-05 | -0.3553093 | 12260 |
| 007 | D-S | physical_S | all_board_points | -0.0008624292 | -0.2312137 | 12260 |

## Held-out metrics: common Factory support

Metrics are equal-frame means at pose level. `frame_repeatability_rmse_mm` is the RMS spread of per-frame bias around the pose mean; mask selection is unchanged.

| pose | chain | coordinate | Bias | RMSE | P95 | Max | P2P | frame repeatability |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 006 | A | full_v | -0.2357315 | 0.2494441 | 0.3830304 | 0.4263624 | 0.4075119 | 0.0005596095 |
| 006 | B | full_v | -0.2254133 | 0.2358461 | 0.3496299 | 0.3967169 | 0.3886235 | 0.0005596095 |
| 006 | C | full_v | 1.075529e-17 | 0.05036459 | 0.09122351 | 0.2187141 | 0.3445629 | 0.0005596095 |
| 006 | D-v | full_v | 0.006096528 | 0.05637147 | 0.09845612 | 0.2241349 | 0.3631349 | 0.0005596095 |
| 006 | D-S | physical_S | 0.006087636 | 0.05634784 | 0.09842381 | 0.2240885 | 0.3630559 | 0.0005595955 |
| 007 | A | full_v | -0.2377464 | 0.2494543 | 0.3698533 | 0.5269183 | 0.4250351 | 0.001097194 |
| 007 | B | full_v | -0.2273034 | 0.2364033 | 0.3393171 | 0.4958483 | 0.4063672 | 0.00109401 |
| 007 | C | full_v | 1.489694e-16 | 0.05362414 | 0.1012967 | 0.2973867 | 0.4397908 | 0.001087023 |
| 007 | D-v | full_v | 0.004292608 | 0.05589816 | 0.1058695 | 0.2730891 | 0.4179371 | 0.001089905 |
| 007 | D-S | physical_S | 0.004286723 | 0.05587834 | 0.1058337 | 0.2731151 | 0.4179253 | 0.00108988 |

## Held-out metrics: all board-mask points

A/D comparison uses every point retained by the unchanged physical-board mask; `Max` is maximum absolute residual.

| pose | chain | coordinate | Bias | RMSE | P95 | Max | P2P | frame repeatability |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 006 | A | full_v | -0.20808 | 0.2244089 | 0.3704134 | 0.4263624 | 0.4075119 | 0.0004411208 |
| 006 | D-v | full_v | 1.800318e-16 | 0.05511202 | 0.09956872 | 0.2339736 | 0.4581084 | 0.0004424849 |
| 006 | D-S | physical_S | 2.360742e-16 | 0.05509798 | 0.09954104 | 0.2339988 | 0.4580873 | 0.0004424937 |
| 007 | A | full_v | -0.2083931 | 0.222919 | 0.3586528 | 0.5269183 | 0.5315022 | 0.001002912 |
| 007 | D-v | full_v | 5.165139e-17 | 0.05147139 | 0.09855545 | 0.2730891 | 0.4204659 | 0.001011548 |
| 007 | D-S | physical_S | 5.308254e-17 | 0.0514589 | 0.09853113 | 0.2731151 | 0.4205168 | 0.001011568 |

## D vs A and C vs D

D-v/D-S vs A uses all board-mask-selected points. C vs D uses the same strict Factory support for all chains; positive `D-C` means C is better.

| pose | selected D | D RMSE gain vs A | D P95 gain vs A | D-C RMSE (mm) | D-C P95 (mm) |
|---:|---|---:|---:|---:|---:|
| 006 | D-S | 0.7544751 | 0.7312704 | 0.005983256 | 0.007200297 |
| 007 | D-S | 0.7691587 | 0.7252743 | 0.0022542 | 0.004537061 |

Thresholds: Session Linear STRONG requires both held-out poses to reach 10% RMSE and 5% P95 gain. Factory increment USEFUL requires C to improve over selected D by at least 0.005 mm RMSE and 0.01 mm P95 for both poses.

## Coordinate decision

D-v and D-S are ranked on all board-mask-selected points by mean pose RMSE, then P95, then frame repeatability; exact ties prefer frozen physical_S.

| scope | coordinate | mean RMSE | mean P95 | mean frame repeatability | selected |
|---|---|---:|---:|---:|---|
| all_board_points | full_v | 0.0532917 | 0.09906209 | 0.0007270163 | NO |
| all_board_points | physical_S | 0.05327844 | 0.09903608 | 0.0007270307 | YES |
| common_factory_support | full_v | 0.05613482 | 0.1021628 | 0.0008247574 | NO |
| common_factory_support | physical_S | 0.05611309 | 0.1021288 | 0.0008247379 | NO |

## Outputs

- `ground5b_report.md`
- `abcd_comparison.csv`
- `session_linear_parameters.csv`
- `session_coordinate_comparison.csv`
- `abcd_rmse_p95.png`
- `session_coordinate_comparison.png`
- `c_minus_d_residual_delta.png`
- `ground5b_summary.json`
- `cache_provenance.json`
