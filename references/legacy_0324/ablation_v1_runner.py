from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
LOCAL_PYDEPS = PROJECT_ROOT / '.pydeps'
if str(LOCAL_PYDEPS) not in sys.path and LOCAL_PYDEPS.exists():
    sys.path.insert(0, str(LOCAL_PYDEPS))

import numpy as np

try:
    import cv2
except ModuleNotFoundError as exc:
    raise RuntimeError('cv2 not found. Please install OpenCV or place dependency in .pydeps.') from exc

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from src.config_plane_v3_rectified_squareaware_left0073_refined_auto_yaw import build_default_config_yaw
from src.linelaser0319_reusable import (
    Legacy0319Config,
    build_legacy0319_config_from_pipeline,
    compute_cam_to_robot_transform,
    pixels_to_robot_3d_legacy0319,
    preprocess_rg_difference_legacy0319,
    steger_extract_subpixel_debug_legacy0319,
)

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}
DEFAULT_VERSION_ORDER = [
    'v1_base',
    'v1_roi',
    'v1_roi_adaptive',
    'v1_roi_adaptive_continuity',
]


@dataclass(frozen=True)
class AblationParams:
    roi_center_y_ratio: float = 0.5
    roi_height_ratio: float = 0.18
    bg_method: str = 'gaussian'
    bg_kernel: int = 51
    percentile_low: float = 5.0
    percentile_high: float = 99.5
    percentile_q: float = 92.0
    mad_k: float = 2.8
    adaptive_eigen_percentile: float = 72.0
    adaptive_eigen_floor: float = 20.0
    nms_kernel: int = 5
    continuity_score_gray_weight: float = 0.18
    continuity_penalty: float = 1.0
    continuity_large_jump_penalty: float = 22.0
    continuity_max_jump: int = 8
    continuity_max_jump_hard: int = 14
    continuity_interpolation_max_gap: int = 4
    continuity_smooth_window: int = 5
    tracker_mode: str = 'robust_tracker'
    top_view_display_mode: str = 'image_like'  # robot_frame | image_like
    tracker_seed_neighbor_tol: int = 5
    tracker_seed_neighbor_weight: float = 18.0
    tracker_candidates_per_col: int = 8
    tracker_seed_candidates_per_col: int = 1
    tracker_predict_window: int = 6
    tracker_max_search_radius: int = 32
    tracker_match_dist_weight: float = 1.15
    tracker_curvature_weight: float = 0.32
    tracker_missing_penalty: float = 8.0
    restart_after_missing_cols: int = 6
    restart_max_count: int = 3
    restart_seed_min_score_quantile: float = 80.0
    restart_seed_max_offset: float = 30.0
    long_gap_repair_max: int = 24
    long_gap_search_radius: int = 12
    long_gap_fit_window: int = 6
    long_gap_min_fill_ratio: float = 0.45
    main_segment_min_ratio: float = 0.35
    use_ground_prior: str = 'auto'  # off | on | auto
    ground_prior_weight: float = 0.55
    ground_band_ratio: float = 0.26
    ground_prior_mode: str = 'hybrid'  # center | trend | hybrid
    ground_auto_std_ratio: float = 0.08
    ground_auto_slope_ratio: float = 0.04
    cc_min_area: int = 18
    cc_min_aspect: float = 2.2
    cc_min_width: int = 52
    cc_max_angle_deg: float = 35.0
    cc_closed_loop_min_area: int = 60
    secondary_suppress_min_offset: float = 4.0
    secondary_suppress_max_offset: float = 16.0
    segment_min_cols: int = 42
    segment_min_area: int = 120
    segment_min_aspect: float = 2.8
    segment_max_abs_slope: float = 0.35
    segment_parallel_overlap_ratio: float = 0.22
    segment_parallel_slope_diff: float = 0.12
    segment_duplicate_max_offset: float = 3.0
    segment_minor_keep_len_ratio: float = 0.12
    segment_minor_keep_score_ratio: float = 0.55
    correction_window: int = 7
    correction_response_weight: float = 0.70
    correction_gray_weight: float = 0.30
    correction_max_shift: float = 3.5
    merge_enable: bool = False
    merge_max_gap: int = 1
    merge_max_slope_diff: float = 0.08
    merge_max_vdiff: float = 2.4
    merge_max_curvature_delta: float = 0.18
    ground_z_std_thresh: float = 4.0
    ground_z_abs_mean_thresh: float = 3.0


@dataclass
class PreprocessArtifacts:
    gray: np.ndarray
    debug_images: dict[str, np.ndarray] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionArtifacts:
    candidate_mask: np.ndarray
    final_mask: np.ndarray
    candidate_points_uv: np.ndarray
    final_points_uv: np.ndarray
    candidate_segments_uv: list[np.ndarray] = field(default_factory=list)
    final_segments_uv: list[np.ndarray] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class SingleImageResult:
    version: str
    image_path: Path
    raw_bgr: np.ndarray
    undistorted_bgr: np.ndarray
    roi_bgr: np.ndarray
    roi_rect: tuple[int, int, int, int]
    preprocess: PreprocessArtifacts
    extraction: ExtractionArtifacts
    final_points_uv_global: np.ndarray
    points_3d: np.ndarray
    preprocess_time_ms: float
    extraction_time_ms: float
    reconstruct_time_ms: float
    total_time_ms: float
    error_message: str | None = None


class UndistortRemapCache:
    def __init__(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
        self.camera_matrix = np.asarray(camera_matrix, dtype=np.float64)
        self.dist_coeffs = np.asarray(dist_coeffs, dtype=np.float64)
        self._cache: dict[tuple[int, int], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    def get_maps(self, width: int, height: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        key = (width, height)
        if key not in self._cache:
            new_camera, _ = cv2.getOptimalNewCameraMatrix(
                self.camera_matrix,
                self.dist_coeffs,
                (width, height),
                1,
                (width, height),
            )
            map1, map2 = cv2.initUndistortRectifyMap(
                self.camera_matrix,
                self.dist_coeffs,
                None,
                new_camera,
                (width, height),
                cv2.CV_32FC1,
            )
            self._cache[key] = (map1, map2, new_camera)
        return self._cache[key]

    def undistort(self, image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        h, w = image_bgr.shape[:2]
        map1, map2, new_camera = self.get_maps(w, h)
        undistorted = cv2.remap(image_bgr, map1, map2, interpolation=cv2.INTER_LINEAR)
        return undistorted, new_camera


def ensure_odd(value: int, min_value: int = 3) -> int:
    value = max(min_value, int(value))
    return value if value % 2 == 1 else value + 1


def percentile_normalize(image: np.ndarray, low_q: float, high_q: float) -> np.ndarray:
    low = float(np.percentile(image, low_q))
    high = float(np.percentile(image, high_q))
    if high <= low + 1e-6:
        return np.zeros_like(image, dtype=np.uint8)
    normalized = np.clip((image.astype(np.float32) - low) / (high - low), 0.0, 1.0)
    return (normalized * 255.0).astype(np.uint8)


def moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) == 0 or window <= 1:
        return values
    window = ensure_odd(window, min_value=3)
    pad = window // 2
    padded = np.pad(values.astype(np.float32), (pad, pad), mode='edge')
    kernel = np.ones(window, dtype=np.float32) / float(window)
    smoothed = np.convolve(padded, kernel, mode='valid')
    return smoothed.astype(np.float32)


def continuity_stats_from_points(points_uv_local: np.ndarray, roi_width: int) -> tuple[float, int, int]:
    if roi_width <= 0:
        return 0.0, 0, 0
    if points_uv_local is None or len(points_uv_local) == 0:
        return 0.0, 0, roi_width
    cols = np.unique(np.clip(np.round(points_uv_local[:, 0]).astype(np.int32), 0, roi_width - 1))
    cols.sort()
    if len(cols) == 0:
        return 0.0, 0, roi_width
    coverage = float(len(cols) / roi_width)
    if len(cols) < 2:
        return coverage, 0, int(max(0, roi_width - len(cols)))
    diffs = np.diff(cols)
    gaps = diffs[diffs > 1] - 1
    gap_count = int(len(gaps))
    max_gap = int(np.max(gaps)) if len(gaps) > 0 else 0
    return coverage, gap_count, max_gap


def segment_lengths_from_cols(cols: np.ndarray) -> list[int]:
    if cols.size == 0:
        return []
    cols = np.sort(cols.astype(np.int32))
    lengths: list[int] = []
    start = int(cols[0])
    prev = int(cols[0])
    for col in cols[1:]:
        col_i = int(col)
        if col_i == prev + 1:
            prev = col_i
            continue
        lengths.append(prev - start + 1)
        start = col_i
        prev = col_i
    lengths.append(prev - start + 1)
    return lengths


def segment_stats_from_points(points_uv_local: np.ndarray) -> tuple[float, float]:
    if points_uv_local is None or len(points_uv_local) == 0:
        return 0.0, 0.0
    cols = np.unique(np.round(points_uv_local[:, 0]).astype(np.int32))
    segs = segment_lengths_from_cols(cols)
    if len(segs) == 0:
        return 0.0, 0.0
    return float(max(segs)), float(np.mean(segs))


def fit_line_quad_residual(points_uv_local: np.ndarray) -> tuple[float, float]:
    if points_uv_local is None or len(points_uv_local) < 3:
        return float('nan'), float('nan')
    u = points_uv_local[:, 0].astype(np.float64)
    v = points_uv_local[:, 1].astype(np.float64)
    order = np.argsort(u)
    u = u[order]
    v = v[order]
    coeff_line = np.polyfit(u, v, deg=1)
    pred_line = np.polyval(coeff_line, u)
    line_rmse = float(np.sqrt(np.mean((v - pred_line) ** 2)))
    if len(points_uv_local) < 5:
        return line_rmse, float('nan')
    coeff_quad = np.polyfit(u, v, deg=2)
    pred_quad = np.polyval(coeff_quad, u)
    quad_rmse = float(np.sqrt(np.mean((v - pred_quad) ** 2)))
    return line_rmse, quad_rmse


def draw_points_overlay(image_bgr: np.ndarray, points_uv: np.ndarray, color: tuple[int, int, int], radius: int = 1) -> np.ndarray:
    canvas = image_bgr.copy()
    if points_uv is None or len(points_uv) == 0:
        return canvas
    points_int = np.round(points_uv).astype(np.int32)
    for x, y in points_int:
        cv2.circle(canvas, (int(x), int(y)), radius, color, -1, lineType=cv2.LINE_AA)
    return canvas

def compute_metrics(result: SingleImageResult, params: AblationParams) -> dict[str, float | str]:
    roi_width = int(result.roi_rect[2] - result.roi_rect[0])
    coverage, gap_count, max_gap = continuity_stats_from_points(result.extraction.final_points_uv, roi_width)
    longest_seg, mean_seg = segment_stats_from_points(result.extraction.final_points_uv)
    points_3d = result.points_3d
    if points_3d is None or len(points_3d) == 0:
        z_mean = float('nan')
        z_std = float('nan')
        x_span = float('nan')
    else:
        z = points_3d[:, 2].astype(np.float64)
        x = points_3d[:, 0].astype(np.float64)
        z_mean = float(np.mean(z))
        z_std = float(np.std(z))
        x_p5, x_p95 = np.percentile(x, [5, 95])
        x_span = float(x_p95 - x_p5)
    line_rmse, quad_rmse = fit_line_quad_residual(result.extraction.final_points_uv)
    is_ground_like = 0.0
    if not math.isnan(z_std) and not math.isnan(z_mean):
        if z_std <= params.ground_z_std_thresh and abs(z_mean) <= params.ground_z_abs_mean_thresh:
            is_ground_like = 1.0
    restart_count = float(result.extraction.meta.get('restart_count', 0.0))
    longest_continuous_segment = float(result.extraction.meta.get('longest_continuous_segment', longest_seg))
    mean_segment_length = float(result.extraction.meta.get('mean_segment_length', mean_seg))
    off_trend_penalty_mean = float(result.extraction.meta.get('off_trend_penalty_mean', float('nan')))
    repaired_gap_count = float(result.extraction.meta.get('repaired_gap_count', 0.0))
    repaired_gap_max = float(result.extraction.meta.get('repaired_gap_max', 0.0))
    seed_confidence = float(result.extraction.meta.get('seed_confidence', 0.0))
    segment_count = float(result.extraction.meta.get('segment_count', len(result.extraction.final_segments_uv)))
    merged_segment_count = float(result.extraction.meta.get('merged_segment_count', 0.0))
    secondary_suppressed_count = float(result.extraction.meta.get('secondary_suppressed_count', 0.0))
    cc_removed_loop_area = float(result.extraction.meta.get('cc_removed_loop_area', 0.0))
    cc_removed_compact_area = float(result.extraction.meta.get('cc_removed_compact_area', 0.0))
    jitter_before = float(result.extraction.meta.get('mean_segment_jitter_before', float('nan')))
    jitter_after = float(result.extraction.meta.get('mean_segment_jitter_after', float('nan')))
    correction_delta = float(result.extraction.meta.get('mean_segment_correction_delta', float('nan')))
    return {
        'version': result.version,
        'image': result.image_path.name,
        'preprocess_time_ms': float(result.preprocess_time_ms),
        'extraction_time_ms': float(result.extraction_time_ms),
        'reconstruct_time_ms': float(result.reconstruct_time_ms),
        'total_time_ms': float(result.total_time_ms),
        'candidate_points_2d': float(len(result.extraction.candidate_points_uv)),
        'extracted_points_2d': float(len(result.extraction.final_points_uv)),
        'valid_points_3d': float(len(points_3d)),
        'effective_column_coverage': float(coverage),
        'continuity_gap_count': float(gap_count),
        'continuity_max_gap': float(max_gap),
        'restart_count': restart_count,
        'longest_continuous_segment': longest_continuous_segment,
        'mean_segment_length': mean_segment_length,
        'off_trend_penalty_mean': off_trend_penalty_mean,
        'repaired_gap_count': repaired_gap_count,
        'repaired_gap_max': repaired_gap_max,
        'seed_confidence': seed_confidence,
        'segment_count': segment_count,
        'merged_segment_count': merged_segment_count,
        'secondary_suppressed_count': secondary_suppressed_count,
        'cc_removed_loop_area': cc_removed_loop_area,
        'cc_removed_compact_area': cc_removed_compact_area,
        'mean_segment_jitter_before': jitter_before,
        'mean_segment_jitter_after': jitter_after,
        'mean_segment_correction_delta': correction_delta,
        'Z_mean': z_mean,
        'Z_std': z_std,
        'X_span_p95_p5': x_span,
        'line_fit_rmse': float(line_rmse),
        'quad_fit_rmse': float(quad_rmse),
        'is_ground_like': float(is_ground_like),
        'error': result.error_message or '',
    }


class LaserLineExtractorV1Base:
    version_name = 'v1_base'

    def __init__(self, config: Legacy0319Config, params: AblationParams):
        self.config = config
        self.params = params
        self.undistorter = UndistortRemapCache(config.camera_matrix, config.dist_coeffs)
        self.transform = compute_cam_to_robot_transform(config.robot_install)

    def get_roi_bounds(self, image_h: int, image_w: int) -> tuple[int, int, int, int]:
        return 0, 0, image_w, image_h

    def preprocess_roi(self, roi_bgr: np.ndarray) -> PreprocessArtifacts:
        gray = preprocess_rg_difference_legacy0319(roi_bgr)
        return PreprocessArtifacts(gray=gray, debug_images={'preprocess_gray': gray}, meta={})

    def extract_points(self, pre: PreprocessArtifacts) -> ExtractionArtifacts:
        debug = steger_extract_subpixel_debug_legacy0319(
            image_gray=pre.gray,
            gray_threshold=float(self.config.steger.gray_threshold),
            eigen_threshold=float(self.config.steger.eigen_threshold),
        )
        ys, xs = np.where(debug.candidate_mask > 0)
        candidate_points = (
            np.column_stack([xs.astype(np.float32), ys.astype(np.float32)])
            if len(xs) > 0 else np.zeros((0, 2), dtype=np.float32)
        )
        return ExtractionArtifacts(
            candidate_mask=debug.candidate_mask,
            final_mask=debug.nms_mask,
            candidate_points_uv=candidate_points,
            final_points_uv=debug.points_uv.astype(np.float32),
            meta={
                'gray_threshold': float(self.config.steger.gray_threshold),
                'eigen_threshold': float(self.config.steger.eigen_threshold),
            },
        )

    @staticmethod
    def _compute_steger_maps(gray_u8: np.ndarray) -> dict[str, np.ndarray]:
        img = gray_u8.astype(np.float32)
        dx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=3)
        dy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=3)
        dxx = cv2.Sobel(dx, cv2.CV_32F, 1, 0, ksize=3)
        dyy = cv2.Sobel(dy, cv2.CV_32F, 0, 1, ksize=3)
        dxy = cv2.Sobel(dx, cv2.CV_32F, 0, 1, ksize=3)
        tmp = np.sqrt((dxx - dyy) ** 2 + 4.0 * dxy**2)
        lambda2 = (dxx + dyy - tmp) / 2.0
        nx = lambda2 - dyy
        ny = dxy
        norm = np.sqrt(nx**2 + ny**2)
        valid_norm = norm > 1e-6
        nx = np.where(valid_norm, nx / np.where(valid_norm, norm, 1.0), 0.0)
        ny = np.where(valid_norm, ny / np.where(valid_norm, norm, 1.0), 0.0)
        numerator = dx * nx + dy * ny
        denominator = dxx * nx**2 + 2.0 * dxy * nx * ny + dyy * ny**2
        denominator = np.where(np.abs(denominator) < 1e-6, 1e-6, denominator)
        t = -numerator / denominator
        mask_t = (np.abs(t * nx) <= 0.3) & (np.abs(t * ny) <= 0.3)
        return {'lambda2': lambda2, 'nx': nx, 'ny': ny, 't': t, 'mask_t': mask_t}

    @staticmethod
    def _subpixel_points_from_mask(mask: np.ndarray, t: np.ndarray, nx: np.ndarray, ny: np.ndarray) -> np.ndarray:
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return np.zeros((0, 2), dtype=np.float32)
        u = xs.astype(np.float32) + t[ys, xs].astype(np.float32) * nx[ys, xs].astype(np.float32)
        v = ys.astype(np.float32) + t[ys, xs].astype(np.float32) * ny[ys, xs].astype(np.float32)
        return np.column_stack([u, v]).astype(np.float32)

    def run_single_image(self, image_bgr: np.ndarray, image_path: Path) -> SingleImageResult:
        t0 = perf_counter()
        try:
            undistorted, updated_camera = self.undistorter.undistort(image_bgr)
            h, w = undistorted.shape[:2]
            x0, y0, x1, y1 = self.get_roi_bounds(h, w)
            roi = undistorted[y0:y1, x0:x1]
            preprocess_art = self.preprocess_roi(roi)
            t1 = perf_counter()
            extraction_art = self.extract_points(preprocess_art)
            t2 = perf_counter()
            final_global = extraction_art.final_points_uv.copy()
            if len(final_global) > 0:
                final_global[:, 0] += float(x0)
                final_global[:, 1] += float(y0)
            final_segments_local = extraction_art.meta.get('final_segments_uv_local', [])
            final_segments_global: list[np.ndarray] = []
            if isinstance(final_segments_local, list):
                for seg in final_segments_local:
                    if not isinstance(seg, np.ndarray) or seg.size == 0:
                        continue
                    seg_g = seg.astype(np.float32).copy()
                    seg_g[:, 0] += float(x0)
                    seg_g[:, 1] += float(y0)
                    final_segments_global.append(seg_g)
            points_3d = pixels_to_robot_3d_legacy0319(
                points_uv=final_global,
                camera_matrix=updated_camera,
                plane_abcd=self.config.plane_abcd,
                cam_to_robot_transform=self.transform,
            )
            final_segments_3d: list[np.ndarray] = []
            if len(final_segments_global) > 0:
                cursor = 0
                for seg_g in final_segments_global:
                    seg_n = int(len(seg_g))
                    if seg_n <= 0:
                        continue
                    seg_3d = points_3d[cursor:cursor + seg_n]
                    final_segments_3d.append(seg_3d.copy())
                    cursor += seg_n
            extraction_art.meta['final_segments_uv_global'] = final_segments_global
            extraction_art.meta['final_segments_3d'] = final_segments_3d
            t3 = perf_counter()
            return SingleImageResult(
                version=self.version_name,
                image_path=image_path,
                raw_bgr=image_bgr,
                undistorted_bgr=undistorted,
                roi_bgr=roi,
                roi_rect=(x0, y0, x1, y1),
                preprocess=preprocess_art,
                extraction=extraction_art,
                final_points_uv_global=final_global,
                points_3d=points_3d,
                preprocess_time_ms=(t1 - t0) * 1000.0,
                extraction_time_ms=(t2 - t1) * 1000.0,
                reconstruct_time_ms=(t3 - t2) * 1000.0,
                total_time_ms=(t3 - t0) * 1000.0,
            )
        except Exception as exc:
            t_fail = perf_counter()
            dummy = np.zeros_like(image_bgr)
            return SingleImageResult(
                version=self.version_name,
                image_path=image_path,
                raw_bgr=image_bgr,
                undistorted_bgr=dummy,
                roi_bgr=dummy,
                roi_rect=(0, 0, image_bgr.shape[1], image_bgr.shape[0]),
                preprocess=PreprocessArtifacts(gray=np.zeros(image_bgr.shape[:2], dtype=np.uint8)),
                extraction=ExtractionArtifacts(
                    candidate_mask=np.zeros(image_bgr.shape[:2], dtype=np.uint8),
                    final_mask=np.zeros(image_bgr.shape[:2], dtype=np.uint8),
                    candidate_points_uv=np.zeros((0, 2), dtype=np.float32),
                    final_points_uv=np.zeros((0, 2), dtype=np.float32),
                    meta={},
                ),
                final_points_uv_global=np.zeros((0, 2), dtype=np.float32),
                points_3d=np.zeros((0, 3), dtype=np.float64),
                preprocess_time_ms=0.0,
                extraction_time_ms=0.0,
                reconstruct_time_ms=0.0,
                total_time_ms=(t_fail - t0) * 1000.0,
                error_message=str(exc),
            )


class LaserLineExtractorROI(LaserLineExtractorV1Base):
    version_name = 'v1_roi'

    def get_roi_bounds(self, image_h: int, image_w: int) -> tuple[int, int, int, int]:
        roi_h = int(round(image_h * float(self.params.roi_height_ratio)))
        roi_h = max(4, min(image_h, roi_h))
        center_y = int(round(image_h * float(self.params.roi_center_y_ratio)))
        y0 = max(0, center_y - roi_h // 2)
        y1 = min(image_h, y0 + roi_h)
        y0 = max(0, y1 - roi_h)
        return 0, y0, image_w, y1

class LaserLineExtractorAdaptive(LaserLineExtractorROI):
    version_name = 'v1_roi_adaptive'

    def preprocess_roi(self, roi_bgr: np.ndarray) -> PreprocessArtifacts:
        _b, g, r = cv2.split(roi_bgr)
        diff = np.maximum(r.astype(np.int16) - g.astype(np.int16), 0).astype(np.uint8)
        method = self.params.bg_method.strip().lower()
        k = ensure_odd(self.params.bg_kernel, min_value=3)

        if method == 'median':
            bg = cv2.medianBlur(diff, k)
            suppressed = cv2.subtract(diff, bg)
        elif method == 'tophat':
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
            suppressed = cv2.morphologyEx(diff, cv2.MORPH_TOPHAT, kernel)
            bg = cv2.subtract(diff, suppressed)
        else:
            bg = cv2.GaussianBlur(diff, (k, k), sigmaX=0)
            suppressed = cv2.subtract(diff, bg)

        normalized = percentile_normalize(
            suppressed,
            low_q=float(self.params.percentile_low),
            high_q=float(self.params.percentile_high),
        )
        med = float(np.median(normalized))
        mad = float(np.median(np.abs(normalized.astype(np.float32) - med)) + 1e-6)
        thr_mad = med + float(self.params.mad_k) * mad
        thr_pct = float(np.percentile(normalized, float(self.params.percentile_q)))
        adaptive_threshold = float(np.clip(max(thr_mad, thr_pct), 0.0, 255.0))

        return PreprocessArtifacts(
            gray=normalized,
            debug_images={
                'rg_diff': diff,
                'local_background': bg,
                'background_suppressed': suppressed,
                'adaptive_preprocess': normalized,
            },
            meta={
                'adaptive_threshold': adaptive_threshold,
                'median': med,
                'mad': mad,
                'threshold_mad': float(thr_mad),
                'threshold_percentile': float(thr_pct),
            },
        )

    def extract_points(self, pre: PreprocessArtifacts) -> ExtractionArtifacts:
        if str(self.params.tracker_mode).lower() == 'adaptive_only':
            return super().extract_points(pre)
        gray = pre.gray
        maps = self._compute_steger_maps(gray)
        lambda2 = maps['lambda2']
        response = np.maximum(-lambda2, 0.0)
        neg_values = response[lambda2 < 0]
        eig_thr = float(np.percentile(neg_values, float(self.params.adaptive_eigen_percentile))) if neg_values.size > 0 else float(self.params.adaptive_eigen_floor)
        eig_thr = max(float(self.params.adaptive_eigen_floor), eig_thr)
        gray_thr = float(pre.meta.get('adaptive_threshold', 200.0))

        candidate_mask_bool = maps['mask_t'] & (gray >= gray_thr) & (lambda2 < -eig_thr)
        nms_k = ensure_odd(self.params.nms_kernel, min_value=3)
        local_max = cv2.dilate(response.astype(np.float32), np.ones((nms_k, nms_k), dtype=np.uint8))
        final_mask_bool = candidate_mask_bool & (response >= local_max - 1e-6)

        candidate_mask = (candidate_mask_bool.astype(np.uint8) * 255)
        final_mask = (final_mask_bool.astype(np.uint8) * 255)
        candidate_points = self._subpixel_points_from_mask(candidate_mask_bool, maps['t'], maps['nx'], maps['ny'])
        final_points = self._subpixel_points_from_mask(final_mask_bool, maps['t'], maps['nx'], maps['ny'])

        return ExtractionArtifacts(
            candidate_mask=candidate_mask,
            final_mask=final_mask,
            candidate_points_uv=candidate_points,
            final_points_uv=final_points,
            meta={'gray_threshold': gray_thr, 'eigen_threshold_adaptive': eig_thr},
        )


class LaserLineExtractorAdaptiveContinuity(LaserLineExtractorAdaptive):
    version_name = 'v1_roi_adaptive_continuity'

    def _estimate_ground_like_2d(self, candidate_columns: list[dict[str, np.ndarray]], h: int, w: int) -> bool:
        best_cols: list[int] = []
        best_ys: list[float] = []
        for x, col in enumerate(candidate_columns):
            ys = col['ys']
            if ys.size == 0:
                continue
            idx = int(np.argmax(col['seed_scores']))
            best_cols.append(x)
            best_ys.append(float(ys[idx]))
        if len(best_cols) < max(20, int(0.12 * w)):
            return False
        ys_arr = np.asarray(best_ys, dtype=np.float32)
        spread_ratio = float(np.std(ys_arr) / max(1.0, float(h)))
        slope_ratio = 0.0
        if len(best_cols) >= 3:
            coeff = np.polyfit(np.asarray(best_cols, dtype=np.float32), ys_arr, 1)
            slope_ratio = float(abs(coeff[0]) * max(1.0, float(w)) / max(1.0, float(h)))
        return (
            spread_ratio <= float(self.params.ground_auto_std_ratio)
            and slope_ratio <= float(self.params.ground_auto_slope_ratio)
        )

    def _component_is_closed_loop(self, comp_mask: np.ndarray, aspect: float) -> bool:
        if aspect >= 2.8:
            return False
        kernel = np.ones((3, 3), dtype=np.uint8)
        nb = cv2.filter2D(comp_mask.astype(np.uint8), cv2.CV_16S, kernel)
        deg = nb - comp_mask.astype(np.int16)
        endpoints = int(np.sum((comp_mask > 0) & (deg == 1)))
        return endpoints <= 1

    def _filter_candidates_connected_components(
        self,
        candidate_mask_bool: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, list[int], dict[int, tuple[int, int, int, int]], dict[str, float]]:
        mask_u8 = candidate_mask_bool.astype(np.uint8)
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)
        filtered = np.zeros_like(candidate_mask_bool, dtype=bool)
        keep_labels: list[int] = []
        label_boxes: dict[int, tuple[int, int, int, int]] = {}
        total_area = int(np.sum(mask_u8 > 0))
        removed_compact = 0
        removed_loop = 0
        kept = 0

        for lab in range(1, n_labels):
            area = int(stats[lab, cv2.CC_STAT_AREA])
            if area < int(self.params.cc_min_area):
                continue
            x = int(stats[lab, cv2.CC_STAT_LEFT])
            y = int(stats[lab, cv2.CC_STAT_TOP])
            w = int(stats[lab, cv2.CC_STAT_WIDTH])
            h = int(stats[lab, cv2.CC_STAT_HEIGHT])
            aspect = float(w / max(1, h))
            if w < int(self.params.cc_min_width) and aspect < float(self.params.cc_min_aspect):
                removed_compact += area
                continue

            ys, xs = np.where(labels == lab)
            angle = 90.0
            if xs.size >= 2:
                pts = np.column_stack([xs.astype(np.float32), ys.astype(np.float32)])
                vx, vy, _, _ = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
                vx_f = float(np.ravel(vx)[0])
                vy_f = float(np.ravel(vy)[0])
                angle = abs(float(np.degrees(np.arctan2(vy_f, vx_f))))
                if angle > 90.0:
                    angle = 180.0 - angle
            if angle > float(self.params.cc_max_angle_deg):
                removed_compact += area
                continue

            roi = (labels[y:y + h, x:x + w] == lab).astype(np.uint8)
            if area >= int(self.params.cc_closed_loop_min_area) and self._component_is_closed_loop(roi, aspect):
                removed_loop += area
                continue

            filtered[labels == lab] = True
            keep_labels.append(int(lab))
            label_boxes[int(lab)] = (x, y, w, h)
            kept += area

        return filtered, labels, keep_labels, label_boxes, {
            'cc_total_area': float(total_area),
            'cc_kept_area': float(kept),
            'cc_removed_compact_area': float(removed_compact),
            'cc_removed_loop_area': float(removed_loop),
        }

    def _predict_from_history(
        self,
        history_cols: list[int],
        history_ys: list[float],
        target_col: int,
        fallback_y: float,
    ) -> tuple[float, float]:
        if len(history_cols) < 2:
            return fallback_y, 0.0
        k = max(2, int(self.params.tracker_predict_window))
        cols = np.asarray(history_cols[-k:], dtype=np.float32)
        ys = np.asarray(history_ys[-k:], dtype=np.float32)
        if len(np.unique(cols)) < 2:
            return float(ys[-1]), 0.0
        coeff = np.polyfit(cols, ys, 1)
        pred = float(np.polyval(coeff, float(target_col)))
        return pred, float(coeff[0])

    def _ground_prior_penalty(
        self,
        y: np.ndarray,
        trend_y: float,
        center_y: float,
        h: int,
        ground_prior_enabled: bool,
    ) -> np.ndarray:
        if not ground_prior_enabled:
            return np.zeros_like(y, dtype=np.float32)
        mode = str(self.params.ground_prior_mode).lower()
        if mode == 'center':
            prior_y = np.ones_like(y, dtype=np.float32) * float(center_y)
        elif mode == 'trend':
            prior_y = np.ones_like(y, dtype=np.float32) * float(trend_y)
        else:
            prior_y = 0.55 * float(trend_y) + 0.45 * float(center_y)
            prior_y = np.ones_like(y, dtype=np.float32) * prior_y
        band = max(2.0, float(h) * float(self.params.ground_band_ratio))
        return float(self.params.ground_prior_weight) * np.abs(y - prior_y) / band

    def _select_candidate(
        self,
        candidate_col: dict[str, np.ndarray],
        pred_y: float,
        last_y: float | None,
        prev_dy: float,
        h: int,
        center_y: float,
        ground_prior_enabled: bool,
    ) -> tuple[float, float, float] | None:
        ys = candidate_col['ys'].astype(np.float32)
        if ys.size == 0:
            return None
        base_scores = candidate_col['base_scores'].astype(np.float32)
        dist = np.abs(ys - float(pred_y))
        in_range = dist <= float(self.params.tracker_max_search_radius)
        if not np.any(in_range):
            return None
        ys = ys[in_range]
        base_scores = base_scores[in_range]
        dist = dist[in_range]

        off_trend_penalty = float(self.params.tracker_match_dist_weight) * dist
        off_trend_penalty += float(self.params.continuity_penalty) * np.maximum(
            0.0,
            dist - float(self.params.continuity_max_jump),
        )
        off_trend_penalty += float(self.params.continuity_large_jump_penalty) * np.maximum(
            0.0,
            dist - float(self.params.continuity_max_jump_hard),
        )

        if last_y is None:
            curvature_penalty = np.zeros_like(off_trend_penalty, dtype=np.float32)
        else:
            dy = ys - float(last_y)
            curvature_penalty = float(self.params.tracker_curvature_weight) * np.abs(dy - float(prev_dy))

        ground_penalty = self._ground_prior_penalty(
            y=ys,
            trend_y=float(pred_y),
            center_y=float(center_y),
            h=h,
            ground_prior_enabled=ground_prior_enabled,
        )

        scores = base_scores - off_trend_penalty - curvature_penalty - ground_penalty
        best = int(np.argmax(scores))
        return float(ys[best]), float(scores[best]), float(off_trend_penalty[best])

    def _track_direction(
        self,
        seed_col: int,
        seed_y: float,
        direction: int,
        candidate_columns: list[dict[str, np.ndarray]],
        center_y: float,
        h: int,
        ground_prior_enabled: bool,
    ) -> list[tuple[int, float, float, float]]:
        w = len(candidate_columns)
        history_cols = [seed_col]
        history_ys = [float(seed_y)]
        outputs: list[tuple[int, float, float, float]] = []
        missing_cols = 0
        col_iter = range(seed_col + direction, w, direction) if direction > 0 else range(seed_col - 1, -1, -1)

        for col in col_iter:
            pred_y, pred_slope = self._predict_from_history(
                history_cols=history_cols,
                history_ys=history_ys,
                target_col=col,
                fallback_y=float(history_ys[-1]),
            )
            prev_dy = float(history_ys[-1] - history_ys[-2]) if len(history_ys) >= 2 else float(pred_slope)
            selected = self._select_candidate(
                candidate_col=candidate_columns[col],
                pred_y=float(pred_y),
                last_y=float(history_ys[-1]),
                prev_dy=prev_dy,
                h=h,
                center_y=float(center_y),
                ground_prior_enabled=ground_prior_enabled,
            )
            if selected is None:
                missing_cols += 1
                if missing_cols > int(self.params.restart_after_missing_cols):
                    break
                continue
            y_new, score_new, off_pen = selected
            if missing_cols > 0:
                reconnect_pen = float(self.params.tracker_missing_penalty) * float(missing_cols)
                score_new -= reconnect_pen
                off_pen += reconnect_pen
            outputs.append((int(col), float(y_new), float(score_new), float(off_pen)))
            history_cols.append(int(col))
            history_ys.append(float(y_new))
            missing_cols = 0
        return outputs

    def _inject_track_segment(
        self,
        segment_points: list[tuple[int, float, float, float]],
        y_track: np.ndarray,
        score_track: np.ndarray,
        offtrend_track: np.ndarray,
    ) -> None:
        for col, y, score, off_pen in segment_points:
            if np.isnan(y_track[col]) or score > score_track[col]:
                y_track[col] = float(y)
                score_track[col] = float(score)
                offtrend_track[col] = float(off_pen)

    def _interpolate_short_gaps(self, y_track: np.ndarray) -> None:
        valid_cols = np.where(~np.isnan(y_track))[0]
        if len(valid_cols) < 2:
            return
        for i in range(len(valid_cols) - 1):
            c0 = int(valid_cols[i])
            c1 = int(valid_cols[i + 1])
            gap = c1 - c0 - 1
            if gap <= 0 or gap > int(self.params.continuity_interpolation_max_gap):
                continue
            y0 = float(y_track[c0])
            y1 = float(y_track[c1])
            for g in range(1, gap + 1):
                alpha = g / (gap + 1.0)
                y_track[c0 + g] = (1.0 - alpha) * y0 + alpha * y1

    def _repair_long_gaps(
        self,
        y_track: np.ndarray,
        score_track: np.ndarray,
        offtrend_track: np.ndarray,
        candidate_columns: list[dict[str, np.ndarray]],
        h: int,
        center_y: float,
        ground_prior_enabled: bool,
    ) -> tuple[int, int, np.ndarray]:
        repaired_mask = np.zeros_like(y_track, dtype=np.uint8)
        valid_cols = np.where(~np.isnan(y_track))[0]
        if len(valid_cols) < 2:
            return 0, 0, repaired_mask

        repaired_gap_sizes: list[int] = []
        fit_window = max(3, int(self.params.long_gap_fit_window))

        for i in range(len(valid_cols) - 1):
            c0 = int(valid_cols[i])
            c1 = int(valid_cols[i + 1])
            gap = c1 - c0 - 1
            if gap <= int(self.params.continuity_interpolation_max_gap) or gap > int(self.params.long_gap_repair_max):
                continue

            left_start = max(0, i - fit_window + 1)
            left_cols = valid_cols[left_start:i + 1]
            right_end = min(len(valid_cols), i + 1 + fit_window)
            right_cols = valid_cols[i + 1:right_end]
            fit_cols = np.concatenate([left_cols, right_cols]).astype(np.float32)
            fit_ys = y_track[fit_cols.astype(np.int32)].astype(np.float32)
            if fit_cols.size < 4:
                continue

            deg = 2 if fit_cols.size >= 7 else 1
            coeff = np.polyfit(fit_cols, fit_ys, deg=deg)
            candidate_fills: list[tuple[int, float, float, float]] = []
            for col in range(c0 + 1, c1):
                pred_y = float(np.polyval(coeff, float(col)))
                selected = self._select_candidate(
                    candidate_col=candidate_columns[col],
                    pred_y=pred_y,
                    last_y=None,
                    prev_dy=0.0,
                    h=h,
                    center_y=float(center_y),
                    ground_prior_enabled=ground_prior_enabled,
                )
                if selected is None:
                    continue
                y_new, score_new, off_pen = selected
                if abs(y_new - pred_y) > float(self.params.long_gap_search_radius):
                    continue
                candidate_fills.append((int(col), float(y_new), float(score_new), float(off_pen)))

            if len(candidate_fills) / float(gap) < float(self.params.long_gap_min_fill_ratio):
                continue

            repaired_gap_sizes.append(gap)
            for col, y, score, off_pen in candidate_fills:
                if np.isnan(y_track[col]) or score > score_track[col]:
                    y_track[col] = float(y)
                    score_track[col] = float(score)
                    offtrend_track[col] = float(off_pen)
                    repaired_mask[col] = 1

        repaired_count = int(len(repaired_gap_sizes))
        repaired_max = int(max(repaired_gap_sizes)) if repaired_count > 0 else 0
        return repaired_count, repaired_max, repaired_mask

    def _filter_main_path(self, y_track: np.ndarray) -> np.ndarray:
        valid_cols = np.where(~np.isnan(y_track))[0]
        if valid_cols.size == 0:
            return y_track
        if valid_cols.size == 1:
            return y_track
        segments: list[tuple[int, int, int]] = []
        start = int(valid_cols[0]); prev = int(valid_cols[0])
        for col in valid_cols[1:]:
            col_i = int(col)
            if col_i == prev + 1:
                prev = col_i
                continue
            segments.append((start, prev, prev - start + 1))
            start = col_i
            prev = col_i
        segments.append((start, prev, prev - start + 1))
        if len(segments) <= 1:
            return y_track
        # Global main-path constraint: keep one dominant segment to avoid
        # persisting on wrong branches after relock.
        best_seg = max(segments, key=lambda s: s[2])
        keep_mask = np.zeros_like(y_track, dtype=bool)
        keep_mask[best_seg[0]:best_seg[1] + 1] = True
        filtered = y_track.copy()
        filtered[~keep_mask] = np.nan
        return filtered

    def _secondary_suppress_parallel_lines(
        self,
        candidate_columns: list[dict[str, np.ndarray]],
        y_track: np.ndarray,
        candidate_mask_bool: np.ndarray,
    ) -> tuple[np.ndarray, int]:
        if len(candidate_columns) == 0:
            return candidate_mask_bool, 0
        filtered = candidate_mask_bool.copy()
        suppressed = 0
        min_off = float(self.params.secondary_suppress_min_offset)
        max_off = float(self.params.secondary_suppress_max_offset)
        valid_cols = np.where(~np.isnan(y_track))[0]
        for col in valid_cols:
            ys = candidate_columns[int(col)]['ys']
            if ys.size == 0:
                continue
            dist = np.abs(ys.astype(np.float32) - float(y_track[int(col)]))
            mask = (dist >= min_off) & (dist <= max_off)
            if not np.any(mask):
                continue
            ys_sup = ys[mask].astype(np.int32)
            for yy in ys_sup:
                if filtered[yy, int(col)]:
                    filtered[yy, int(col)] = False
                    suppressed += 1
        return filtered, int(suppressed)

    def _segment_jitter(self, values: np.ndarray) -> float:
        if values.size < 3:
            return 0.0
        return float(np.std(np.diff(values.astype(np.float32))))

    def _segment_correct_v(
        self,
        v_raw: np.ndarray,
        response: np.ndarray,
        gray_vals: np.ndarray,
    ) -> np.ndarray:
        n = len(v_raw)
        if n <= 2:
            return v_raw.astype(np.float32)
        win = ensure_odd(int(self.params.correction_window), min_value=3)
        radius = win // 2
        resp_n = response.astype(np.float32)
        gray_n = gray_vals.astype(np.float32)
        if np.max(resp_n) > 1e-6:
            resp_n = resp_n / np.max(resp_n)
        if np.max(gray_n) > 1e-6:
            gray_n = gray_n / np.max(gray_n)
        weights = (
            float(self.params.correction_response_weight) * resp_n
            + float(self.params.correction_gray_weight) * gray_n
            + 1e-4
        )
        v_corr = v_raw.astype(np.float32).copy()
        max_shift = float(self.params.correction_max_shift)
        for i in range(n):
            l = max(0, i - radius)
            r = min(n, i + radius + 1)
            w = weights[l:r]
            vv = v_raw[l:r].astype(np.float32)
            v_hat = float(np.sum(w * vv) / max(1e-6, float(np.sum(w))))
            shift = float(np.clip(v_hat - float(v_raw[i]), -max_shift, max_shift))
            v_corr[i] = float(v_raw[i]) + shift
        return v_corr

    def _build_segments_from_components(
        self,
        labels: np.ndarray,
        keep_labels: list[int],
        label_boxes: dict[int, tuple[int, int, int, int]],
        response: np.ndarray,
        gray: np.ndarray,
        maps: dict[str, np.ndarray],
    ) -> list[dict[str, Any]]:
        segments: list[dict[str, Any]] = []
        h, w = gray.shape[:2]
        for lab in keep_labels:
            box = label_boxes.get(int(lab))
            if box is None:
                continue
            x0, y0, bw, bh = box
            label_roi = labels[y0:y0 + bh, x0:x0 + bw]
            local_mask = label_roi == int(lab)
            if not np.any(local_mask):
                continue
            ys_local, xs_local = np.where(local_mask)
            xs = xs_local.astype(np.int32) + int(x0)
            ys = ys_local.astype(np.int32) + int(y0)
            area = int(xs.size)
            cols_unique = np.unique(xs.astype(np.int32))
            if cols_unique.size < 2:
                continue
            rs_all = response[ys, xs].astype(np.float32)
            gs_all = gray[ys, xs].astype(np.float32)
            t_all = maps['t'][ys, xs].astype(np.float32)
            nx_all = maps['nx'][ys, xs].astype(np.float32)
            ny_all = maps['ny'][ys, xs].astype(np.float32)
            u_pix = xs.astype(np.float32) + t_all * nx_all
            v_pix = ys.astype(np.float32) + t_all * ny_all
            ww_all = 0.75 * rs_all + 0.25 * gs_all + 1e-4

            sum_w = np.bincount(xs, weights=ww_all, minlength=w).astype(np.float32)
            sum_uw = np.bincount(xs, weights=ww_all * u_pix, minlength=w).astype(np.float32)
            sum_vw = np.bincount(xs, weights=ww_all * v_pix, minlength=w).astype(np.float32)
            sum_g = np.bincount(xs, weights=gs_all, minlength=w).astype(np.float32)
            cnt = np.bincount(xs, minlength=w).astype(np.float32)
            max_r = np.full(w, -np.inf, dtype=np.float32)
            np.maximum.at(max_r, xs, rs_all)

            cols = np.where(sum_w > 0.0)[0].astype(np.int32)
            if len(cols) < 2:
                continue

            u_np = (sum_uw[cols] / np.maximum(1e-6, sum_w[cols])).astype(np.float32)
            v_np = (sum_vw[cols] / np.maximum(1e-6, sum_w[cols])).astype(np.float32)
            u_np = np.clip(u_np, cols.astype(np.float32) - 0.6, cols.astype(np.float32) + 0.6)
            v_np = np.clip(v_np, 0.0, float(h - 1))
            resp_np = np.maximum(0.0, max_r[cols]).astype(np.float32)
            gray_np = (sum_g[cols] / np.maximum(1.0, cnt[cols])).astype(np.float32)
            cols_np = cols.astype(np.int32)
            slope = 0.0
            if len(u_np) >= 2:
                coeff = np.polyfit(u_np.astype(np.float64), v_np.astype(np.float64), deg=1)
                slope = float(coeff[0])
            x_span = int(np.max(xs) - np.min(xs) + 1)
            y_span = int(np.max(ys) - np.min(ys) + 1)
            aspect = float(x_span / max(1, y_span))
            seg = {
                'label': int(lab),
                'labels': [int(lab)],
                'cols': cols_np,
                'u_raw': u_np,
                'v_raw': v_np,
                'response': resp_np,
                'gray': gray_np,
                'start_col': int(cols_np[0]),
                'end_col': int(cols_np[-1]),
                'length': int(len(cols_np)),
                'area': int(area),
                'aspect': float(aspect),
                'slope': float(slope),
                'mean_response': float(np.mean(resp_np)),
                'mean_gray': float(np.mean(gray_np)),
            }
            seg['score'] = float(
                0.65 * seg['mean_response'] + 0.30 * seg['mean_gray'] + 0.05 * float(seg['length'])
            )
            segments.append(seg)
        return segments

    def _filter_segments(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept: list[dict[str, Any]] = []
        for seg in segments:
            length = int(seg['length'])
            area = int(seg['area'])
            aspect = float(seg['aspect'])
            slope = float(seg['slope'])
            if length < int(self.params.segment_min_cols):
                continue
            if area < int(self.params.segment_min_area):
                continue
            if abs(slope) > float(self.params.segment_max_abs_slope):
                continue
            if aspect < float(self.params.segment_min_aspect) and length < int(1.6 * float(self.params.segment_min_cols)):
                continue
            kept.append(seg)
        kept.sort(key=lambda s: s['start_col'])
        return kept

    def _suppress_parallel_segments(self, segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        if len(segments) <= 1:
            return segments, 0
        order = sorted(range(len(segments)), key=lambda i: float(segments[i]['score']), reverse=True)
        suppressed = np.zeros(len(segments), dtype=bool)
        sup_count = 0
        for oi, idx_i in enumerate(order):
            if suppressed[idx_i]:
                continue
            seg_i = segments[idx_i]
            cols_i = seg_i['cols'].astype(np.int32)
            for idx_j in order[oi + 1:]:
                if suppressed[idx_j]:
                    continue
                seg_j = segments[idx_j]
                cols_j = seg_j['cols'].astype(np.int32)
                overlap_start = max(int(cols_i[0]), int(cols_j[0]))
                overlap_end = min(int(cols_i[-1]), int(cols_j[-1]))
                if overlap_end <= overlap_start:
                    continue
                overlap_cols = np.arange(overlap_start, overlap_end + 1, dtype=np.int32)
                overlap_ratio = float(len(overlap_cols)) / max(1.0, float(min(len(cols_i), len(cols_j))))
                if overlap_ratio < float(self.params.segment_parallel_overlap_ratio):
                    continue
                vi = np.interp(overlap_cols, cols_i, seg_i['v_raw'])
                vj = np.interp(overlap_cols, cols_j, seg_j['v_raw'])
                mean_off = float(np.mean(np.abs(vi - vj)))
                slope_diff = abs(float(seg_i['slope']) - float(seg_j['slope']))
                near_duplicate_range = (
                    overlap_ratio >= 0.90
                    and abs(int(seg_i['start_col']) - int(seg_j['start_col'])) <= 8
                    and abs(int(seg_i['end_col']) - int(seg_j['end_col'])) <= 8
                    and mean_off <= 12.0
                )
                if (
                    near_duplicate_range
                    or (
                        slope_diff <= float(self.params.segment_parallel_slope_diff)
                        and (
                            mean_off <= float(self.params.segment_duplicate_max_offset)
                            or (
                                float(self.params.secondary_suppress_min_offset)
                                <= mean_off
                                <= float(self.params.secondary_suppress_max_offset)
                            )
                        )
                    )
                ):
                    suppressed[idx_j] = True
                    sup_count += 1
        kept = [seg for i, seg in enumerate(segments) if not suppressed[i]]
        kept.sort(key=lambda s: s['start_col'])
        return kept, int(sup_count)

    def _prune_minor_segments(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(segments) <= 1:
            return segments
        best_len = max(float(seg['length']) for seg in segments)
        best_score = max(float(seg['score']) for seg in segments)
        len_ratio_thr = float(self.params.segment_minor_keep_len_ratio)
        score_ratio_thr = float(self.params.segment_minor_keep_score_ratio)
        kept: list[dict[str, Any]] = []
        for seg in segments:
            len_ratio = float(seg['length']) / max(1e-6, best_len)
            score_ratio = float(seg['score']) / max(1e-6, best_score)
            if len_ratio >= len_ratio_thr or score_ratio >= score_ratio_thr:
                kept.append(seg)
        if len(kept) == 0:
            best = max(segments, key=lambda s: float(s['score']))
            return [best]
        kept.sort(key=lambda s: s['start_col'])
        return kept

    def _merge_segments_strict(self, segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        if not bool(self.params.merge_enable) or len(segments) <= 1:
            return segments, 0
        merged: list[dict[str, Any]] = []
        merged_count = 0
        cur = segments[0].copy()
        cur['v_corr'] = cur['v_corr'].copy()
        cur['u_corr'] = cur['u_corr'].copy()
        cur['cols_corr'] = cur['cols_corr'].copy()
        for nxt0 in segments[1:]:
            nxt = nxt0
            gap = int(nxt['start_col']) - int(cur['end_col']) - 1
            slope_diff = abs(float(cur['slope']) - float(nxt['slope']))
            end_vdiff = abs(float(cur['v_corr'][-1]) - float(nxt['v_corr'][0]))
            curvature_delta = slope_diff
            do_merge = (
                gap >= 0
                and gap <= int(self.params.merge_max_gap)
                and slope_diff <= float(self.params.merge_max_slope_diff)
                and end_vdiff <= float(self.params.merge_max_vdiff)
                and curvature_delta <= float(self.params.merge_max_curvature_delta)
            )
            if not do_merge:
                merged.append(cur)
                cur = nxt.copy()
                cur['v_corr'] = cur['v_corr'].copy()
                cur['u_corr'] = cur['u_corr'].copy()
                cur['cols_corr'] = cur['cols_corr'].copy()
                continue

            if gap > 0:
                interp_cols = np.arange(int(cur['end_col']) + 1, int(nxt['start_col']), dtype=np.int32)
                interp_v = np.linspace(float(cur['v_corr'][-1]), float(nxt['v_corr'][0]), num=len(interp_cols) + 2, dtype=np.float32)[1:-1]
                interp_u = interp_cols.astype(np.float32)
                cur['cols_corr'] = np.concatenate([cur['cols_corr'], interp_cols, nxt['cols_corr']]).astype(np.int32)
                cur['u_corr'] = np.concatenate([cur['u_corr'], interp_u, nxt['u_corr']]).astype(np.float32)
                cur['v_corr'] = np.concatenate([cur['v_corr'], interp_v, nxt['v_corr']]).astype(np.float32)
            else:
                cur['cols_corr'] = np.concatenate([cur['cols_corr'], nxt['cols_corr']]).astype(np.int32)
                cur['u_corr'] = np.concatenate([cur['u_corr'], nxt['u_corr']]).astype(np.float32)
                cur['v_corr'] = np.concatenate([cur['v_corr'], nxt['v_corr']]).astype(np.float32)
            cur['end_col'] = int(nxt['end_col'])
            cur['length'] = int(len(cur['cols_corr']))
            cur['labels'] = list(cur.get('labels', [int(cur.get('label', -1))])) + list(nxt.get('labels', [int(nxt.get('label', -1))]))
            cur['slope'] = float(
                np.polyfit(cur['u_corr'].astype(np.float64), cur['v_corr'].astype(np.float64), deg=1)[0]
            ) if len(cur['u_corr']) >= 2 else 0.0
            merged_count += 1
        merged.append(cur)
        return merged, int(merged_count)

    def extract_points(self, pre: PreprocessArtifacts) -> ExtractionArtifacts:
        gray = pre.gray
        maps = self._compute_steger_maps(gray)
        lambda2 = maps['lambda2']
        response = np.maximum(-lambda2, 0.0)
        neg_values = response[lambda2 < 0]
        eig_thr = (
            float(np.percentile(neg_values, float(self.params.adaptive_eigen_percentile)))
            if neg_values.size > 0
            else float(self.params.adaptive_eigen_floor)
        )
        eig_thr = max(float(self.params.adaptive_eigen_floor), eig_thr)
        gray_thr = float(pre.meta.get('adaptive_threshold', 200.0))

        candidate_mask_bool = maps['mask_t'] & (gray >= gray_thr) & (lambda2 < -eig_thr)
        candidate_mask_bool, labels, keep_labels, label_boxes, cc_meta = self._filter_candidates_connected_components(candidate_mask_bool)

        segments = self._build_segments_from_components(
            labels=labels,
            keep_labels=keep_labels,
            label_boxes=label_boxes,
            response=response,
            gray=gray,
            maps=maps,
        )
        segments = self._filter_segments(segments)
        segments, parallel_sup_count = self._suppress_parallel_segments(segments)
        segments = self._prune_minor_segments(segments)

        if len(segments) == 0:
            return ExtractionArtifacts(
                candidate_mask=(candidate_mask_bool.astype(np.uint8) * 255),
                final_mask=np.zeros_like(gray, dtype=np.uint8),
                candidate_points_uv=np.zeros((0, 2), dtype=np.float32),
                final_points_uv=np.zeros((0, 2), dtype=np.float32),
                candidate_segments_uv=[],
                final_segments_uv=[],
                meta={
                    'gray_threshold': gray_thr,
                    'eigen_threshold_adaptive': eig_thr,
                    'segment_count': 0.0,
                    'merged_segment_count': 0.0,
                    'restart_count': 0.0,
                    'longest_continuous_segment': 0.0,
                    'mean_segment_length': 0.0,
                    'seed_confidence': 0.0,
                    'secondary_suppressed_count': float(parallel_sup_count),
                    'mean_segment_jitter_before': float('nan'),
                    'mean_segment_jitter_after': float('nan'),
                    'mean_segment_correction_delta': float('nan'),
                    **cc_meta,
                },
            )

        jitter_before_vals: list[float] = []
        jitter_after_vals: list[float] = []
        correction_delta_vals: list[float] = []
        for seg in segments:
            v_raw = seg['v_raw'].astype(np.float32)
            v_corr = self._segment_correct_v(v_raw, seg['response'].astype(np.float32), seg['gray'].astype(np.float32))
            seg['v_corr'] = v_corr
            seg['u_corr'] = seg['u_raw'].astype(np.float32)
            seg['cols_corr'] = seg['cols'].astype(np.int32)
            jitter_before_vals.append(self._segment_jitter(v_raw))
            jitter_after_vals.append(self._segment_jitter(v_corr))
            correction_delta_vals.append(float(np.mean(np.abs(v_corr - v_raw))))

        segments, merged_count = self._merge_segments_strict(segments)
        segments.sort(key=lambda s: s['start_col'])

        keep_labels_final: set[int] = set()
        for seg in segments:
            for lab in seg.get('labels', [seg.get('label', -1)]):
                if int(lab) >= 0:
                    keep_labels_final.add(int(lab))
        candidate_mask_post = np.isin(labels, list(keep_labels_final))

        candidate_points = self._subpixel_points_from_mask(candidate_mask_post, maps['t'], maps['nx'], maps['ny'])
        candidate_segments_uv = [
            np.column_stack([seg['u_raw'], seg['v_raw']]).astype(np.float32) for seg in segments
        ]
        final_segments_uv = [
            np.column_stack([seg['u_corr'], seg['v_corr']]).astype(np.float32) for seg in segments
        ]
        if len(final_segments_uv) > 0:
            final_points = np.concatenate(final_segments_uv, axis=0).astype(np.float32)
        else:
            final_points = np.zeros((0, 2), dtype=np.float32)

        h, w = gray.shape[:2]
        final_mask = np.zeros((h, w), dtype=np.uint8)
        for seg in segments:
            cols = seg['cols_corr'].astype(np.int32)
            vals = seg['v_corr'].astype(np.float32)
            for col, vv in zip(cols, vals):
                yi = int(np.clip(round(float(vv)), 0, h - 1))
                xi = int(np.clip(col, 0, w - 1))
                final_mask[yi, xi] = 255

        seg_lengths = [len(seg['cols_corr']) for seg in segments]
        longest_seg = float(max(seg_lengths)) if len(seg_lengths) > 0 else 0.0
        mean_seg = float(np.mean(seg_lengths)) if len(seg_lengths) > 0 else 0.0

        return ExtractionArtifacts(
            candidate_mask=(candidate_mask_post.astype(np.uint8) * 255),
            final_mask=final_mask,
            candidate_points_uv=candidate_points,
            final_points_uv=final_points,
            candidate_segments_uv=candidate_segments_uv,
            final_segments_uv=final_segments_uv,
            meta={
                'gray_threshold': gray_thr,
                'eigen_threshold_adaptive': eig_thr,
                'segment_count': float(len(segments)),
                'merged_segment_count': float(merged_count),
                'restart_count': 0.0,
                'longest_continuous_segment': float(longest_seg),
                'mean_segment_length': float(mean_seg),
                'seed_confidence': 1.0,
                'secondary_suppressed_count': float(parallel_sup_count),
                'mean_segment_jitter_before': float(np.mean(jitter_before_vals)) if len(jitter_before_vals) > 0 else float('nan'),
                'mean_segment_jitter_after': float(np.mean(jitter_after_vals)) if len(jitter_after_vals) > 0 else float('nan'),
                'mean_segment_correction_delta': float(np.mean(correction_delta_vals)) if len(correction_delta_vals) > 0 else float('nan'),
                'final_segments_uv_local': final_segments_uv,
                'candidate_segments_uv_local': candidate_segments_uv,
                **cc_meta,
            },
        )

def discover_images(input_dir: Path | None, config_image_paths: tuple[Path, ...]) -> list[Path]:
    if input_dir is None:
        paths = [Path(p) for p in config_image_paths]
    else:
        if not input_dir.exists():
            raise FileNotFoundError(f'input_dir does not exist: {input_dir}')
        paths = sorted([p for p in input_dir.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS])

    resolved = [p for p in paths if p.suffix.lower() in SUPPORTED_EXTENSIONS and p.exists()]
    if len(resolved) == 0:
        supported = ', '.join(sorted(SUPPORTED_EXTENSIONS))
        raise RuntimeError(f'No valid images found. Supported formats: {supported}.')
    return resolved


def save_visualizations(
    result: SingleImageResult,
    output_dir: Path,
    enable_3d_vis: bool,
    save_intermediate: bool,
    top_view_display_mode: str = 'image_like',
) -> Path:
    version_dir = output_dir / 'visualizations' / result.version
    version_dir.mkdir(parents=True, exist_ok=True)
    stem = result.image_path.stem
    vis_path = version_dir / f'{stem}_{result.version}_overview.png'

    x0, y0, x1, y1 = result.roi_rect
    undist_with_roi = result.undistorted_bgr.copy()
    cv2.rectangle(undist_with_roi, (x0, y0), (x1 - 1, y1 - 1), (0, 255, 0), 2)

    candidate_global = result.extraction.candidate_points_uv.copy()
    if len(candidate_global) > 0:
        candidate_global[:, 0] += float(x0)
        candidate_global[:, 1] += float(y0)
    candidate_overlay = draw_points_overlay(result.undistorted_bgr, candidate_global, color=(255, 180, 0), radius=1)
    final_overlay = candidate_overlay.copy()
    final_segments_global = result.extraction.meta.get('final_segments_uv_global', [])
    if isinstance(final_segments_global, list) and len(final_segments_global) > 0:
        for seg in final_segments_global:
            if not isinstance(seg, np.ndarray) or len(seg) == 0:
                continue
            final_overlay = draw_points_overlay(final_overlay, seg, color=(0, 255, 255), radius=1)
    else:
        final_overlay = draw_points_overlay(final_overlay, result.final_points_uv_global, color=(0, 255, 255), radius=1)

    fig = plt.figure(figsize=(18, 9.5))
    gs = fig.add_gridspec(2, 4, width_ratios=[1.0, 1.0, 1.15, 1.25], height_ratios=[1.0, 1.0])

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(cv2.cvtColor(undist_with_roi, cv2.COLOR_BGR2RGB))
    ax1.set_title('Undistorted + ROI')
    ax1.axis('off')

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(cv2.cvtColor(result.roi_bgr, cv2.COLOR_BGR2RGB))
    ax2.set_title('ROI Crop')
    ax2.axis('off')

    ax3 = fig.add_subplot(gs[0, 2])
    ax3.imshow(result.preprocess.gray, cmap='gray', vmin=0, vmax=255)
    ax3.set_title('Preprocess')
    ax3.axis('off')

    ax4 = fig.add_subplot(gs[1, 0])
    ax4.imshow(result.extraction.candidate_mask, cmap='gray', vmin=0, vmax=255)
    ax4.set_title('Candidate Mask')
    ax4.axis('off')

    ax5 = fig.add_subplot(gs[1, 1:3])
    ax5.imshow(cv2.cvtColor(final_overlay, cv2.COLOR_BGR2RGB))
    ax5.set_title('Final Centerline')
    legend_handles = [
        Line2D([0], [0], marker='o', color='none', markerfacecolor=(0.0, 180.0 / 255.0, 1.0), markersize=6, label='candidate'),
        Line2D([0], [0], marker='o', color='none', markerfacecolor=(1.0, 1.0, 0.0), markersize=6, label='final'),
    ]
    ax5.legend(handles=legend_handles, loc='upper left', fontsize=8, framealpha=0.72)
    ax5.axis('off')

    ax6 = fig.add_subplot(gs[:, 3])
    if enable_3d_vis and len(result.points_3d) > 0:
        x_plot = result.points_3d[:, 1]  # horizontal = robot Y
        y_plot = result.points_3d[:, 0]  # vertical = robot X
        z_plot = result.points_3d[:, 2]
        sc = ax6.scatter(x_plot, y_plot, c=z_plot, cmap='jet', s=8)
        cbar = fig.colorbar(sc, ax=ax6, fraction=0.046, pad=0.04)
        cbar.set_label('Robot Z (Up, mm)')
        ax6.set_xlim(-350, 350)  # Y range
        ax6.set_ylim(0, 700)     # X range
        mode = str(top_view_display_mode).lower()
        if mode == 'image_like':
            ax6.invert_xaxis()
        ax6.set_xlabel('Robot Y (Left, mm)')
        ax6.set_ylabel('Robot X (Forward, mm)')
        if mode == 'image_like':
            ax6.set_title('3D Top View (Y horizontal, X vertical, image-like display)')
        else:
            ax6.set_title('3D Top View (robot-frame display)')
        ax6.grid(True, linestyle='--', alpha=0.4)
        ax6.set_aspect('equal', adjustable='box')
    else:
        ax6.text(0.5, 0.5, '3D disabled or no points', ha='center', va='center')
        ax6.axis('off')

    _, _, max_gap = continuity_stats_from_points(result.extraction.final_points_uv, int(x1 - x0))
    restart_count = int(float(result.extraction.meta.get('restart_count', 0.0)))
    fig.suptitle(
        f"{result.version} | {result.image_path.name} | "
        f"pre={result.preprocess_time_ms:.2f}ms ext={result.extraction_time_ms:.2f}ms total={result.total_time_ms:.2f}ms | "
        f"restart={restart_count} max_gap={max_gap}"
    )
    fig.subplots_adjust(left=0.03, right=0.97, top=0.90, bottom=0.05, wspace=0.18, hspace=0.22)
    fig.savefig(vis_path, dpi=170)
    plt.close(fig)

    if save_intermediate:
        inter_dir = output_dir / 'intermediate' / result.version / stem
        inter_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(inter_dir / f'{stem}_undistorted.png'), result.undistorted_bgr)
        cv2.imwrite(str(inter_dir / f'{stem}_roi.png'), result.roi_bgr)
        cv2.imwrite(str(inter_dir / f'{stem}_preprocess.png'), result.preprocess.gray)
        cv2.imwrite(str(inter_dir / f'{stem}_candidate_mask.png'), result.extraction.candidate_mask)
        cv2.imwrite(str(inter_dir / f'{stem}_final_mask.png'), result.extraction.final_mask)
        cv2.imwrite(str(inter_dir / f'{stem}_overlay_final.png'), final_overlay)
        if result.version == 'v1_roi_adaptive_continuity':
            candidate_segments_local = result.extraction.meta.get('candidate_segments_uv_local', [])
            final_segments_local = result.extraction.meta.get('final_segments_uv_local', [])
            seg_prop = result.undistorted_bgr.copy()
            raw_vs_corrected = result.undistorted_bgr.copy()
            if isinstance(candidate_segments_local, list):
                for seg in candidate_segments_local:
                    if not isinstance(seg, np.ndarray) or len(seg) == 0:
                        continue
                    seg_g = seg.astype(np.float32).copy()
                    seg_g[:, 0] += float(x0)
                    seg_g[:, 1] += float(y0)
                    poly = np.round(seg_g).astype(np.int32).reshape(-1, 1, 2)
                    cv2.polylines(seg_prop, [poly], isClosed=False, color=(0, 165, 255), thickness=1, lineType=cv2.LINE_AA)
            if isinstance(candidate_segments_local, list):
                for seg in candidate_segments_local:
                    if not isinstance(seg, np.ndarray) or len(seg) == 0:
                        continue
                    seg_g = seg.astype(np.float32).copy()
                    seg_g[:, 0] += float(x0)
                    seg_g[:, 1] += float(y0)
                    poly = np.round(seg_g).astype(np.int32).reshape(-1, 1, 2)
                    cv2.polylines(raw_vs_corrected, [poly], isClosed=False, color=(0, 165, 255), thickness=1, lineType=cv2.LINE_AA)
            if isinstance(final_segments_local, list):
                for seg in final_segments_local:
                    if not isinstance(seg, np.ndarray) or len(seg) == 0:
                        continue
                    seg_g = seg.astype(np.float32).copy()
                    seg_g[:, 0] += float(x0)
                    seg_g[:, 1] += float(y0)
                    poly = np.round(seg_g).astype(np.int32).reshape(-1, 1, 2)
                    cv2.polylines(raw_vs_corrected, [poly], isClosed=False, color=(0, 255, 255), thickness=1, lineType=cv2.LINE_AA)
            cv2.imwrite(str(inter_dir / f'{stem}_segment_proposal.png'), seg_prop)
            cv2.imwrite(str(inter_dir / f'{stem}_raw_vs_corrected.png'), raw_vs_corrected)
        for key, img in result.preprocess.debug_images.items():
            cv2.imwrite(str(inter_dir / f'{stem}_{key}.png'), img)

    return vis_path


def run_dataset(
    extractor,
    image_paths: list[Path],
    output_dir: Path,
    enable_3d_vis: bool,
    save_intermediate: bool,
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for idx, image_path in enumerate(image_paths, start=1):
        image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image_bgr is None:
            dummy = np.zeros((720, 1280, 3), dtype=np.uint8)
            result = SingleImageResult(
                version=extractor.version_name,
                image_path=image_path,
                raw_bgr=dummy,
                undistorted_bgr=dummy,
                roi_bgr=dummy,
                roi_rect=(0, 0, dummy.shape[1], dummy.shape[0]),
                preprocess=PreprocessArtifacts(gray=np.zeros(dummy.shape[:2], dtype=np.uint8)),
                extraction=ExtractionArtifacts(
                    candidate_mask=np.zeros(dummy.shape[:2], dtype=np.uint8),
                    final_mask=np.zeros(dummy.shape[:2], dtype=np.uint8),
                    candidate_points_uv=np.zeros((0, 2), dtype=np.float32),
                    final_points_uv=np.zeros((0, 2), dtype=np.float32),
                    meta={},
                ),
                final_points_uv_global=np.zeros((0, 2), dtype=np.float32),
                points_3d=np.zeros((0, 3), dtype=np.float64),
                preprocess_time_ms=0.0,
                extraction_time_ms=0.0,
                reconstruct_time_ms=0.0,
                total_time_ms=0.0,
                error_message='Failed to read image',
            )
        else:
            result = extractor.run_single_image(image_bgr=image_bgr, image_path=image_path)

        row = compute_metrics(result, extractor.params)
        rows.append(row)
        save_visualizations(
            result,
            output_dir,
            enable_3d_vis,
            save_intermediate,
            top_view_display_mode=str(getattr(extractor.params, 'top_view_display_mode', 'image_like')),
        )

        print(
            f"[{extractor.version_name}] {idx}/{len(image_paths)} {image_path.name} | "
            f"pts2d={int(float(row['extracted_points_2d']))} pts3d={int(float(row['valid_points_3d']))} "
            f"cov={float(row['effective_column_coverage']):.4f} gap={int(float(row['continuity_gap_count']))} "
            f"max_gap={int(float(row['continuity_max_gap']))} seg={int(float(row.get('segment_count', 0.0)))} "
            f"total={float(row['total_time_ms']):.2f}ms"
        )

    return rows

def write_rows_csv(rows: list[dict[str, float | str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(rows) == 0:
        output_path.write_text('', encoding='utf-8-sig')
        return
    with output_path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def aggregate_summary(all_rows: dict[str, list[dict[str, float | str]]]) -> list[dict[str, float | str]]:
    summary_rows: list[dict[str, float | str]] = []
    for version in DEFAULT_VERSION_ORDER:
        if version not in all_rows:
            continue
        rows = all_rows[version]
        if len(rows) == 0:
            continue

        def mean_of(key: str) -> float:
            vals = [float(r[key]) for r in rows if key in r]
            arr = np.asarray(vals, dtype=np.float64)
            arr = arr[np.isfinite(arr)]
            return float(np.mean(arr)) if arr.size > 0 else float('nan')

        def mean_abs_of(key: str) -> float:
            vals = [abs(float(r[key])) for r in rows if key in r]
            arr = np.asarray(vals, dtype=np.float64)
            arr = arr[np.isfinite(arr)]
            return float(np.mean(arr)) if arr.size > 0 else float('nan')

        total = len(rows)
        empty_count = sum(1 for r in rows if int(float(r['valid_points_3d'])) == 0)
        ground_count = sum(1 for r in rows if float(r['is_ground_like']) > 0.5)
        summary_rows.append(
            {
                'version': version,
                'image_count': float(total),
                'empty_count': float(empty_count),
                'empty_rate': float(empty_count / max(1, total)),
                'ground_like_count': float(ground_count),
                'mean_preprocess_time_ms': mean_of('preprocess_time_ms'),
                'mean_extraction_time_ms': mean_of('extraction_time_ms'),
                'mean_total_time_ms': mean_of('total_time_ms'),
                'mean_candidate_points_2d': mean_of('candidate_points_2d'),
                'mean_extracted_points_2d': mean_of('extracted_points_2d'),
                'mean_valid_points_3d': mean_of('valid_points_3d'),
                'mean_effective_column_coverage': mean_of('effective_column_coverage'),
                'mean_continuity_gap_count': mean_of('continuity_gap_count'),
                'mean_continuity_max_gap': mean_of('continuity_max_gap'),
                'mean_restart_count': mean_of('restart_count'),
                'mean_longest_continuous_segment': mean_of('longest_continuous_segment'),
                'mean_mean_segment_length': mean_of('mean_segment_length'),
                'mean_off_trend_penalty_mean': mean_of('off_trend_penalty_mean'),
                'mean_repaired_gap_count': mean_of('repaired_gap_count'),
                'mean_repaired_gap_max': mean_of('repaired_gap_max'),
                'mean_seed_confidence': mean_of('seed_confidence'),
                'mean_segment_count': mean_of('segment_count'),
                'mean_merged_segment_count': mean_of('merged_segment_count'),
                'mean_secondary_suppressed_count': mean_of('secondary_suppressed_count'),
                'mean_cc_removed_loop_area': mean_of('cc_removed_loop_area'),
                'mean_cc_removed_compact_area': mean_of('cc_removed_compact_area'),
                'mean_segment_jitter_before': mean_of('mean_segment_jitter_before'),
                'mean_segment_jitter_after': mean_of('mean_segment_jitter_after'),
                'mean_segment_correction_delta': mean_of('mean_segment_correction_delta'),
                'mean_Z_mean': mean_of('Z_mean'),
                'mean_abs_Z_mean': mean_abs_of('Z_mean'),
                'mean_Z_std': mean_of('Z_std'),
                'mean_X_span_p95_p5': mean_of('X_span_p95_p5'),
                'mean_line_fit_rmse': mean_of('line_fit_rmse'),
                'mean_quad_fit_rmse': mean_of('quad_fit_rmse'),
            }
        )

    if len(summary_rows) > 0:
        speed_vals = np.array([1.0 / max(1e-6, float(r['mean_total_time_ms'])) for r in summary_rows], dtype=np.float64)
        cov_vals = np.array([float(r['mean_effective_column_coverage']) for r in summary_rows], dtype=np.float64)
        gap_vals = np.array([float(r['mean_continuity_gap_count']) for r in summary_rows], dtype=np.float64)
        max_gap_vals = np.array([float(r['mean_continuity_max_gap']) for r in summary_rows], dtype=np.float64)
        longest_seg_vals = np.array([float(r['mean_longest_continuous_segment']) for r in summary_rows], dtype=np.float64)
        zstd_vals = np.array([float(r['mean_Z_std']) for r in summary_rows], dtype=np.float64)
        abs_z_vals = np.array([float(r['mean_abs_Z_mean']) for r in summary_rows], dtype=np.float64)
        xspan_vals = np.array([float(r['mean_X_span_p95_p5']) for r in summary_rows], dtype=np.float64)

        def normalize(arr: np.ndarray, inverse: bool = False) -> np.ndarray:
            arr2 = np.asarray(arr, dtype=np.float64).copy()
            finite_mask = np.isfinite(arr2)
            if not np.any(finite_mask):
                return np.ones_like(arr2) * 0.5
            fill_value = float(np.median(arr2[finite_mask]))
            arr2[~finite_mask] = fill_value
            arr2 = -arr2 if inverse else arr2
            a_min = float(np.min(arr2))
            a_max = float(np.max(arr2))
            if a_max <= a_min + 1e-9:
                return np.ones_like(arr2) * 0.5
            return (arr2 - a_min) / (a_max - a_min)

        speed_n = normalize(speed_vals)
        cov_n = normalize(cov_vals)
        gap_n = normalize(gap_vals, inverse=True)
        max_gap_n = normalize(max_gap_vals, inverse=True)
        longest_seg_n = normalize(longest_seg_vals)
        zstd_n = normalize(zstd_vals, inverse=True)
        abs_z_n = normalize(abs_z_vals, inverse=True)
        xspan_n = normalize(xspan_vals, inverse=True)

        for i, row in enumerate(summary_rows):
            row['composite_score'] = float(
                0.22 * cov_n[i]
                + 0.14 * gap_n[i]
                + 0.14 * max_gap_n[i]
                + 0.16 * longest_seg_n[i]
                + 0.10 * speed_n[i]
                + 0.10 * zstd_n[i]
                + 0.08 * abs_z_n[i]
                + 0.06 * xspan_n[i]
            )

        summary_rows.sort(key=lambda r: float(r['composite_score']), reverse=True)
        for idx, row in enumerate(summary_rows, start=1):
            row['rank'] = float(idx)

    return summary_rows


def percentage_change(new_value: float, old_value: float) -> float:
    if math.isnan(new_value) or math.isnan(old_value) or abs(old_value) < 1e-9:
        return float('nan')
    return float((new_value - old_value) / abs(old_value) * 100.0)


def build_report_markdown(summary_rows: list[dict[str, float | str]]) -> str:
    by_version = {str(r['version']): r for r in summary_rows}

    def safe(v: str, k: str) -> float:
        return float(by_version[v][k]) if v in by_version else float('nan')

    base = 'v1_base'
    a = 'v1_roi'
    b = 'v1_roi_adaptive'
    c = 'v1_roi_adaptive_continuity'

    base_time = safe(base, 'mean_total_time_ms')
    a_time = safe(a, 'mean_total_time_ms')
    b_time = safe(b, 'mean_total_time_ms')
    c_time = safe(c, 'mean_total_time_ms')

    base_cov = safe(base, 'mean_effective_column_coverage')
    a_cov = safe(a, 'mean_effective_column_coverage')
    b_cov = safe(b, 'mean_effective_column_coverage')

    recommended = summary_rows[0]['version'] if len(summary_rows) > 0 else 'N/A'
    speedup_a_vs_base = float((base_time - a_time) / max(1e-6, base_time) * 100.0) if not math.isnan(base_time) and not math.isnan(a_time) else float('nan')

    lines = [
        '# v1 轻量鲁棒优化 + 消融实验报告',
        '',
        '## Composite Score 权重',
        '- coverage: 0.22（越大越好）',
        '- gap_count: 0.14（越小越好）',
        '- max_gap: 0.14（越小越好）',
        '- longest_continuous_segment: 0.16（越大越好）',
        '- speed(1/total_time): 0.10（越大越好）',
        '- Z_std: 0.10（越小越好）',
        '- abs(Z_mean): 0.08（越小越好）',
        '- X_span_p95_p5: 0.06（越小越好）',
        '',
        '## 各版本均值汇总',
        '|version|rank|score|mean_total_ms|mean_coverage|mean_gap_count|mean_max_gap|mean_seg_count|mean_longest_seg|jitter_before|jitter_after|mean_Z_std|empty_rate|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]

    for row in summary_rows:
        lines.append(
            f"|{row['version']}|{int(float(row.get('rank', 0)))}|{float(row.get('composite_score', float('nan'))):.6f}|"
            f"{float(row['mean_total_time_ms']):.3f}|{float(row['mean_effective_column_coverage']):.6f}|"
            f"{float(row['mean_continuity_gap_count']):.3f}|{float(row['mean_continuity_max_gap']):.3f}|"
            f"{float(row['mean_segment_count']):.3f}|{float(row['mean_longest_continuous_segment']):.3f}|"
            f"{float(row['mean_segment_jitter_before']):.6f}|{float(row['mean_segment_jitter_after']):.6f}|"
            f"{float(row['mean_Z_std']):.6f}|{float(row['empty_rate']):.6f}|"
        )

    lines += [
        '',
        '## 关键结论',
        f"- 版本 A(v1_roi) 相比 baseline(v1_base)：速度提升 {speedup_a_vs_base:.2f}% ，覆盖率变化 {percentage_change(a_cov, base_cov):.2f}%。",
        f"- 版本 B(v1_roi_adaptive) 相比 A：覆盖率变化 {percentage_change(b_cov, a_cov):.2f}% ，空结果率变化 {percentage_change(safe(b, 'empty_rate'), safe(a, 'empty_rate')):.2f}% ，Z_std 变化 {percentage_change(safe(b, 'mean_Z_std'), safe(a, 'mean_Z_std')):.2f}%。",
        f"- 版本 C(v1_roi_adaptive_continuity) 相比 B：gap_count 变化 {percentage_change(safe(c, 'mean_continuity_gap_count'), safe(b, 'mean_continuity_gap_count')):.2f}% ，max_gap 变化 {percentage_change(safe(c, 'mean_continuity_max_gap'), safe(b, 'mean_continuity_max_gap')):.2f}% ，longest_segment 变化 {percentage_change(safe(c, 'mean_longest_continuous_segment'), safe(b, 'mean_longest_continuous_segment')):.2f}% ，总耗时变化 {percentage_change(c_time, b_time):.2f}%。",
        f"- 版本 C 段级统计：segment_count 均值 {safe(c, 'mean_segment_count'):.2f}，merged_segment_count 均值 {safe(c, 'mean_merged_segment_count'):.2f}。",
        f"- 版本 C 坐标抖动：jitter_before={safe(c, 'mean_segment_jitter_before'):.4f}，jitter_after={safe(c, 'mean_segment_jitter_after'):.4f}，correction_delta={safe(c, 'mean_segment_correction_delta'):.4f}。",
        f"- 版本 C 重启机制统计：restart_count 均值 {safe(c, 'mean_restart_count'):.2f}，repaired_gap_count 均值 {safe(c, 'mean_repaired_gap_count'):.2f}，repaired_gap_max 均值 {safe(c, 'mean_repaired_gap_max'):.2f}。",
        f"- ground-like 相关：版本 C 的 abs(Z_mean)={safe(c, 'mean_abs_Z_mean'):.3f}，Z_std={safe(c, 'mean_Z_std'):.3f}，X_span={safe(c, 'mean_X_span_p95_p5'):.3f}。",
        f"- 推荐下一步工程测试版本：`{recommended}`。",
    ]

    return '\n'.join(lines) + '\n'


def export_summary(output_dir: Path, all_rows: dict[str, list[dict[str, float | str]]]) -> tuple[list[dict[str, float | str]], Path, Path]:
    summary_rows = aggregate_summary(all_rows)
    summary_csv = output_dir / 'summary.csv'
    write_rows_csv(summary_rows, summary_csv)
    report_md = output_dir / 'report.md'
    report_md.write_text(build_report_markdown(summary_rows), encoding='utf-8-sig')
    return summary_rows, summary_csv, report_md


def parse_versions(raw: str) -> list[str]:
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    if len(parts) == 0:
        return DEFAULT_VERSION_ORDER.copy()
    unknown = [p for p in parts if p not in DEFAULT_VERSION_ORDER]
    if unknown:
        raise ValueError(f'Unsupported versions: {unknown}. Supported: {DEFAULT_VERSION_ORDER}')
    return parts

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Lightweight robust ablation runner based on v1 baseline.')
    parser.add_argument('--baseline_file', type=Path, default=Path('src/linelaser0319_reusable.py'))
    parser.add_argument('--input_dir', type=Path, default=None)
    parser.add_argument('--output_dir', type=Path, default=Path('outputs/v1_ablation_eval'))
    parser.add_argument('--enable_3d_vis', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--save_intermediate', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--versions', type=str, default=','.join(DEFAULT_VERSION_ORDER))
    parser.add_argument('--gray_threshold', type=float, default=200.0)
    parser.add_argument('--eigen_threshold', type=float, default=170.0)
    parser.add_argument('--roi_center_y_ratio', type=float, default=0.5)
    parser.add_argument('--roi_height_ratio', type=float, default=0.18)
    parser.add_argument('--bg_method', type=str, default='gaussian', choices=['gaussian', 'median', 'tophat'])
    parser.add_argument('--bg_kernel', type=int, default=51)
    parser.add_argument('--percentile_low', type=float, default=5.0)
    parser.add_argument('--percentile_high', type=float, default=99.5)
    parser.add_argument('--percentile_q', type=float, default=92.0)
    parser.add_argument('--mad_k', type=float, default=2.8)
    parser.add_argument('--adaptive_eigen_percentile', type=float, default=72.0)
    parser.add_argument('--tracker_mode', type=str, default='robust_tracker', choices=['robust_tracker', 'adaptive_only'])
    parser.add_argument('--top_view_display_mode', type=str, default='image_like', choices=['robot_frame', 'image_like'])
    parser.add_argument('--continuity_max_jump', type=int, default=8)
    parser.add_argument('--continuity_max_jump_hard', type=int, default=14)
    parser.add_argument('--continuity_interpolation_max_gap', type=int, default=4)
    parser.add_argument('--continuity_smooth_window', type=int, default=5)
    parser.add_argument('--tracker_seed_neighbor_tol', type=int, default=5)
    parser.add_argument('--tracker_seed_neighbor_weight', type=float, default=18.0)
    parser.add_argument('--tracker_candidates_per_col', type=int, default=8)
    parser.add_argument('--tracker_seed_candidates_per_col', type=int, default=1)
    parser.add_argument('--tracker_predict_window', type=int, default=6)
    parser.add_argument('--tracker_max_search_radius', type=int, default=32)
    parser.add_argument('--tracker_match_dist_weight', type=float, default=1.15)
    parser.add_argument('--tracker_curvature_weight', type=float, default=0.32)
    parser.add_argument('--tracker_missing_penalty', type=float, default=8.0)
    parser.add_argument('--restart_after_missing_cols', type=int, default=6)
    parser.add_argument('--restart_max_count', type=int, default=3)
    parser.add_argument('--restart_seed_min_score_quantile', type=float, default=80.0)
    parser.add_argument('--restart_seed_max_offset', type=float, default=30.0)
    parser.add_argument('--long_gap_repair_max', type=int, default=24)
    parser.add_argument('--long_gap_search_radius', type=int, default=12)
    parser.add_argument('--long_gap_fit_window', type=int, default=6)
    parser.add_argument('--long_gap_min_fill_ratio', type=float, default=0.45)
    parser.add_argument('--main_segment_min_ratio', type=float, default=0.35)
    parser.add_argument('--use_ground_prior', type=str, default='auto', choices=['off', 'on', 'auto'])
    parser.add_argument('--ground_prior_weight', type=float, default=0.55)
    parser.add_argument('--ground_band_ratio', type=float, default=0.26)
    parser.add_argument('--ground_prior_mode', type=str, default='hybrid', choices=['center', 'trend', 'hybrid'])
    parser.add_argument('--ground_auto_std_ratio', type=float, default=0.08)
    parser.add_argument('--ground_auto_slope_ratio', type=float, default=0.04)
    parser.add_argument('--cc_min_area', type=int, default=18)
    parser.add_argument('--cc_min_aspect', type=float, default=2.2)
    parser.add_argument('--cc_min_width', type=int, default=52)
    parser.add_argument('--cc_max_angle_deg', type=float, default=35.0)
    parser.add_argument('--cc_closed_loop_min_area', type=int, default=60)
    parser.add_argument('--secondary_suppress_min_offset', type=float, default=4.0)
    parser.add_argument('--secondary_suppress_max_offset', type=float, default=16.0)
    parser.add_argument('--segment_min_cols', type=int, default=42)
    parser.add_argument('--segment_min_area', type=int, default=120)
    parser.add_argument('--segment_min_aspect', type=float, default=2.8)
    parser.add_argument('--segment_max_abs_slope', type=float, default=0.35)
    parser.add_argument('--segment_parallel_overlap_ratio', type=float, default=0.22)
    parser.add_argument('--segment_parallel_slope_diff', type=float, default=0.12)
    parser.add_argument('--segment_duplicate_max_offset', type=float, default=3.0)
    parser.add_argument('--segment_minor_keep_len_ratio', type=float, default=0.12)
    parser.add_argument('--segment_minor_keep_score_ratio', type=float, default=0.55)
    parser.add_argument('--correction_window', type=int, default=7)
    parser.add_argument('--correction_response_weight', type=float, default=0.70)
    parser.add_argument('--correction_gray_weight', type=float, default=0.30)
    parser.add_argument('--correction_max_shift', type=float, default=3.5)
    parser.add_argument('--merge_enable', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('--merge_max_gap', type=int, default=1)
    parser.add_argument('--merge_max_slope_diff', type=float, default=0.08)
    parser.add_argument('--merge_max_vdiff', type=float, default=2.4)
    parser.add_argument('--merge_max_curvature_delta', type=float, default=0.18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.baseline_file.exists():
        raise FileNotFoundError(f'baseline_file not found: {args.baseline_file}')

    params = AblationParams(
        roi_center_y_ratio=float(args.roi_center_y_ratio),
        roi_height_ratio=float(args.roi_height_ratio),
        bg_method=str(args.bg_method),
        bg_kernel=int(args.bg_kernel),
        percentile_low=float(args.percentile_low),
        percentile_high=float(args.percentile_high),
        percentile_q=float(args.percentile_q),
        mad_k=float(args.mad_k),
        adaptive_eigen_percentile=float(args.adaptive_eigen_percentile),
        tracker_mode=str(args.tracker_mode),
        top_view_display_mode=str(args.top_view_display_mode),
        continuity_max_jump=int(args.continuity_max_jump),
        continuity_max_jump_hard=int(args.continuity_max_jump_hard),
        continuity_interpolation_max_gap=int(args.continuity_interpolation_max_gap),
        continuity_smooth_window=int(args.continuity_smooth_window),
        tracker_seed_neighbor_tol=int(args.tracker_seed_neighbor_tol),
        tracker_seed_neighbor_weight=float(args.tracker_seed_neighbor_weight),
        tracker_candidates_per_col=int(args.tracker_candidates_per_col),
        tracker_seed_candidates_per_col=int(args.tracker_seed_candidates_per_col),
        tracker_predict_window=int(args.tracker_predict_window),
        tracker_max_search_radius=int(args.tracker_max_search_radius),
        tracker_match_dist_weight=float(args.tracker_match_dist_weight),
        tracker_curvature_weight=float(args.tracker_curvature_weight),
        tracker_missing_penalty=float(args.tracker_missing_penalty),
        restart_after_missing_cols=int(args.restart_after_missing_cols),
        restart_max_count=int(args.restart_max_count),
        restart_seed_min_score_quantile=float(args.restart_seed_min_score_quantile),
        restart_seed_max_offset=float(args.restart_seed_max_offset),
        long_gap_repair_max=int(args.long_gap_repair_max),
        long_gap_search_radius=int(args.long_gap_search_radius),
        long_gap_fit_window=int(args.long_gap_fit_window),
        long_gap_min_fill_ratio=float(args.long_gap_min_fill_ratio),
        main_segment_min_ratio=float(args.main_segment_min_ratio),
        use_ground_prior=str(args.use_ground_prior),
        ground_prior_weight=float(args.ground_prior_weight),
        ground_band_ratio=float(args.ground_band_ratio),
        ground_prior_mode=str(args.ground_prior_mode),
        ground_auto_std_ratio=float(args.ground_auto_std_ratio),
        ground_auto_slope_ratio=float(args.ground_auto_slope_ratio),
        cc_min_area=int(args.cc_min_area),
        cc_min_aspect=float(args.cc_min_aspect),
        cc_min_width=int(args.cc_min_width),
        cc_max_angle_deg=float(args.cc_max_angle_deg),
        cc_closed_loop_min_area=int(args.cc_closed_loop_min_area),
        secondary_suppress_min_offset=float(args.secondary_suppress_min_offset),
        secondary_suppress_max_offset=float(args.secondary_suppress_max_offset),
        segment_min_cols=int(args.segment_min_cols),
        segment_min_area=int(args.segment_min_area),
        segment_min_aspect=float(args.segment_min_aspect),
        segment_max_abs_slope=float(args.segment_max_abs_slope),
        segment_parallel_overlap_ratio=float(args.segment_parallel_overlap_ratio),
        segment_parallel_slope_diff=float(args.segment_parallel_slope_diff),
        segment_duplicate_max_offset=float(args.segment_duplicate_max_offset),
        segment_minor_keep_len_ratio=float(args.segment_minor_keep_len_ratio),
        segment_minor_keep_score_ratio=float(args.segment_minor_keep_score_ratio),
        correction_window=int(args.correction_window),
        correction_response_weight=float(args.correction_response_weight),
        correction_gray_weight=float(args.correction_gray_weight),
        correction_max_shift=float(args.correction_max_shift),
        merge_enable=bool(args.merge_enable),
        merge_max_gap=int(args.merge_max_gap),
        merge_max_slope_diff=float(args.merge_max_slope_diff),
        merge_max_vdiff=float(args.merge_max_vdiff),
        merge_max_curvature_delta=float(args.merge_max_curvature_delta),
    )

    selected_versions = parse_versions(args.versions)
    cfg_yaw = build_default_config_yaw(preprocess_profile='red_filter')
    legacy_cfg = build_legacy0319_config_from_pipeline(
        pipeline_config=cfg_yaw,
        gray_threshold=float(args.gray_threshold),
        eigen_threshold=float(args.eigen_threshold),
    )

    image_paths = discover_images(args.input_dir, cfg_yaw.image_paths)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_config = {
        'baseline_file': str(args.baseline_file),
        'input_dir': str(args.input_dir) if args.input_dir is not None else '<from_yaw_config>',
        'output_dir': str(output_dir),
        'enable_3d_vis': bool(args.enable_3d_vis),
        'save_intermediate': bool(args.save_intermediate),
        'versions': selected_versions,
        'supported_extensions': sorted(SUPPORTED_EXTENSIONS),
        'image_count': len(image_paths),
        'images': [str(p) for p in image_paths],
        'legacy_config': {
            'camera_matrix': legacy_cfg.camera_matrix.tolist(),
            'dist_coeffs': legacy_cfg.dist_coeffs.tolist(),
            'plane_abcd': legacy_cfg.plane_abcd.tolist(),
            'robot_install': asdict(legacy_cfg.robot_install),
            'steger': asdict(legacy_cfg.steger),
        },
        'ablation_params': asdict(params),
    }
    (output_dir / 'run_config.json').write_text(json.dumps(run_config, ensure_ascii=False, indent=2), encoding='utf-8')

    extractor_map: dict[str, Any] = {
        'v1_base': LaserLineExtractorV1Base(config=legacy_cfg, params=params),
        'v1_roi': LaserLineExtractorROI(config=legacy_cfg, params=params),
        'v1_roi_adaptive': LaserLineExtractorAdaptive(config=legacy_cfg, params=params),
        'v1_roi_adaptive_continuity': LaserLineExtractorAdaptiveContinuity(config=legacy_cfg, params=params),
    }

    all_rows: dict[str, list[dict[str, float | str]]] = {}
    print('=== Ablation Run Start ===')
    print(f'images={len(image_paths)} versions={selected_versions}')

    for version in selected_versions:
        extractor = extractor_map[version]
        print(f'\n--- Running {version} ---')
        rows = run_dataset(
            extractor=extractor,
            image_paths=image_paths,
            output_dir=output_dir,
            enable_3d_vis=bool(args.enable_3d_vis),
            save_intermediate=bool(args.save_intermediate),
        )
        all_rows[version] = rows
        write_rows_csv(rows, output_dir / f'metrics_{version}.csv')

    summary_rows, summary_csv, report_md = export_summary(output_dir=output_dir, all_rows=all_rows)

    print('\n=== Summary (ranked) ===')
    for row in summary_rows:
        print(
            f"{row['version']}: rank={int(float(row.get('rank', 0)))} "
            f"score={float(row.get('composite_score', float('nan'))):.6f} "
            f"total={float(row['mean_total_time_ms']):.3f}ms "
            f"cov={float(row['mean_effective_column_coverage']):.6f} "
            f"gap={float(row['mean_continuity_gap_count']):.3f} "
            f"max_gap={float(row['mean_continuity_max_gap']):.3f} "
            f"restart={float(row['mean_restart_count']):.3f}"
        )

    print('\n=== Outputs ===')
    print(f'output_dir={output_dir}')
    print(f'summary_csv={summary_csv}')
    print(f'report_md={report_md}')


if __name__ == '__main__':
    main()
