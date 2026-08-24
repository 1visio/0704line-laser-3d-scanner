# Ground-5C A-3｜Strict Held-out Validation

## 最终判定

- `FROZEN_SESSION_LINEAR = PASS`
- `PER_POSE_REFIT_NEEDED = NO`
- `RECOMMENDED_COORDINATE = physical_S`
- `MORE_COVERAGE_REQUIRED = NO`

核心问题：`Can the single physical_S Session Linear frozen from poses001–005 predict poses006–007 without re-grounding? YES`

B 链没有重新拟合：直接读取 A-2 frozen JSON 的 physical_S、origin/direction、a_session、b_session、valid_domain 和 bin_edges。C_oracle 只作为 held-out 上限诊断，不写回任何冻结参数。

## Frozen input and provenance

- frozen JSON: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\ground5c_frozen_session_linear_0821\frozen_session_linear.json`
- frozen JSON SHA-256 at startup: `aca75aa5e7530eb680a6f85231d571065378c4f5f22bcdb3b9d742259df2fe49`
- coordinate: `physical_S`
- `a_session=-0.000382799377854498`, `b_session=-0.1969349667207237`
- valid domain: `[-139.76604886428078, 144.30211420107466]`
- bin edge count: `41` (40 bins)
- validation cache entries used: `10`; `steger_rerun=false`

validation 只加载 pose006/007；没有加载 fit records，没有读取 Ground5A/5B held-out 指标。C0/C1、PnP、physical-board mask 均复用既有链。

## Predeclared engineering criteria

判据在读取 held-out 结果前固定，运行后未调整：
- strict PASS per pose: B RMSE <= `0.080 mm`, B-vs-A RMSE improvement >= `50%`, B-C_oracle RMSE gap <= `0.030 mm`, coverage >= `80%`。
- PARTIAL 的“明显优于 A”固定为 RMSE improvement >= `20%` 且 P95 improvement >= `10%`，两个 pose 都满足但至少一个未达 strict PASS。

## Equal-bin metrics

主指标是在相同 frozen-domain / board-mask / supported-bin 上计算；每个 frame/bin 取 raw Zg median，再每个 pose/bin 取 frame median 的 median。C_oracle 的拟合也是 supported pose/bin 等权，不使用 pooled raw points。

| pose | A RMSE | B RMSE | C_oracle RMSE | B-A RMSE improvement | B-A P95 improvement | B-C RMSE gap | coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| 006 | 0.225996 | 0.0643314 | 0.0457472 | 71.53% | 62.27% | 0.0185841 | 84.62% |
| 007 | 0.225792 | 0.0586993 | 0.0418336 | 74.00% | 64.94% | 0.0168656 | 84.62% |

完整 Bias/RMSE/P95/Max/P2P 见 `heldout_equal_bin_metrics.csv`；同一 support 的 raw-point 工程诊断见 `heldout_raw_point_metrics.csv`。

## Oracle parameters

| pose | a_oracle (mm/mm) | b_oracle (mm) | fit bins | oracle fit RMSE (mm) |
|---|---:|---:|---:|---:|
| 006 | -0.00095464108 | -0.2298767 | 33 | 0.045747234 |
| 007 | -0.00086295168 | -0.23055733 | 33 | 0.041833638 |

## Interpretation

A 是 raw PnP-ground Zg；B 是 A-2 冻结的单一 physical_S Session Linear；C_oracle 允许每个 held-out pose 自己拟合，仅用于判断 session-to-session 参数迁移损失。B/C 差距不能反向修改 A-2。

输出：`heldout_comparison.csv`、`heldout_equal_bin_metrics.csv`、`heldout_raw_point_metrics.csv`、`heldout_oracle_parameters.csv`、`heldout_residual_ABC.png`、`validation_provenance.json`。
