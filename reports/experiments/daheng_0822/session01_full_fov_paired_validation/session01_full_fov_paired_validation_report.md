# Session01 全 FOV H1 vs H-B2 配对验证

- 数据根目录：D:\Docs\linelaserscan\calibration_tool\projects\daheng\outputs\0822\session01
- 输出目录：D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation
- 生成时间 UTC：2026-08-22T06:14:55.141686+00:00
- 本轮只读 validation；未运行新 correction fit、模型搜索、ROI/Ground/C0/C1 修改。

## 最终判定

~~~text
SESSION01_DATA_INTEGRITY=PARTIAL
SESSION01_PNP_GROUND_VALID=YES
SESSION01_FULL_FOV_COVERAGE=NOT_SUPPORTED
EDGE_V_GT_2400_FAILURE_REPRODUCED=PARTIAL

H1_SPATIAL_CONSISTENCY=NOT_SUPPORTED
HB2_SPATIAL_CONSISTENCY=NOT_SUPPORTED

HB2_POSITION_SPREAD_ADVANTAGE_REPRODUCED=PARTIAL
HB2_EDGE_TAIL_PENALTY_REPRODUCED=PARTIAL

PREFERRED_DEPTH_BASELINE_AFTER_SESSION01=UNDECIDED
SPATIAL_RESIDUAL_REPRODUCED_IN_NEW_SESSION=PARTIAL

NEW_SPATIAL_CORRECTION_ALLOWED_NOW=NO
SECOND_INDEPENDENT_SESSION_REQUIRED=YES
~~~

结论边界：raw 采集文件结构完整，但 Session01 没有可用于误差验证的有效 processed height 行。 因此不能把历史 edge failure 或 H-B2 spatial spread 关系判为新 session 的 YES/NO； PARTIAL/NOT_SUPPORTED 是数据可判定性结论，不是算法性能的替代判定。

## 1. 数据完整性与处理覆盖

| 项目 | 数量/结果 |
|---|---:|
| 自动发现 height×position condition | 30 |
| raw PNG | 600 |
| frames.csv 行 | 600 |
| height_shadow.csv 行 | 180 |
| shadow 与 frames.csv camera_frame_number 匹配 | 143 |
| shadow frame id 未在 frames.csv 中 | 37 |
| 有效 processed frame | 0 |
| 有效 processed coverage / raw PNG | 0.0000% |

每个 condition 的 raw PNG 与 frames.csv 均为 20；shadow 行数为 5、6 或 7，按任务约束不要求等于 raw 数。 结构性 raw QC 未发现缺文件、重复 frame id 或 frame gap；但 shadow 行均为无高度结果，且有 37 行不能通过 camera_frame_number 可靠关联。

| height | shadow 行分布 | v_median 位置范围 [px] | >2200 positions | >2400 positions | >2600 positions |
|---|---:|---:|---:|---:|---:|
| h10 | [6, 7] | 1430.0–1476.0 | 0 | 0 | 0 |
| h20 | [5, 6] | 1447.5–1483.5 | 0 | 0 | 0 |
| h30 | [6] | 1436.2–1496.0 | 0 | 0 | 0 |

FOV 解释采用 condition 的 v_median 作为实际 position 坐标。虽然每条 shadow 行的 v_max=2999，这只说明激光点集合延伸到图像底部，不能把它当成十个 position 的 v>2400 空间支持；Session01 实际 position 支持集中在约 1430.0–1496.0 px。

## 2. Truth 与 provenance / reuse audit

未发现 certified-height metadata；本轮对 h10/h20/h30 只使用 nominal truth 10/20/30 mm，没有从 q1/q2/v 或测量结果猜测真实高度。

| artifact | 本轮处理 |
|---|---|
| Session01 session_ground_calibration.json | 读取并保存状态、RMSE、Ground fit/support；不改写 |
| Frozen C0 | 仅 provenance 核查；不重跑/不拟合 |
| Frozen C1 | 仅 provenance 核查；不重跑/不拟合 |
| Frozen H1 | 仅读取 frozen 参数 provenance；不从空结果合成高度 |
| Frozen H-B2 | 仅读取 candidate 参数/domain provenance；不从空结果合成高度 |
| 新增计算 | condition discovery、frame-key join、QC、v rank/coverage、NA 指标表、图、报告 |

Session01 PnP / Ground 状态：

- PnP status/valid：VALID / True
- PnP detection：5_frame_median，corners=88
- PnP reprojection RMSE：0.216905 px
- session ground reference：VALID，source=pnp_board_mask，fit=session_laser_ground
- slope/intercept：0.000255503 mm/mm / -0.133125 mm
- Ground fit RMSE：0.053502 mm；valid s range=[-130.1993360105663, 121.3555919775798]
- Ground support：applied，mask=full_board_physical，input/selected/rejected=2785/2414/371
- laser ground sanity：VALID，RMSE=0.138899 mm，P95=0.215923 mm，Max=0.276316 mm
- calibration warning：['checkerboard_too_close_to_image_edge']；warning 未使 session JSON 失效。

## 3. Pointwise / condition / height metrics

pointwise 表保留了 180 条 shadow diagnostic 行及 frame association、v/q/status 字段；height_raw/height_h1/height_hb2 三列全为空，processed_valid=false，所以 residual、Bias、MAE、RMSE、P95、Max、repeatability 和 H1/H-B2 paired delta 全部按 NA 保留。没有使用 q2 公式补算 H-B2，也没有用 H1 scale 补算 H1。

condition-level、height×position-level 和 pooled rows 仍写出用于审计的结构、n、coverage/status；NOT_SUPPORTED_NO_VALID_PROCESSED_FRAME 表示没有可参与数值计算的行。

## 4. Edge audit：v_median > 2400

本轮按 frame-level v_median > 2400 独立筛选；shadow diagnostic edge n=0，valid edge n=0，因而 Base/H1/H-B2 的 edge 指标、>|0.1|、>|0.2| 和 residual-v Spearman 全部 NA。不能据此声称历史 edge failure 已重现或已消失。

历史 A-11 报告曾在另一套有效 pointwise artifact 上记录：H-B2 position spread 优于 H1，而 H1 edge tail 略优；该历史关系仅作为对照，不被本轮空结果替代。

## 5. 输出文件

- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_ingestion_qc.csv
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_pointwise_paired.csv
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_condition_metrics.csv
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_height_spatial_metrics.csv
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_edge_v_gt_2400_metrics.csv
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_v_coverage.csv
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_full_fov_paired_validation_report.md
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_v_coverage.png
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_position_bias_by_height.png
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_residual_vs_v.png
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_h1_vs_hb2_paired_delta.png
- D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_full_fov_paired_validation\session01_edge_comparison.png

## 6. 禁止项复核

- 未修改 H1/H-B2 参数。
- 未新增 q1/v/spline/LUT correction。
- 未修改 ROI、Ground、C0、C1。
- 未根据结果删除 position。
- 未将 Session01 定义为训练集。
- 未从 raw PNG 重新运行 image/reconstruction pipeline。
