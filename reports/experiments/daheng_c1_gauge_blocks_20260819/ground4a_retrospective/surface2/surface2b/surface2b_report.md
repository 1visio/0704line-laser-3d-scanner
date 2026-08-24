# Surface-2B q1/q2 domain continuity 与 residual consistency 审计

## 结论

`Q2_GAP_FILLED=NO`  
`Q1Q2_STATE_CONSISTENCY=PARTIAL`  
`SURFACE2C_ALLOWED=NO`

判定采用 Surface-1A 已冻结的 Chebyshev q tolerance `0.05`。Residual consistency 的预先固定诊断阈值为：SUPPORTED 要求 condition-pair median ≤ `0.05 mm` 且其 P95 ≤ `0.10 mm`；PARTIAL 上限分别为 `0.10/0.20 mm`。Surface-2C 仅在 q2=YES 且 consistency=SUPPORTED 时放行。

## Frozen provenance 与复用

- 人工 ROI：15/15 confirmed，final SHA `04cbcae3ae58172099509aaca99056a3eb17ea09511fba17974cdd70d1d089de`；draft entries 与 final 完全一致。
- Frozen C0 SHA：`113d3c1b8f92d5a734a2bf612b82a4bd59c0436a89664b5e565e7dd1034bab27`。
- Frozen C1 SHA：`32717a3688905b237b0acbfb54e3290e112bc816c9be1133825d255196801ae3`。
- q1/q2 继续由 Frozen C0 的 `P_c0=lambda_c0*[xn,yn,1]` 及 Surface-1A center/scale 计算；C1 后坐标没有参与 q 定义。
- 30/50 mm 正式点直接复用 Surface-1A；36/40/46 mm 复用 75 帧一次-Steger cache，并用 frozen ROI 新增重建。
- repeat1 仅拟合当前 height×spatial-position 的 session-linear ground proxy；repeat2–5 为 formal。
- 未重拟 C0/C1，未按 residual 修改 ROI，未拟合 S0/S1/S2、Δh、Δlambda，也没有 random point split。

## Height-level q domain 与 C1 clamp

| height | analysis points | q1 min | q1 P05 | q1 median | q1 P95 | q1 max | q2 min | q2 P05 | q2 median | q2 P95 | q2 max | C1 clamp / formal valid |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 1347 | -1.6220 | -1.5983 | 0.8147 | 2.0365 | 2.0602 | 0.1625 | 0.1633 | 0.1880 | 0.2444 | 0.2453 | 0/1443 (0.00%) |
| 36 | 1461 | -1.5387 | -1.5138 | 0.1387 | 1.8685 | 1.9002 | -0.0853 | -0.0838 | -0.0462 | -0.0038 | -0.0025 | 0/1672 (0.00%) |
| 40 | 1438 | -1.5285 | -1.4902 | -0.1623 | 1.8048 | 1.8295 | -0.2514 | -0.2504 | -0.2054 | -0.1707 | -0.1691 | 0/1676 (0.00%) |
| 46 | 1459 | -1.6152 | -1.5906 | 0.2284 | 1.7901 | 1.8145 | -0.5019 | -0.5005 | -0.4644 | -0.4203 | -0.4186 | 0/1620 (0.00%) |
| 50 | 1100 | -1.5719 | -1.5530 | 0.0121 | 1.8073 | 1.8288 | -0.6643 | -0.6637 | -0.6231 | -0.5861 | -0.5854 | 0/1176 (0.00%) |

Clamp rate 的分母是 frozen C1 重建成功的 formal height ROI 点；clamp 表示 Frozen C1 evaluator 在冻结 domain 边界取值，没有 extrapolation。

## q2 相邻 coverage

q2 median 的 30→50 方向为 `decreasing`；严格有序=`True`。

| adjacent height | median Δq2 | full gap | full overlap | P05–P95 gap | P05–P95 overlap | robust gap≤0.05 |
|---|---:|---:|---:|---:|---:|---|
| 30→36 | -0.23421 | 0.16501 | 0.00000 | 0.16719 | 0.00000 | False |
| 36→40 | -0.15924 | 0.08371 | 0.00000 | 0.08687 | 0.00000 | False |
| 40→46 | -0.25899 | 0.16724 | 0.00000 | 0.16996 | 0.00000 | False |
| 46→50 | -0.15866 | 0.08351 | 0.00000 | 0.08564 | 0.00000 | False |

## 相近 q1/q2 的 residual consistency

- 跨高度 condition-pair 数：`0`。
- 有近邻匹配的相邻 height pair：`[]`，共 `0/4`。
- condition-pair median absolute residual difference 的中位数：`None` mm。
- 上述 condition-pair median 的 P95：`None` mm。
- condition-pair P95 absolute difference 的中位数：`None` mm。

按 q1 rank 对齐的 20 个相邻高度 condition（仅作趋势描述，不冒充同 q 状态）中，residual bias 的 |Δ| median/P95/max 为 `0.0241/0.0447/0.0449 mm`。因此 residual-vs-height/q2 的离散轨迹没有突跳证据，但缺少 q-domain overlap，最多只能判为 `PARTIAL`。

由于相邻高度 q2 band 均没有进入 frozen q tolerance，本轮没有可辨识的跨高度“同一 q1/q2 状态”样本；因此不能升级为 `SUPPORTED`。这里的 `PARTIAL` 只来自 rank-level 趋势连续，不能解释为已经验证了同状态 residual 一致。

所有跨高度/空间比较使用实际 q1，并在每个高度内按 formal-analysis q1 median 从小到大定义 `position_rank=1..5`。原始 pose_id 只保留作 acquisition provenance，绝不直接作为跨高度统一位置。

### 按 q1 / position_rank 的描述性结果

| height | q1 rank | source pose | q1 median | q2 median | residual bias mm | RMSE mm | P95 abs mm |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 1 | 001 | -1.5761 | 0.2440 | -0.0969 | 0.0974 | 0.1144 |
| 30 | 2 | 002 | -0.3948 | 0.2194 | -0.1233 | 0.1242 | 0.1455 |
| 30 | 3 | 003 | 0.8064 | 0.1884 | -0.0843 | 0.0849 | 0.1003 |
| 30 | 4 | 004 | 1.3842 | 0.1728 | -0.0851 | 0.0871 | 0.1129 |
| 30 | 5 | 005 | 2.0101 | 0.1639 | -0.1693 | 0.1700 | 0.1951 |
| 36 | 1 | 005 | -1.4820 | -0.0045 | -0.0739 | 0.0755 | 0.0999 |
| 36 | 2 | 004 | -0.6865 | -0.0179 | -0.1206 | 0.1219 | 0.1514 |
| 36 | 3 | 003 | 0.1113 | -0.0456 | -0.0599 | 0.0624 | 0.0895 |
| 36 | 4 | 002 | 1.0095 | -0.0651 | -0.1190 | 0.1195 | 0.1411 |
| 36 | 5 | 001 | 1.8396 | -0.0831 | -0.1455 | 0.1467 | 0.1777 |
| 40 | 1 | 001 | -1.4749 | -0.1713 | -0.0895 | 0.0922 | 0.1232 |
| 40 | 2 | 002 | -1.0067 | -0.1757 | -0.0908 | 0.0950 | 0.1340 |
| 40 | 3 | 003 | -0.1794 | -0.2047 | -0.0734 | 0.0750 | 0.0983 |
| 40 | 4 | 004 | 0.7819 | -0.2277 | -0.0743 | 0.0764 | 0.1066 |
| 40 | 5 | 005 | 1.7734 | -0.2498 | -0.1374 | 0.1386 | 0.1697 |
| 46 | 1 | 005 | -1.5634 | -0.4211 | -0.1290 | 0.1312 | 0.1660 |
| 46 | 2 | 004 | -0.9113 | -0.4268 | -0.1357 | 0.1386 | 0.1764 |
| 46 | 3 | 003 | 0.2501 | -0.4649 | -0.1040 | 0.1066 | 0.1437 |
| 46 | 4 | 002 | 1.1280 | -0.4862 | -0.1059 | 0.1074 | 0.1333 |
| 46 | 5 | 001 | 1.7534 | -0.5000 | -0.1151 | 0.1175 | 0.1529 |
| 50 | 1 | 005 | -1.5327 | -0.5866 | -0.0886 | 0.0896 | 0.1097 |
| 50 | 2 | 004 | -0.8644 | -0.5936 | -0.1332 | 0.1339 | 0.1539 |
| 50 | 3 | 003 | 0.0189 | -0.6233 | -0.0623 | 0.0635 | 0.0814 |
| 50 | 4 | 002 | 1.1976 | -0.6505 | -0.1123 | 0.1132 | 0.1327 |
| 50 | 5 | 001 | 1.7870 | -0.6633 | -0.1247 | 0.1252 | 0.1423 |

绝对 bias 最大的三个 condition（仅报告、不删点）：30mm/rank5=-0.1693 mm; 36mm/rank5=-0.1455 mm; 40mm/rank5=-0.1374 mm。

## 异常 height/position

- 无 condition-level clamp 或 formal repeat 缺失。

新数据 15 个 repeat1 proxy 均成功：`15/15`。

## 输出

- `surface2b_samples.csv`：30/36/40/46/50 mm formal q/residual 点及 analysis flags。
- `surface2b_frame_metrics.csv`、`surface2b_ground_proxy_metrics.csv`、`surface2b_clamp_statistics.csv`。
- `surface2b_domain_statistics.csv`、`surface2b_condition_statistics.csv`。
- `surface2b_q2_gap_overlap.json`、`surface2b_q_near_pair_metrics.csv`、`surface2b_rank_residual_continuity.csv`、`surface2b_summary.json`。
- `surface2b_q1_q2_coverage.png`、`surface2b_q2_vs_height.png`、`surface2b_raw_residual_vs_q2.png`。
