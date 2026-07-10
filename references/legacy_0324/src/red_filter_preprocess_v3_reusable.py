from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class RedFilterPreprocessV3Config:
    """
    双分支 red-filter 预处理配置。

    分支A（red branch）:
    - 延续 v2 的红差分思路，用于抑制背景与反光噪声。

    分支B（ridge branch）:
    - 针对白色/浅色表面弱激光线进行局部亮度增强，避免只靠红差分导致的漏检。

    最终输出:
    - normalized_gray_raw: 两分支融合后的“保真输入”，建议用于亚像素定位。
    - normalized_gray: 在 raw 基础上做轻量噪声清理后的结果，建议用于候选掩膜。
    """

    # A) red branch
    red_mix_green: float = 0.05
    red_mix_blue: float = 0.05
    red_blur_kernel: int = 51
    red_use_top_hat: bool = True
    red_top_hat_kernel: int = 13
    red_top_hat_gain: float = 1.0
    red_base_gain: float = 0.7
    red_use_clahe: bool = False
    red_clahe_clip_limit: float = 2.5
    red_clahe_tile_grid_size: int = 8
    red_normalize_percentile_low: float = 0.3
    red_normalize_percentile_high: float = 99.8

    # B) ridge branch
    ridge_source_mode: str = "max_rg"  # {"r_only", "gray", "max_rg"}
    ridge_blur_kernel: int = 41
    ridge_use_top_hat: bool = True
    ridge_top_hat_kernel: int = 15
    ridge_top_hat_gain: float = 0.9
    ridge_local_window: int = 31
    ridge_local_gain: float = 1.1
    ridge_background_gain: float = 0.8
    ridge_base_gain: float = 0.4
    ridge_use_clahe: bool = False
    ridge_clahe_clip_limit: float = 2.0
    ridge_clahe_tile_grid_size: int = 8
    ridge_normalize_percentile_low: float = 0.2
    ridge_normalize_percentile_high: float = 99.8

    # C) fusion
    fusion_mode: str = "weighted_max"  # {"weighted_max", "blend"}
    fusion_red_weight: float = 1.0
    fusion_ridge_weight: float = 0.95
    fused_normalize_percentile_low: float = 0.2
    fused_normalize_percentile_high: float = 99.85

    # D) optional noise filter for normalized_gray
    use_noise_filter: bool = True
    noise_threshold: int = 20
    noise_min_area: int = 20
    noise_min_width: int = 12
    noise_min_aspect: float = 2.0
    noise_open_kernel: int = 3
    noise_median_kernel: int = 3

    # Seed preserve: protect bright/short true line fragments from being removed.
    preserve_seed_threshold: int = 34
    preserve_seed_min_area: int = 8
    preserve_seed_min_long_edge: int = 10


@dataclass(frozen=True)
class RedFilterPreprocessV3Result:
    undistorted_image: np.ndarray
    updated_camera_matrix: Optional[np.ndarray]

    red_difference: np.ndarray
    background_estimate: np.ndarray
    background_suppressed: np.ndarray
    contrast_enhanced: np.ndarray
    normalized_red_branch: np.ndarray

    ridge_source: np.ndarray
    ridge_background_estimate: np.ndarray
    ridge_background_suppressed: np.ndarray
    ridge_local_residual: np.ndarray
    ridge_contrast_enhanced: np.ndarray
    normalized_ridge_branch: np.ndarray

    normalized_gray_raw: np.ndarray
    normalized_gray: np.ndarray
    candidate_seed_mask: np.ndarray


def _ensure_odd(value: int) -> int:
    value = int(value)
    return value if value % 2 == 1 else value + 1


def _clip_u8(image: np.ndarray) -> np.ndarray:
    return np.clip(image, 0, 255).astype(np.uint8)


def _undistort_if_needed(
    image_bgr: np.ndarray,
    camera_matrix: Optional[np.ndarray],
    dist_coeffs: Optional[np.ndarray],
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    if camera_matrix is None or dist_coeffs is None:
        return image_bgr.copy(), None

    h, w = image_bgr.shape[:2]
    new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
        camera_matrix,
        dist_coeffs,
        (w, h),
        1,
        (w, h),
    )
    undistorted = cv2.undistort(
        image_bgr,
        camera_matrix,
        dist_coeffs,
        None,
        new_camera_matrix,
    )
    return undistorted, new_camera_matrix


def _compute_red_difference(image_bgr: np.ndarray, green_weight: float, blue_weight: float) -> np.ndarray:
    b_channel, g_channel, r_channel = cv2.split(image_bgr)
    red_difference = (
        r_channel.astype(np.float32)
        - float(green_weight) * g_channel.astype(np.float32)
        - float(blue_weight) * b_channel.astype(np.float32)
    )
    return _clip_u8(red_difference)


def _choose_ridge_source(image_bgr: np.ndarray, mode: str) -> np.ndarray:
    _, _, r_channel = cv2.split(image_bgr)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    if mode == "r_only":
        return r_channel.copy()
    if mode == "gray":
        return gray
    if mode == "max_rg":
        return np.maximum(r_channel, gray)
    raise ValueError(f"Unsupported ridge_source_mode: {mode}")


def _suppress_background(image_gray: np.ndarray, blur_kernel: int) -> tuple[np.ndarray, np.ndarray]:
    blur_kernel = _ensure_odd(blur_kernel)
    background = cv2.GaussianBlur(image_gray, (blur_kernel, blur_kernel), 0)
    suppressed = cv2.subtract(image_gray, background)
    return background, suppressed


def _compute_local_residual(image_gray: np.ndarray, window: int) -> np.ndarray:
    window = _ensure_odd(window)
    local_mean = cv2.blur(image_gray.astype(np.float32), (window, window))
    residual = image_gray.astype(np.float32) - local_mean
    residual = np.maximum(residual, 0.0)
    return _clip_u8(residual)


def _apply_top_hat(image_gray: np.ndarray, kernel_size: int, base_gain: float, top_hat_gain: float) -> np.ndarray:
    kernel_size = _ensure_odd(kernel_size)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    top_hat = cv2.morphologyEx(image_gray, cv2.MORPH_TOPHAT, kernel)
    enhanced = (
        float(base_gain) * image_gray.astype(np.float32)
        + float(top_hat_gain) * top_hat.astype(np.float32)
    )
    return _clip_u8(enhanced)


def _apply_clahe(image_gray: np.ndarray, clip_limit: float, tile_grid_size: int) -> np.ndarray:
    grid = max(2, int(tile_grid_size))
    clahe = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=(grid, grid))
    return clahe.apply(image_gray)


def _normalize_percentile(image_gray: np.ndarray, low_percentile: float, high_percentile: float) -> np.ndarray:
    low = float(np.clip(low_percentile, 0.0, 100.0))
    high = float(np.clip(high_percentile, low + 1e-3, 100.0))
    low_value, high_value = np.percentile(image_gray, [low, high])
    if high_value <= low_value + 1e-6:
        return np.zeros_like(image_gray)
    normalized = (image_gray.astype(np.float32) - low_value) * (255.0 / (high_value - low_value))
    return _clip_u8(normalized)


def _build_candidate_seed_mask(
    normalized_red_branch: np.ndarray,
    normalized_ridge_branch: np.ndarray,
    threshold: int,
) -> np.ndarray:
    threshold = int(np.clip(threshold, 0, 255))
    seed_red = (normalized_red_branch >= threshold).astype(np.uint8) * 255
    seed_ridge = (normalized_ridge_branch >= threshold).astype(np.uint8) * 255
    return cv2.bitwise_or(seed_red, seed_ridge)


def _suppress_outlier_blobs_with_seed_preserve(
    image_gray: np.ndarray,
    seed_mask: np.ndarray,
    threshold: int,
    min_area: int,
    min_width: int,
    min_aspect: float,
    open_kernel: int,
    median_kernel: int,
    preserve_seed_min_area: int,
    preserve_seed_min_long_edge: int,
) -> np.ndarray:
    source = image_gray.copy()
    if int(median_kernel) > 1:
        source = cv2.medianBlur(source, _ensure_odd(median_kernel))

    threshold = int(np.clip(threshold, 0, 255))
    binary = (source >= threshold).astype(np.uint8) * 255
    binary = cv2.bitwise_or(binary, seed_mask.astype(np.uint8))

    if int(open_kernel) > 1:
        kernel_size = _ensure_odd(open_kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    keep = np.zeros_like(binary)

    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        width = int(stats[label, cv2.CC_STAT_WIDTH])
        height = int(stats[label, cv2.CC_STAT_HEIGHT])

        short_edge = max(1, min(width, height))
        long_edge = max(width, height)
        aspect = float(long_edge / short_edge)

        component_mask = (labels == label).astype(np.uint8) * 255
        seed_overlap = cv2.bitwise_and(component_mask, seed_mask)
        has_seed = np.count_nonzero(seed_overlap) > 0

        regular_ok = (area >= int(min_area)) and (
            width >= int(min_width) or aspect >= float(min_aspect)
        )
        seed_ok = has_seed and (
            area >= int(preserve_seed_min_area)
            and long_edge >= int(preserve_seed_min_long_edge)
        )

        if regular_ok or seed_ok:
            keep[labels == label] = 255

    filtered = np.zeros_like(source)
    filtered[keep > 0] = source[keep > 0]
    return filtered


def _run_red_branch(image_bgr: np.ndarray, config: RedFilterPreprocessV3Config):
    red_difference = _compute_red_difference(
        image_bgr,
        green_weight=config.red_mix_green,
        blue_weight=config.red_mix_blue,
    )
    background_estimate, background_suppressed = _suppress_background(
        red_difference,
        blur_kernel=config.red_blur_kernel,
    )

    contrast_enhanced = background_suppressed
    if config.red_use_top_hat:
        contrast_enhanced = _apply_top_hat(
            contrast_enhanced,
            kernel_size=config.red_top_hat_kernel,
            base_gain=config.red_base_gain,
            top_hat_gain=config.red_top_hat_gain,
        )
    if config.red_use_clahe:
        contrast_enhanced = _apply_clahe(
            contrast_enhanced,
            clip_limit=config.red_clahe_clip_limit,
            tile_grid_size=config.red_clahe_tile_grid_size,
        )

    normalized_red_branch = _normalize_percentile(
        contrast_enhanced,
        low_percentile=config.red_normalize_percentile_low,
        high_percentile=config.red_normalize_percentile_high,
    )
    return red_difference, background_estimate, background_suppressed, contrast_enhanced, normalized_red_branch


def _run_ridge_branch(image_bgr: np.ndarray, config: RedFilterPreprocessV3Config):
    ridge_source = _choose_ridge_source(image_bgr, config.ridge_source_mode)
    ridge_background_estimate, ridge_background_suppressed = _suppress_background(
        ridge_source,
        blur_kernel=config.ridge_blur_kernel,
    )
    ridge_local_residual = _compute_local_residual(
        ridge_source,
        window=config.ridge_local_window,
    )

    ridge_contrast = (
        float(config.ridge_base_gain) * ridge_source.astype(np.float32)
        + float(config.ridge_background_gain) * ridge_background_suppressed.astype(np.float32)
        + float(config.ridge_local_gain) * ridge_local_residual.astype(np.float32)
    )
    ridge_contrast_enhanced = _clip_u8(ridge_contrast)

    if config.ridge_use_top_hat:
        ridge_contrast_enhanced = _apply_top_hat(
            ridge_contrast_enhanced,
            kernel_size=config.ridge_top_hat_kernel,
            base_gain=1.0,
            top_hat_gain=config.ridge_top_hat_gain,
        )
    if config.ridge_use_clahe:
        ridge_contrast_enhanced = _apply_clahe(
            ridge_contrast_enhanced,
            clip_limit=config.ridge_clahe_clip_limit,
            tile_grid_size=config.ridge_clahe_tile_grid_size,
        )

    normalized_ridge_branch = _normalize_percentile(
        ridge_contrast_enhanced,
        low_percentile=config.ridge_normalize_percentile_low,
        high_percentile=config.ridge_normalize_percentile_high,
    )
    return (
        ridge_source,
        ridge_background_estimate,
        ridge_background_suppressed,
        ridge_local_residual,
        ridge_contrast_enhanced,
        normalized_ridge_branch,
    )


def _fuse_branches(
    normalized_red_branch: np.ndarray,
    normalized_ridge_branch: np.ndarray,
    config: RedFilterPreprocessV3Config,
) -> np.ndarray:
    red_f = normalized_red_branch.astype(np.float32) * float(config.fusion_red_weight)
    ridge_f = normalized_ridge_branch.astype(np.float32) * float(config.fusion_ridge_weight)

    if config.fusion_mode == "weighted_max":
        fused = np.maximum(red_f, ridge_f)
    elif config.fusion_mode == "blend":
        fused = 0.5 * (red_f + ridge_f)
    else:
        raise ValueError(f"Unsupported fusion_mode: {config.fusion_mode}")

    fused_u8 = _clip_u8(fused)
    return _normalize_percentile(
        fused_u8,
        low_percentile=config.fused_normalize_percentile_low,
        high_percentile=config.fused_normalize_percentile_high,
    )


def preprocess_red_filter_v3(
    image_bgr: np.ndarray,
    config: RedFilterPreprocessV3Config = RedFilterPreprocessV3Config(),
    camera_matrix: Optional[np.ndarray] = None,
    dist_coeffs: Optional[np.ndarray] = None,
) -> RedFilterPreprocessV3Result:
    """执行双分支预处理并返回中间结果。"""
    undistorted_image, updated_camera_matrix = _undistort_if_needed(
        image_bgr,
        camera_matrix,
        dist_coeffs,
    )

    (
        red_difference,
        background_estimate,
        background_suppressed,
        contrast_enhanced,
        normalized_red_branch,
    ) = _run_red_branch(undistorted_image, config)

    (
        ridge_source,
        ridge_background_estimate,
        ridge_background_suppressed,
        ridge_local_residual,
        ridge_contrast_enhanced,
        normalized_ridge_branch,
    ) = _run_ridge_branch(undistorted_image, config)

    normalized_gray_raw = _fuse_branches(
        normalized_red_branch=normalized_red_branch,
        normalized_ridge_branch=normalized_ridge_branch,
        config=config,
    )

    candidate_seed_mask = _build_candidate_seed_mask(
        normalized_red_branch=normalized_red_branch,
        normalized_ridge_branch=normalized_ridge_branch,
        threshold=config.preserve_seed_threshold,
    )

    normalized_gray = normalized_gray_raw.copy()
    if config.use_noise_filter:
        normalized_gray = _suppress_outlier_blobs_with_seed_preserve(
            image_gray=normalized_gray_raw,
            seed_mask=candidate_seed_mask,
            threshold=config.noise_threshold,
            min_area=config.noise_min_area,
            min_width=config.noise_min_width,
            min_aspect=config.noise_min_aspect,
            open_kernel=config.noise_open_kernel,
            median_kernel=config.noise_median_kernel,
            preserve_seed_min_area=config.preserve_seed_min_area,
            preserve_seed_min_long_edge=config.preserve_seed_min_long_edge,
        )

    return RedFilterPreprocessV3Result(
        undistorted_image=undistorted_image,
        updated_camera_matrix=updated_camera_matrix,
        red_difference=red_difference,
        background_estimate=background_estimate,
        background_suppressed=background_suppressed,
        contrast_enhanced=contrast_enhanced,
        normalized_red_branch=normalized_red_branch,
        ridge_source=ridge_source,
        ridge_background_estimate=ridge_background_estimate,
        ridge_background_suppressed=ridge_background_suppressed,
        ridge_local_residual=ridge_local_residual,
        ridge_contrast_enhanced=ridge_contrast_enhanced,
        normalized_ridge_branch=normalized_ridge_branch,
        normalized_gray_raw=normalized_gray_raw,
        normalized_gray=normalized_gray,
        candidate_seed_mask=candidate_seed_mask,
    )


def save_preprocess_red_filter_v3_debug_images(
    output_dir: str | Path,
    stem: str,
    result: RedFilterPreprocessV3Result,
) -> None:
    """保存 v3 的调试图像，命名与现有工程兼容。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def _save(name: str, image: np.ndarray) -> None:
        cv2.imwrite(str(output_dir / f"{stem}_{name}.png"), image)

    _save("red_difference", result.red_difference)
    _save("background_suppressed", result.background_suppressed)
    _save("contrast_enhanced", result.contrast_enhanced)
    _save("normalized_raw", result.normalized_gray_raw)
    _save("normalized_filtered", result.normalized_gray)

    _save("normalized_red_branch", result.normalized_red_branch)
    _save("ridge_source", result.ridge_source)
    _save("ridge_background_suppressed", result.ridge_background_suppressed)
    _save("ridge_local_residual", result.ridge_local_residual)
    _save("ridge_contrast_enhanced", result.ridge_contrast_enhanced)
    _save("normalized_ridge_branch", result.normalized_ridge_branch)
    _save("candidate_seed_mask", result.candidate_seed_mask)
