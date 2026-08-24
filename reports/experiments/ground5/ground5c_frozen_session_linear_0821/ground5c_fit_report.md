# Ground-5C｜Frozen Session Linear Fit-only Audit

## 结论

- `UNION_SUPPORT = PASS`
- `FROZEN_SESSION_LINEAR_FIT = PASS`
- `RECOMMENDED_COORDINATE = physical_S`
- `MORE_COVERAGE_REQUIRED = NO`
- frozen `a_session = -0.000382799377854`, `b_session = -0.196934966721`
- frozen valid domain = `[-139.76604886428078, 144.30211420107466]`

本轮只读取 fit 目录的 pose001–005；没有发现 validation 目录，没有读取 pose006/007 评价结果，也没有运行正式 held-out 验证。

## Provenance / reuse audit

- 复用：Ground5A 的 PnP、physical-board mask、Frozen C0/C1 reconstruction、图像/标定配置解析。
- 复用：Ground5A 的 Steger cache；本轮只解引用 25 个 fit cache entry，`steger_rerun=false`。
- 复用：Ground-1 的全局 physical-S origin/direction；没有重新定义 S。
- 本轮新增：40-bin union-support、frame median → pose median、pose_count 门槛、equal-bin linear fit 和 fit-only LOPO。
- 未使用：Factory Profile、Ground-3 数值参数、C0/C1/H1 修改、residual/truth mask、raw-point pooled fit。

## Support

固定 bins 的范围是该坐标在 001–005 所有 board-mask-selected laser ground points 的 union min/max；LOPO 使用这组预先固定的 fit-only bins。每个 frame/bin 只取 raw PnP-ground `Zg` median；每个 pose/bin 再取 frame median 的 median，空 bin 不补值。

| coordinate | union bins | formal (>=2 poses) | strong (>=3 poses) | weak (1 pose) | min pose formal fraction | status |
|---|---:|---:|---:|---:|---:|---|
| full_v | 40 | 39 | 36 | 1 | 0.8205 | PASS |
| physical_S | 40 | 39 | 36 | 1 | 0.8205 | PASS |

正式 fit 的每个 bin 先对其有效 pose 的 pose/bin median 做算术平均，因此每个 formal bin 只贡献一个等权观测；不按原始点数或 Z residual 加权/删 bin。valid domain 只表示 formal bin 的外边界，内部仍以 formal bin index 为准，不外推、不 clamp。

## Coordinate selection by fit-only LOPO

选择顺序冻结为 mean LOPO RMSE → mean LOPO P95 → mean support coverage → mean frame repeatability；前三级近似持平时优先 physical_S。

| coordinate | mean LOPO RMSE (mm) | mean LOPO P95 (mm) | mean coverage | mean repeatability (mm) |
|---|---:|---:|---:|---:|
| full_v | 0.057853174 | 0.11497819 | 0.958773 | 0.0017684343 |
| physical_S | 0.057777918 | 0.11416093 | 0.958773 | 0.0017931632 |

冻结结果：`physical_S`，原因：`mean_lopo_rmse`。

## Frozen parameters

- coordinate: `physical_S`
- `a_session`: `-0.000382799377854` mm / coordinate-unit
- `b_session`: `-0.196934966721` mm
- valid domain: `[-139.76604886428078, 144.30211420107466]`
- formal bin count: `39`; strong: `36`; weak diagnostic: `1`

## Outputs

- `union_coverage.csv` / `union_coverage.png`
- `per_pose_linear_diagnostics.csv`
- `fit_lopo_coordinate_comparison.csv`
- `pooled_fit_residual.png`
- `frozen_session_linear.json`
