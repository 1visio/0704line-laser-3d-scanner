"""Height measurement from reconstructed laser-line points.

Inputs are 3D points in the ground coordinate system: ``(Xg, Yg, Zg)`` in mm.
When baseline points are available, the module fits a local ground profile
``Zg = a*s + b`` along the measured obstacle direction and subtracts that
local ground height from each obstacle point. Without baseline points it falls
back to the fixed ``Zg = 0`` reference.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


class MeasurementError(RuntimeError):
    """Raised when input points are insufficient or geometrically degenerate."""


@dataclass(frozen=True, slots=True)
class MeasurementParams:
    """Robust measurement parameters."""

    outlier_sigma_multiplier: float = 2.0
    outlier_max_iterations: int = 5
    min_baseline_points: int = 30
    min_height_points: int = 30

    def __post_init__(self) -> None:
        if self.outlier_sigma_multiplier <= 0.0:
            raise ValueError("outlier_sigma_multiplier must be positive")
        if self.outlier_max_iterations < 1:
            raise ValueError("outlier_max_iterations must be >= 1")
        if self.min_baseline_points < 2:
            raise ValueError("min_baseline_points must be >= 2")
        if self.min_height_points < 2:
            raise ValueError("min_height_points must be >= 2")


@dataclass(frozen=True, slots=True)
class LineFitXY:
    """Orthogonal least-squares line fit in the ground XY plane."""

    centre_xy: np.ndarray
    direction_xy: np.ndarray
    endpoints_xy: np.ndarray
    rmse_mm: float
    inlier_mask: np.ndarray


@dataclass(frozen=True, slots=True)
class GroundProfileFit:
    """Local ground height model along the measured obstacle line."""

    origin_xy: np.ndarray
    direction_xy: np.ndarray
    slope_z_per_mm: float
    intercept_z_mm: float
    rmse_mm: float
    inlier_mask: np.ndarray

    def project_s(self, points_xy: np.ndarray) -> np.ndarray:
        points = np.asarray(points_xy, dtype=np.float64)
        return (points - self.origin_xy) @ self.direction_xy

    def predict_z(self, points_xy: np.ndarray) -> np.ndarray:
        s = self.project_s(points_xy)
        return self.slope_z_per_mm * s + self.intercept_z_mm


@dataclass(frozen=True, slots=True)
class HeightLineMeasurement:
    """Measured obstacle height-line result."""

    ground_baseline_zg_mm: float
    ground_noise_sigma_mm: float | None
    ground_reference_mode: str
    baseline_fit: LineFitXY | None
    ground_profile_fit: GroundProfileFit | None
    height_fit: LineFitXY
    height_mean_mm: float
    height_median_mm: float
    height_std_mm: float
    length_mm: float
    endpoints_ground: np.ndarray
    angle_with_baseline_deg: float | None
    baseline_point_count: int
    baseline_inlier_count: int
    height_point_count: int
    height_inlier_count: int


def _validate_points(points: np.ndarray, name: str, minimum: int) -> np.ndarray:
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 3:
        raise MeasurementError(f"{name} must have shape (N, 3)")
    if not np.isfinite(array).all():
        raise MeasurementError(f"{name} contains NaN or infinite values")
    if len(array) < minimum:
        raise MeasurementError(
            f"{name} has too few points: {len(array)} < {minimum}"
        )
    return array


def _robust_sigma(residuals: np.ndarray) -> float:
    """MAD-based robust standard deviation, with std fallback."""
    mad = float(np.median(np.abs(residuals - np.median(residuals))))
    sigma = 1.4826 * mad
    if sigma <= np.finfo(np.float64).eps:
        sigma = float(np.std(residuals))
    return sigma


def _fit_line_xy(
    points_xy: np.ndarray, params: MeasurementParams, name: str
) -> LineFitXY:
    """Fit a robust 2D line in XY and reject orthogonal outliers."""
    mask = np.ones(len(points_xy), dtype=bool)
    centre = np.zeros(2)
    direction = np.array([1.0, 0.0])
    for _ in range(params.outlier_max_iterations):
        selected = points_xy[mask]
        if len(selected) < 2:
            raise MeasurementError(f"{name} has too few inliers")
        centre = np.mean(selected, axis=0)
        centred = selected - centre
        _, singular_values, right_vectors = np.linalg.svd(
            centred, full_matrices=False
        )
        if singular_values[0] <= np.finfo(np.float64).eps:
            raise MeasurementError(f"{name} points are degenerate")
        direction = right_vectors[0]
        if direction[0] < 0.0 or (direction[0] == 0.0 and direction[1] < 0.0):
            direction = -direction

        normal = np.array([-direction[1], direction[0]])
        signed_residuals = (points_xy - centre) @ normal
        sigma = _robust_sigma(signed_residuals[mask])
        if sigma <= np.finfo(np.float64).eps:
            break
        new_mask = (
            np.abs(signed_residuals)
            <= params.outlier_sigma_multiplier * sigma
        )
        if new_mask.sum() < 2 or bool(np.all(new_mask == mask)):
            break
        mask = new_mask

    selected = points_xy[mask]
    projections = (selected - centre) @ direction
    endpoints = np.vstack(
        [
            centre + float(np.min(projections)) * direction,
            centre + float(np.max(projections)) * direction,
        ]
    )
    normal = np.array([-direction[1], direction[0]])
    orthogonal = np.abs((selected - centre) @ normal)
    return LineFitXY(
        centre_xy=np.ascontiguousarray(centre),
        direction_xy=np.ascontiguousarray(direction),
        endpoints_xy=np.ascontiguousarray(endpoints),
        rmse_mm=float(np.sqrt(np.mean(orthogonal**2))),
        inlier_mask=mask,
    )


def _fit_ground_profile(
    baseline_points: np.ndarray,
    params: MeasurementParams,
    origin_xy: np.ndarray,
    direction_xy: np.ndarray,
) -> tuple[GroundProfileFit, float]:
    """Fit local ground ``Zg = a*s + b`` along the obstacle direction."""
    s = (baseline_points[:, :2] - origin_xy) @ direction_xy
    z = baseline_points[:, 2]
    mask = np.ones(len(z), dtype=bool)

    def fit_selected(
        selected_s: np.ndarray, selected_z: np.ndarray
    ) -> tuple[float, float]:
        if float(np.ptp(selected_s)) < 1.0:
            return 0.0, float(np.median(selected_z))
        design = np.column_stack([selected_s, np.ones_like(selected_s)])
        slope, intercept = np.linalg.lstsq(design, selected_z, rcond=None)[0]
        return float(slope), float(intercept)

    slope = 0.0
    intercept = float(np.median(z))
    sigma = _robust_sigma(z - intercept)
    for _ in range(params.outlier_max_iterations):
        selected_s = s[mask]
        selected_z = z[mask]
        if len(selected_z) < 2:
            raise MeasurementError("baseline has too few ground-profile inliers")
        slope, intercept = fit_selected(selected_s, selected_z)
        residuals = z - (slope * s + intercept)
        sigma = _robust_sigma(residuals[mask])
        if sigma <= np.finfo(np.float64).eps:
            break
        new_mask = (
            np.abs(residuals) <= params.outlier_sigma_multiplier * sigma
        )
        if new_mask.sum() < 2 or bool(np.all(new_mask == mask)):
            break
        mask = new_mask

    selected_residuals = z[mask] - (slope * s[mask] + intercept)
    profile = GroundProfileFit(
        origin_xy=np.ascontiguousarray(origin_xy),
        direction_xy=np.ascontiguousarray(direction_xy),
        slope_z_per_mm=slope,
        intercept_z_mm=intercept,
        rmse_mm=float(np.sqrt(np.mean(selected_residuals**2))),
        inlier_mask=mask,
    )
    return profile, sigma


def measure_height_line(
    baseline_ground: np.ndarray | None,
    height_ground: np.ndarray,
    params: MeasurementParams | None = None,
) -> HeightLineMeasurement:
    """Measure a laser-line obstacle height."""
    if params is None:
        params = MeasurementParams()

    height = _validate_points(height_ground, "height line", params.min_height_points)
    if baseline_ground is None:
        baseline = np.empty((0, 3), dtype=np.float64)
    else:
        baseline = _validate_points(
            baseline_ground, "baseline line", params.min_baseline_points
        )

    height_fit = _fit_line_xy(height[:, :2], params, "height line")
    height_inliers = height[height_fit.inlier_mask]

    if len(baseline) == 0:
        reference_zg = 0.0
        ground_sigma = None
        baseline_z_mask = np.empty(0, dtype=bool)
        baseline_fit = None
        ground_profile_fit = None
        ground_reference_mode = "zg_zero"
        local_ground_z = np.zeros(len(height_inliers), dtype=np.float64)
    else:
        ground_profile_fit, ground_sigma = _fit_ground_profile(
            baseline,
            params,
            height_fit.centre_xy,
            height_fit.direction_xy,
        )
        baseline_z_mask = ground_profile_fit.inlier_mask
        baseline_fit = _fit_line_xy(
            baseline[baseline_z_mask][:, :2], params, "baseline line"
        )
        local_ground_z = ground_profile_fit.predict_z(height_inliers[:, :2])
        reference_zg = float(np.mean(local_ground_z))
        ground_reference_mode = "baseline_roi_profile"

    relative_heights = height_inliers[:, 2] - local_ground_z
    projections = (
        height_inliers[:, :2] - height_fit.centre_xy
    ) @ height_fit.direction_xy
    length = float(np.max(projections) - np.min(projections))
    mean_height = float(np.mean(relative_heights))

    if ground_profile_fit is None:
        endpoint_z = np.full(2, mean_height)
    else:
        endpoint_z = (
            ground_profile_fit.predict_z(height_fit.endpoints_xy) + mean_height
        )
    endpoints_ground = np.column_stack([height_fit.endpoints_xy, endpoint_z])

    angle: float | None = None
    if baseline_fit is not None:
        cosine = float(
            np.clip(
                np.abs(height_fit.direction_xy @ baseline_fit.direction_xy),
                0.0,
                1.0,
            )
        )
        angle = float(np.degrees(np.arccos(cosine)))

    return HeightLineMeasurement(
        ground_baseline_zg_mm=reference_zg,
        ground_noise_sigma_mm=ground_sigma,
        ground_reference_mode=ground_reference_mode,
        baseline_fit=baseline_fit,
        ground_profile_fit=ground_profile_fit,
        height_fit=height_fit,
        height_mean_mm=mean_height,
        height_median_mm=float(np.median(relative_heights)),
        height_std_mm=float(np.std(relative_heights)),
        length_mm=length,
        endpoints_ground=np.ascontiguousarray(endpoints_ground),
        angle_with_baseline_deg=angle,
        baseline_point_count=len(baseline),
        baseline_inlier_count=int(baseline_z_mask.sum()),
        height_point_count=len(height),
        height_inlier_count=int(height_fit.inlier_mask.sum()),
    )


def measure_height_lines(
    baseline_ground: np.ndarray | None,
    height_groups_ground: Sequence[np.ndarray],
    params: MeasurementParams | None = None,
) -> list[HeightLineMeasurement]:
    """Measure each obstacle group with the same baseline point set."""
    if not height_groups_ground:
        raise MeasurementError("at least one obstacle group is required")

    measurements: list[HeightLineMeasurement] = []
    for index, height_ground in enumerate(height_groups_ground, start=1):
        try:
            measurement = measure_height_line(
                baseline_ground, height_ground, params
            )
        except MeasurementError as error:
            raise MeasurementError(f"obstacle {index}: {error}") from error
        measurements.append(measurement)
    return measurements
