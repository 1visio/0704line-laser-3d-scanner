# Task A-13A｜Session01 PNG replay 与 Geometry-only ROI Freeze

生成时间（UTC）：`2026-08-22T07:10:42.140389+00:00`

## 结论边界

本报告只完成 Session01 原始 PNG QC、Frozen Steger 单次提取缓存、median PNG/median centerline、geometry-only step/notch ROI candidate、review overlay 与 ROI freeze。没有计算 Base/H1/H-B2 高度误差，没有拟合 correction，也没有修改 C0/C1/Ground/H1/H-B2。

上一版 A-13 基于 whole-frame `height_shadow.csv` 的高度/FOV 解释在本报告中废弃：`height_shadow.csv.height_*` 不作正式高度，whole-frame `v_median` 不作 position coordinate；上一版 `FULL_FOV_COVERAGE=NOT_SUPPORTED` 只保留为 shadow-logging QC 历史记录，不能解释为 PNG 采集失败。

## 输入与 provenance

- PNG root: `D:\Docs\linelaserscan\calibration_tool\projects\daheng\outputs\0822\session01`
- Frozen Steger manifest: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\laser_measurement_tool\configs\calibration_daheng_0811\manifest.yaml`; SHA256 `240c6ea407dbb3d46dd3287467cd8e9e1b92ca9a179fe22a94df2a4983eb2f90`.
- Conditions: `30` (`h10/h20/h30 × p01..p10`); repeats/condition: `20`; PNG total: `600`.
- `h10/h20/h30` 在本阶段只保留为 condition label；未发现或使用更精确 certified height，且 nominal truth 没有进入 ROI candidate、ROI range 或 position ordering。
- frames.csv 仅用于 filename/frame identity、OffsetX/Y、曝光、尺寸和采集 QC；没有用作高度或 FOV coordinate。
- `height_shadow.csv` 没有参与本轮 formal ROI、position 或 FOV 计算。

### Session Ground provenance

- `session_ground_calibration.json`: `VALID` / `valid=True`.
- PnP reference R camera→ground: `[[0.9989971277915087, 0.0003664569910963127, 0.0447728084174941], [5.421010862427523e-20, -0.9999665061143105, 0.008184537222028755], [0.044774308083050864, -0.00817632917710942, -0.9989636674959064]]`.
- PnP reference t camera→ground (mm): `[-31.89361181346621, -5.830200567232144, 711.6051137507399]`.
- Session Ground R camera→ground: `[[0.999011111566454, 0.00036355970827463415, 0.04445972099661178], [0.0, -0.9999665677003052, 0.008177009335376075], [0.04446120743702361, -0.008168923185423322, -0.9989777123275737]]`.
- Session Ground t camera→ground (mm): `[-31.67126115868773, -5.824962288392667, 711.6302871366686]`.
- PnP/session delta: `{"translation_mm": 0.2238324208079244, "rotation_deg": 0.01796240817613262}`.
- PnP status: `VALID`; reprojection RMSE: `0.2169045006992862` px; board corners: `88`.
- Ground reference: `VALID` / `VALID`; source `pnp_board_mask`; fit `session_laser_ground`.
- Ground slope/intercept: `0.0002555034429961136` / `-0.13312497186185696`; RMSE `0.05350248072215189` mm.
- Valid S range (mm): `[-130.1993360105663, 121.3555919775798]`; support: `{"enabled": true, "status": "applied", "source": "pnp_board_mask", "mask_mode": "full_board_physical", "corner_count": 88, "pattern_cols": 11, "pattern_rows": 8, "square_size_mm": 20.0, "inset_mm": 0.0, "input_point_count": 2785, "selected_point_count": 2414, "rejected_point_count": 371, "polygon_full_uv": [[1837.674098863649, -152.81945058992596], [3542.2149916669287, 1621.3256359851764], [2225.653879367829, 2912.4830897931765], [493.2028719116488, 1132.3115424273756]]}`.
- Laser-ground sanity: `VALID`; formal chain `['Steger', 'Frozen C0', 'Frozen C1', 'Session ground extrinsic']`; correction applied `False`.

`session_ground_calibration.json` 的 Ground VALID 与 `height_shadow.csv` 的 `ground_reference_status=inactive` 不矛盾：前者是已保存的 Session Ground calibration/sanity provenance，后者是当时 shadow logging measurement path 的应用状态。`height_shadow.csv` 中同时存在 `not_measured`/无效高度状态，因此本阶段不将其当作 Ground 高度测量，也不因 inactive 状态重拟或修改 Ground。

## Raw PNG / frames.csv QC

- 发现条件：`30`；发现 PNG：`600`；预期：`600`。
- `frames.csv` 行数均为 `20`：`True`。
- discovery errors：`none`。
- raw PNG shape/dtype：`3000×480 Mono8`；metadata shape/offset 与 frames.csv 一致：`True`。
- frame gap 非零数：`0`；重复 filename/frame id：`0`。
- 数据完整性判定：`PASS`。

## Frozen Steger replay 与 cache

- 每帧仅通过 `laser_measurement_tool.laser.laser_extractor.extract_laser_center` 调用现有 Frozen Steger；输出先保持 PNG local `(u,v)`，再按该行 frames.csv `OffsetX/Y` 转成 full-sensor `(u,v)`。
- Frozen options：`sigma=1.5, threshold=30.0, deriv_thresh=0.5, roi_margin=48, roi_max_height=512, scan_axis=row`；search ROI 为全幅坐标 `[offset_x=1760, offset_y=0, width=480, height=3000]`，仅是算法搜索边界，不是点选择。
- cache：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_steger_centers.npz`；`one_steger_per_frame=True`；frame entries=`600`；本次是否复用既有兼容 cache：`True`。
- center cache CSV：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_steger_centers.csv`；NPZ 中保存 full-sensor centerline 与 frame offsets，A-13B 应直接复用，不重新提取。
- Extraction 判定：`PASS`。

## Geometry-only ROI protocol

每个 condition 的 20 张 PNG 生成一个 median PNG 和一个 median Frozen Steger centerline。candidate 仅由 image/centerline 的 `u(v)` profile 相对 median background 的 step/notch 几何产生；采用历史 negative-residual detector，并保留 positive-residual polarity 作为同一几何规则下的 PNG replay 兼容分支。

ROI 三段仍遵循历史 gauge-block 协议：`height = candidate_v ±45 px`；`baseline_before = [height_start−220, height_start−20]`；`baseline_after = [height_end+20, height_end+220]`，并检查不重叠顺序。truth height、C0/C1/Ground reconstruction、Base/H1/H-B2 residual、q1/q2 均未参与选择/调整。
- candidates：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_roi_candidates.json`；overlays：`D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\roi_review_overlays`（30 张）。
- Review/freeze：`PASS`；本环境采用逐 condition overlay 的 geometry-only review，并将通过非重叠范围、median centerline formal-point support 的 entries 标为 FROZEN；确认方法在 registry 中明确为 `geometry_only_overlay_review`。
- Edge baseline clipping：`6`/`30` entries；这是 v 边界处按历史协议裁剪到图像范围的记录，A-13B 必须保留该状态并单独报告 baseline support，不得将其当成新增 correction。

## True position v coverage

正式 spatial coordinate 定义为 height ROI 的 `height_roi_center_v`（full-sensor v），并在每个 height 内按该值从小到大生成 `v_order_rank`。whole-frame centerline `v_median` 明确无效，不进入 coverage。
- `h10`：v range `112.5`–`2852.5`；min/max adjacent gap `260.0`/`380.0` px；P01–P10 separation confirmed=`True`；order `['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'p10']`。
- `h20`：v range `62.5`–`2862.5`；min/max adjacent gap `280.0`/`355.0` px；P01–P10 separation confirmed=`True`；order `['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'p10']`。
- `h30`：v range `47.5`–`2897.5`；min/max adjacent gap `285.0`/`360.0` px；P01–P10 separation confirmed=`True`；order `['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'p10']`。
- pooled height-ROI center v range: `47.5`–`2897.5` px.
- v>2200: `True`；v>2400: `True`；v>2600: `True`。
- coverage CSV: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_true_position_v_coverage.csv`；plot: `D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_true_position_v_coverage.png`。

## Formal exclusions and next stage

- 本阶段没有正式高度 truth/error 表，也没有 Base/H1/H-B2 comparison；这些只能在 A-13B 读取本轮 frozen registry 与 cached centerline 后执行。
- 本轮没有新增 correction、没有删 position、没有修改 ROI/ Ground/ C0/ C1，也没有采 Session02。
- A-13B 的输入应使用 `session01_roi_registry_manual.json` 的 height ROI 和 `session01_steger_centers.npz`，不得回退到 height_shadow.csv 或 whole-frame v median。

## Final flags

```text
SESSION01_RAW_PNG_USABLE=YES
SESSION01_STEGER_EXTRACTION_COMPLETE=YES
SESSION01_ROI_REVIEW_COMPLETE=YES
SESSION01_ROI_FREEZE_COMPLETE=YES

WHOLE_FRAME_V_MEDIAN_INVALID_AS_POSITION=YES
HEIGHT_ROI_V_USED_AS_POSITION=YES

P01_P10_POSITION_SEPARATION_CONFIRMED=YES
COVERS_V_GT_2200=YES
COVERS_V_GT_2400=YES
COVERS_V_GT_2600=YES

SESSION01_READY_FOR_A13B=YES
NEW_ACQUISITION_REQUIRED_NOW=NO
```

## Artifact paths

- [session01_raw_png_qc.csv](D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_raw_png_qc.csv)
- [session01_steger_centers.npz](D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_steger_centers.npz)
- [session01_steger_centers.csv](D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_steger_centers.csv)
- [session01_roi_candidates.json](D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_roi_candidates.json)
- [session01_roi_registry_manual.json](D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_roi_registry_manual.json)
- [session01_true_position_v_coverage.csv](D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_true_position_v_coverage.csv)
- [session01_true_position_v_coverage.png](D:\Docs\linelaserscan\0704line-laser-3d-scanner\outputs\daheng_0822_session01_roi_freeze\session01_true_position_v_coverage.png)
