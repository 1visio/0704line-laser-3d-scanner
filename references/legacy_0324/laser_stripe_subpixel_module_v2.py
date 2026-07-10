
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np


# =========================
# 数据结构
# =========================

@dataclass(frozen=True)
class LaserStripeSubpixelConfig:
    """
    改进版：支持“多段合法激光线段”的亚像素提取。

    关键修改：
    1) main_component_mask 不再默认只保留“面积*长宽比”最高的一个连通域；
    2) 改为保留一组“足够长、足够细、方向一致”的线状连通域；
    3) 默认对每个保留下来的连通域分别做亚像素提取，再把结果拼接；
    4) 更适合激光面落在多个台阶/遮挡物体表面时出现的多段断裂条纹。
    """

    # ---------- 候选掩膜 ----------
    candidate_threshold: int = 24
    use_otsu_fallback: bool = True
    close_kernel: int = 3
    open_kernel: int = 0

    # ---------- 连通域筛选 ----------
    min_component_area: int = 80
    min_component_aspect: float = 2.0
    min_component_span: int = 120
    component_area_ratio_to_best: float = 0.08
    component_angle_tolerance_deg: float = 12.0

    # 兼容旧接口：若为 True，退化为只保留“最优一个”连通域
    keep_only_best_component: bool = False

    # 是否对保留的每个连通域分别做一遍亚像素提取
    extract_components_individually: bool = True

    # ---------- 列扫描 / 条纹宽度 ----------
    min_stripe_width: int = 2
    max_stripe_width: int = 40
    profile_expand: int = 3
    subpixel_window_radius: int = 4
    min_peak_intensity: int = 18
    min_profile_energy: float = 30.0

    # ---------- 动态规划主路径 ----------
    max_jump_y: float = 6.0
    max_gap_columns: int = 3
    score_weight_peak: float = 1.0
    score_weight_energy: float = 0.08
    jump_penalty: float = 1.4
    gap_penalty: float = 3.5
    start_bonus: float = 8.0

    # ---------- 输出路径质量 ----------
    min_points_in_path: int = 30
    smooth_window: int = 7

    # ---------- 调试 ----------
    debug: bool = True


@dataclass
class ScanlineCandidate:
    x: int
    y_sub: float
    peak: float
    energy: float
    score: float


@dataclass
class ComponentInfo:
    label: int
    area: int
    x: int
    y: int
    w: int
    h: int
    long_edge: int
    short_edge: int
    aspect: float
    angle_deg: float
    score: float


@dataclass
class LaserStripeSubpixelResult:
    success: bool
    points_xy: np.ndarray
    segment_points_xy: List[np.ndarray]
    points_xy_rotated: np.ndarray
    rotation_angle_deg: float
    candidate_mask: np.ndarray
    main_component_mask: np.ndarray
    rotated_raw: np.ndarray
    rotated_mask: np.ndarray
    overlay_bgr: Optional[np.ndarray]
    message: str


# =========================
# 基础工具
# =========================

def _ensure_odd(value: int) -> int:
    return value if value % 2 == 1 else value + 1


def _moving_average_1d(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or len(values) < 3:
        return values.copy()
    window = max(3, _ensure_odd(int(window)))
    radius = window // 2
    out = np.zeros_like(values, dtype=np.float32)
    for i in range(len(values)):
        left = max(0, i - radius)
        right = min(len(values), i + radius + 1)
        out[i] = float(np.mean(values[left:right]))
    return out


def _rotation_matrix_keep_size(width: int, height: int, angle_deg: float) -> np.ndarray:
    center = (width / 2.0, height / 2.0)
    return cv2.getRotationMatrix2D(center, angle_deg, 1.0)


def _rotate_image(
    image: np.ndarray,
    angle_deg: float,
    interpolation: int,
) -> Tuple[np.ndarray, np.ndarray]:
    h, w = image.shape[:2]
    M = _rotation_matrix_keep_size(w, h, angle_deg)
    rotated = cv2.warpAffine(
        image,
        M,
        (w, h),
        flags=interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return rotated, M


def _apply_affine_to_points(points_xy: np.ndarray, M: np.ndarray) -> np.ndarray:
    if points_xy.size == 0:
        return points_xy.reshape(0, 2).astype(np.float32)
    pts = np.hstack([points_xy.astype(np.float32), np.ones((len(points_xy), 1), dtype=np.float32)])
    transformed = (M @ pts.T).T
    return transformed.astype(np.float32)


def _invert_affine(M: np.ndarray) -> np.ndarray:
    return cv2.invertAffineTransform(M)


def _normalize_line_angle_deg(angle_deg: float) -> float:
    angle = float(angle_deg)
    while angle >= 90.0:
        angle -= 180.0
    while angle < -90.0:
        angle += 180.0
    return angle


def _line_angle_diff_deg(a_deg: float, b_deg: float) -> float:
    a = _normalize_line_angle_deg(a_deg)
    b = _normalize_line_angle_deg(b_deg)
    d = abs(a - b)
    return min(d, 180.0 - d)


# =========================
# 候选掩膜与连通域分析
# =========================

def _build_candidate_mask(
    normalized_gray: np.ndarray,
    config: LaserStripeSubpixelConfig,
) -> np.ndarray:
    gray = normalized_gray.astype(np.uint8)

    threshold_value = int(np.clip(config.candidate_threshold, 0, 255))
    _, binary_fixed = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)

    if config.use_otsu_fallback:
        otsu_thr, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        threshold_value = max(threshold_value, int(otsu_thr))
        _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    else:
        binary = binary_fixed

    if int(config.close_kernel) > 1:
        k = _ensure_odd(int(config.close_kernel))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    if int(config.open_kernel) > 1:
        k = _ensure_odd(int(config.open_kernel))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return binary


def _component_score(width: int, height: int, area: int) -> float:
    short_edge = max(1, min(width, height))
    long_edge = max(width, height)
    aspect = long_edge / short_edge
    return float(area) * float(aspect)


def _estimate_stripe_angle_deg(mask: np.ndarray) -> float:
    ys, xs = np.where(mask > 0)
    if len(xs) < 10:
        return 0.0

    pts = np.column_stack([xs.astype(np.float32), ys.astype(np.float32)])
    mean = np.mean(pts, axis=0, keepdims=True)
    centered = pts - mean
    cov = np.cov(centered.T)

    eigvals, eigvecs = np.linalg.eigh(cov)
    main_vec = eigvecs[:, int(np.argmax(eigvals))]
    angle_rad = np.arctan2(main_vec[1], main_vec[0])
    angle_deg = float(np.degrees(angle_rad))
    return _normalize_line_angle_deg(angle_deg)


def _collect_component_infos(candidate_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[ComponentInfo]]:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(candidate_mask, connectivity=8)

    infos: List[ComponentInfo] = []
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])

        long_edge = max(w, h)
        short_edge = max(1, min(w, h))
        aspect = float(long_edge / short_edge)

        component_mask = np.zeros_like(candidate_mask)
        component_mask[labels == label] = 255
        angle_deg = _estimate_stripe_angle_deg(component_mask)

        infos.append(
            ComponentInfo(
                label=label,
                area=area,
                x=x,
                y=y,
                w=w,
                h=h,
                long_edge=long_edge,
                short_edge=short_edge,
                aspect=aspect,
                angle_deg=angle_deg,
                score=_component_score(w, h, area),
            )
        )

    return labels, stats, np.arange(num_labels), infos


def _estimate_dominant_angle_from_infos(infos: Sequence[ComponentInfo]) -> float:
    if len(infos) == 0:
        return 0.0

    # 线方向具有 180° 对称性，因此使用双角度平均
    sum_cos = 0.0
    sum_sin = 0.0
    for info in infos:
        weight = float(max(1, info.area))
        theta = np.deg2rad(2.0 * info.angle_deg)
        sum_cos += weight * float(np.cos(theta))
        sum_sin += weight * float(np.sin(theta))

    if abs(sum_cos) < 1e-9 and abs(sum_sin) < 1e-9:
        return 0.0

    dominant = 0.5 * float(np.degrees(np.arctan2(sum_sin, sum_cos)))
    return _normalize_line_angle_deg(dominant)


def _split_connected_components(binary_mask: np.ndarray) -> List[np.ndarray]:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
    parts: List[np.ndarray] = []
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area <= 0:
            continue
        comp = np.zeros_like(binary_mask)
        comp[labels == label] = 255
        parts.append(comp)
    return parts


def _select_main_component(
    candidate_mask: np.ndarray,
    config: LaserStripeSubpixelConfig,
) -> np.ndarray:
    """
    改进点：
    - 旧版：只保留“最优一个”连通域；
    - 新版：保留一组满足线状约束、并与主方向一致的连通域。
    """
    labels, stats, _, infos = _collect_component_infos(candidate_mask)

    out = np.zeros_like(candidate_mask)
    if len(infos) == 0:
        return out

    if config.keep_only_best_component:
        best_label = -1
        best_score = -1.0
        for info in infos:
            if info.area < int(config.min_component_area):
                continue
            if info.aspect < float(config.min_component_aspect):
                continue
            if info.long_edge < int(config.min_component_span):
                continue
            if info.score > best_score:
                best_score = info.score
                best_label = info.label

        if best_label > 0:
            out[labels == best_label] = 255
            return out

    elongated_infos = [
        info for info in infos
        if info.area >= int(config.min_component_area)
        and info.aspect >= float(config.min_component_aspect)
        and info.long_edge >= int(config.min_component_span)
    ]

    if len(elongated_infos) == 0:
        # 退化：保留面积最大的连通域
        best_label = max(infos, key=lambda t: t.area).label
        out[labels == best_label] = 255
        return out

    dominant_angle = _estimate_dominant_angle_from_infos(elongated_infos)
    best_area = max(info.area for info in elongated_infos)
    area_floor = max(int(config.min_component_area), int(best_area * float(config.component_area_ratio_to_best)))

    kept_any = False
    for info in elongated_infos:
        if info.area < area_floor:
            continue
        if _line_angle_diff_deg(info.angle_deg, dominant_angle) > float(config.component_angle_tolerance_deg):
            continue
        out[labels == info.label] = 255
        kept_any = True

    if kept_any:
        return out

    # 再退化：保留主方向最近的那个最大连通域
    fallback = min(
        elongated_infos,
        key=lambda t: (_line_angle_diff_deg(t.angle_deg, dominant_angle), -t.area)
    )
    out[labels == fallback.label] = 255
    return out


# =========================
# 列扫描 + 亚像素定位
# =========================

def _find_runs(mask_1d: np.ndarray) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    in_run = False
    start = 0
    for i, value in enumerate(mask_1d):
        if value and not in_run:
            in_run = True
            start = i
        elif not value and in_run:
            runs.append((start, i - 1))
            in_run = False
    if in_run:
        runs.append((start, len(mask_1d) - 1))
    return runs


def _subpixel_from_profile(
    profile: np.ndarray,
    center_index_in_profile: int,
    radius: int,
) -> Tuple[Optional[float], float, float]:
    if profile.size == 0:
        return None, 0.0, 0.0

    radius = max(1, int(radius))
    left = max(0, center_index_in_profile - radius)
    right = min(profile.size, center_index_in_profile + radius + 1)
    window = profile[left:right].astype(np.float32)

    if window.size < 3:
        return None, 0.0, 0.0

    peak = float(np.max(window))
    baseline = float(np.min(window))
    weights = np.maximum(window - baseline, 0.0)
    energy = float(np.sum(weights))

    if energy <= 1e-6:
        return None, peak, energy

    coords = np.arange(left, right, dtype=np.float32)
    subpixel_index = float(np.sum(coords * weights) / energy)
    return subpixel_index, peak, energy


def _extract_candidates_by_column(
    rotated_raw: np.ndarray,
    rotated_mask: np.ndarray,
    config: LaserStripeSubpixelConfig,
) -> Tuple[List[int], List[List[ScanlineCandidate]]]:
    h, w = rotated_raw.shape[:2]
    ys, xs = np.where(rotated_mask > 0)

    if len(xs) < 10:
        return [], []

    x_min = int(np.min(xs))
    x_max = int(np.max(xs))

    valid_columns: List[int] = []
    candidates_per_column: List[List[ScanlineCandidate]] = []

    for x in range(x_min, x_max + 1):
        col_mask = rotated_mask[:, x] > 0
        runs = _find_runs(col_mask.astype(np.uint8))

        column_candidates: List[ScanlineCandidate] = []
        for y0, y1 in runs:
            width = y1 - y0 + 1
            if width < int(config.min_stripe_width) or width > int(config.max_stripe_width):
                continue

            y0e = max(0, y0 - int(config.profile_expand))
            y1e = min(h - 1, y1 + int(config.profile_expand))

            profile = rotated_raw[y0e:y1e + 1, x].astype(np.float32)
            if profile.size < 3:
                continue

            local_peak_idx = int(np.argmax(profile))
            peak_value = float(profile[local_peak_idx])
            if peak_value < float(config.min_peak_intensity):
                continue

            y_sub_local, peak, energy = _subpixel_from_profile(
                profile=profile,
                center_index_in_profile=local_peak_idx,
                radius=int(config.subpixel_window_radius),
            )
            if y_sub_local is None:
                continue
            if energy < float(config.min_profile_energy):
                continue

            y_sub_global = float(y0e + y_sub_local)
            score = (
                float(config.score_weight_peak) * peak +
                float(config.score_weight_energy) * energy
            )

            column_candidates.append(
                ScanlineCandidate(
                    x=x,
                    y_sub=y_sub_global,
                    peak=peak,
                    energy=energy,
                    score=score,
                )
            )

        valid_columns.append(x)
        candidates_per_column.append(column_candidates)

    return valid_columns, candidates_per_column


# =========================
# 动态规划主路径筛选
# =========================

@dataclass
class _DPNode:
    col_idx: int
    cand_idx: int
    score: float
    prev_node_index: int


def _select_main_path_dp(
    valid_columns: Sequence[int],
    candidates_per_column: Sequence[Sequence[ScanlineCandidate]],
    config: LaserStripeSubpixelConfig,
) -> np.ndarray:
    if len(valid_columns) == 0:
        return np.zeros((0, 2), dtype=np.float32)

    all_nodes: List[_DPNode] = []
    node_indices_per_col: List[List[int]] = []

    for col_i, _ in enumerate(valid_columns):
        current_nodes: List[int] = []
        curr_cands = candidates_per_column[col_i]

        if len(curr_cands) == 0:
            node_indices_per_col.append(current_nodes)
            continue

        for cand_i, cand in enumerate(curr_cands):
            best_score = cand.score + float(config.start_bonus)
            best_prev = -1

            for prev_col_i in range(max(0, col_i - int(config.max_gap_columns) - 1), col_i):
                if len(node_indices_per_col) <= prev_col_i:
                    continue

                gap = valid_columns[col_i] - valid_columns[prev_col_i] - 1
                if gap > int(config.max_gap_columns):
                    continue

                for prev_node_index in node_indices_per_col[prev_col_i]:
                    prev_node = all_nodes[prev_node_index]
                    prev_cand = candidates_per_column[prev_node.col_idx][prev_node.cand_idx]

                    dy = abs(cand.y_sub - prev_cand.y_sub)
                    if dy > float(config.max_jump_y) * (gap + 1):
                        continue

                    transition = (
                        prev_node.score
                        + cand.score
                        - float(config.jump_penalty) * dy
                        - float(config.gap_penalty) * gap
                    )

                    if transition > best_score:
                        best_score = transition
                        best_prev = prev_node_index

            node = _DPNode(
                col_idx=col_i,
                cand_idx=cand_i,
                score=best_score,
                prev_node_index=best_prev,
            )
            all_nodes.append(node)
            current_nodes.append(len(all_nodes) - 1)

        node_indices_per_col.append(current_nodes)

    if len(all_nodes) == 0:
        return np.zeros((0, 2), dtype=np.float32)

    best_end = int(np.argmax([node.score for node in all_nodes]))

    path_points: List[Tuple[float, float]] = []
    trace = best_end
    while trace >= 0:
        node = all_nodes[trace]
        cand = candidates_per_column[node.col_idx][node.cand_idx]
        path_points.append((float(cand.x), float(cand.y_sub)))
        trace = node.prev_node_index

    path_points.reverse()
    if len(path_points) == 0:
        return np.zeros((0, 2), dtype=np.float32)

    pts = np.array(path_points, dtype=np.float32)

    unique_pts: List[Tuple[float, float]] = []
    last_x = None
    for x, y in pts:
        if last_x is None or abs(x - last_x) > 1e-6:
            unique_pts.append((float(x), float(y)))
            last_x = float(x)

    pts = np.array(unique_pts, dtype=np.float32)

    if len(pts) >= 3 and int(config.smooth_window) > 1:
        pts[:, 1] = _moving_average_1d(pts[:, 1], int(config.smooth_window))

    return pts


def _extract_single_component_path(
    normalized_gray_raw: np.ndarray,
    component_mask: np.ndarray,
    config: LaserStripeSubpixelConfig,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    stripe_angle_deg = _estimate_stripe_angle_deg(component_mask)
    rotate_deg = -stripe_angle_deg

    rotated_raw, M = _rotate_image(normalized_gray_raw, rotate_deg, interpolation=cv2.INTER_LINEAR)
    rotated_mask, _ = _rotate_image(component_mask, rotate_deg, interpolation=cv2.INTER_NEAREST)

    valid_columns, candidates_per_column = _extract_candidates_by_column(
        rotated_raw=rotated_raw,
        rotated_mask=rotated_mask,
        config=config,
    )

    rotated_points = _select_main_path_dp(valid_columns, candidates_per_column, config)

    if len(rotated_points) < int(config.min_points_in_path):
        return (
            np.zeros((0, 2), dtype=np.float32),
            rotated_raw,
            rotated_mask,
            rotate_deg,
        )

    M_inv = _invert_affine(M)
    points_xy = _apply_affine_to_points(rotated_points, M_inv)

    return points_xy, rotated_raw, rotated_mask, rotate_deg


# =========================
# 主接口
# =========================

def extract_laser_stripe_subpixel(
    normalized_gray_raw: np.ndarray,
    normalized_gray: np.ndarray,
    image_bgr: Optional[np.ndarray] = None,
    config: LaserStripeSubpixelConfig = LaserStripeSubpixelConfig(),
) -> LaserStripeSubpixelResult:
    if normalized_gray_raw.ndim != 2 or normalized_gray.ndim != 2:
        raise ValueError("normalized_gray_raw 和 normalized_gray 必须是单通道灰度图。")

    if normalized_gray_raw.shape != normalized_gray.shape:
        raise ValueError("normalized_gray_raw 和 normalized_gray 尺寸必须一致。")

    # 1) 候选掩膜
    candidate_mask = _build_candidate_mask(normalized_gray, config)

    # 2) 选择一组主线状连通域
    main_component_mask = _select_main_component(candidate_mask, config)
    if np.count_nonzero(main_component_mask) < int(config.min_component_area):
        return LaserStripeSubpixelResult(
            success=False,
            points_xy=np.zeros((0, 2), dtype=np.float32),
            segment_points_xy=[],
            points_xy_rotated=np.zeros((0, 2), dtype=np.float32),
            rotation_angle_deg=0.0,
            candidate_mask=candidate_mask,
            main_component_mask=main_component_mask,
            rotated_raw=normalized_gray_raw.copy(),
            rotated_mask=main_component_mask.copy(),
            overlay_bgr=image_bgr.copy() if image_bgr is not None else None,
            message="主线状连通域为空，未能找到可信的激光条纹候选。",
        )

    dominant_angle_deg = _estimate_stripe_angle_deg(main_component_mask)
    rotated_raw_union, _ = _rotate_image(normalized_gray_raw, -dominant_angle_deg, interpolation=cv2.INTER_LINEAR)
    rotated_mask_union, _ = _rotate_image(main_component_mask, -dominant_angle_deg, interpolation=cv2.INTER_NEAREST)

    segment_points_xy: List[np.ndarray] = []
    points_xy_rotated_debug = np.zeros((0, 2), dtype=np.float32)

    if config.extract_components_individually:
        components = _split_connected_components(main_component_mask)
        # 从左到右排序，便于后续查看
        components = sorted(
            components,
            key=lambda m: np.min(np.where(m > 0)[1]) if np.count_nonzero(m) > 0 else 1e9
        )

        for idx, comp_mask in enumerate(components):
            pts_xy, rotated_raw_i, rotated_mask_i, rotate_deg_i = _extract_single_component_path(
                normalized_gray_raw=normalized_gray_raw,
                component_mask=comp_mask,
                config=config,
            )
            if len(pts_xy) >= int(config.min_points_in_path):
                segment_points_xy.append(pts_xy)

            if idx == 0 and len(pts_xy) > 0:
                # 仅保留一个代表性的 rotated debug 结果
                points_xy_rotated_debug, _, _, _ = _extract_single_component_path(
                    normalized_gray_raw=normalized_gray_raw,
                    component_mask=comp_mask,
                    config=config,
                )
    else:
        pts_xy, _, _, _ = _extract_single_component_path(
            normalized_gray_raw=normalized_gray_raw,
            component_mask=main_component_mask,
            config=config,
        )
        if len(pts_xy) >= int(config.min_points_in_path):
            segment_points_xy = [pts_xy]

    if len(segment_points_xy) == 0:
        overlay = image_bgr.copy() if image_bgr is not None else None
        return LaserStripeSubpixelResult(
            success=False,
            points_xy=np.zeros((0, 2), dtype=np.float32),
            segment_points_xy=[],
            points_xy_rotated=points_xy_rotated_debug,
            rotation_angle_deg=-dominant_angle_deg,
            candidate_mask=candidate_mask,
            main_component_mask=main_component_mask,
            rotated_raw=rotated_raw_union,
            rotated_mask=rotated_mask_union,
            overlay_bgr=overlay,
            message="保留了主线状连通域，但逐段亚像素提取未达到最小点数要求。",
        )

    points_xy = np.vstack(segment_points_xy).astype(np.float32)

    overlay = None
    if image_bgr is not None:
        overlay = visualize_laser_stripe_result(
            image_bgr=image_bgr,
            segment_points_xy=segment_points_xy,
            candidate_mask=candidate_mask,
            main_component_mask=main_component_mask,
            point_radius=1,
            polyline_thickness=1,
        )

    return LaserStripeSubpixelResult(
        success=True,
        points_xy=points_xy,
        segment_points_xy=segment_points_xy,
        points_xy_rotated=points_xy_rotated_debug,
        rotation_angle_deg=-dominant_angle_deg,
        candidate_mask=candidate_mask,
        main_component_mask=main_component_mask,
        rotated_raw=rotated_raw_union,
        rotated_mask=rotated_mask_union,
        overlay_bgr=overlay,
        message=f"提取成功，保留 {len(segment_points_xy)} 段线条，共 {len(points_xy)} 个亚像素点。",
    )


# =========================
# 可视化
# =========================

def visualize_laser_stripe_result(
    image_bgr: np.ndarray,
    segment_points_xy: List[np.ndarray],
    candidate_mask: Optional[np.ndarray] = None,
    main_component_mask: Optional[np.ndarray] = None,
    point_radius: int = 1,
    polyline_thickness: int = 1,
) -> np.ndarray:
    canvas = image_bgr.copy()

    if candidate_mask is not None:
        green = np.zeros_like(canvas)
        green[:, :, 1] = candidate_mask
        canvas = cv2.addWeighted(canvas, 1.0, green, 0.18, 0)

    if main_component_mask is not None:
        red = np.zeros_like(canvas)
        red[:, :, 2] = main_component_mask
        canvas = cv2.addWeighted(canvas, 1.0, red, 0.20, 0)

    for points_xy in segment_points_xy:
        if points_xy is None or len(points_xy) == 0:
            continue

        pts_int = np.round(points_xy).astype(np.int32)

        if len(pts_int) >= 2:
            cv2.polylines(
                canvas,
                [pts_int.reshape(-1, 1, 2)],
                isClosed=False,
                color=(255, 255, 0),
                thickness=int(polyline_thickness),
                lineType=cv2.LINE_AA,
            )

        for x, y in pts_int:
            cv2.circle(
                canvas,
                (int(x), int(y)),
                int(point_radius),
                (0, 255, 255),
                -1,
                lineType=cv2.LINE_AA,
            )

    return canvas


# =========================
# 与 red_filter 预处理链对接
# =========================

def extract_from_preprocess_result(
    preprocess_result,
    image_bgr: Optional[np.ndarray] = None,
    config: LaserStripeSubpixelConfig = LaserStripeSubpixelConfig(),
) -> LaserStripeSubpixelResult:
    if not hasattr(preprocess_result, "normalized_gray_raw"):
        raise AttributeError("preprocess_result 缺少 normalized_gray_raw 字段。")
    if not hasattr(preprocess_result, "normalized_gray"):
        raise AttributeError("preprocess_result 缺少 normalized_gray 字段。")

    return extract_laser_stripe_subpixel(
        normalized_gray_raw=preprocess_result.normalized_gray_raw,
        normalized_gray=preprocess_result.normalized_gray,
        image_bgr=image_bgr,
        config=config,
    )


# =========================
# 演示 main
# =========================

def main():
    image_path = "test_image.jpg"

    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"无法读取图像: {image_path}")

    try:
        from your_preprocess_module import preprocess_red_filter_v2, RedFilterPreprocessV2Config
    except Exception as exc:
        raise ImportError(
            "请把 main() 里的 `your_preprocess_module` 改成你自己的预处理模块名，"
            "并确保其中包含 preprocess_red_filter_v2 / RedFilterPreprocessV2Config。"
        ) from exc

    preprocess_cfg = RedFilterPreprocessV2Config()
    preprocess_result = preprocess_red_filter_v2(
        image_bgr=image_bgr,
        config=preprocess_cfg,
        camera_matrix=None,
        dist_coeffs=None,
    )

    subpixel_cfg = LaserStripeSubpixelConfig(
        candidate_threshold=24,
        min_component_area=80,
        min_component_aspect=2.0,
        min_component_span=120,
        component_area_ratio_to_best=0.08,
        component_angle_tolerance_deg=12.0,
        keep_only_best_component=False,
        extract_components_individually=True,
        min_stripe_width=2,
        max_stripe_width=40,
        profile_expand=3,
        subpixel_window_radius=4,
        min_peak_intensity=18,
        min_profile_energy=30.0,
        max_jump_y=6.0,
        max_gap_columns=3,
        min_points_in_path=30,
        smooth_window=7,
        debug=True,
    )

    result = extract_from_preprocess_result(
        preprocess_result=preprocess_result,
        image_bgr=image_bgr,
        config=subpixel_cfg,
    )

    print(result.message)
    print(f"success: {result.success}")
    print(f"num points: {len(result.points_xy)}")
    print(f"num segments: {len(result.segment_points_xy)}")
    print(f"rotation angle(deg): {result.rotation_angle_deg:.3f}")

    cv2.imwrite("debug_candidate_mask.png", result.candidate_mask)
    cv2.imwrite("debug_main_component_mask.png", result.main_component_mask)
    cv2.imwrite("debug_rotated_raw.png", result.rotated_raw)
    cv2.imwrite("debug_rotated_mask.png", result.rotated_mask)
    if result.overlay_bgr is not None:
        cv2.imwrite("debug_overlay.png", result.overlay_bgr)

    if len(result.points_xy) > 0:
        np.savetxt("subpixel_points_xy.txt", result.points_xy, fmt="%.6f")

        # 每段单独保存，便于后续三维重建逐段分析
        for i, seg in enumerate(result.segment_points_xy):
            np.savetxt(f"subpixel_points_segment_{i:02d}.txt", seg, fmt="%.6f")


if __name__ == "__main__":
    main()
