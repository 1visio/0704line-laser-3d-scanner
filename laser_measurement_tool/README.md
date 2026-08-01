# 单帧线激光三维截面测量工具

从单帧线激光图像提取亚像素中心，恢复地面坐标系点云，并测量障碍物高度与
截面长度。当前快照已内置运行所需的相机内参、激光平面、地面外参和地面 U
向补偿表，可单独复制或克隆本目录运行。

## 运行

```powershell
python -m pip install -r requirements.txt
python main.py
```

默认配置为 `configs/measure_tool.yaml`，其中所有相对路径都以该配置文件所在
目录为基准。内置标定文件位于 `configs/calibration/`，测量结果写入 `output/`。

```powershell
python main.py --config configs/measure_tool.yaml
$env:PYTHONPATH="$PWD;$PWD\.."
python -m unittest discover -s tests
```

## 目录

- `configs/calibration/`：当前设备对应的运行标定与补偿数据。
- `laser/`：centroid、Steger 和 shared Steger 激光中心提取实现。
- `reconstruction/`：像素去畸变、射线与激光平面求交、地面坐标转换。
- `measurement/`：局部地面拟合和障碍物高度统计。
- `gui/`：图像、三维点云和截面交互视图。
- `docs/`：配置、补偿和使用说明。

内置标定只适用于生成这些参数时的相机、镜头、激光器及其安装位置。更换设备
或移动相机/激光器后，必须重新标定并替换 `configs/calibration/` 中对应文件。
