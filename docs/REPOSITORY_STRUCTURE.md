# 仓库目录职责与整理约定

本文档给出仓库当前真实结构、各目录的职责和保留边界。新增文件前先判断它属于
“运行源码、实验工具、可追溯报告、历史参考、原始数据/运行产物”中的哪一类，避免
再次把源码、报告和大体积结果混在一起。

## 1. 当前主线

当前唯一推荐的日常运行主线是 `laser_measurement_tool/`：

```text
online_camera.py
  -> online/ 采集、线程与逐帧处理
  -> laser/ 中心线提取
  -> reconstruction/ 三维恢复
  -> measurement/ 测量
  -> gui/ 显示、交互与导出
```

另外两条链路有独立用途，不应与主线混称：

- `laser_measurement_tool/main.py`：单帧 GUI，不是默认实时入口；
- `laser_measurement_tool/scan_offline.py`：Stage-1 离线/运动学演示入口；
- `src/line_laser_static/`：早期静态扫描头最小包和数据契约，保留作基础链路与回归参考。

## 2. 根目录

| 路径 | 当前内容 | 定位 | 整理约定 |
|---|---|---|---|
| `laser_measurement_tool/` | 实时/单帧/离线扫描工具、标定配置、测试 | **主程序** | 新的产品功能优先放这里 |
| `src/line_laser_static/` | 可安装的静态扫描最小包 | 次级基础链 | 保留；不要再复制一套实时 GUI |
| `tests/` | `line_laser_static` 的仓库级测试 | 次级基础链测试 | 与 `src/` 配套 |
| `tools/` | 大恒量块实验、回放、验证和人工 ROI 工具 | 实验工具 | 脚本必须参数化输入/输出，禁止新增机器绝对路径 |
| `laser_pretest_dataset/` | 预调数据采集与离线质量分析小工具 | 独立实验工具 | 原始数据和结果只留本地 |
| `configs/` | `line_laser_static` 的运行配置 | 次级基础链配置 | 不与主程序 YAML 混用 |
| `calibration/` | `line_laser_static` 的演示/名义标定 JSON | 示例标定 | 非正式测量参数 |
| `data/` | 小型示例、元数据骨架和本地原始数据入口 | 数据入口 | 只提交最小测试样例；`data/raw/` 不入 Git |
| `docs/` | 当前工程使用说明和结构约定 | 当前文档 | 放长期有效、需要持续维护的说明 |
| `reports/` | 算法、性能、实现和变更报告 | 可追溯报告 | 报告可入 Git，大型附件/逐点数据不入 Git |
| `references/legacy_0324/` | 0324 旧工程算法参考副本及来源哈希 | 历史参考 | 不作为运行入口，不做日常开发 |
| `docx/` | 机械/硬件资料、设计文档源文件及导出件 | 文档素材 | 后续可并入 `docs/hardware/`；当前先不批量移动 |
| `final/` | 阶段性交付版文档 | 历史交付 | 后续可并入 `docs/deliverables/`；同名文件先核版本再去重 |
| `outputs/` | 量块评估、人工冻结、留出验证等运行结果 | **本地产物** | 已忽略；不要提交运行内容 |
| `calibrate_chessboard_opencv.py` | 独立 OpenCV 棋盘格标定脚本 | 工具入口 | 后续可移到 `tools/calibration/`，本轮不改路径 |
| `pyproject.toml` | `line_laser_static` 包定义 | 工程配置 | 当前不代表主 GUI 的完整依赖 |
| `pytest.ini` | 主程序测试发现配置 | 工程配置 | 当前默认只运行 `laser_measurement_tool/tests` |

## 3. 主程序内部

| 路径 | 内容 | 约定 |
|---|---|---|
| `online_camera.py` | 推荐实时入口 | README 和用户手册只把它标为默认入口 |
| `main.py` | 单帧测量 GUI | 保留，但明确标成单帧工具 |
| `scan_offline.py` | Stage-1 离线扫描 CLI | 只负责入口编排，核心逻辑放 `scan/` |
| `online/` | 相机 backend、采集/处理线程、帧槽、pipeline、录制 | 实时运行核心 |
| `laser/` | centroid、Steger、shared Steger 中心提取 | 算法实现 |
| `reconstruction/` | 去畸变、激光模型求交、相机/地面坐标转换 | 几何核心 |
| `measurement/` | 地面基准、区域和高度/长度测量 | 计量逻辑 |
| `scan/` | 扫描运动学、session 和点云累积 | Stage-1 扫描核心 |
| `gui/` | 在线/单帧窗口、图像/点云/截面视图 | 界面层，不放算法 |
| `visualization/` | 非 GUI 绑定的可视化辅助 | 避免与 `gui/` 重复实现业务逻辑 |
| `utils/` | 图像与元数据 I/O 等通用辅助 | 只放跨模块复用代码 |
| `configs/` | 主程序 YAML 和设备标定包 | `measure_tool.yaml` 为默认；`v0`/设备日期版是历史或专用配置 |
| `calibration/` | 标定加载/校验代码 | 与根目录示例 `calibration/` 不同 |
| `samples/` | 最小示例输入 | 仅保留可用于文档/测试的小文件 |
| `docs/` | 在线用户手册、配置和补偿说明 | 主程序专项文档 |
| `tests/` | 主程序单元与集成测试 | 功能变更需同步更新 |
| `tools/` | 标定拟合、比较、基准与一次性分析脚本 | 按用途逐步拆为 `calibration/`、`evaluation/`、`debug/` |
| `output/` | 在线测量、录制、Stage-1 扫描输出 | 本地生成，已忽略 |
| `output_daheng_0811/` | 旧大恒实验输入、缓存、逐点结果和报告混合目录 | 本地 artifact；关键结论见 `reports/experiments/daheng_0811/` |

## 4. Artifact provenance / reuse audit

本轮只读审计确认：

- 工作区（不含 `.git`、`.venv`）约 358.5 MiB；`outputs/` 与
  `laser_measurement_tool/output_daheng_0811/` 合计约 324.8 MiB；
- `outputs/` 中的量块实验存在原始版、`manual_frozen`、`manual_frozen_v2` 和
  `ground4a` 等不同协议/冻结版本。即使图片相同，也不能在未比较 manifest、配置、ROI、
  weighting 和验证协议前按目录名删除；
- `output_daheng_0811/` 此前有 299 个 tracked 文件，约 60.5 MB。本轮已把少量可读
  report/summary 复制到 `reports/experiments/daheng_0811/`，并将完整目录从 Git 索引移除；
  本机文件仍然保留，脚本可继续读取；
- `cloud_scan.ply` 与 `cloud_scan.pcd` 是同一扫描的两种导出格式，但 Stage-1 验证脚本会
  同时检查它们，不属于可直接删除的重复文件；
- 未发现 `.pt`、`.pth`、`.onnx`、`.ckpt` 等模型权重或独立 mask 数据集。

实验结果进入 Git 时只保留：

1. `README/report.md`：目的、结论和复现命令；
2. 小型 `summary.json/csv`：数据集名称、配置名称、算法版本、ROI、weighting、CV 协议；
3. 必要的少量最终图。

开发阶段不强制逐文件哈希。只有发布版本、冻结标定包、正式计量验收或需要跨机器严格复现时，
再为关键输入增加哈希；普通调试 run 记录路径、配置名、命令和日期即可。

原始 TIFF、逐点/逐帧大 CSV、中心缓存、overlay 批量图、PLY/PCD 和完整 run 目录放外部
实验归档或 Git LFS。现有 `output_daheng_0811/` 已从 Git 索引移除，后续 clone 不再包含
完整实验 run；需要回放时通过脚本输入/输出参数指定本机 artifact 路径。不要删除本机唯一的
原始 artifact 副本。

## 5. 当前可删除与不可直接删除项

可直接清理：

- `__pycache__/`、`*.pyc`、`.pytest_cache/`、coverage、IDE 缓存和日志；
- 已证明哈希一致、且引用检查为空的重复松散文件；
- 可由同一份输入、配置和版本稳定再生成的本地运行产物，但先确认没有唯一 provenance。

需要先确认或归档：

- `output_daheng_0811/` 和 `outputs/` 下的实验 run；
- `configs/calibration_v0/`、`configs/calibration_daheng_0811/` 等设备/历史标定；
- `docx/` 与 `final/` 的同名文档；
- `references/legacy_0324/`（它是带来源哈希的有意归档，不是普通重复代码）。

## 6. 后续目标结构

优先采用小步迁移，避免一次大搬家造成 import、配置相对路径和历史链接同时失效：

```text
laser_measurement_tool/       主程序
src/ + tests/                 静态基础链
tools/                        参数化实验/维护工具
docs/                         当前说明
reports/                      小型、可追溯实验结论
references/                   只读历史参考
data/                         最小样例与本地数据入口
outputs/                      全部本地运行产物
```

第一优先级不是移动源码，而是停止提交运行产物、标明唯一主入口，并把实验的配置和
provenance 从大文件中拆出来。这样能显著降低远程仓库噪声，同时不破坏当前可运行链路。
