# Auto ROI V2 report｜Session01

本轮只生成 geometry-only Auto ROI V2 candidates、QC、overlay 和 draft registry；没有重跑 Steger、没有重跑 A-13B、没有拟合/修改 C0/C1/Session PnP/Ground/H1/H-B2，也没有写入人工 freeze。

## V1 root cause

V1 failure mechanism 已单独记录在 `auto_roi_v1_failure_audit.md`：profile notch/step peak 被当作 object center，再套固定 `candidate_v ±45 px`；范围/点支持检查没有验证完整的 ground→object-top→ground 结构。

## V2 geometry rule

V2 在 median Frozen Steger `u(v)` 上检测两个相反方向的 transition edges，形成 `stable ground → edge1 → object-top plateau → edge2 → stable ground`。height ROI 使用 `edge1/edge2` 内部并扣除统一 transition safety margin；baseline 由两侧稳定 ground segment 生成，边界裁剪显式记录。所有参数在 `auto_roi_v2_parameters.json` 中统一冻结，本轮没有按 condition 改参数。

Quality gates：两个 edge、object width、interior width、edge margin、plateau slope/roughness/continuity、两侧 ground 稳定性、baseline/height 不重叠、20 repeats formal support。候选未通过时标为 `UNCERTAIN`，不能自动 freeze。

## Provenance / reuse audit

- Frozen cache source hashes: `600/600` match; center points `1672465`; `one_steger_per_frame=True`.
- Median centerline NPZ: `30` conditions; loaded from existing A-13A artifact, not regenerated.
- ROI selection inputs were image/centerline geometry only. V1 ranges were read only for the requested V1-vs-V2 geometry diff and were not used to select V2 edges.

## Development cases

| case | V2 QC | edge1 / edge2 | object width | interior width | reasons |
|---|---|---:|---:|---:|---|
| `h10_p05` | `PASS` | 1273 / 1362 | 89.0 | 60 | none |
| `h20_p03` | `PASS` | 660 / 755 | 95.0 | 66 | none |
| `h30_p04` | `PASS` | 948 / 1040 | 92.0 | 63 | none |
| `h30_p07` | `PASS` | 1842 / 1942 | 100.0 | 71 | none |

四个 development case 均生成了 V1-vs-V2 overlay；本表没有查看或计算任何高度误差。

## All-condition QC

- Conditions run: `30`; PASS `20`; UNCERTAIN `10`; FAIL `0`.
- Object width distribution (px): `{"n": 30, "min": 89.0, "median": 94.5, "max": 120.0, "p05": 89.0, "p95": 111.29999999999998}`.
- Height interior width distribution (px): `{"n": 30, "min": 60.0, "median": 65.5, "max": 91.0, "p05": 60.0, "p95": 82.29999999999998}`.
- Transition exclusion margin distribution (px): `{"n": 30, "min": 15.0, "median": 15.0, "max": 15.0, "p05": 15.0, "p95": 15.0}`.
- V2 center minus V1 center distribution (px): `{"n": 30, "min": -27.5, "median": 5.75, "max": 20.5, "p05": -13.875, "p95": 17.599999999999994}`.
- V2 height width minus V1 height width distribution (px): `{"n": 30, "min": -31.0, "median": -25.5, "max": 0.0, "p05": -31.0, "p95": -8.700000000000017}`.
- Baseline-clipped conditions: `6`.
- Conditions requiring focused human review: `h10_p01`, `h10_p07`, `h10_p10`, `h20_p01`, `h20_p02`, `h20_p10`, `h30_p01`, `h30_p02`, `h30_p03`, `h30_p09`, `h30_p10`.

## V1 versus V2 geometry

`session01_auto_roi_v2_qc.csv` records V1 center/width, V2 center/width, center delta and width delta. These are geometry changes only; no residual/error column is generated or consulted.

## Draft-only boundary

The automatic output is `session01_roi_registry_v2_draft.json`. Every entry has `auto_candidate_generated=true`, `human_reviewed=false`, `human_decision=PENDING`, `manual_confirmed=false`, and `frozen=false`. A manual registry is intentionally not produced in this task. Stop here for genuine human review of all 30 overlays.

## Final flags

```text
ROI_V1_ROOT_CAUSE_IDENTIFIED=YES
AUTO_ROI_V2_IMPLEMENTED=YES
DEV_H10_P05_GEOMETRY_OK=YES
DEV_H20_P03_GEOMETRY_OK=YES
DEV_H30_P04_GEOMETRY_OK=YES
DEV_H30_P07_GEOMETRY_OK=YES
AUTO_ROI_V2_ALL_CONDITIONS_RUN=YES
AUTO_ROI_V2_PASS_COUNT=20
AUTO_ROI_V2_UNCERTAIN_COUNT=10
AUTO_ROI_V2_FAIL_COUNT=0
AUTO_ROI_CAN_FREEZE_WITHOUT_HUMAN=NO
HUMAN_REVIEW_REQUIRED=YES
A13B_V1_INVALIDATED_BY_ROI_SELECTION=YES
A13B_V2_ALLOWED=NO
```

人工 review 完成并生成新的 frozen registry 之前，禁止重跑 A-13B。
