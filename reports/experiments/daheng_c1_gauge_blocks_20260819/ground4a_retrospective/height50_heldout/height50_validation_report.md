# Height-2/3：obs_50mm 首次真正 held-out 高度尺度验证

- `HEIGHT_SCALE_50MM_VALIDATION=PARTIAL`
- 判定摘要：H1 的 pooled MAE/RMSE 与 ±0.1 达标率改善，但 P95/Max 尾部指标和部分 position 的绝对误差变差，因此标为 `PARTIAL`，不视为完全泛化通过。
- 本轮为 retrospective held-out diagnostic；不修改 C0/C1、Ground G(S)、GUI 或生产配置。

## 冻结参数

- H1：`h_corr = k*h`，`k_full = 1.004033959133720`。
- 训练输入：原 Ground-4A 29 个成功 `session_linear` condition，等权；输入 SHA-256：`f069020d7ff84b7189b0c386cd4c2a93bd55ac6753957e48d77b1966ecd47b68`。
- 参数 SHA-256：`fb05c3e6ea09775f5dc906c8d44a25f6e8fb0cdd97846f97fca38bc55c381391`；冻结状态：`FROZEN_BEFORE_50MM_READ`。
- `obs_50mm` 未参与 k 拟合、模型选择或参数调整；k 在读取 50mm 图像之前写入冻结 artifact。

## Provenance / reuse audit

- 复用：Ground-4A 29-condition 的 B 链协议、Daheng 0811 配置、Frozen C1 ray correction，以及 Ground-1 frozen `origin_xy/direction_xy/S domain`。
- 复用：25 个 50mm 帧的 one-pass Steger cache；本轮 evaluate 未重新运行 Steger，C1 使用同一缓存中心点。
- 新增：25 帧 C1 重建、5 个 repeat-1 session-linear ground proxy、20 个 formal repeat2–5 frame metrics、5 个 position condition means。
- ROI registry：`height50_manual_roi_registry.json`，geometry-only/manual-confirmed，SHA-256：`0e5174952ff93c634edd32b0dafc7ce651bf4f371602d5ec8e90c65c8d2bb2d4`。
- C1 config `enable_laser_ray_correction=true`；config SHA-256：`c22e463aff6dc51565679382cc766a3c7078a57f676809e7b31ee1cbe185f15f`。

## Formal repeat2–5：20 帧 pooled metrics

| chain | n | Bias | MAE | RMSE | P95 | Max | ±0.05 | ±0.1 | ±0.2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw B session_linear | 20 | -0.10424 | 0.10424 | 0.10740 | 0.13371 | 0.13428 | 0/20 (0.0%) | 8/20 (40.0%) | 20/20 (100.0%) |
| frozen H1 scale | 20 | 0.09703 | 0.09703 | 0.10044 | 0.14001 | 0.14028 | 0/20 (0.0%) | 12/20 (60.0%) | 20/20 (100.0%) |

## 5 个 position condition mean

| chain | n | Bias | MAE | RMSE | P95 | Max | ±0.05 | ±0.1 | ±0.2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw B condition mean | 5 | -0.10424 | 0.10424 | 0.10738 | 0.13149 | 0.13320 | 0/5 (0.0%) | 2/5 (40.0%) | 5/5 (100.0%) |
| frozen H1 condition mean | 5 | 0.09703 | 0.09703 | 0.10043 | 0.13384 | 0.13912 | 0/5 (0.0%) | 3/5 (60.0%) | 5/5 (100.0%) |

## Raw → H1 增量

- frame MAE delta (H1 - raw)：`-0.00721` mm；RMSE delta：`-0.00696` mm。
- position-mean MAE delta (H1 - raw)：`-0.00721` mm；RMSE delta：`-0.00696` mm。负值表示改善。

| position | raw mean | H1 mean | raw bias | H1 bias | raw repeatability sigma | H1 repeatability sigma |
|---|---:|---:|---:|---:|---:|---:|
| laser001 | 49.87533 | 50.07652 | -0.12467 | 0.07652 | 0.00051 | 0.00052 |
| laser002 | 49.88760 | 50.08884 | -0.11240 | 0.08884 | 0.00233 | 0.00234 |
| laser003 | 49.93768 | 50.13912 | -0.06232 | 0.13912 | 0.00164 | 0.00165 |
| laser004 | 49.86680 | 50.06796 | -0.13320 | 0.06796 | 0.00100 | 0.00100 |
| laser005 | 49.91138 | 50.11272 | -0.08862 | 0.11272 | 0.00187 | 0.00188 |

## Repeatability

- raw B：median/P95/Max sigma = `0.00164` / `0.00224` / `0.00233` mm。
- frozen H1：median/P95/Max sigma = `0.00165` / `0.00225` / `0.00234` mm。

## ROI 与选择边界

- 每个 laser position 使用 5 帧 median image + Steger overlay；5 个 repeat 共用一个手工 registry。
- ROI 仅依据原图中的物理 ground/height 几何范围；未使用 50mm 真值、误差、residual 或 residual threshold。
- 未对棋盘缺失点插值，也未按重建数值结果删除点；重建无效点只按 C1 的原有有效性自然剔除并计入审计列。
- repeat1 只用于该 position 的 `Zg=a*S+b` ground proxy；正式指标只用 repeat2–5。

## Ground / C1 细节

- 统一使用 frozen `S=(XY-origin_xy)·direction_xy`，未按 position 重新定义 S。
- repeat1 ground proxy 状态：001=success, 002=success, 003=success, 004=success, 005=success.
- 未重新拟合 C0/C1、未重新拟合 G(S)，H1 只作用于 raw B height。

## 输出

- `frozen_height_scale.json`：冻结 k、输入 SHA、参数 SHA。
- `height50_manual_roi_registry.json` 与 `overlays/*_manual_roi_overlay.png`：geometry-only ROI registry/复核图。
- `height50_frame_metrics.csv`：全 25 帧，repeat1 标为 in-sample，repeat2–5 为 formal。
- `height50_position_metrics.csv`：5 个 position 的 repeat2–5 condition summary。
