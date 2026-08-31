# C1 / H1 / H-B2 高度补偿交接说明

> 文档目的：说明两个仓库中与 C1、H1、H-B2 相关的脚本、数据流、拟合方法和在线工具接入方式，供后续人员复用、验证和发布。
>
> 快照日期：2026-08-31
>
> 本机实际工作区：D:/Docs/linelaserscan

## 0. 先看结论

这几个名称不在同一层：

| 名称 | 实际作用层 | 核心公式/作用 | 当前结论 |
|---|---|---|---|
| C1 | 激光射线/几何重建层 | lambda_final = lambda_quadratic + F(pca_s) | 已有 C1_4k 冻结文件，另有独立 validation PASS；仍需针对最终 calibration package 做发布前一致性检查 |
| H1 | 最终标量高度测量层 | h_corr = k * h_raw | 当前 Haikang 诊断结论为 H1_INTERPOLATION_ONLY，不能直接当生产补偿；Daheng Stage-A 文件也明确标记为 experimental |
| H-B2 | 最终标量高度测量层，且依赖重建 q2 | h_corr = h_raw - (a0 + a2 * q2) | 有实验冻结候选，production_default=false；q2 越界必须拒绝或仅诊断，不能无界外推 |
| Ground-U / b(v) | 点云 Ground-Z 空间补偿层 | Zg_corrected = Zg_raw - bias(u) | 与 H1/H-B2 不同；当前 Daheng manifest 的 ground_u_compensation 为 null |

因此，“采集不同高度、不同位置的图片后怎么拟合”不能只给一个统一脚本。首先要根据误差表现选择拟合对象：

1. 如果误差来自激光射线在图像位置上的系统性几何偏差，拟合 C1。
2. 如果最终量测高度整体存在比例误差，拟合 H1。
3. 如果最终高度残差随重建后的二次曲面坐标 q2 变化，评估 H-B2。
4. 如果 Ground-Z 随图像列/行发生空间偏差，评估 Ground-U 的 b(u) 或 b(v)。

只拿“不同高度、不同位置的图片”而没有已知真实高度、相机/ROI/曝光/算法配置和独立留出集，不能形成可发布的补偿模型。

## 1. 仓库范围与在线管线

本说明针对：

- 标定仓库：D:/Docs/linelaserscan/calibration_tool
- 在线扫描仓库：D:/Docs/linelaserscan/0704line-laser-3d-scanner

仓库内还有 gitlab-clean 历史/清理副本。本说明以 calibration_tool 和 0704line-laser-3d-scanner 两个主工作副本为准，不以 clean 副本作为运行入口。

在线主链路如下：

    相机采集
      -> Steger / centroid 提取激光中心
      -> 加回硬件 ROI offset，恢复全幅图像坐标
      -> 去畸变 / 激光射线
      -> Quadratic C0
      -> C1 对 lambda 的修正
      -> 相机坐标到 Ground 坐标
      -> Ground-U 点云补偿（如果启用）
      -> 截面与高度量测
      -> H1 或 H-B2 最终标量高度补偿
      -> UI / CSV / shadow metadata

重要边界：

- C1 会进入三维重建，影响点云和后续 q1/q2。
- Ground-U 会修改 Ground 坐标中的 Z，影响点云。
- H1/H-B2 只作用于最终的 raw height，不修改 C0、C1、lambda 或点云坐标。
- 在线 pipeline 初始帧的 shadow metadata 可能以 height_raw=None 调用补偿解析；只有 GUI 完成具体高度量测后，H1/H-B2 才有实际标量输入。

## 2. 相关脚本和入口在哪里

### 2.1 calibration_tool 中的 C1

#### C1 grouped CV 拟合脚本

路径：

    D:/Docs/linelaserscan/calibration_tool/scripts/fit_c1_frozen_quadratic_grouped_cv.py

职责：

- 在已经冻结的 Quadratic C0 上，只拟合低自由度的一维 C1 残差修正。
- 不重新提取激光中心。
- 不重新拟合 C0。
- 不读取 validation 数据。
- 不修改 production config。
- 使用 frame/pose grouped CV，避免把同一帧的点随机拆到训练和测试两侧。

固定协议：

- Full-36 FIT poses。
- 32400 个已存在 residual points。
- 公共 Full-36 PCA-s 域。
- v 方向 100 px bin。
- cubic B-spline（三次 B 样条）。
- 候选模型 C1_3k、C1_4k、C1_5k，分别为 3、4、5 个 interior knots。
- frame-balanced weighting：每一帧总权重为 1。
- Huber IRLS，Huber k=1.345。
- 二阶 smoothness penalty，固定 0.1。
- 6-fold pose-grouped round-robin。

脚本默认输入/输出：

    输入 residual points:
    projects/daheng/outputs/0818/quadratic_residual_observability/quadratic_residual_points.csv

    输入 audit:
    projects/daheng/outputs/0818/quadratic_residual_observability/audit_summary.json

    输入 frozen C0:
    projects/daheng/outputs/0818/c0_freeze/quadratic_graph.yaml

    输出目录:
    projects/daheng/outputs/0818/c1_frozen_quadratic_grouped_cv

脚本会检查以下列是否存在并且一致：

    residual_mm
    residual_centered_mm
    frame_residual_median_mm
    pca_s
    v_px
    frame_id
    split
    quadratic_valid

其中：

    residual_centered_mm =
        residual_mm - frame_residual_median_mm

运行方式：

~~~powershell
cd D:/Docs/linelaserscan/calibration_tool
python scripts/fit_c1_frozen_quadratic_grouped_cv.py --points projects/daheng/outputs/0818/quadratic_residual_observability/quadratic_residual_points.csv --audit-summary projects/daheng/outputs/0818/quadratic_residual_observability/audit_summary.json --frozen-model projects/daheng/outputs/0818/c0_freeze/quadratic_graph.yaml --output-dir projects/daheng/outputs/0818/c1_frozen_quadratic_grouped_cv --folds 6 --overwrite
~~~

#### Operational-35 C1_4k 冻结脚本

路径：

    D:/Docs/linelaserscan/calibration_tool/scripts/freeze_operational35_c1_4k.py

职责：

- 复现既有 C1_4k 协议。
- 使用 35 个 operational poses，排除 frame027。
- 不重新做 candidate selection。
- 不重新做 grouped CV。
- 不重新拟合 C0。
- 不读取 validation。
- 只调用一次 C1_4k 拟合，用于生成可复现冻结产物。

默认输入/输出：

    SOURCE_DIR:
    projects/daheng/outputs/0818/c1_frozen_quadratic_grouped_cv

    OUTPUT_DEFAULT:
    projects/daheng/outputs/0818/c1_4k_freeze

典型输出：

    frozen_c1_4k.json
    frozen_c1_4k_lut.csv
    frozen_c1_4k_freeze_manifest.json

这个脚本不是新数据的通用 fitter。若采集了新的相机、镜头、ROI 或标定姿态，不能只把新 CSV 替换进去就认为仍然兼容；必须重新进行对应的 C0、残差 artifact、C1 和 validation 协议。

#### Ground-U / b(v) 脚本

路径：

    D:/Docs/linelaserscan/calibration_tool/scripts/build_paired_pnp_ground_bias_v.py

职责：

- 使用 paired PnP ground reference 与激光重建结果，构造 image-row v 上的 Ground-Z 残差表。
- 输出 ground_bias_table.csv 和 ground_bias_table.npy。
- 默认支持区间为 300 <= v <= 2699。
- 每个 v 至少有 5 个样本才标记为 support。
- 不插值、不外推、不平滑。

这不是 H1，也不是 H-B2。它修正的是 Ground 点云的 Z，不是 GUI 最终的 scalar height。

### 2.2 calibration_tool 中的命名陷阱

calibration_tool 的 geometry experiment 中可能出现 H1、h001、h002 等多高度实验标签。这些通常是实验条件名称或 ROI 诊断，不代表 0704 在线 correction 模块中的 H1 scalar height model。

此外，某些配置注释中出现 C1 作为阈值/版本注释，例如 threshold_px 的历史备注。这种 C1 与 laser ray correction 的 C1_4k 不是同一个对象。

判断依据应使用：

- C1 激光射线补偿：frozen_c1_4k.json、laser_ray_correction.py。
- H1 标量高度补偿：stage_a_height_scale.py、validate_height_linear_cv.py。

### 2.3 0704 仓库中的 H1

#### H1 拟合与 grouped CV

路径：

    D:/Docs/linelaserscan/0704line-laser-3d-scanner/tools/validate_height_linear_cv.py

职责：

- 输入已经得到的 height condition mean，而不是重新从原始图片提取点。
- 比较 H0、H1、H2。
- H0：不补偿。
- H1：只拟合比例系数。
- H2：拟合比例加截距。
- 支持 Leave-One-Height-Out 和 Leave-One-Position-Out。
- 只用训练组拟合参数，再预测 held-out 组。

默认输入：

    outputs/daheng_c1_gauge_blocks_20260819_ground4a/ground4a_condition_comparison.csv

输入至少需要：

    dataset
    truth_mm
    position_rank
    chain
    successful_repeat2_5
    failed_repeat2_5
    measured_mean_mm

当前脚本只接受 Ground-4A B session_linear 条件链，并要求 30 个 B 条件、29 个成功条件。新数据如果字段不同，应先写一个明确的 adapter（适配器），不要在 fitter 内隐式猜列。

运行：

~~~powershell
cd D:/Docs/linelaserscan/0704line-laser-3d-scanner
python tools/validate_height_linear_cv.py --input outputs/daheng_c1_gauge_blocks_20260819_ground4a/ground4a_condition_comparison.csv --output-dir outputs/daheng_c1_gauge_blocks_20260819_ground4a
~~~

#### Haikang H1 可行性审计

路径：

    D:/Docs/linelaserscan/0704line-laser-3d-scanner/tools/audit_haikang_h1_feasibility_0829.py

配套说明：

    D:/Docs/linelaserscan/0704line-laser-3d-scanner/laser_measurement_tool/docs/HAIKANG_0829_H1_FEASIBILITY.md

职责：

- 复用 H1 的 h_corr = k * h_raw 实现。
- 每个 height x position condition 使用一个中位数/汇总值作为正式拟合样本。
- 20 个 frame rows 主要用于 QC 和 provenance，不应当当作 20 个独立训练样本。
- 进行 3 个 interior LOHO、2 个 endpoint 检查和 10 个 LOPO。
- 只生成诊断结果，不修改 C0、C1、H-B2 或在线配置。

默认输入目录：

    laser_measurement_tool/output_haikang_0828/online_recordings/0829/c0_height_audit/manual_roi_measurement

目录内主要文件：

    manual_h_raw_position_summary.csv
    manual_h_raw_frames.csv
    accuracy_report.json
    report.md

### 2.4 0704 仓库中的 H-B2

#### H-B2 runtime model

路径：

    D:/Docs/linelaserscan/0704line-laser-3d-scanner/laser_measurement_tool/correction/stage_a_height_scale.py

该模块同时实现：

- H1 Stage-A scalar scale。
- H-B2 q2-dependent scalar correction。
- correction mode 的互斥校验。
- q2 越界策略。
- online shadow fields。

H-B2 当前冻结候选：

    D:/Docs/linelaserscan/0704line-laser-3d-scanner/laser_measurement_tool/configs/calibration_daheng_0811/hb2_height_correction.json

当前候选参数：

    model_id: H-B2
    a0_mm: -0.10068827127712787
    a2_mm_per_q2: 0.053274373969597236
    q2_domain: [-0.50189189917237, 1.4605125871893883]
    out_of_domain_policy: reject
    production_default: false

H-B2 的计算定义：

    correction = a0 + a2 * q2
    h_corr = h_raw - correction

其中 q2 不是图片的像素坐标，而是由 Quadratic C0 重建得到的二次曲面坐标。只有图片文件而没有与同一 C0/C1/ROI 配置对应的 q2，就不能正确拟合 H-B2。

#### H-B2 候选冻结脚本与测试

候选冻结脚本：

    D:/Docs/linelaserscan/0704line-laser-3d-scanner/tools/freeze_surface3_hb2_candidate.py

在线 replay：

    D:/Docs/linelaserscan/0704line-laser-3d-scanner/tools/replay_hb2_gui_integration.py

单元测试：

    D:/Docs/linelaserscan/0704line-laser-3d-scanner/laser_measurement_tool/tests/test_hb2_height_correction.py

H-B2 目前只能作为实验候选。尤其不能因为 development 数据上的 RMSE 下降，就把 strict-50 或其他越界高度的外推结果当成生产证据。

## 3. 当前 artifact 状态和可复用边界

这部分是本轮的 artifact provenance / reuse audit（artifact 来源与复用审计）结论。

### 3.1 C1

主要文件：

    calibration_tool/projects/daheng/outputs/0818/c1_frozen_quadratic_grouped_cv/c1_run_manifest.json
    calibration_tool/projects/daheng/outputs/0818/c1_4k_freeze/frozen_c1_4k.json
    calibration_tool/projects/daheng/outputs/0818/c1_validation_c1_4k/c1_validation_manifest.json
    calibration_tool/projects/daheng/outputs/0818/c1_validation_c1_4k/c1_validation_report.md

已知状态：

- 早期 grouped-CV manifest 曾为 C1_STATUS=PARTIAL，且 frame027 处于 quarantine pending recapture 的历史状态。
- 当前冻结文件的 freeze_status 是 FROZEN_FOR_VALIDATION。
- 后续独立 validation manifest 的 C1_VALIDATION_STATUS 是 PASS。
- 该 validation 使用 16 个 validation poses、14400 个点，没有重新拟合 C1、PCA、knots 或 penalty。
- 已报告的 pooled 指标：C0 RMSE 约 0.093428 mm，C1 RMSE 约 0.074269 mm；C1 RMSE 改善约 20.5%，P95 改善约 25.3%。
- 0704 的 calibration_daheng_0811/manifest.yaml 已引用 frozen_c1_4k.json。

注意：

- calibration_tool 中的 frozen_c1_4k.json 与 0704 配置目录中的文件内容一致，差异只是 LF/CRLF 行尾。
- 0704 manifest 使用的 sha256_file 会先将 CRLF 规范化为 LF，所以 raw byte SHA 不同不等于模型内容不同。
- C1 validation PASS 只证明当时的模型/输入/验证协议；最终发布仍要检查 calibration package、manifest、C0、ROI 和运行时配置是否成套一致。

### 3.2 H1

主要文件：

    0704line-laser-3d-scanner/laser_measurement_tool/output_haikang_0828/online_recordings/0829/c0_height_audit/h1_feasibility/h1_feasibility_summary.json
    0704line-laser-3d-scanner/laser_measurement_tool/output_haikang_0828/online_recordings/0829/c0_height_audit/h1_feasibility/h1_feasibility_report.md
    0704line-laser-3d-scanner/laser_measurement_tool/configs/calibration_daheng_0811/stage_a_height_scale.json

Haikang 诊断结果：

- 分类：H1_INTERPOLATION_ONLY。
- interior LOHO 的 MAE/P95 有改善，但 Max 并未全部改善。
- LOPO pooled MAE 从约 0.078566 mm 降到约 0.053145 mm；但 10 个 position fold 中有 8 个存在至少一个变差 condition，最大变差约 0.14958 mm。
- 低端点存在风险，不能据此宣称整个 [2, 30] mm 域都可生产使用。
- 没有生成生产补偿文件，也没有修改生产配置。

Daheng Stage-A 文件：

- status 为 experimental_stage_validated。
- valid domain 为 [1.0, 30.0]。
- scale 约为 1.00403395913372。
- production_calibration=false。
- 来源是一个历史 50 mm held-out 相关 artifact，不应与 Haikang H1 审计结果混用。

因此，当前 H1 的正确表述是“已有可复用的拟合实现和实验参数，但还没有对目标设备、目标 package 和最终运行域完成可发布验收”。

### 3.3 H-B2

主要文件：

    0704line-laser-3d-scanner/laser_measurement_tool/configs/calibration_daheng_0811/hb2_height_correction.json

已知边界：

- frozen=true 只代表参数 artifact 已冻结，不代表 production enabled。
- status 为 experimental_frozen_candidate。
- production_default=false。
- q2 越界默认应 reject。
- clamp 只能用于明确标记的 diagnostic。
- 已有 shadow 数据中出现 HB2_Q2_OOD，因此当前运行域覆盖仍需补采和验收。

### 3.4 Ground-U

当前 Daheng calibration manifest：

    0704line-laser-3d-scanner/laser_measurement_tool/configs/calibration_daheng_0811/manifest.yaml

其中 ground_u_compensation 当前为 null。也就是说，当前这个 Daheng 包并没有真正启用 Ground-U 表。

Ground-U 的生成脚本和 runtime 公式不能替代 H1/H-B2：

    Zg_corrected = Zg_raw - bias(u)

其中 u 是默认 image column；如果配置为 v，则使用 row_v_px。越界行为由 runtime 插值器处理，但正式产物当前不允许擅自外推。

### 3.5 本轮复用与新增计算

本轮复用的结果：

- 复用了现有 C1 grouped-CV、C1 freeze 和独立 validation 的结果与 provenance。
- 复用了现有 H1 LOHO/LOPO 诊断结果。
- 复用了现有 H-B2 候选、q2 域和 runtime 测试定义。
- 复用了现有 Ground-U 生成脚本、manifest 结构和运行时公式。

本轮新增计算：

- 仅做了路径、状态、脚本入口、配置依赖、文件内容和规范化 SHA 的核对。
- 没有重新提取图像、重新拟合 C0/C1/H1/H-B2，也没有生成新的模型 artifact。

## 4. 采集新图像前，先固定协议

### 4.1 推荐的 condition 设计

对于 scalar height H1/H-B2，建议至少构造：

- 高度：2、6、10、20、30 mm；如果实际工作区包含 1 mm 或 30 mm 以上，端点要单独设计。
- 位置：覆盖完整 FOV，至少 10 个固定 position ID，不能只在中心位置采集。
- 每个 height x position condition：至少 20 帧；正式拟合可先将每个 condition 汇总成中位数或稳健均值。
- 独立 validation：换一批采集 session、位置组合或量块重复，不要只从同一组 frame 随机抽样。

建议把数据拆成：

    development/
      raw/<height_id>/<position_id>/<frame files>
      metadata/
      derived/

    validation/
      raw/<height_id>/<position_id>/<frame files>
      metadata/
      derived/

一个可用的 condition 表可以包含：

~~~csv
dataset,condition,height_gt_mm,position_id,position_rank,session_id,frame_count,valid_frame_count,valid_frame_ratio,h_raw_mm_median,h_raw_mm_mean,h_raw_mm_std,q1_mean,q2_mean,q2_in_domain,config_sha256,source_commit
development,h06_p01,6.0,p01,1,session_A,20,20,1.0,6.02,6.02,0.03,0.12,0.31,true,<hash>,<commit>
~~~

每帧表还应保存：

~~~csv
dataset,condition,frame_id,image_path,timestamp,height_gt_mm,position_id,camera_serial,exposure_us,gain_db,pixel_format,roi_offset_x,roi_offset_y,roi_width,roi_height,extractor_method,extractor_profile,valid,h_raw_mm,q1,q2,q2_in_domain,invalid_reason
~~~

### 4.2 必须锁定的变量

同一次拟合 campaign（标定活动）内，必须固定：

- 相机型号、序列号和分辨率。
- 镜头、激光器、机械安装和工作距离。
- 硬件 ROI 和软件 search ROI。
- ROI offset 的坐标约定。
- exposure、gain、pixel format 和 laser power。
- Steger/centroid 方法、sigma、threshold、deriv_thresh、scan_axis。
- C0 激光模型、C1 文件、外参和 session ground 状态。
- 测量窗口、去异常阈值、最少点数和高度统计方式。

尤其要注意：0704 Daheng 配置硬件 ROI 是 offset_x=1760、width=480、全高 3000。在线 pipeline 会把 ROI 偏移加回全幅标定坐标。如果离线脚本忘了加回 offset，后续 C1、q2 和空间误差都会错位。

### 4.3 真实高度和位置不能只存在文件夹名

每个 condition 必须有：

- 可追溯的 height_gt_mm。
- 量块/台阶/基准面的实际测量记录。
- position_id 和实际位置定义。
- 采集顺序和 session_id。
- failed frame 的原因。

如果 ground truth 没有测量记录，只能做趋势图，不能输出可发布补偿。

### 4.4 标定三联图与高度量测图不要混用

calibration_tool 的标准几何采集组是：

1. chess：高曝光、激光关闭。
2. laser：低曝光、激光开启。
3. nolaser：同一低曝光、激光关闭。

三张图之间不移动目标，顺序是 chess -> laser -> nolaser。

这组数据主要服务于内参、激光面、PnP/ground 等几何标定。量块高度补偿数据可以复用相同相机/激光/ROI 协议，但不能把“没有真实高度标签的几何三联图”直接当作 H1/H-B2 拟合样本。

## 5. 先做 artifact provenance / reuse audit

在重新计算前逐项检查：

| 审计项 | 要问的问题 | 不一致时的动作 |
|---|---|---|
| 数据集 | 是同一相机、同一量块、同一 session，还是只是文件名相似？ | 不直接复用，重新建立 manifest |
| 配置 | ROI、exposure、gain、算法参数是否一致？ | 重新提取，至少不能直接复用 pixel residual |
| mask | image ROI、有效行、Ground mask 是否一致？ | 重建 mask 并记录版本 |
| 模型 | C0、C1、外参、Ground model 是否同一版本？ | 重新计算 q1/q2/height |
| weighting | frame-balanced、condition-balanced 还是 point-balanced？ | 保持协议一致，禁止静默改变 |
| CV | grouped by frame、height、position 还是随机 point split？ | 协议不同的结果不能横向当作同一证据 |
| 版本 | script hash、config hash、commit 是否记录？ | 补齐 provenance 后再拟合 |
| 输出 | CSV、JSON、LUT/table 是否由当前输入生成？ | 校验 SHA 和生成时间 |

当前目录中已有多种协议的 outputs，不要只按文件夹名称判断可复用。应优先读取各自的 manifest、report、输入 hash、配置 hash 和 status。

## 6. 高度补偿的拟合流程

### 6.1 先固定 baseline

baseline（基线）应包括：

- 已验证的相机内参。
- 激光模型和 C0。
- C1 文件（如果 C1 已经被接受）。
- 相机到 Ground 外参。
- 固定的 Steger profile。
- 固定的测量窗口和 outlier 规则。

对 H1/H-B2，baseline 的关键不是“把补偿设为 none”，而是要保证 raw height 是由同一个 C0/C1/ROI/测量链得到的。否则拟合出来的 k 或 a0/a2 只是在吸收配置差异。

### 6.2 从图片生成 raw height 和 q2

对每个 frame：

1. 读取图像和 metadata。
2. 用固定 extractor 提取激光中心。
3. 加回硬件 ROI offset。
4. 使用已固定 C0/C1 和外参进行重建。
5. 用既定测量函数得到 h_raw_mm。
6. 同时保存该 frame 的 q1、q2、q2_in_domain。
7. 保存 valid/invalid 及其原因。

H1 只需要 h_raw 和 truth；H-B2 还必须有与同一重建链对应的 q2。

### 6.3 condition 汇总

推荐一个 height x position condition 使用一个稳健统计量：

    h_raw_condition = median(valid h_raw_frame)

同时保存：

- valid_frame_count。
- valid_frame_ratio。
- frame 内标准差或 MAD。
- 被拒绝帧数量及原因。
- q2 的 median、P05、P95、min、max。

不要把 20 个高度重复 frame 当作 20 个独立 position/height 样本。这会人为放大单个 condition 的权重。

### 6.4 H1：只拟合比例

H1 的模型是：

    h_corr = k * h_raw

训练数据为 condition-level 的 raw height 和真实高度：

    x_i = h_raw_i
    y_i = height_gt_i

通过原点的最小二乘比例为：

    k = sum(x_i * y_i) / sum(x_i * x_i)

实现对应于：

    validate_height_linear_cv.py::_fit_parameters(train, "H1")

同时比较：

    H0: h_corr = h_raw
    H1: h_corr = k * h_raw
    H2: h_corr = a * h_raw + b

H2 的截距在工程上容易吸收量块零点、测量窗口、Ground session 和真实装配偏置。因此 H2 即使训练误差更小，也不能自动替代 H1。当前脚本只有在 H1 稳定且 H2 没有一致性优势时才偏向选择 H1。

### 6.5 H1 的 CV 协议

至少执行以下三类评估：

#### Leave-One-Height-Out（按高度留一）

- 每次把一个高度的所有 position 留作测试。
- 其余高度用于拟合 k。
- 评估高度方向的插值/泛化。

#### Leave-One-Position-Out（按位置留一）

- 每次把一个 position 的所有高度留作测试。
- 其余 position 用于拟合 k。
- 评估 FOV 位置泛化。

#### Endpoint holdout（端点留出）

- 最低高度单独测试。
- 最高高度单独测试。
- 不要用内部高度 CV 的结果替代端点结论。

每个 fold 必须只使用训练集拟合 k。最终报告至少包含：

- Bias。
- MAE。
- RMSE。
- P95 absolute error。
- Max absolute error。
- 通过 |error| <= 0.1 mm 和 <= 0.2 mm 的比例。
- 每个 height/position condition 的变差计数。
- k 的 fold mean、std、min、max 和 relative range。

当前 validate_height_linear_cv.py 的已有规则中，H1 需要：

- 两个主要 grouped CV 方向的 fold 指标稳定改善。
- k 的 relative range <= 0.005。
- 否则状态只能是 PARTIAL 或 FAIL，不能发布。

这只是当前仓库协议，不是对所有设备的通用精度门限。生产发布前仍应根据目标规格增加绝对误差、重复性、端点和独立 session 的门槛。

### 6.6 H-B2：拟合 q2 相关残差

先定义每个 condition/frame 的 raw residual：

    r_i = h_raw_i - height_gt_i

当前 H-B2 runtime 的 correction 形式是：

    r_hat_i = a0 + a2 * q2_i
    h_corr_i = h_raw_i - r_hat_i

必须明确：

- q2 的定义来自当前 Quadratic C0。
- q2 的单位、取值范围和符号不能自行改。
- a0 的单位为 mm。
- a2 的单位为 mm/q2。
- q2 域必须从 development 数据的有效观测域定义。
- validation 数据不得反过来扩展 q2 域。

H-B2 的推荐过程：

1. 用固定 C0/C1 重建每个 frame。
2. 保存 h_raw、truth、q2、q2_in_domain。
3. 在 development 集上拟合 a0、a2。
4. 按 height、position 和 q2 区间做 grouped CV。
5. 检查 q2 域两端和完整 FOV。
6. 使用全新的 session/量块做 validation。
7. 只有在 validation 完成后，才考虑生成新的冻结候选。

越界策略：

- 生产默认：reject，并写出明确的 OOD 状态。
- 诊断：可 clamp，但必须写 CLAMPED 状态。
- extrapolate_diagnostic 只能作为诊断数值，不能作为生产补偿行为。

当前 H-B2 候选的 q2 域是约 [-0.5019, 1.4605]。如果新采集数据落在域外，正确动作是记录覆盖缺口并补采，而不是自动拟合/外推扩大域。

### 6.7 C1：如果真正要拟合 C1

C1 不是用 height_gt 直接拟合。它使用激光射线/几何残差：

    lambda_final(s) = lambda_quadratic(s) + F(s)
    residual_after = residual_before - F(pca_s)

因此需要：

- 固定并审计的 C0 quadratic_graph。
- 每个激光中心对应的归一化射线坐标。
- PnP/几何 residual。
- pca_s 和 v_px。
- frame_id、pose_id、split。
- quadratic_valid。
- 经过 audit 的 Full-36 或兼容协议数据。

现有 fitter 的重点是：

- C1 只对 frame-centered residual 拟合。
- frame-balanced，避免某些帧点多就支配模型。
- 使用 grouped CV，不进行 point-wise random split。
- 使用低自由度 cubic B-spline，避免高阶模型吞噪声。
- 最终运行时 clip 到训练 PCA-s 域。

新数据若要重新拟合 C1，必须先回答：

1. C0 是否来自同一相机、同一 ROI、同一激光方向？
2. residual 的定义和符号是否与旧 artifact 一致？
3. PCA center/axis/domain 是否应复用？
4. 采集 pose 是否能形成新的 grouped holdout？
5. 是否需要重新拟合 C0，而不是把 C0 误差交给 C1？

如果其中任一答案是否定，不能直接复用当前 C1_4k。

### 6.8 Ground-U：如果误差是空间 b(u)/b(v)

当同一真实平面在不同图像位置出现 Ground-Z 偏差，应使用 paired PnP ground bias 流程：

    采集 chess / laser / nolaser paired data
      -> PnP ground reference
      -> 激光重建 Ground-Z
      -> 按 u 或 v 聚合 residual
      -> support mask
      -> ground_bias_table.csv / .npy
      -> manifest 引用
      -> runtime subtract bias

当前 builder 的输出没有插值、外推和平滑。支持不足的行保持 NaN/unsupported。不要为了让曲线连续而手工填补缺口。

## 7. 推荐的具体数据处理顺序

把新数据处理成以下阶段，阶段之间产生可审计 artifact：

### Stage 0：原始数据 manifest

记录：

- raw image path 和 SHA。
- camera serial。
- session、height、position、frame。
- exposure、gain、pixel format。
- ROI 和 algorithm config。
- ground truth 来源。

### Stage 1：提取与几何重建

输出：

- laser center CSV。
- validity。
- full-frame pixel coordinates。
- C0/C1 版本。
- reconstructed point/section。
- q1/q2。

### Stage 2：raw height 汇总

输出：

- per-frame raw height。
- per-condition median/mean/std/MAD。
- valid ratio。
- q2 domain coverage。

### Stage 3：development fit

只使用 development 条件：

- H1：H0/H1/H2 + LOHO/LOPO。
- H-B2：a0/a2 + q2-domain + grouped CV。
- C1：residual artifact + grouped spline CV。
- Ground-U：paired PnP residual table。

### Stage 4：独立 validation

validation 数据在 model selection 和 domain definition 完成之前必须保持不可见。验证时只加载冻结模型，不改参数。

### Stage 5：冻结与发布包

输出：

- model JSON/LUT/table。
- provenance JSON。
- source config/script/model hashes。
- validation report。
- 明确的 status 和 production enable flag。

## 8. 如何接入 0704 在线工具

### 8.1 先理解两个配置层

0704 有两个容易混淆的配置层：

1. calibration manifest：描述一套内参、激光模型、外参、Ground-U 和可选 C1 文件。
2. measure_tool YAML：描述相机、extractor、runtime correction mode 和 H1/H-B2 文件路径。

calibration_tool 产出的 calibration_bundle.yaml 与 0704 runtime 使用的 calibration/manifest.yaml 结构不同，不能只改文件名。必须把 release bundle 转换成 0704 runtime manifest。

0704 manifest 需要的主要文件包括：

- intrinsics。
- laser_plane 或对应 runtime laser model。
- extrinsics。
- ground_u_compensation；没有 Ground-U 时也要显式写 null。
- 可选 laser_ray_correction。

H1/H-B2 当前不是 manifest loader 自动读取的字段，而是从 measure_tool YAML 的 correction 区读取。因此：

- manifest 负责几何 package。
- measure_tool YAML 负责 H1/H-B2 runtime mode。
- H1/H-B2 文件必须在 package 目录内，并在交接记录中单独记录 SHA。
- 不能只更新 manifest 而忘记更新 correction。

### 8.2 先备份 0704 现有配置

以下命令只做备份和目录复制，不删除文件：

~~~powershell
cd D:/Docs/linelaserscan/0704line-laser-3d-scanner/laser_measurement_tool
$stamp = Get-Date -Format yyyyMMdd_HHmmss
Copy-Item configs/calibration configs/calibration_backup_$stamp -Recurse
Copy-Item configs/measure_tool.yaml configs/measure_tool_backup_$stamp.yaml
~~~

建议每个发布 package 使用独立目录，例如：

    laser_measurement_tool/configs/calibration_daheng_height_20260831/

目录内放：

    manifest.yaml
    calibration_result.yaml
    quadratic_graph.yaml
    camera_ground_extrinsics.yaml
    frozen_c1_4k.json
    stage_a_height_scale.json
    hb2_height_correction.json
    ground_bias_table.npy
    package_provenance.json

不需要的补偿文件可以不复制，但 manifest 中必须显式写 null 或由当前 loader 支持的值。

### 8.3 manifest 示例

下面是结构示意，文件名和 hash 必须替换成真实发布包的内容：

~~~yaml
schema_version: 1
package_id: daheng-height-20260831-v1

camera:
  model: MV-CS050-60GM
  image_width: 4096
  image_height: 3000

extractor:
  algorithm: steger
  settings:
    sigma: 1.5
    threshold: 30.0
    deriv_thresh: 0.5
    roi_margin: 120
    roi_max_height: 512
    scan_axis: row

files:
  intrinsics:
    path: calibration_result.yaml
    sha256: <normalized-sha256>
  laser_plane:
    path: quadratic_graph.yaml
    sha256: <normalized-sha256>
  extrinsics:
    path: camera_ground_extrinsics.yaml
    sha256: <normalized-sha256>
  ground_u_compensation: null
  laser_ray_correction:
    path: frozen_c1_4k.json
    sha256: <normalized-sha256>

quality:
  acceptance_decision: accepted
~~~

manifest loader 会把 calibration package 内的路径解析到 manifest 所在目录，并校验相对路径和 hash。路径不能越出 package 目录。

### 8.4 生成规范化 hash

0704 的 calibration manifest hash 逻辑会把 CRLF 规范化为 LF。发布前使用与 loader 一致的规则计算：

~~~powershell
cd D:/Docs/linelaserscan/0704line-laser-3d-scanner/laser_measurement_tool
python -c "from pathlib import Path; import hashlib; root=Path('configs/calibration_daheng_height_20260831'); names=['calibration_result.yaml','quadratic_graph.yaml','camera_ground_extrinsics.yaml','frozen_c1_4k.json']; [print(n, hashlib.sha256((root/n).read_bytes().replace(b'\r\n', b'\n')).hexdigest()) for n in names]"
~~~

H1/H-B2 文件当前不由 manifest loader 自动校验，建议把它们的 hash 写入：

    calibration_daheng_height_20260831/package_provenance.json

并在发布报告中同时记录：

- manifest hash。
- H1/H-B2 config hash。
- C1 hash。
- script hash。
- source commit。

### 8.5 measure_tool YAML 示例

建议复制一个已知相机配置，再针对新 package 改路径。不要直接覆盖 measure_tool.yaml；先生成带 package ID 的显式配置。

~~~yaml
schema_version: 1
system: daheng

camera:
  exposure_us: 2000.0
  gain_db: 0.0
  pixel_format: Mono8
  offset_x: 1760
  offset_y: 0
  width: 480
  height: 3000
  timeout_ms: 3000

calibration:
  manifest: calibration_daheng_height_20260831/manifest.yaml
  intrinsics: calibration_daheng_height_20260831/calibration_result.yaml
  laser_model: calibration_daheng_height_20260831/quadratic_graph.yaml
  extrinsics: calibration_daheng_height_20260831/camera_ground_extrinsics.yaml
  ground_u_compensation: null
  laser_ray_correction: calibration_daheng_height_20260831/frozen_c1_4k.json

correction:
  mode: h1
  stage_a_height_scale_enabled: true
  stage_a_height_scale_config: calibration_daheng_height_20260831/stage_a_height_scale.json
  hb2_height_correction_config: calibration_daheng_height_20260831/hb2_height_correction.json
  hb2_q2_policy: reject

extraction:
  method: steger
  profile: realtime_steger.yaml
  steger:
    scan_axis: row
    search_roi:
      offset_x: 1760
      offset_y: 0
      width: 480
      height: 3000

reconstruction:
  enable_laser_ray_correction: true

measurement:
  outlier_sigma_multiplier: 2.0
  outlier_max_iterations: 5
  min_baseline_points: 20
  min_height_points: 20
~~~

模式选择：

- 无高度补偿 smoke test：mode: none。
- H1：mode: h1，stage_a_height_scale_enabled: true。
- H-B2：mode: hb2，H-B2 文件存在，q2 policy 建议 reject。

不要在同一运行配置中同时让 H1 和 H-B2 生效。runtime 的 CorrectionConfig 会校验模式互斥，但交接时仍应保持配置清晰。

### 8.6 当前仓库的显式 Daheng 启动方式

当前 0704 的默认 configs/measure_tool.yaml 不是 Daheng H1 配置，且默认 correction 为 none。必须显式传入 Daheng 配置和 camera backend：

~~~powershell
cd D:/Docs/linelaserscan/0704line-laser-3d-scanner
./.venv/Scripts/python.exe ./laser_measurement_tool/online_camera.py --camera-backend daheng --config ./laser_measurement_tool/configs/measure_tool_daheng_0811.yaml
~~~

如果新配置名为 measure_tool_daheng_height_20260831.yaml：

~~~powershell
cd D:/Docs/linelaserscan/0704line-laser-3d-scanner
./.venv/Scripts/python.exe ./laser_measurement_tool/online_camera.py --camera-backend daheng --config ./laser_measurement_tool/configs/measure_tool_daheng_height_20260831.yaml
~~~

也可以先用 single-frame 入口做不启动相机的配置 smoke test：

~~~powershell
cd D:/Docs/linelaserscan/0704line-laser-3d-scanner
./.venv/Scripts/python.exe ./laser_measurement_tool/main.py --config ./laser_measurement_tool/configs/measure_tool_daheng_height_20260831.yaml
~~~

具体参数以当前版本的 --help 和配置 parser 为准。

### 8.7 在线接入后的验证顺序

#### 配置加载验证

确认：

- system 是 daheng。
- package_id 是预期值。
- manifest 路径和 calibration 文件路径都在目标 package 内。
- C1 manifest hash 通过。
- H1/H-B2 文件存在，且 package_provenance.json 中的 hash 一致。
- extraction method、scan_axis、ROI 和采集时一致。
- H-B2 q2 policy 不是无标记的 extrapolation。

#### 点云/几何验证

使用平面或已知基准面检查：

- C0/C1 是否加载。
- C1 是否出现 CLAMPED/INVALID。
- q1/q2 是否有限。
- Ground-Z 的符号和零点是否与历史配置一致。
- Ground-U 为 null 时，确认没有误启用旧表。

#### scalar height 验证

使用至少一个不参与拟合的已知高度：

- raw height。
- H1 height。
- H-B2 height。
- active correction mode。
- correction status。
- q1/q2。
- q2_in_domain。

对 H1 期望：

    height_h1 = scale * height_raw

对 H-B2 期望：

    height_hb2 = height_raw - (a0 + a2 * q2)

#### 记录文件验证

检查：

- UI 导出的 height fields。
- online recording 的 shadow fields。
- height_shadow.csv。
- correction status 是否区分 NOT_MEASURED、APPLIED、OUT_OF_DOMAIN、CLAMPED 等状态。

特别注意：pipeline 第一阶段可能没有 height_raw，因此不能只看第一帧的 shadow metadata 判断 H1/H-B2 没有接入。要在 GUI 完成一次有效高度量测后检查。

## 9. 发布验收门槛建议

### 9.1 C1

至少满足：

- frozen C1、C0、laser model、ROI 和 manifest 是同一 package。
- 独立 validation 使用冻结模型，不再次拟合。
- pooled 和 top/middle/bottom 分层指标均有报告。
- 无未解释的 C1 clamp/invalid。
- C1 validation 的输入 hash、模型 hash 和脚本 hash 已记录。

### 9.2 H1

建议把以下条件写成项目级 gate：

- LOHO 高度方向改善。
- LOPO 位置方向改善。
- 端点单独通过。
- 独立 session 通过。
- k 的 fold relative range 不超过当前脚本 0.005 规则，或有经过评审的替代阈值。
- 没有不可接受的 worst-condition regression。
- 不把 condition 内重复 frame 数量当作额外样本权重。
- final artifact 的 production_calibration 明确设置前，先完成验证报告。

### 9.3 H-B2

建议把以下条件写成项目级 gate：

- development q2 域清楚。
- independent validation 完整覆盖 production q2 域。
- 生产 q2 越界率为 0，或有明确的产品行为。
- reject/clamp/extrapolate 的状态在 UI 和 CSV 可见。
- 每个高度、每个 FOV position 都有结果。
- 端点和域边界附近有单独验证。
- 一旦改 a0、a2、q2 定义或 q2 域，必须生成新的 candidate version 和新的 validation。

### 9.4 Ground-U

建议把以下条件写成项目级 gate：

- paired PnP reference 和激光重建来自同一采集协议。
- support mask 无未解释的大段缺口。
- 不允许通过手工插值填补 unsupported。
- corrected point-cloud Z 的 P-V、RMS、重复性和 holdout 结果都记录。
- manifest 的 ground_u_compensation path/hash 正确。

calibration_tool README 中已有的 ground compensation P-V、RMS、重复性门槛属于 Ground-U/ground compensation 质量门，不应直接拿来当 H1 scalar height 的替代门槛。

## 10. 常见错误和排查方法

### 错误 1：把 H1 当成 C1

现象：用 height_gt 与 raw height 拟合出了 k，就认为 C1 已完成。

原因：C1 修的是 lambda/射线几何；H1 修的是最终 scalar height。

排查：确认是否有 quadratic residual points、pca_s、v_px、frame_id 和 C0 hash。没有这些就不是 C1 拟合。

### 错误 2：没有加回 ROI offset

现象：中心位置似乎正常，横向位置或整幅 FOV 明显变差，C1/q2 异常。

原因：离线使用了 ROI 内坐标，而 C0/C1 使用全幅标定坐标。

排查：检查 0704 online pipeline 是否将 offset_x/offset_y 加回；检查 CSV 中 pixel coordinate 是否为 4096x3000 全幅坐标。

### 错误 3：把 20 帧当成 20 个独立 condition

现象：某个 position 的 k 支配整体拟合，CV 看起来过于乐观。

原因：重复帧相关，导致不均衡加权。

排查：condition-level 汇总；frame rows 只用于 QC 或稳健统计。

### 错误 4：用同一数据 fit 和 report

现象：训练误差很小，但换一批量块或位置就失效。

原因：没有 grouped holdout 或 independent validation。

排查：检查 report 是否包含 held-out group、输入 hash、validation 是否在 fit 之后才读取。

### 错误 5：H-B2 q2 越界仍然外推

现象：域外 height 数值看起来连续，但实际误差不可控。

原因：把 extrapolate_diagnostic 当成 production behavior。

排查：生产使用 reject；所有 OOD/CLAMPED 必须在 UI/CSV 中可见。

### 错误 6：只更新 manifest，没更新 measure_tool correction

现象：C1 或几何包换了，但 H1/H-B2 仍指向旧文件或 mode:none。

原因：0704 manifest 与 app YAML 是两层配置。

排查：同时检查 manifest、measure_tool YAML、package_provenance.json 和启动命令。

### 错误 7：直接启动默认在线配置

现象：以为启用了 Daheng H1，实际启动了默认配置或 correction none。

原因：measure_tool.yaml 是默认入口；Daheng 配置不是默认配置。

排查：启动命令必须同时带 --camera-backend daheng 和显式 --config。

### 错误 8：看到 raw SHA 不同就认定 C1 文件不同

现象：calibration_tool 与 0704 的 frozen_c1_4k.json SHA 不同。

原因：LF/CRLF 行尾不同。

排查：用 manifest loader 的 CRLF -> LF 规范化 hash 规则，并做内容 diff。

## 11. 后续人员的最短执行清单

### 如果目标是 H1

1. 固定 C0/C1/ROI/Steger/测量方式。
2. 采集 height x position matrix，保留 raw images 和 metadata。
3. 每个 condition 生成 h_raw median 和 truth。
4. 先做 provenance audit。
5. 用 H0/H1/H2 比较。
6. 做 LOHO、LOPO、端点和独立 session validation。
7. 只有 validation 通过后，生成 stage_a_height_scale.json。
8. 在 measure_tool YAML 中设置 mode:h1。
9. 用不参与拟合的量块验证 UI、CSV 和 shadow fields。

### 如果目标是 H-B2

1. 在同一 C0/C1 链上保存每个 frame 的 q2。
2. 拟合 h_raw - truth 与 q2 的关系。
3. 只用 development 定义 a0、a2 和 q2 domain。
4. grouped by height/position/q2 做 CV。
5. 新 session 验证完整域和边界。
6. 生产默认 q2 越界 reject。
7. 在 measure_tool YAML 中设置 mode:hb2。
8. 验证 H-B2 只改变 scalar height，不改变点云坐标。

### 如果目标是 C1

1. 不要从 height summary 开始。
2. 先确认 C0 frozen 和 residual artifact。
3. 检查 residual_centered_mm、pca_s、v_px、frame_id 和 split。
4. 使用现有 grouped spline CV 协议。
5. 确认 C1 domain clip、frame balance、Huber 和 penalty。
6. 用独立 validation 只评估冻结模型。
7. 将 C1 放入 manifest 的 laser_ray_correction，并校验规范化 hash。
8. 在线检查 C1 clamp/invalid 和点云变化。

### 如果目标是 Ground-U

1. 采集 paired PnP ground reference。
2. 使用 build_paired_pnp_ground_bias_v.py。
3. 检查 support mask 和 holdout。
4. 不插值/外推 unsupported。
5. 将 ground_bias_table.npy 放入 package。
6. 更新 manifest path/hash。
7. 确认 H1/H-B2 不会被误认为 Ground-U。

## 12. 主要源码与 artifact 索引

以下行号对应本次审计时的仓库快照；后续提交可能发生偏移，优先以函数名和 manifest 内容为准。

### calibration_tool

| 文件 | 重点 |
|---|---|
| scripts/fit_c1_frozen_quadratic_grouped_cv.py | C1 输入契约、spline、Huber IRLS、frame balancing、grouped CV；约 L1-L232、L514-L537、L710-L727 |
| scripts/freeze_operational35_c1_4k.py | Operational-35 C1_4k 冻结、frame027 排除、Full-36 PCA 复现；约 L280-L329、L352-L398 |
| scripts/build_paired_pnp_ground_bias_v.py | paired PnP Ground-U/b(v) builder；约 L151-L224、L649-L682 |
| projects/daheng/outputs/0818/c1_4k_freeze/frozen_c1_4k.json | 冻结 C1_4k 模型与 provenance |
| projects/daheng/outputs/0818/c1_validation_c1_4k/c1_validation_manifest.json | 独立 C1 validation status |
| projects/daheng/outputs/0818/c1_validation_c1_4k/c1_validation_report.md | C1 pooled/分层验证指标 |
| docs/线激光标定工具用户手册.md | release bundle 到 0704 runtime manifest 的转换和启动说明；约 L738-L896 |
| README.md | CLI、三联图、artifact、bundle/release 总说明 |

### 0704line-laser-3d-scanner

| 文件 | 重点 |
|---|---|
| tools/validate_height_linear_cv.py | H0/H1/H2 公式、LOHO/LOPO、指标、模型选择；约 L125-L195、L231-L302、L391-L472 |
| tools/audit_haikang_h1_feasibility_0829.py | Haikang H1 condition-level 诊断和 H1_INTERPOLATION_ONLY 分类 |
| laser_measurement_tool/correction/stage_a_height_scale.py | H1/H-B2 runtime model、mode、OOD policy；约 L149-L218、L387-L613 |
| laser_measurement_tool/configs/calibration_daheng_0811/stage_a_height_scale.json | Daheng Stage-A 实验配置 |
| laser_measurement_tool/configs/calibration_daheng_0811/hb2_height_correction.json | H-B2 实验冻结候选 |
| tools/freeze_surface3_hb2_candidate.py | H-B2 candidate、q2 domain 和 acceptance plan |
| laser_measurement_tool/reconstruction/laser_ray_correction.py | C1 JSON 加载、PCA-s clip、lambda_final |
| laser_measurement_tool/calibration/manifest.py | runtime package、必需文件、C1/Ground-U optional entry、规范化 SHA |
| laser_measurement_tool/online/pipeline.py | run_frame、重建链和 height shadow metadata |
| laser_measurement_tool/online/window.py | GUI measurement result、导出和 active correction fields |
| laser_measurement_tool/online/recording.py | height shadow recording |
| laser_measurement_tool/online_camera.py | 在线入口参数和 camera backend |
| laser_measurement_tool/configs/measure_tool.yaml | 默认运行配置；当前 correction none |
| laser_measurement_tool/configs/measure_tool_daheng_0811.yaml | 显式 Daheng 配置；当前示例 mode h1，但文件仍为实验配置 |
| laser_measurement_tool/docs/HAIKANG_0829_H1_FEASIBILITY.md | H1 诊断范围、CV 协议和不准生产接入的说明 |
| laser_measurement_tool/tests/test_hb2_height_correction.py | H-B2 公式、OOD 和 mode 互斥测试 |

## 13. 最终交接声明

截至本说明快照：

- C1 有冻结模型和独立 validation PASS 证据，适合作为当前 C1 运行链的复用起点，但发布前仍需按最终 package 重新核 hash 和配置一致性。
- H1 有完整的拟合实现和诊断 artifact，但现有 Haikang 结果只是插值候选；Daheng Stage-A 仍明确是 experimental，不能直接当作生产结论。
- H-B2 有实验冻结候选和 runtime 支持，但 production_default=false，q2 域外必须拒绝或仅诊断。
- Ground-U 是另一条空间点云补偿链，当前 Daheng manifest 仍为 null。
- 本轮没有重新拟合任何模型；后续如采集新数据，应严格区分复用现有 artifact 与本轮新计算，并在新输出中保存输入、配置、脚本、模型和验证集 hash。
