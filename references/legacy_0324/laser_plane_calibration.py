from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from src.red_filter_preprocess_v3_reusable import (
    RedFilterPreprocessV3Config,
    preprocess_red_filter_v3,
)
from laser_stripe_subpixel_module_v2 import (
    LaserStripeSubpixelConfig,
    extract_from_preprocess_result,
)


DEFAULT_IMAGE_DIR = Path(r"C:\Users\xmc\PycharmProjects\PythonProject\data\picture5")
DEFAULT_OUTPUT_DIR = Path(r"G:\dev\projects\0324line_3d\outputs\laser-plane-calibration")
DEFAULT_CAMERA_MATRIX = np.array(
    [[1135.517944, 0.0, 944.524521], [0.0, 1135.493918, 624.981139], [0.0, 0.0, 1.0]],
    dtype=np.float64,
)
DEFAULT_DIST_COEFFS = np.array([0.037361, -0.043033, 0.0, 0.0, 0.0], dtype=np.float64)
DEFAULT_CHESSBOARD_SIZE = (10, 6)
DEFAULT_SQUARE_SIZE_M = 0.02


@dataclass(frozen=True)
class FrameResult:
    position_id: str
    board_success: bool
    laser_success: bool
    preprocess_mode: str
    num_points: int
    camera_points: np.ndarray
    overlay_path: Path | None
    candidate_path: Path | None
    signal_path: Path | None
    threshold: float | None
    residual_mean_px: float | None
    coverage_ratio: float | None
    message: str


@dataclass(frozen=True)
class ExtractionAttempt:
    mode: str
    success: bool
    points_xy: np.ndarray
    overlay_bgr: np.ndarray | None
    candidate_mask: np.ndarray
    signal_image: np.ndarray
    threshold_hint: float
    residual_mean_px: float
    coverage_ratio: float
    message: str


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_output_dir(path: Path, allow_overwrite: bool) -> Path:
    if allow_overwrite:
        return ensure_output_dir(path)
    if not path.exists():
        return ensure_output_dir(path)
    if not any(path.iterdir()):
        return path
    version_index = 1
    while True:
        candidate = path.parent / f"{path.name}-v{version_index:03d}"
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        version_index += 1


def compute_red_difference(image: np.ndarray) -> np.ndarray:
    blue, green, red = cv2.split(image)
    diff = red.astype(np.float32) - 0.5 * green.astype(np.float32) - 0.5 * blue.astype(np.float32)
    return np.clip(diff, 0, 255).astype(np.uint8)


def compute_laser_signal(board_image: np.ndarray, laser_image: np.ndarray) -> np.ndarray:
    board_red = compute_red_difference(board_image).astype(np.float32)
    laser_red = compute_red_difference(laser_image).astype(np.float32)
    # Subtracting the board-only frame suppresses checker texture and ambient reflections.
    diff_signal = np.clip(laser_red - board_red, 0.0, 255.0).astype(np.uint8)
    return cv2.GaussianBlur(diff_signal, (5, 5), 0)


def compute_gray_delta(board_image: np.ndarray, laser_image: np.ndarray) -> np.ndarray:
    board_gray = cv2.cvtColor(board_image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    laser_gray = cv2.cvtColor(laser_image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    delta = np.clip(laser_gray - board_gray, 0.0, 255.0).astype(np.uint8)
    return cv2.GaussianBlur(delta, (5, 5), 0)


def build_object_points(chessboard_size: tuple[int, int], square_size_m: float) -> np.ndarray:
    objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0 : chessboard_size[0], 0 : chessboard_size[1]].T.reshape(-1, 2) * square_size_m
    return objp


def detect_board_pose(
    board_image: np.ndarray,
    chessboard_size: tuple[int, int],
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    square_size_m: float,
) -> tuple[bool, np.ndarray | None, np.ndarray | None, np.ndarray | None]:
    gray = cv2.cvtColor(board_image, cv2.COLOR_BGR2GRAY)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE | cv2.CALIB_CB_FILTER_QUADS
    found, corners = cv2.findChessboardCorners(gray, chessboard_size, flags=flags)
    if not found:
        return False, None, None, None

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    objp = build_object_points(chessboard_size, square_size_m)
    solved, rvec, tvec = cv2.solvePnP(objp, corners, camera_matrix, dist_coeffs)
    if not solved:
        return False, None, None, None

    return True, corners.reshape(-1, 2), rvec, tvec


def build_board_mask(image_shape: tuple[int, int], corners: np.ndarray, dilation_px: int = 9) -> np.ndarray:
    hull = cv2.convexHull(corners.astype(np.float32)).astype(np.int32)
    mask = np.zeros(image_shape, dtype=np.uint8)
    cv2.fillConvexPoly(mask, hull, 255)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation_px, dilation_px))
    return cv2.dilate(mask, kernel, iterations=1)


def fit_line_and_filter(points: np.ndarray, max_iterations: int = 2) -> tuple[np.ndarray, float]:
    if len(points) < 2:
        return points, 0.0

    filtered = points.copy()
    last_mean = 0.0
    for _ in range(max_iterations):
        coeff = np.polyfit(filtered[:, 0], filtered[:, 1], 1)
        predicted = coeff[0] * filtered[:, 0] + coeff[1]
        residuals = np.abs(filtered[:, 1] - predicted)
        median = float(np.median(residuals))
        mad = float(np.median(np.abs(residuals - median))) + 1e-6
        threshold = max(2.5, median + 3.0 * 1.4826 * mad)
        keep = residuals <= threshold
        last_mean = float(np.mean(residuals))
        if keep.all():
            break
        filtered = filtered[keep]
        if len(filtered) < 2:
            break

    return filtered, last_mean


def distance_to_line(rows: np.ndarray, cols: np.ndarray, line_coeffs: tuple[float, float]) -> np.ndarray:
    slope, intercept = line_coeffs
    return np.abs(rows - (slope * cols + intercept)) / np.sqrt(slope**2 + 1.0)


def fit_line_ransac(
    xs: np.ndarray,
    ys: np.ndarray,
    iterations: int = 400,
    distance_threshold: float = 4.0,
    random_seed: int = 0,
) -> tuple[tuple[float, float] | None, np.ndarray | None]:
    if len(xs) < 2:
        return None, None

    rng = np.random.default_rng(random_seed)
    points = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    num_points = len(points)
    best_line: tuple[float, float] | None = None
    best_inliers: np.ndarray | None = None
    best_score = -1.0

    for _ in range(iterations):
        first_idx, second_idx = rng.choice(num_points, size=2, replace=False)
        first_point = points[first_idx]
        second_point = points[second_idx]
        dx = second_point[0] - first_point[0]
        dy = second_point[1] - first_point[1]
        if abs(dx) < 10.0:
            continue

        slope = dy / dx
        if abs(slope) > 0.5:
            continue

        intercept = first_point[1] - slope * first_point[0]
        distances = distance_to_line(points[:, 1], points[:, 0], (slope, intercept))
        inliers = distances <= distance_threshold
        inlier_count = int(np.count_nonzero(inliers))
        if inlier_count < 30:
            continue

        span = float(points[inliers, 0].max() - points[inliers, 0].min())
        score = inlier_count + 0.01 * span
        if score > best_score:
            best_score = score
            best_inliers = inliers
            best_line = (float(slope), float(intercept))

    if best_line is None or best_inliers is None:
        return None, None

    refined_coeffs = np.polyfit(points[best_inliers, 0], points[best_inliers, 1], 1)
    refined_line = (float(refined_coeffs[0]), float(refined_coeffs[1]))
    return refined_line, best_inliers


def collect_image_files(image_dir: Path, prefix: str) -> list[Path]:
    extensions = ("bmp", "png", "jpg", "jpeg", "tif", "tiff")
    files: list[Path] = []
    for extension in extensions:
        files.extend(image_dir.glob(f"{prefix}_*.{extension}"))
        files.extend(image_dir.glob(f"{prefix}_*.{extension.upper()}"))
    unique_files = {path.resolve(): path for path in files}
    return sorted(unique_files.values())


def _normalize_u8(image: np.ndarray) -> np.ndarray:
    low, high = np.percentile(image, [0.5, 99.5])
    if high <= low + 1e-6:
        return np.zeros_like(image, dtype=np.uint8)
    out = (image.astype(np.float32) - low) * (255.0 / (high - low))
    return np.clip(out, 0, 255).astype(np.uint8)


def preprocess_legacy_like_3test1112(laser_image: np.ndarray, board_mask: np.ndarray) -> SimpleNamespace:
    # Legacy-compatible preprocessing branch used only when v3 quality is weak.
    gray = cv2.cvtColor(laser_image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    normalized = _normalize_u8(enhanced)
    normalized[board_mask == 0] = 0
    filtered = cv2.medianBlur(normalized, 3)
    filtered[board_mask == 0] = 0
    return SimpleNamespace(
        normalized_gray_raw=normalized,
        normalized_gray=filtered,
    )


def _compute_line_residual(points_xy: np.ndarray) -> float:
    if len(points_xy) < 2:
        return 999.0
    coeff = np.polyfit(points_xy[:, 0], points_xy[:, 1], 1)
    pred = coeff[0] * points_xy[:, 0] + coeff[1]
    return float(np.mean(np.abs(points_xy[:, 1] - pred)))


def _compute_coverage(points_xy: np.ndarray, board_mask: np.ndarray) -> float:
    if len(points_xy) < 2:
        return 0.0
    cols = np.where(board_mask > 0)[1]
    if len(cols) == 0:
        return 0.0
    span = float(points_xy[:, 0].max() - points_xy[:, 0].min())
    board_span = float(cols.max() - cols.min())
    if board_span <= 1e-6:
        return 0.0
    return span / board_span


def _quality_ok(points_xy: np.ndarray, board_mask: np.ndarray) -> tuple[bool, float, float]:
    residual = _compute_line_residual(points_xy)
    coverage = _compute_coverage(points_xy, board_mask)
    # Calibration images often contain only the board-intersection stripe segment,
    # so coverage should be permissive while still rejecting noisy fragments.
    ok = len(points_xy) >= 55 and coverage >= 0.08 and residual <= 4.8
    return ok, residual, coverage


def _run_subpixel_attempt(
    board_image: np.ndarray,
    laser_image: np.ndarray,
    board_mask: np.ndarray,
    mode: str,
) -> ExtractionAttempt:
    if mode == "v3":
        preprocess_laser = preprocess_red_filter_v3(
            image_bgr=laser_image,
            config=RedFilterPreprocessV3Config(),
            camera_matrix=None,
            dist_coeffs=None,
        )
        preprocess_board = preprocess_red_filter_v3(
            image_bgr=board_image,
            config=RedFilterPreprocessV3Config(),
            camera_matrix=None,
            dist_coeffs=None,
        )
        signal_raw = cv2.subtract(preprocess_laser.normalized_gray_raw, preprocess_board.normalized_gray_raw)
        signal_filtered = cv2.subtract(preprocess_laser.normalized_gray, preprocess_board.normalized_gray)
        signal_raw[board_mask == 0] = 0
        signal_filtered[board_mask == 0] = 0
        preprocess_input = SimpleNamespace(normalized_gray_raw=signal_raw, normalized_gray=signal_filtered)
        signal_image = signal_raw
        subpixel_cfg = LaserStripeSubpixelConfig(
            candidate_threshold=12,
            keep_only_best_component=False,
            extract_components_individually=True,
            min_component_area=80,
            min_component_span=120,
            min_points_in_path=30,
            smooth_window=7,
            debug=True,
        )
    elif mode == "legacy":
        preprocess_laser = preprocess_legacy_like_3test1112(laser_image, board_mask)
        preprocess_board = preprocess_legacy_like_3test1112(board_image, board_mask)
        signal_raw = cv2.subtract(preprocess_laser.normalized_gray_raw, preprocess_board.normalized_gray_raw)
        signal_filtered = cv2.subtract(preprocess_laser.normalized_gray, preprocess_board.normalized_gray)
        signal_raw[board_mask == 0] = 0
        signal_filtered[board_mask == 0] = 0
        preprocess_input = SimpleNamespace(normalized_gray_raw=signal_raw, normalized_gray=signal_filtered)
        signal_image = signal_raw
        subpixel_cfg = LaserStripeSubpixelConfig(
            candidate_threshold=10,
            keep_only_best_component=False,
            extract_components_individually=True,
            min_component_area=60,
            min_component_span=90,
            min_points_in_path=25,
            smooth_window=7,
            debug=True,
        )
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    subpixel_result = extract_from_preprocess_result(
        preprocess_result=preprocess_input,
        image_bgr=laser_image,
        config=subpixel_cfg,
    )
    points_xy = subpixel_result.points_xy.astype(np.float64) if subpixel_result.points_xy is not None else np.zeros((0, 2), dtype=np.float64)
    ok, residual, coverage = _quality_ok(points_xy, board_mask)
    valid_signal = signal_image[board_mask > 0]
    threshold_hint = float(np.percentile(valid_signal, 90)) if valid_signal.size > 0 else 0.0

    return ExtractionAttempt(
        mode=mode,
        success=bool(subpixel_result.success and ok),
        points_xy=points_xy,
        overlay_bgr=subpixel_result.overlay_bgr,
        candidate_mask=subpixel_result.candidate_mask.astype(np.uint8),
        signal_image=signal_image.astype(np.uint8),
        threshold_hint=threshold_hint,
        residual_mean_px=residual,
        coverage_ratio=coverage,
        message=subpixel_result.message,
    )


def _select_best_attempt(attempts: list[ExtractionAttempt]) -> ExtractionAttempt:
    def score(item: ExtractionAttempt) -> float:
        value = float(len(item.points_xy))
        value += 160.0 * item.coverage_ratio
        value -= 25.0 * item.residual_mean_px
        if item.success:
            value += 500.0
        return value

    ranked = sorted(attempts, key=score, reverse=True)
    return ranked[0]


def image_points_to_camera(
    image_points: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
) -> np.ndarray:
    if len(image_points) == 0:
        return np.empty((0, 3), dtype=np.float64)

    rotation, _ = cv2.Rodrigues(rvec)
    board_normal = rotation[:, 2]
    board_origin = tvec.reshape(3)
    undistorted = cv2.undistortPoints(
        image_points.reshape(-1, 1, 2).astype(np.float64),
        camera_matrix,
        dist_coeffs,
    ).reshape(-1, 2)

    camera_points: list[np.ndarray] = []
    for x_norm, y_norm in undistorted:
        ray = np.array([x_norm, y_norm, 1.0], dtype=np.float64)
        denominator = float(board_normal @ ray)
        if abs(denominator) < 1e-9:
            continue
        scale = float(board_normal @ board_origin) / denominator
        if scale <= 0:
            continue
        camera_points.append(scale * ray)

    if not camera_points:
        return np.empty((0, 3), dtype=np.float64)
    return np.asarray(camera_points, dtype=np.float64)


def fit_plane(points: np.ndarray, max_iterations: int = 3) -> tuple[np.ndarray, np.ndarray]:
    if len(points) < 3:
        raise ValueError("Need at least 3 points to fit a plane.")

    filtered = points.copy()
    for _ in range(max_iterations):
        centroid = np.mean(filtered, axis=0)
        _, _, vh = np.linalg.svd(filtered - centroid, full_matrices=False)
        normal = vh[-1]
        if normal[1] < 0:
            normal = -normal
        d_value = -float(normal @ centroid)
        residuals = np.abs(filtered @ normal + d_value)
        median = float(np.median(residuals))
        mad = float(np.median(np.abs(residuals - median))) + 1e-9
        threshold = max(0.0015, median + 3.0 * 1.4826 * mad)
        keep = residuals <= threshold
        if keep.all():
            return np.array([normal[0], normal[1], normal[2], d_value], dtype=np.float64), residuals
        filtered = filtered[keep]
        if len(filtered) < 3:
            break

    centroid = np.mean(filtered, axis=0)
    _, _, vh = np.linalg.svd(filtered - centroid, full_matrices=False)
    normal = vh[-1]
    if normal[1] < 0:
        normal = -normal
    d_value = -float(normal @ centroid)
    residuals = np.abs(filtered @ normal + d_value)
    return np.array([normal[0], normal[1], normal[2], d_value], dtype=np.float64), residuals


def save_overlay(
    laser_image: np.ndarray,
    board_corners: np.ndarray,
    attempt: ExtractionAttempt,
    output_path: Path,
) -> None:
    if attempt.overlay_bgr is not None:
        overlay = attempt.overlay_bgr.copy()
    else:
        overlay = laser_image.copy()
    cv2.polylines(overlay, [cv2.convexHull(board_corners.astype(np.float32)).astype(np.int32)], True, (255, 255, 0), 2)
    if len(attempt.points_xy) >= 2:
        pts = np.round(attempt.points_xy).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(overlay, [pts], False, (0, 255, 0), 1, lineType=cv2.LINE_AA)
    cv2.imwrite(str(output_path), overlay)


def process_frame(
    board_path: Path,
    laser_path: Path,
    output_dir: Path,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    chessboard_size: tuple[int, int],
    square_size_m: float,
) -> FrameResult:
    position_id = board_path.stem.split("_")[-1]
    board_image = cv2.imread(str(board_path))
    laser_image = cv2.imread(str(laser_path))
    if board_image is None or laser_image is None:
        return FrameResult(position_id, False, False, "none", 0, np.empty((0, 3)), None, None, None, None, None, "image read failed")

    board_success, board_corners, rvec, tvec = detect_board_pose(
        board_image,
        chessboard_size,
        camera_matrix,
        dist_coeffs,
        square_size_m,
    )
    if not board_success or board_corners is None or rvec is None or tvec is None:
        return FrameResult(position_id, False, False, "none", 0, np.empty((0, 3)), None, None, None, None, None, "board detection failed")

    board_mask = build_board_mask(board_image.shape[:2], board_corners)
    primary = _run_subpixel_attempt(
        board_image=board_image,
        laser_image=laser_image,
        board_mask=board_mask,
        mode="v3",
    )
    fallback = _run_subpixel_attempt(
        board_image=board_image,
        laser_image=laser_image,
        board_mask=board_mask,
        mode="legacy",
    )
    best_attempt = _select_best_attempt([primary, fallback])

    # Fit uses subpixel stripe center points (not stripe-band pixels).
    camera_points = image_points_to_camera(best_attempt.points_xy, camera_matrix, dist_coeffs, rvec, tvec)
    laser_success = bool(best_attempt.success and len(camera_points) >= 55)

    overlay_path = output_dir / f"laser_{position_id}_centerline.png"
    candidate_path = output_dir / f"laser_{position_id}_candidate.png"
    signal_path = output_dir / f"laser_{position_id}_signal.png"
    save_overlay(laser_image, board_corners, best_attempt, overlay_path)
    cv2.imwrite(str(signal_path), best_attempt.signal_image)
    cv2.imwrite(str(candidate_path), best_attempt.candidate_mask)

    return FrameResult(
        position_id=position_id,
        board_success=True,
        laser_success=laser_success,
        preprocess_mode=best_attempt.mode,
        num_points=len(camera_points),
        camera_points=camera_points,
        overlay_path=overlay_path,
        candidate_path=candidate_path,
        signal_path=signal_path,
        threshold=best_attempt.threshold_hint,
        residual_mean_px=best_attempt.residual_mean_px,
        coverage_ratio=best_attempt.coverage_ratio,
        message=best_attempt.message,
    )


def save_plane_visualization(points: np.ndarray, plane_coeffs_m: np.ndarray, output_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=1, c="deepskyblue", alpha=0.35)

        a, b, c, d = plane_coeffs_m.tolist()
        x_min, x_max = float(np.min(points[:, 0])), float(np.max(points[:, 0]))
        y_min, y_max = float(np.min(points[:, 1])), float(np.max(points[:, 1]))
        xx, yy = np.meshgrid(np.linspace(x_min, x_max, 40), np.linspace(y_min, y_max, 40))
        if abs(c) > 1e-9:
            zz = (-a * xx - b * yy - d) / c
            ax.plot_surface(xx, yy, zz, color="tomato", alpha=0.35, linewidth=0)

        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.set_zlabel("Z (m)")
        ax.set_title("Laser Plane Calibration")
        ax.view_init(elev=30, azim=45)
        fig.tight_layout()
        fig.savefig(output_path, dpi=180)
        plt.close(fig)
    except Exception:
        fallback = np.zeros((540, 960, 3), dtype=np.uint8)
        cv2.putText(
            fallback,
            "laser_plane_visualization unavailable (matplotlib missing)",
            (30, 280),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 200, 255),
            2,
            lineType=cv2.LINE_AA,
        )
        cv2.imwrite(str(output_path), fallback)


def write_analysis_report_zh(
    output_path: Path,
    output_dir: Path,
    frame_results: list[FrameResult],
    plane_coeffs_mm: np.ndarray,
    residuals_m: np.ndarray,
    total_points: int,
) -> None:
    mode_count: dict[str, int] = {}
    for item in frame_results:
        mode_count[item.preprocess_mode] = mode_count.get(item.preprocess_mode, 0) + 1

    lines = [
        "激光面标定中文分析报告",
        "====================",
        f"输出目录: {output_dir}",
        f"总帧数: {len(frame_results)}",
        f"有效帧数: {sum(1 for item in frame_results if item.laser_success)}",
        f"拟合点总数: {total_points}",
        f"平均残差: {np.mean(residuals_m) * 1000.0:.4f} mm",
        f"最大残差: {np.max(residuals_m) * 1000.0:.4f} mm",
        "",
        "算法说明:",
        "1) 预处理主流程使用 red_filter_preprocess_v3_reusable。",
        "2) 激光条纹中心使用 laser_stripe_subpixel_module_v2 提取亚像素中心线。",
        "3) 三维反投影使用 undistortPoints，避免畸变造成几何偏差。",
        "4) 若主流程质量偏低，自动回退到 3test1112 风格预处理 + 同一亚像素模块。",
        "5) 平面拟合仅使用亚像素中心线点，不再使用激光带像素点。",
        "",
        f"预处理模式统计: {mode_count}",
        f"平面系数(mm): a={plane_coeffs_mm[0]:.8f}, b={plane_coeffs_mm[1]:.8f}, c={plane_coeffs_mm[2]:.8f}, d={plane_coeffs_mm[3]:.8f}",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class LaserPlaneCalibrationConfig:
    """
    复用配置对象：可在其他脚本中直接 import 后调用，无需改 CLI。
    """

    image_dir: Path = DEFAULT_IMAGE_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    square_size_m: float = DEFAULT_SQUARE_SIZE_M
    allow_overwrite: bool = False
    camera_matrix: np.ndarray = field(default_factory=lambda: DEFAULT_CAMERA_MATRIX.copy())
    dist_coeffs: np.ndarray = field(default_factory=lambda: DEFAULT_DIST_COEFFS.copy())
    chessboard_size: tuple[int, int] = DEFAULT_CHESSBOARD_SIZE


@dataclass(frozen=True)
class LaserPlaneCalibrationSummary:
    output_dir: Path
    report_path: Path
    coeff_path: Path
    analysis_path: Path
    plane_visualization_path: Path
    used_frames: int
    total_frames: int
    total_points: int
    plane_coeffs_m: np.ndarray
    plane_coeffs_mm: np.ndarray
    residuals_m: np.ndarray
    frame_results: tuple[FrameResult, ...]


def run_laser_plane_calibration(config: LaserPlaneCalibrationConfig) -> LaserPlaneCalibrationSummary:
    """
    激光面标定复用入口。

    步骤:
    1) 读取 board / laser 图像对；
    2) 逐帧执行：棋盘位姿 -> 预处理+亚像素中心线 -> undistortPoints 反投影；
    3) 用有效中心线三维点拟合激光平面并输出报告。
    """

    output_dir = resolve_output_dir(config.output_dir, allow_overwrite=config.allow_overwrite)
    board_files = collect_image_files(config.image_dir, "board")
    laser_files = collect_image_files(config.image_dir, "laser")
    if not board_files or not laser_files:
        raise FileNotFoundError(f"No calibration images found in {config.image_dir}")

    laser_lookup = {path.stem.split("_")[-1]: path for path in laser_files}
    frame_results: list[FrameResult] = []
    all_points: list[np.ndarray] = []

    for board_path in board_files:
        position_id = board_path.stem.split("_")[-1]
        laser_path = laser_lookup.get(position_id)
        if laser_path is None:
            continue
        result = process_frame(
            board_path=board_path,
            laser_path=laser_path,
            output_dir=output_dir,
            camera_matrix=config.camera_matrix,
            dist_coeffs=config.dist_coeffs,
            chessboard_size=config.chessboard_size,
            square_size_m=config.square_size_m,
        )
        frame_results.append(result)
        if result.laser_success and len(result.camera_points) > 0:
            all_points.append(result.camera_points)

    if not all_points:
        raise RuntimeError("No valid laser centerline points were reconstructed.")

    stacked_points = np.vstack(all_points)
    plane_coeffs_m, residuals_m = fit_plane(stacked_points)
    plane_coeffs_mm = plane_coeffs_m.copy()
    plane_coeffs_mm[3] *= 1000.0
    plane_visualization_path = output_dir / "laser_plane_visualization.png"
    save_plane_visualization(stacked_points, plane_coeffs_m, plane_visualization_path)

    plane_report = [
        "===== Laser Plane Recalibration Report =====",
        f"image_dir={config.image_dir}",
        f"used_frames={sum(1 for item in frame_results if item.laser_success)}",
        f"total_frames={len(frame_results)}",
        f"total_points={len(stacked_points)}",
        "",
        "plane_coeffs_m=ax+by+cz+d=0",
        f"a={plane_coeffs_m[0]:.8f}",
        f"b={plane_coeffs_m[1]:.8f}",
        f"c={plane_coeffs_m[2]:.8f}",
        f"d={plane_coeffs_m[3]:.8f}",
        "",
        "plane_coeffs_mm_for_current_repo=ax+by+cz+d=0",
        f"a={plane_coeffs_mm[0]:.8f}",
        f"b={plane_coeffs_mm[1]:.8f}",
        f"c={plane_coeffs_mm[2]:.8f}",
        f"d={plane_coeffs_mm[3]:.8f}",
        "",
        f"mean_residual_mm={np.mean(residuals_m) * 1000.0:.4f}",
        f"max_residual_mm={np.max(residuals_m) * 1000.0:.4f}",
        "",
        "per_frame:",
    ]

    for item in frame_results:
        plane_report.append(
            " | ".join(
                [
                    f"id={item.position_id}",
                    f"board={'ok' if item.board_success else 'fail'}",
                    f"laser={'ok' if item.laser_success else 'fail'}",
                    f"mode={item.preprocess_mode}",
                    f"points={item.num_points}",
                    f"threshold={item.threshold:.2f}" if item.threshold is not None else "threshold=na",
                    f"line_residual_px={item.residual_mean_px:.3f}" if item.residual_mean_px is not None else "line_residual_px=na",
                    f"coverage={item.coverage_ratio:.3f}" if item.coverage_ratio is not None else "coverage=na",
                    f"msg={item.message}",
                ]
            )
        )

    report_path = output_dir / "calibration_report.txt"
    coeff_path = output_dir / "plane_coeffs_mm.txt"
    analysis_path = output_dir / "analysis_report_zh.txt"
    report_path.write_text("\n".join(plane_report) + "\n", encoding="utf-8")
    coeff_path.write_text(
        "ax + by + cz + d = 0\n"
        f"a = {plane_coeffs_mm[0]:.8f}\n"
        f"b = {plane_coeffs_mm[1]:.8f}\n"
        f"c = {plane_coeffs_mm[2]:.8f}\n"
        f"d = {plane_coeffs_mm[3]:.8f}\n",
        encoding="utf-8",
    )
    write_analysis_report_zh(
        output_path=analysis_path,
        output_dir=output_dir,
        frame_results=frame_results,
        plane_coeffs_mm=plane_coeffs_mm,
        residuals_m=residuals_m,
        total_points=len(stacked_points),
    )

    return LaserPlaneCalibrationSummary(
        output_dir=output_dir,
        report_path=report_path,
        coeff_path=coeff_path,
        analysis_path=analysis_path,
        plane_visualization_path=plane_visualization_path,
        used_frames=sum(1 for item in frame_results if item.laser_success),
        total_frames=len(frame_results),
        total_points=len(stacked_points),
        plane_coeffs_m=plane_coeffs_m,
        plane_coeffs_mm=plane_coeffs_mm,
        residuals_m=residuals_m,
        frame_results=tuple(frame_results),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recalibrate a laser plane from chessboard + laser image pairs.")
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--square-size-m", type=float, default=DEFAULT_SQUARE_SIZE_M)
    parser.add_argument("--allow-overwrite", action="store_true", help="Allow writing into a non-empty output folder.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = LaserPlaneCalibrationConfig(
        image_dir=args.image_dir,
        output_dir=args.output_dir,
        square_size_m=args.square_size_m,
        allow_overwrite=args.allow_overwrite,
    )
    try:
        summary = run_laser_plane_calibration(config)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"report={summary.report_path}")
    print(f"coeffs={summary.coeff_path}")
    print(f"analysis={summary.analysis_path}")
    print(f"plane_vis={summary.plane_visualization_path}")
    print(f"output_dir={summary.output_dir}")
    print(f"used_frames={summary.used_frames}")
    print(f"total_points={summary.total_points}")
    print(f"plane_mm={summary.plane_coeffs_mm.tolist()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
