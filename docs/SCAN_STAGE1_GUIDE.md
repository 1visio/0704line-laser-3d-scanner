# Stage-1 离线扫描验证指南

## repeat-one 的含义

`repeat-one` 是运动学软件演示，不是真实扫描。程序读取一张真实的单帧
激光图像，仍然只调用现有的激光中心提取、标定 manifest 和
`reconstruct_uv_to_ground()`（包括 `circular_cone` 模型）得到
相机坐标系点云 `points_camera`。随后把同一组 `points_camera` 依次赋予
多个模拟俯仰角，通过通用旋转轴变换到统一的 scan 坐标系并累积。

因此该模式用于验证：

- `Pc → Ps` 的扫描运动学变换；
- 多帧 profile/点云累积和 PLY、PCD 输出；
- 从真实图像到扫描输出的软件数据流。

它不能用于评价真实扫描精度，也不能用于推断真实电机运动或真实物体
表面形状。每次 `repeat-one` 输出的 `source.json` 和 `result.json` 都会
明确写入 `kinematic_demo_only: true`。

## ROI 图像坐标

如果图像是硬件 ROI（尺寸小于 calibration manifest 中的全幅尺寸），离线
扫描会优先读取图像同名 sidecar JSON、同目录 `result.json`，以及录制目录
的 `frames.csv` 中的 `offset_x/offset_y`。没有合法偏移时会拒绝运行，避免
把 ROI 局部像素误当作全幅标定坐标。程序不会复制或修改原始图像。

## Windows PowerShell 示例

在仓库的 `laser_measurement_tool` 目录执行：

```powershell
cd D:\Docs\linelaserscan\0704line-laser-3d-scanner\laser_measurement_tool
..\.venv\Scripts\python.exe scan_offline.py `
  --config configs\measure_tool.yaml `
  --scan-config configs\scan_stage1.yaml `
  --mode repeat-one `
  --image "D:\实际路径\test.tif"
```

扫描成功后，终端会打印帧数、角度范围、scan 点数、坐标单位以及 PLY/PCD
路径。每次运行都会创建新的 `scan_YYYYMMDD_NNN` Session，不会静默覆盖
已有实验；单帧中心提取失败或点数为零的帧会带有 `WARNING frame_index=...`。

该阶段不连接真实电机、不使用 ICP，也不包含 GUI 扫描控制。
