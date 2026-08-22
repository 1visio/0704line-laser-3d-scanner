# Ground-5C A-4.1｜Frozen Session Ground GUI Runtime Integration

日期：2026-08-21  
范围：只接入已冻结的 Ground-5C A-2 `physical_S` Session Linear；不重新拟合、不修改 C0/C1/H1 或 `reconstructor.py`。

## Provenance

- Frozen 参数：`outputs/ground5c_frozen_session_linear_0821/frozen_session_linear.json`
- JSON SHA256：`aca75aa5e7530eb680a6f85231d571065378c4f5f22bcdb3b9d742259df2fe49`
- coordinate：`physical_S`
- formula：`S=(XY-origin_xy) dot direction_xy`
- origin：`[4.345466690716022, 2.878594498981755] mm`
- direction：`[0.012883418031591754, 0.9999170053258537]`，单位向量
- `a_session=-0.000382799377854498`
- `b_session=-0.1969349667207237 mm`
- valid S domain：`[-139.76604886428078, 144.30211420107466] mm`
- fit poses：`001–005`；held-out pose 不进入 runtime 参数

Loader 会校验 schema/status、physical-S formula、单位 direction、有限参数、formal-bin 连续性、fit pose IDs 以及 A-2 禁止项（raw pooling、Z residual filtering、extrapolation、clamp、Factory/Ground-3/H1）。加载后把当前 Session PnP source/generation 绑定到 reference，并保存 JSON SHA 与精简 provenance。

## Runtime chain

复用既有 `FramePipeline`：

```text
Frozen C0+C1 reconstruction
        ↓
points_ground_raw                 （保持不变）
        ↓ 仅在 frozen valid S domain 内 Z -= a*S+b
points_ground / section_xz         （metric view）
        ├─ online point cloud
        ├─ section view
        ├─ online CSV/PLY/JSON export
        └─ MainWindow 单帧分析与高度测量
```

范围外点不修正、不 extrapolate、不 clamp。在线加载已有帧时直接使用其 retained raw ground points 更新显示，不重新调用 `run_frame`，因此不重复激光中心提取。

在线状态区显示 source、coordinate、a/b、valid S range、JSON SHA 和本帧 `applied/out-of-range`；导出 JSON 同时保存 reference provenance 和 runtime counts。

## Height chain

当 `MainWindow` 收到 active `SessionGroundReference` 时，`measure_height_lines(..., ground_correction_mode="session_reference")` 将已 leveled 的 metric points 直接作为输入，以 `Zg=0` 为 ground reference；baseline ROI 仍可保留用于点数/诊断，但不再调用 local `fit_ground_profile`，所以不会二次 ground correction。`height_raw` 完成后才进入既有 Stage-A/H1 链路。

## Invalidation

Frozen reference 只能在有效 Session PnP 下加载。现有 PnP generation/source 失效机制继续生效：Session PnP 更新、恢复 reference extrinsic、断开相机或切换 calibration package 时，pipeline reference 与 GUI handle 都清除；旧 generation 的帧不会重新填充点云。

## Verification

本轮新增/更新测试：

- Frozen JSON 原样加载、SHA/provenance、physical-S 参数和 fit poses 校验；
- valid-domain 内修正、范围外保持 raw；
- `points_ground_raw` 不变；
- GUI Frozen load 受 Session PnP 门控，且加载不重新运行 `run_frame`；
- PnP generation 改变后 reference 失效；
- Session active 时 baseline 不再二次拟合；
- 在线 point cloud/export/单帧分析继续共享同一 reference 对象/应用路径。

通过：

- `test_ground_reference + test_height_measure + test_app_config`：33 passed
- `test_session_gui_integration + test_online_export + test_main_window_save`：11 passed
- `py_compile`：通过
- `git diff --check`：通过

仓库全量 `unittest discover` 仍有若干既有环境相关错误（从子目录运行导致的包根路径导入、既有 C1 默认值断言、在线节流时序断言以及缺少 Stage-1 可选模块）；本轮相关测试未复现失败，未修改这些无关问题。

## Final status

- `GROUND5C_RUNTIME_LOAD = PASS`
- `METRIC_POINT_CHAIN = PASS`
- `RAW_POINT_PRESERVED = YES`
- `PNP_INVALIDATION = PASS`
- `DOUBLE_GROUND_CORRECTION = NO`
