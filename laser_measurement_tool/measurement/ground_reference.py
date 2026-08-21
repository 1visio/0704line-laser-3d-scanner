"""Reusable robust linear ground reference fitting.

The fitting kernel in this module is the original baseline-ROI kernel from
``height_measure``.  It models the ground only as ``Zg = a*S + b``; no
additional surface model or calibration parameter is introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


class MeasurementError(RuntimeError):
    """Raised when input points are insufficient or geometrically degenerate."""


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
    """Linear ground height model along a ground-line direction."""

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
class SessionGroundReference:
    """Frozen runtime ``Zg = a*S+b`` reference for one online session.

    ``valid_s_range_mm`` is the S span of the fitted inliers.  Runtime point
    application never extrapolates outside that span: out-of-range points are
    returned unchanged and reported by the boolean mask from
    :meth:`apply_to_points`.
    """

    origin_xy: np.ndarray
    direction_xy: np.ndarray
    slope_z_per_mm: float
    intercept_z_mm: float
    rmse_mm: float
    valid_s_range_mm: tuple[float, float]
    status: str = "VALID"
    source: str = "session_laser_ground"
    inlier_mask: np.ndarray | None = None
    point_count: int = 0
    inlier_count: int = 0

    @property
    def slope(self) -> float:
        return self.slope_z_per_mm

    @property
    def intercept(self) -> float:
        return self.intercept_z_mm

    @property
    def rmse(self) -> float:
        return self.rmse_mm

    @property
    def valid_s_range(self) -> tuple[float, float]:
        return self.valid_s_range_mm

    def project_s(self, points_xy: np.ndarray) -> np.ndarray:
        points = np.asarray(points_xy, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 2:
            raise MeasurementError("ground reference XY points must have shape (N, 2)")
        if not np.isfinite(points).all():
            raise MeasurementError("ground reference XY points contain NaN or infinite values")
        return (points - self.origin_xy) @ self.direction_xy

    def predict_z(self, points_xy: np.ndarray) -> np.ndarray:
        s = self.project_s(points_xy)
        return self.slope_z_per_mm * s + self.intercept_z_mm

    def valid_s_mask(self, points_xy: np.ndarray) -> np.ndarray:
        s = self.project_s(points_xy)
        lower, upper = self.valid_s_range_mm
        return np.isfinite(s) & (s >= lower) & (s <= upper)

    def apply_to_points(
        self, points_ground: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Level valid points and return ``(points, valid_mask)``.

        The returned array is always a copy.  Points outside the fitted S
        domain remain raw so callers cannot silently extrapolate the session
        reference.
        """
        points = np.asarray(points_ground, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3:
            raise MeasurementError("ground points must have shape (N, 3)")
        if not np.isfinite(points).all():
            raise MeasurementError("ground points contain NaN or infinite values")
        corrected = np.ascontiguousarray(points.copy())
        if not len(points):
            return corrected, np.empty(0, dtype=bool)
        valid = self.valid_s_mask(points[:, :2])
        if np.any(valid):
            corrected[valid, 2] -= self.predict_z(points[valid, :2])
        return corrected, valid

    # Descriptive aliases keep the runtime object convenient for callers that
    # think in terms of levelling a point cloud rather than applying a model.
    level_points = apply_to_points
    apply = apply_to_points

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe runtime snapshot."""
        return {
            "status": self.status,
            "source": self.source,
            "origin_xy": np.asarray(self.origin_xy, dtype=np.float64).tolist(),
            "direction_xy": np.asarray(self.direction_xy, dtype=np.float64).tolist(),
            "slope": float(self.slope_z_per_mm),
            "intercept": float(self.intercept_z_mm),
            "slope_z_per_mm": float(self.slope_z_per_mm),
            "intercept_z_mm": float(self.intercept_z_mm),
            "rmse_mm": float(self.rmse_mm),
            "valid_s_range_mm": [
                float(self.valid_s_range_mm[0]),
                float(self.valid_s_range_mm[1]),
            ],
            "point_count": int(self.point_count),
            "inlier_count": int(self.inlier_count),
        }


def validate_points(points: np.ndarray, name: str, minimum: int) -> np.ndarray:
    """Validate and normalize a 3D ground-point array."""
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


def robust_sigma(residuals: np.ndarray) -> float:
    """MAD-based robust standard deviation, with std fallback."""
    mad = float(np.median(np.abs(residuals - np.median(residuals))))
    sigma = 1.4826 * mad
    if sigma <= np.finfo(np.float64).eps:
        sigma = float(np.std(residuals))
    return sigma


def fit_line_xy(
    points_xy: np.ndarray, params: Any, name: str
) -> LineFitXY:
    """Fit a robust 2D line in XY and reject orthogonal outliers."""
    # This body intentionally mirrors the former height_measure kernel.
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
        sigma = robust_sigma(signed_residuals[mask])
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


def fit_ground_profile(
    baseline_points: np.ndarray,
    params: Any,
    origin_xy: np.ndarray,
    direction_xy: np.ndarray,
) -> tuple[GroundProfileFit, float]:
    """Fit the existing robust linear ground profile ``Zg = a*S+b``."""
    # This body intentionally mirrors the former height_measure kernel.
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
    sigma = robust_sigma(z - intercept)
    for _ in range(params.outlier_max_iterations):
        selected_s = s[mask]
        selected_z = z[mask]
        if len(selected_z) < 2:
            raise MeasurementError("baseline has too few ground-profile inliers")
        slope, intercept = fit_selected(selected_s, selected_z)
        residuals = z - (slope * s + intercept)
        sigma = robust_sigma(residuals[mask])
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


def fit_session_ground_reference(
    points_ground: np.ndarray,
    params: Any | None = None,
    *,
    source: str = "session_laser_ground",
) -> SessionGroundReference:
    """Fit one frozen session ground reference from an empty-ground point cloud."""
    if params is None:
        # Import lazily to avoid a module cycle: height_measure re-exports the
        # same kernel and imports this module at import time.
        from .height_measure import MeasurementParams

        params = MeasurementParams()
    points = validate_points(points_ground, "session ground reference", params.min_baseline_points)
    line_fit = fit_line_xy(points[:, :2], params, "session ground reference")
    profile, _ = fit_ground_profile(
        points,
        params,
        line_fit.centre_xy,
        line_fit.direction_xy,
    )
    s = profile.project_s(points[:, :2])
    inlier_s = s[profile.inlier_mask]
    if len(inlier_s) < 2 or not np.isfinite(inlier_s).all():
        raise MeasurementError("session ground reference has too few valid S points")
    return SessionGroundReference(
        origin_xy=np.ascontiguousarray(profile.origin_xy.copy()),
        direction_xy=np.ascontiguousarray(profile.direction_xy.copy()),
        slope_z_per_mm=profile.slope_z_per_mm,
        intercept_z_mm=profile.intercept_z_mm,
        rmse_mm=profile.rmse_mm,
        valid_s_range_mm=(float(np.min(inlier_s)), float(np.max(inlier_s))),
        status="VALID",
        source=source,
        inlier_mask=np.ascontiguousarray(profile.inlier_mask.copy()),
        point_count=len(points),
        inlier_count=int(profile.inlier_mask.sum()),
    )


__all__ = [
    "GroundProfileFit",
    "LineFitXY",
    "MeasurementError",
    "SessionGroundReference",
    "fit_ground_profile",
    "fit_line_xy",
    "fit_session_ground_reference",
    "robust_sigma",
    "validate_points",
]
