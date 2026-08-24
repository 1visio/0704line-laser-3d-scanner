# Ground point audit export

本次改动为正式 GUI `Session PnP / 激光地面一致性检查` 增加只读的
point-level audit export。导出复用同一次 `FrameResult`、同一次 physical-board
mask 和同一次 `evaluate_ground_sanity()` 输入，不重新运行 Steger、Frozen C0/C1、
Session PnP、Session Ground 拟合或任何 compensation。

运行时点击“激光地面一致性检查”后，文件写入当前
`session_ground_calibration.json` 所在目录的 `ground_spatial_audit/`：

- `ground_residual_points.csv`
- `ground_point_export_manifest.json`
- `ground_point_audit_export.md`

CSV 的 `source_point_index` 直接来自 shared board-mask 的 bool mask，`point_id`
由 `frame_id + source_point_index` 构成；不会通过数组长度、排序或历史 point CSV
推断 linkage。`points_ground_raw` 是唯一的 sanity/residual view；active Session
Ground reference 存在时，`points_ground_metric` 只作为旁路记录。

## Verification flags

本轮专项测试覆盖 source-index 顺序、raw/metric 分离、plane replay、Frozen C0/C1
manifest hash、非一致 sanity slice 拒绝和 PASS artifact 写入前校验：

```text
GROUND_POINT_EXPORT = PASS
UV_POINT_IDENTITY = PASS
RAW_GROUND_PRESERVED = YES
FRAME_PROVENANCE = PASS
GENERATION_PROVENANCE = PASS
SANITY_METRIC_REPLAY = PASS
READY_FOR_SPATIAL_RESIDUAL_AUDIT = YES
```

当前 checkout 没有 `ground_point_linkage_audit.json` / `report.md`，也没有被复用的
历史 point CSV；本报告记录的是导出链实现和专项验证。真实 session artifact 由 GUI
在当前帧检查时生成。
