# Surface-2A/2B 数据接入、ROI 准备与 q-domain 审计

## 当前状态

`SURFACE2_STATUS=ROI_REVIEW_PENDING`

本轮已完成新数据完整性审计、一次/帧 Steger 中心线提取、五帧 median 与几何 overlay 准备。ROI 仍是 draft，尚未人工冻结；因此本轮**停止在 ROI review**，没有生成 q1/q2、height residual 或 Surface-2C 的最终结论。

`Q2_GAP_FILLED=UNDECIDED`  
`Q1Q2_STATE_CONSISTENCY=UNDECIDED`  
`SURFACE2C_ALLOWED=NO`


## Provenance / 复用边界

- 输入根目录：`D:\Docs\linelaserscan\calibration_tool\projects\daheng\data`
- 配置：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\laser_measurement_tool\configs\measure_tool_daheng_0811.yaml`；仅用于同一 Steger extraction 参数，未调用重建。
- 复用 `evaluate_daheng_c1_gauge_blocks.py` 的 `load_image_and_centers()`、`profile_candidates()`、`build_roi_registry()`。
- 复用 `annotate_daheng_gauge_rois.py` 的 `median_image()`、`binned_centerline()`、`render_overlay()`。
- 新增计算：75 帧完整性/manifest/尺寸/hash 审计、75 次 Steger（每 TIFF 一次）、15 组 median/centerline/geometry overlay 和 draft registry。
- 未执行：Frozen C0、Frozen C1、q1/q2 计算、残差驱动筛点、residual/height 计算、任何补偿拟合。
- warning 帧保留在审计和 Steger 输入中，没有因 `dynamic_range_low` 自动删除。

## 数据完整性

| dataset | frames.csv | TIFF | pose×repeat | manifest status | quality_failed_count==0 | warning frame count | structural errors |
|---|---:|---:|---|---|---|---:|---:|
| obs_36mm | 25 | 25 | 5×5 | completed | False | 5 | 0 |
| obs_40mm | 25 | 25 | 5×5 | completed | False | 25 | 0 |
| obs_46mm | 25 | 25 | 5×5 | completed | False | 25 | 0 |

整体：`75/75` 帧成功完成中心线提取；Steger call count=`75`；缺失 key=`0`；提取异常=`0`。

### 已知质量异常

- 36 mm：pose 005 的 5 帧 manifest 标记 `dynamic_range_low` / `quality_passed=False`。
- 40 mm：25 帧均标记 `dynamic_range_low` / `quality_passed=False`。
- 46 mm：25 帧均标记 `dynamic_range_low` / `quality_passed=False`。

这些是采集质量告警，不是本轮的 ROI 删除规则；是否可用于 q-domain 只能在几何 ROI 人工确认、中心线质量复核后再决定。

## ROI review 输出

`15 geometry candidates generated; manual_review_required=True`

- median image：`roi_review/median_images/`
- median Steger / candidate overlay：`roi_review/overlays/`
- geometry candidate：`surface2_roi_candidates.csv`
- centerline profile：`surface2_centerline_profiles.csv`
- 未冻结 draft：`surface2_roi_registry_manual_draft.json`

人工确认时，只允许依据上述 median 图像、五帧 Steger 点和 physical ground plane geometry 调整 `height_v_range` 与 `baseline_v_ranges`；不要查看或使用 height error/residual。确认后应写出完整的 15-entry manual registry，并将每个 entry 与顶层 `manual_confirmed` 明确置为 true，再进入 Surface-2B。

## Surface-2B 尚未执行的项目

ROI 冻结后，下一轮才可在同一 frozen Ground-1 q 坐标定义下：复用 Frozen C0/C1 计算 q1/q2、用 repeat1 ground proxy 和 repeat2–5 formal 生成 residual，合并已有 30/50 mm，并报告 q2 gap/overlap、q1/q2 coverage、residual continuity 与相近 `(q1,q2)` 的跨 height/position 一致性。本报告不提前推断这些结论。

## 下一步

`Surface-2C` 当前不允许进入。先完成 15 组 ROI 的人工 geometry confirmation；若任一 pose 的物理 ground plane、包边/突起边界或 centerline 质量无法确认，应在 registry/report 中标记该项并重新采集或人工处理，不用 residual 阈值补救。
