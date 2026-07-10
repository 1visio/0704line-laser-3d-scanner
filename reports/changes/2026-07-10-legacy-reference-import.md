# 旧线激光算法参考代码迁入与可行性分析

- 日期：2026-07-10
- 来源分析：G:/dev/projects/0514_ruanzhu/新线激光系统可复用代码分析.md
- 源码来源：G:/dev/projects/0324line_3d
- 结论：Windows/Python 路线可行；旧算法可作为基线，但必须隔离旧几何参数并适配黑白蓝光图像

## 主要改动

1. 原样复制激光平面标定、ROI/Steger 中心线、单帧求交和批量导出相关源文件。
2. 新增 SHA-256 来源清单和完整性测试，确保参考副本可追溯。
3. 刻意不复制旧 config_plane_*，阻止旧 K/D、激光平面和安装参数误入新设备。
4. README 标注各文件用途、适配边界、Windows 依赖和嵌入式迁移路线。
5. pyproject.toml 新增 legacy-reference 可选依赖，不增加默认最小工程负担。

## 可行性判断

| 部分 | 可行性 | 判断 |
|---|---|---|
| Windows/Python 离线调试 | 高 | 代码仅需 NumPy/OpenCV，评估图额外需要 Matplotlib，不依赖 ROS |
| 激光平面几何与拟合 | 高 | 棋盘位姿、反投影、平面拟合和残差报告可复用；K/D 与数据必须重做 |
| ROI + Steger 中心线 | 高 | 核心亚像素算法可复用；新图像需重新设置 ROI、灰度和特征值阈值 |
| 旧颜色预处理 | 低 | 旧代码面向红激光 BGR；450 nm 蓝光黑白相机必须改用 Mono8/暗场差分 |
| 单帧三维求交 | 高 | 公式可复用；应输出相机坐标系毫米点，不沿用旧机器人姿态和 flip_robot_y |
| 批量导出 | 中 | 文件发现和导出结构可复用；旧配置构造、字段单位和坐标修正需替换 |
| 嵌入式迁移 | 中高 | 先冻结 Python 参考结果，再只迁移 remap、预处理、Steger 等耗时热点 |

## 推荐代码流程

~~~mermaid
flowchart LR
    A["新相机 K/D"] --> B["新 board/laser 图像对"]
    B --> C["复用标定几何<br/>灰度差分 + 亚像素交线"]
    C --> D["新激光平面<br/>留出验证"]
    D --> E["Mono8 暗场/背景差分"]
    E --> F["复用 ROI + Steger"]
    F --> G["final_points_uv_global"]
    G --> H["本项目 RayPlaneReconstructor"]
    H --> I["相机系 mm 点云"]
    I --> J{"验收通过？"}
    J -->|是| K["冻结算法与参数"]
    J -->|否| L["按预处理→ROI/阈值→几何顺序调整"]
    L --> E
~~~

### 图例

- 复用：保留已有几何、Steger 和批处理结构。
- 新设备输入：K/D、激光平面、图像和阈值全部来自新设备。
- 安全边界：不复制旧 config_plane_*，不使用旧机器人安装变换。
- 阶段门：只有有效率、断线、重复性和三维误差同时通过才冻结算法。

## 参考副本

参考目录：references/legacy_0324/

- laser_plane_calibration.py
- laser_stripe_subpixel_module_v2.py
- src/red_filter_preprocess_v3_reusable.py
- ablation_v1_runner.py
- src/linelaser0319_reusable.py
- export_v1_roi_centerline_batch.py
- src/__init__.py
- README.md
- SOURCE_MANIFEST.json

## 验证结果

| 检查 | 结果 |
|---|---|
| 新旧文件 SHA-256 | 7/7 一致 |
| unittest | 5/5 通过 |
| compileall | 通过 |
| laser_plane_calibration.py --help | 通过 |
| export_v1_roi_centerline_batch.py --help | 通过 |
| 标定、Steger、求交公开符号导入 | 通过 |
| 旧 config_plane_* 未复制 | 通过 |

## 不重复开发算法的判定

在 20–50 张新设备图像上固定参数，若有效中心点比例不低于 95%，无系统性跳线，固定平面
重复性和最终平面/台阶三维误差满足项目验收标准，则直接冻结这套 ROI + Steger 基线，不再
重复开发条纹提取算法。若不通过，先替换 Mono8 预处理并单变量调整 ROI/阈值；只有基础链路
仍不达标时再引入更复杂的连续跟踪。

## 下一步

等待真实相机内参后，新增薄适配层：从本项目 JSON 加载 K/D 和新激光平面，将 Mono8
预处理结果送入旧 Steger 函数，再把二维中心点交给本项目 RayPlaneReconstructor。参考副本
本身继续保持原样，用作结果对照和回归依据。
