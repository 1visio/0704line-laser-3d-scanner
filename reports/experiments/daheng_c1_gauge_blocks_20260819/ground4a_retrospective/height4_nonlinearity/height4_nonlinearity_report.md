# Height-4 高度尺度非线性诊断

- `HEIGHT_DEPENDENCE = SUPPORTED`
- 本轮只做诊断性比较，不重新冻结 scale、affine 或 height-dependent production compensation。
- 50 mm 保持纯 validation 身份：未参与任何趋势拟合、模型选择或参数更新。

## Provenance / reuse audit

- 复用：Ground-4A `session_linear` 的 29 个成功 condition mean；输入 SHA-256：`f069020d7ff84b7189b0c386cd4c2a93bd55ac6753957e48d77b1966ecd47b68`。
- 复用：Height-1 H1/H2 LHO CV 结果；H1 full-data frozen k：`1.004033959133720`。
- 复用：Height-2/3 的 50 mm position/frame metrics；position SHA-256：`c55fc8dff1a42d74af212bf0ed44fd9710dbac09f9a653a16c61da98f4e04901`，frame SHA-256：`78f14944b3dba6b9e6056b7394bb385819da2eb7e83602872d533a85df139c80`。
- 本轮新增：按高度/position 的 descriptive `k_required`、6–30 mm-only trend fit、图表和归因报告。
- 未做：50 mm 拟合 k、重新冻结 affine、修改 C0/C1、修改 G(S) 或生产配置。

## 按高度统计（condition/position mean）

`k_required` 定义为 `true_height / mean(raw_height)`；同时保留 condition-wise k 的均值/范围。1.001 mm 和 2 mm 标为 offset-sensitive，不用于 height trend fit。

| height | scope | n | raw bias | raw MAE | raw RMSE | k_required | k condition-wise mean | k range |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1mm | ground4a_development_condition_mean | 5 | -0.021457 | 0.030346 | 0.034843 | 1.021905 | 1.022703 | 0.987124–1.058239 |
| 2mm | ground4a_development_condition_mean | 4 | -0.026869 | 0.029259 | 0.035036 | 1.013617 | 1.013749 | 0.997616–1.029749 |
| 6mm | ground4a_development_condition_mean | 5 | -0.021820 | 0.023992 | 0.033167 | 1.003650 | 1.003667 | 0.999096–1.010828 |
| 10mm | ground4a_development_condition_mean | 5 | -0.047983 | 0.047983 | 0.051809 | 1.004821 | 1.004825 | 1.002894–1.008453 |
| 20mm | ground4a_development_condition_mean | 5 | -0.088081 | 0.088081 | 0.092413 | 1.004424 | 1.004426 | 1.002460–1.006607 |
| 30mm | ground4a_development_condition_mean | 5 | -0.111811 | 0.111811 | 0.116298 | 1.003741 | 1.003742 | 1.002820–1.005675 |
| 50mm | height50_heldout_position_mean | 5 | -0.104244 | 0.104244 | 0.107384 | 1.002089 | 1.002089 | 1.001248–1.002671 |

## Position k_required（6/10/20/30 mm development + 50 mm held-out）

| position | 6 mm | 10 mm | 20 mm | 30 mm | 50 mm held-out |
|---|---:|---:|---:|---:|---:|
| laser001 | 1.000969 | 1.003200 | 1.002460 | 1.003239 | 1.002500 |
| laser002 | 1.005840 | 1.004754 | 1.004030 | 1.004126 | 1.002253 |
| laser003 | 1.001604 | 1.002894 | 1.003754 | 1.002820 | 1.001248 |
| laser004 | 0.999096 | 1.004825 | 1.005277 | 1.002850 | 1.002671 |
| laser005 | 1.010828 | 1.008453 | 1.006607 | 1.005675 | 1.001776 |

## Constant scale / affine / height-dependent trend

- Constant H1：frozen `k=1.004033959133720`。6–30 mm 的 aggregate k_required 范围为 `1.003650`–`1.004821`；50 mm aggregate 为 `1.002089`，低于 development minimum。
- 50 mm 五个 position 的 k_required 范围为 `1.001248`–`1.002671`，全部低于 frozen H1；这解释了 H1 在 50 mm 的共同过补偿方向。
- 50 mm formal repeat2–5 frame：raw B 的 Bias/MAE/RMSE/P95/Max 为 `-0.104244`/`0.104244`/`0.107396`/`0.133708`/`0.134281` mm；frozen H1 为 `0.097034`/`0.097034`/`0.100440`/`0.140012`/`0.140283` mm，MAE/RMSE 改善但 P95/Max 变差。
- raw bias 的 6–30 mm 诊断直线斜率为 `-0.003679` mm/mm，R²=`0.9676`；6/10/20/30 的 group mean 单调变负。
- k_required 的 6–30 mm 诊断斜率为 `-0.000010599` /mm，R²=`0.0414`；这段内部近似平坦且不呈稳定单调，但 50 mm 出现共同的 high-end drop。
- Affine H2：只引用 Height-1 已有 LHO CV，不在本轮重拟合。LHO-height pooled H1 MAE/RMSE/P95/Max=`0.025658`/`0.030333`/`0.051176`/`0.054080`，H2=`0.023545`/`0.027883`/`0.047175`/`0.053085`；H1 为 6/6 folds 全部改善，H2 为 5/6，不能把 H2 解释为已验证的 50 mm 泛化模型。
- LHO-position pooled H1/H2 MAE=`0.026780`/`0.026564`、RMSE=`0.032050`/`0.031547`；两者均为 5/5 folds 改善，但 H2 Max=`0.070480` 高于 H1 的 `0.065530`。

## 归因结论

- `HEIGHT_DEPENDENCE = SUPPORTED`：支持“raw 高度误差随高度增加而恶化，且 frozen H1 在 50 mm 端点出现共同过补偿”的高度依赖现象。
- 该结论不等于已经识别出可部署的非线性函数：6–30 mm 的 k_required 不完全单调，且 position 间基线不同；50 mm 的 laser003/005 仍比其他 position 更差，提示 position×height/session interaction。
- 因此当前更准确的表述是：高度趋势得到支持，但趋势形状和 50 mm 幅度仍不足以支持重新冻结 affine、spline 或 position-specific 补偿。

## 下一步最有信息量的中间高度

- 首选 `40 mm`；若可增加完整量块，建议 `35/40/45 mm`，每个高度覆盖全部 5 个 laser position，并沿用 repeat1 proxy + repeat2–5 formal held-out protocol。
- 重点观察：raw bias 是否继续单调变负；frozen H1 corrected bias 是否从负跨零并继续变正；k_required 是否在 30–50 mm 单调下降；P95/Max 是否从 35–45 mm 开始恶化；laser003/005 是否持续异常。
- 这些中间高度只用于下一轮 held-out 归因验证，不回填当前 k，也不在本轮生成生产参数。

## 文件

- `height_scale_by_height.csv`、`height_scale_by_position.csv`
- `k_required_vs_height.png`、`height_bias_vs_height.png`
- 本报告中的所有 trend fit 仅使用 6/10/20/30 mm；50 mm 只用于 held-out 对照与状态判断。
