from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
LOCAL_PYDEPS = PROJECT_ROOT / ".pydeps"
if str(LOCAL_PYDEPS) not in sys.path and LOCAL_PYDEPS.exists():
    sys.path.insert(0, str(LOCAL_PYDEPS))

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export v1_roi FinalCenterline images/data and corrected single-frame robot clouds."
    )
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frame-name-start", required=True)
    parser.add_argument("--frame-name-end", required=True)
    parser.add_argument("--gray-threshold", type=float, default=200.0)
    parser.add_argument("--eigen-threshold", type=float, default=170.0)
    parser.add_argument("--roi-center-y-ratio", type=float, default=0.5)
    parser.add_argument("--roi-height-ratio", type=float, default=0.18)
    parser.add_argument(
        "--flip-robot-y",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply the same v1_roi Y-axis correction used by offline_stitch_v1_roi before exporting clouds.",
    )
    return parser.parse_args()


def discover_images(root: Path, frame_name_start: str, frame_name_end: str) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Image directory does not exist: {root}")
    files = sorted(
        [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS],
        key=lambda p: p.name,
    )
    selected = [p for p in files if frame_name_start <= p.name <= frame_name_end]
    if not selected:
        raise ValueError(f"No images selected between {frame_name_start} and {frame_name_end} in {root}")
    return selected


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def corrected_points_m(points_3d_mm: np.ndarray, flip_robot_y: bool) -> np.ndarray:
    points_m = np.asarray(points_3d_mm, dtype=np.float64).reshape(-1, 3) / 1000.0
    if flip_robot_y and len(points_m) > 0:
        points_m[:, 1] *= -1.0
    return points_m


def draw_final_centerline(result, cv2) -> np.ndarray:
    overlay = result.undistorted_bgr.copy()
    x0, y0, x1, y1 = result.roi_rect
    cv2.rectangle(overlay, (x0, y0), (x1 - 1, y1 - 1), (0, 180, 0), 2)
    points = np.asarray(result.final_points_uv_global, dtype=np.float64).reshape(-1, 2)
    for u, v in points:
        x = int(round(float(u)))
        y = int(round(float(v)))
        if 0 <= x < overlay.shape[1] and 0 <= y < overlay.shape[0]:
            cv2.circle(overlay, (x, y), 2, (0, 255, 255), -1, lineType=cv2.LINE_AA)
    cv2.putText(
        overlay,
        "FinalCenterline",
        (24, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return overlay


def main() -> None:
    args = parse_args()
    import cv2

    from ablation_v1_runner import AblationParams, LaserLineExtractorROI
    from src.config_plane_v3_rectified_squareaware_left0073_refined_auto_yaw import build_default_config_yaw
    from src.linelaser0319_reusable import build_legacy0319_config_from_pipeline

    image_paths = discover_images(args.image_dir, args.frame_name_start, args.frame_name_end)
    output_dir = args.output_dir
    centerline_dir = output_dir / "final_centerline_images"
    mask_dir = output_dir / "final_centerline_masks"
    centerline_csv_dir = output_dir / "final_centerline_csv"
    cloud_dir = output_dir / "single_frame_clouds_m"
    for directory in [centerline_dir, mask_dir, centerline_csv_dir, cloud_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    cfg_yaw = build_default_config_yaw(preprocess_profile="red_filter")
    legacy_cfg = build_legacy0319_config_from_pipeline(
        pipeline_config=cfg_yaw,
        gray_threshold=float(args.gray_threshold),
        eigen_threshold=float(args.eigen_threshold),
    )
    params = AblationParams(
        roi_center_y_ratio=float(args.roi_center_y_ratio),
        roi_height_ratio=float(args.roi_height_ratio),
    )
    extractor = LaserLineExtractorROI(config=legacy_cfg, params=params)

    summary_rows: list[dict[str, object]] = []
    all_centerline_rows: list[dict[str, object]] = []
    for frame_id, image_path in enumerate(image_paths):
        image = cv2.imread(str(image_path))
        if image is None:
            raise FileNotFoundError(f"Unable to read image: {image_path}")
        result = extractor.run_single_image(image, image_path)
        points_m = corrected_points_m(result.points_3d, bool(args.flip_robot_y))
        uv = np.asarray(result.final_points_uv_global, dtype=np.float64).reshape(-1, 2)

        stem = image_path.stem
        overlay = draw_final_centerline(result, cv2)
        cv2.imwrite(str(centerline_dir / f"{stem}_FinalCenterline.png"), overlay)
        cv2.imwrite(str(mask_dir / f"{stem}_final_mask.png"), result.extraction.final_mask)

        center_rows: list[dict[str, object]] = []
        for point_index, ((u, v), (x_m, y_m, z_m)) in enumerate(zip(uv, points_m)):
            row = {
                "frame_id": frame_id,
                "frame_name": image_path.name,
                "point_index": point_index,
                "u_px": f"{u:.6f}",
                "v_px": f"{v:.6f}",
                "x_robot_m": f"{x_m:.9f}",
                "y_robot_m": f"{y_m:.9f}",
                "z_robot_m": f"{z_m:.9f}",
            }
            center_rows.append(row)
            all_centerline_rows.append(row)
        write_csv(
            centerline_csv_dir / f"{stem}_FinalCenterline.csv",
            ["frame_id", "frame_name", "point_index", "u_px", "v_px", "x_robot_m", "y_robot_m", "z_robot_m"],
            center_rows,
        )
        write_csv(
            cloud_dir / f"{frame_id:06d}_{stem}.csv",
            ["x_m", "y_m", "z_m"],
            (
                {"x_m": f"{x:.9f}", "y_m": f"{y:.9f}", "z_m": f"{z:.9f}"}
                for x, y, z in points_m
            ),
        )
        summary_rows.append(
            {
                "frame_id": frame_id,
                "frame_name": image_path.name,
                "centerline_points": len(uv),
                "cloud_points": len(points_m),
                "roi_x0": result.roi_rect[0],
                "roi_y0": result.roi_rect[1],
                "roi_x1": result.roi_rect[2],
                "roi_y1": result.roi_rect[3],
                "preprocess_time_ms": f"{result.preprocess_time_ms:.3f}",
                "extraction_time_ms": f"{result.extraction_time_ms:.3f}",
                "reconstruct_time_ms": f"{result.reconstruct_time_ms:.3f}",
                "total_time_ms": f"{result.total_time_ms:.3f}",
                "error_message": result.error_message or "",
            }
        )

    write_csv(
        output_dir / "all_final_centerline_points.csv",
        ["frame_id", "frame_name", "point_index", "u_px", "v_px", "x_robot_m", "y_robot_m", "z_robot_m"],
        all_centerline_rows,
    )
    write_csv(
        output_dir / "v1_roi_frame_summary.csv",
        [
            "frame_id",
            "frame_name",
            "centerline_points",
            "cloud_points",
            "roi_x0",
            "roi_y0",
            "roi_x1",
            "roi_y1",
            "preprocess_time_ms",
            "extraction_time_ms",
            "reconstruct_time_ms",
            "total_time_ms",
            "error_message",
        ],
        summary_rows,
    )

    point_counts = [int(row["cloud_points"]) for row in summary_rows]
    report_lines = [
        "# v1_roi FinalCenterline Batch Export",
        "",
        f"- image_dir: {args.image_dir}",
        f"- frame_range: {args.frame_name_start} to {args.frame_name_end}",
        f"- frame_count: {len(image_paths)}",
        f"- total_points: {sum(point_counts)}",
        f"- mean_points_per_frame: {float(np.mean(point_counts)) if point_counts else 0.0:.3f}",
        f"- flip_robot_y: {bool(args.flip_robot_y)}",
        "- point_unit: meters",
        "",
        "## Output Files",
        "- final_centerline_images/*_FinalCenterline.png",
        "- final_centerline_masks/*_final_mask.png",
        "- final_centerline_csv/*_FinalCenterline.csv",
        "- single_frame_clouds_m/*.csv",
        "- all_final_centerline_points.csv",
        "- v1_roi_frame_summary.csv",
    ]
    (output_dir / "v1_roi_centerline_export_report.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )
    print(f"frames={len(image_paths)} total_points={sum(point_counts)}")
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
