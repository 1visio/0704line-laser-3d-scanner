# 0324 旧工程算法参考副本

本目录保存从 G:/dev/projects/0324line_3d 原样复制的算法文件，用于新静态扫描头的实现
参考和结果回归。副本日期为 2026-07-10；源文件与副本 SHA-256 一致。

这些文件不是新设备的默认运行代码。旧设备配置、数据和输出没有复制，原始工程也没有被修改。

## 文件用途

| 文件 | 可复用部分 | 新设备必须替换 |
|---|---|---|
| laser_plane_calibration.py | 棋盘位姿、板面交线反投影、鲁棒平面拟合、残差报告 | 默认路径、K/D、棋盘尺寸、红光预处理参数和全部标定图像 |
| laser_stripe_subpixel_module_v2.py | 候选筛选、逐列亚像素、动态规划主路径 | 条纹方向、宽度、阈值和质量门槛 |
| src/red_filter_preprocess_v3_reusable.py | 背景抑制、局部残差、顶帽和分支融合结构 | 450 nm 黑白相机不能照搬红色通道分支 |
| ablation_v1_runner.py | UndistortRemapCache、LaserLineExtractorROI、Steger 与计时/指标结构 | 顶层旧配置导入、R-G 预处理、机器人坐标变换 |
| src/linelaser0319_reusable.py | Steger 亚像素实现、射线和平面求交公式 | 文件内全部默认 K/D、平面、安装姿态和阈值 |
| export_v1_roi_centerline_batch.py | 图片发现、逐帧导出、叠加图、CSV 和统计报告 | 旧配置构造、米/毫米字段、flip_robot_y |

完整来源和哈希见 SOURCE_MANIFEST.json。

## 为什么可在 Windows/Python 推进

- 六个算法文件均为普通 Python、NumPy、OpenCV；只有评估绘图额外使用 Matplotlib。
- 激光平面标定、单帧中心线和单帧点云不依赖 ROS、rosbag 或 ROS 消息。
- 输入可直接使用厂商 SDK 保存的无损图像，输出为 PNG/CSV/文本，便于离线回归。
- 当前 Windows 环境已验证 NumPy 2.4.3、OpenCV 4.13.0、Matplotlib 3.10.8 可导入。

## 必须避免的误用

1. laser_plane_calibration.py 内仍保留旧绝对路径和旧 K/D，只能作为参考。CLI 没有
   K/D 参数；新系统应通过 LaserPlaneCalibrationConfig 显式传入新标定值。
2. ablation_v1_runner.py 顶层导入未复制的旧 config_plane_*。这是有意的安全阻断，
   防止新设备误用旧激光平面。后续应从本项目 JSON 配置构造 Legacy0319Config。
3. preprocess_rg_difference_legacy0319() 假设输入为红激光 BGR 图。新方案是蓝光黑白相机，
   应改为 Mono8 暗场扣除/背景差分，再把灰度结果交给同一 Steger 函数。
4. LaserLineExtractorROI.points_3d 已进入旧机器人坐标系。静态阶段应使用
   final_points_uv_global，再接本项目 RayPlaneReconstructor 输出相机坐标系毫米点。
5. 不使用旧 Legacy0319RobotInstall、flip_robot_y 或默认 plane_abcd 修正坐标。

## 新内参完成后的建议顺序

~~~mermaid
flowchart LR
    A["新相机 K/D<br/>冻结分辨率与焦点"] --> B["board_*/laser_*<br/>多姿态图像对"]
    B --> C["参考平面标定流程<br/>灰度差分 + 亚像素交线"]
    C --> D["新 laser_plane<br/>独立留出验证"]
    D --> E["Mono8 预处理<br/>暗场/背景差分"]
    E --> F["ROI + Steger<br/>final_points_uv_global"]
    F --> G["本项目 RayPlaneReconstructor<br/>相机系 mm"]
    G --> H["CSV/PLY + 验收指标"]
~~~

图例：

- 参考平面标定流程：复用几何与拟合，不复用默认参数。
- ROI + Steger：优先保留旧算法，只针对新图像重新扫阈值。
- 本项目重建器：统一坐标、单位和无效点规则，隔离旧机器人安装变换。
- 验收指标：有效率、断线、重复性、平面/台阶三维误差共同决定是否继续复用。

## 测试决策

在 20–50 张新设备静态图像上固定参数测试。若有效中心点比例不低于 95%，无系统跳线，
固定平面重复性和最终三维误差满足项目验收标准，则冻结该算法版本，不重复开发新的条纹
提取方法。若失败，按“Mono8 预处理 → ROI/阈值 → Steger 参数 → 标定几何”的顺序单变量
调整；只有基础链路仍不达标时才评估更复杂的连续跟踪算法。

## 嵌入式迁移边界

Windows/Python 适合当前标定和算法冻结。稳定后优先固化 JSON 数据契约和测试图集，再在
目标 ARM/x86 平台验证 NumPy/OpenCV 可用性。若帧率不足，只迁移耗时热点
（去畸变 remap、预处理、Steger）到 C++/OpenCV 或平台加速库，保留 Python 参考结果作为
逐点回归基准；标定和报告工具无需首批迁入设备端。
