# 线激光预调实验离线分析工具

该工具批量分析不同曝光、材料、工作距离、基线和激光角度下的多帧灰度激光线图像，并生成可直接用于科研组会 PPT 的图片和 CSV 指标。

## 目录结构

```text
laser_pretest_dataset/
├─ scripts/
│  ├─ batch_process.py
│  ├─ laser_extract.py
│  ├─ plot_quality.py
│  └─ config.yaml
├─ metadata.csv
├─ metadata_example.csv
├─ raw/
│  ├─ A001/frame_0001.png
│  └─ A002/frame_0001.png
└─ results/
```

现有 `metadata.csv` 和 `metadata.xlsx` 不会被程序修改。`metadata_example.csv` 仅供复制字段和填写格式时参考。

## 安装与运行

在 PowerShell 中进入本目录：

```powershell
python -m pip install -r requirements.txt
python scripts/batch_process.py --dataset . --config scripts/config.yaml --output results
```

也可以从上级目录运行：

```powershell
python laser_pretest_dataset/scripts/batch_process.py --dataset laser_pretest_dataset --config laser_pretest_dataset/scripts/config.yaml --output laser_pretest_dataset/results
```

退出码为 `0` 表示全部实验组成功，`1` 表示至少一个实验组失败，`2` 表示 metadata 或配置等全局输入无效。单组失败不会阻断其余实验组，原因会写入 `results/metrics_summary.csv`。

## metadata.csv

必须包含以下字段：

```csv
exp_id,image_dir,exposure_us,gain,material,distance_mm,baseline_mm,laser_angle_deg,frame_count,remark
A001,raw/A001,2000,0,white_board,300,80,15,20,基准组
```

- `exp_id` 必须唯一。
- `image_dir` 必须是数据集内部的相对路径。
- 图像文件名必须匹配 `frame_*.png`，程序按数字自然排序。
- `frame_count` 与实际文件数不一致只会记录 `frame_count_match=False`，不会判定实验失败。
- 空白行会被忽略。

## 配置说明

- `roi`：原图绝对坐标；`width` 或 `height` 为 `null` 时延伸到图像边界。
- `gaussian_filter`：只用于逐列定位峰值行，不参与指标计算。
- `peak_window_radius`：灰度重心窗口在峰值上下的固定半径。
- `min_peak_intensity`：原始灰度 DN 的最小峰值阈值。
- `fwhm_ratio`：FWHM 阈值相对于原始峰值的比例，标准半高宽为 `0.5`。
- `min_fwhm_px/max_fwhm_px`：有效线宽范围。
- 两组 `x_positions`：原图绝对列，必须位于 ROI 内。
- `display_min/display_max`：所有图片采用固定显示范围。`display_max: null` 使用数据类型上限，不会逐图归一化；Mono12 保存到 uint16 时建议显式设置为 `4095`。

## 算法与指标口径

程序使用 `cv2.IMREAD_UNCHANGED` 读取单通道 `uint8` 或 `uint16` PNG。ROI 内逐列处理：

1. 可选高斯滤波后定位最大值行。
2. 回到未归一化的原始灰度，在固定窗口内以 `sum(y * I) / sum(I)` 计算亚像素中心。
3. 原始峰值乘以 `fwhm_ratio`，向上下搜索阈值交点并线性插值，得到 FWHM。
4. 峰值不足、重心窗口越界、缺少任一 FWHM 交点或线宽超限时，该列无效，中心和线宽写为 `NaN`。

每组 `metrics.csv` 包含逐帧 `FRAME` 行和一行 `SUMMARY`。统计项包括有效列比例、原始峰值 DN 分布、FWHM 分布，以及跨帧中心重复性的样本标准差。总表 `results/metrics_summary.csv` 每个实验组一行。指标单位仅为 DN 和 px，不含辐射或空间尺寸标定。

## 每组输出

```text
results/<exp_id>/
├─ 01_raw_with_roi.png
├─ 02_intensity_profiles.png
├─ 03_line_width_distribution.png
├─ 04_centerline_overlay.png
├─ 05_repeatability_selected_columns.png
├─ 06_repeatability_std_distribution.png
└─ metrics.csv
```

`01`、`02`、`04` 以自然排序后的第一帧为代表帧；`03` 同时叠加全部帧和逐列均值；重复性图使用全部帧。

## 测试

```powershell
cd scripts
python -m unittest discover -s ..\tests -v
```

测试使用临时合成图片，不修改 `raw`、`results` 或现有 metadata。
