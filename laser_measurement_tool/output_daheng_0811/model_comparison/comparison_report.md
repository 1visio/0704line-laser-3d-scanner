# 0811 Circular Cone / Quadratic Graph 同数据重建比较

## 数据边界与残差定义

- 测量帧：5 组；只读取既有 `laser_center.csv` 和 `height_points.csv` 的 `(u,v)`，未读取原图、未运行中心提取器。
- 测量 `residual(v)`：已选棋盘点重建后的 `Zg(v)`，单位 mm；0811 地面外参把棋盘参考面定义为 `Zg=0`。
- 标定 validation `residual(v)`：模型交点到每幅图真实棋盘平面的有符号距离，单位 mm；直接复用 0811 `pointwise_model_errors.csv`。
- 两模型共用同一内参、地面外参、工作距离、像素点和有效性约束，只替换 laser surface model。

## 已选测量点的 Zg 残差（全部帧）

| model | valid points | valid rate | mean signed (mm) | MAE (mm) | RMSE (mm) | P95 abs (mm) | max abs (mm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| circular_cone | 6002 | 1.000000 | 0.008823 | 0.080325 | 0.095778 | 0.176349 | 0.260455 |
| quadratic_graph | 6002 | 1.000000 | 0.034910 | 0.090770 | 0.122654 | 0.284041 | 0.358144 |

## 标定独立验证集的棋盘平面残差

| model | valid points | valid rate | mean signed (mm) | MAE (mm) | RMSE (mm) | P95 abs (mm) | max abs (mm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| circular_cone | 5400 | 1.000000 | -0.008635 | 0.069361 | 0.083220 | 0.149546 | 0.258878 |
| quadratic_graph | 5400 | 1.000000 | -0.007354 | 0.066710 | 0.080191 | 0.146535 | 0.258603 |

## 判读

- 测量选点：Quadratic Graph 相对 Circular Cone 的 RMSE 差值为 `+0.026876 mm`（负值表示 Quadratic Graph 更小）。
- 标定 validation：Quadratic Graph 相对 Circular Cone 的 RMSE 差值为 `-0.003029 mm`（负值表示 Quadratic Graph 更小）。
- 测量选点按帧看，Circular Cone 在 `laser 002`～`laser 005` 的 RMSE 更小，Quadratic Graph 只在 `laser 006` 更小。
- 测量选点按 v 分区看，`v < 500 px` 时 Circular Cone / Quadratic Graph RMSE 分别为 `0.140055 / 0.226994 mm`；`v >= 500 px` 时分别为 `0.079447 / 0.071037 mm`。Quadratic Graph 的整体劣势主要来自图像顶部低 v 区域的正偏差。
- Circular Cone 复算与原 `height_points.csv` 的逐点 `Zg` 最大绝对差不超过 `6.51e-7 mm`（CSV 小数位舍入量级），确认没有重新提取或改变既有选点。
- 散点和分箱均值见两张 `residual_vs_v_*.png`；逐帧与分箱数字见 CSV。
