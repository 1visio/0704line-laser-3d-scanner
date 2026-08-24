# 实验结果共享索引

本次快照整理于 2026-08-24，来源是本机 `outputs/` 中已经存在的运行产物。
本轮没有重新拟合、重新验证或重新计算；各实验目录中的报告、summary 和
provenance 文件仍是对应结果的主要依据。

整理时所在的代码提交为 `4e2c3cdf83d64140f83baaf4d9c02fc177904962`。当前工作区
同时存在未提交的 `tools/` 改动，因此这个提交号只记录整理时的 checkout，不能单独
证明每个结果都由该提交生成；需要严格复现时，应同时检查各目录内的 provenance、配置、
ROI、weighting 和验证协议。

## 本次同步范围

本次新增 271 个文件，约 16.3 MiB。保留以下类型的可审阅产物：

- `*_report.md`、审计报告和失败分析；
- summary、参数、状态、provenance/audit JSON；
- 小型 metrics、comparison、coverage 和 parameters CSV；
- 少量关键结果图。

仍保留在 `outputs/` 的内容包括原始/逐点/逐帧数据、`cache`、`draft`、`candidate`、
`registry`、中心缓存、批量 overlay/median/review 图像，以及超过 5 MiB 的单文件。
本次特意保留了两个用于追溯的轻量 manifest：`cache_provenance.json` 和
`session01_steger_centers_manifest.json`。

`outputs/**` 的 Git 忽略规则没有修改；完整实验运行目录仍只存在于本机 artifact
目录。其他机器若需要完整逐点数据，应通过外部归档或 Git LFS 获取，而不是假定本目录
包含全部输入和中间结果。

## 实验索引

| Git 共享目录 | 本地来源 |
|---|---|
| `daheng_0822/session01_full_fov_paired_validation/` | `outputs/daheng_0822_session01_full_fov_paired_validation/` |
| `daheng_0822/session01_roi_freeze/` | `outputs/daheng_0822_session01_roi_freeze/` |
| `daheng_c1_gauge_blocks_20260819/acceptance_baseline/` | `outputs/daheng_c1_gauge_blocks_20260819/` |
| `daheng_c1_gauge_blocks_20260819/acceptance_manual_frozen/` | `outputs/daheng_c1_gauge_blocks_20260819_manual_frozen/` |
| `daheng_c1_gauge_blocks_20260819/acceptance_manual_frozen_v2/` | `outputs/daheng_c1_gauge_blocks_20260819_manual_frozen_v2/` |
| `daheng_c1_gauge_blocks_20260819/ground4a_retrospective/` | `outputs/daheng_c1_gauge_blocks_20260819_ground4a/` |
| `daheng_c1_gauge_blocks_20260819/hb2_gui_integration/` | `outputs/daheng_c1_gauge_blocks_20260819_hb2_gui_integration/` |
| `daheng_c1_gauge_blocks_20260819/height_depth_baseline_spatial_audit/` | `outputs/daheng_c1_gauge_blocks_20260819_height_depth_baseline_spatial_audit/` |
| `ground5/ground5a_factory_profile_0821/` | `outputs/ground5a_factory_profile_0821/` |
| `ground5/ground5b_session_linear_minimality_0821/` | `outputs/ground5b_session_linear_minimality_0821/` |
| `ground5/ground5c_frozen_session_linear_0821/` | `outputs/ground5c_frozen_session_linear_0821/` |
| `ground5/ground5c_heldout_validation_0821/` | `outputs/ground5c_heldout_validation_0821/` |

`acceptance_baseline`、`acceptance_manual_frozen` 和 `acceptance_manual_frozen_v2`
刻意分开保存。它们可能对应不同的输入、ROI、weighting 或验证协议；在联合分析前，
不要仅凭目录名把它们合并成同一个结果集。

## 提交边界

提交时只暂存 `reports/experiments/` 下本次新增的共享包，不要使用 `git add -f
outputs/**`。本索引和这些小型实验产物适合作为代码仓库中的可追溯分析记录；完整
运行产物仍按项目约定留在本地或独立数据归档中。
