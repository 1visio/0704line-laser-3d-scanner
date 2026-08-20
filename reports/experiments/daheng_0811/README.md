# 大恒 0811 实验结论索引

这里仅保留开发阶段仍有参考价值的可读结论和小型 summary。原始图像、逐点 CSV、
中心缓存、批量图片和点云继续保存在本机 artifact 目录，不进入 Git。

本目录是从 `laser_measurement_tool/output_daheng_0811/` 现有结果中整理出的快照；
本轮没有重新拟合或重新计算，也没有新增文件哈希验证。

| 目录 | 内容 | 当前用途 |
|---|---|---|
| `ground_reference_20frames/` | Ground-1 基线报告和 summary | 诊断基线 |
| `ground_pose_invariance_ground_only/` | Ground-2R 姿态不变性报告和 summary | 支持 Ground-3 的输入结论 |
| `ground_spatial_correction_ground3/` | Ground-3 空间补偿报告和 summary | 已通过的候选结果，尚未等同于生产验收 |
| `model_comparison_latest_quadratic_8frames_v2/` | 最新 8 帧模型比较及验证差值 | 当前模型比较结论 |
| `frame_000667_model_test_20mm_v2/` | 单帧 20 mm 对照和在线链路回放检查 | 单帧回归证据 |
| `shadow_frame_000667_c1_4k/` | C1 shadow 集成报告和点集摘要 | 集成检查 |

没有迁移的旧版/重复结果包括：

- `frame_000667_model_test_20mm/`：已有 v2；
- `ground_pose_invariance_20frames/`：报告结论为 board-dependent / blocked；
- `model_comparison/`：旧 5 组协议，保留在本地历史 artifact；
- 每帧 `result.json`、CSV、PLY、PNG、NPY 和 reconstruction metadata：属于展开产物。

开发阶段记录一次实验时，只要求写清：输入数据位置或数据集名称、使用的配置、运行命令、
协议/ROI、结论和日期。文件哈希不是强制项；只有发布、冻结标定包或正式计量复现时再增加。
