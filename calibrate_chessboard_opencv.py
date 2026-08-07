from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须为正整数")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用 OpenCV 棋盘格图像进行单目相机标定")
    parser.add_argument("--image-dir", type=Path, required=True, help="标定图像文件夹")
    parser.add_argument(
        "--pattern-cols",
        type=positive_int,
        default=6,
        help="横向内角点数量（默认：6）",
    )
    parser.add_argument(
        "--pattern-rows",
        type=positive_int,
        default=5,
        help="纵向内角点数量（默认：5）",
    )
    parser.add_argument(
        "--square-size-mm",
        type=positive_float,
        default=30.0,
        help="棋盘格单格边长，单位 mm（默认：30）",
    )
    parser.add_argument("--output", type=Path, required=True, help="标定结果输出目录")
    return parser.parse_args()


def list_images(image_dir: Path) -> list[Path]:
    if not image_dir.exists():
        raise FileNotFoundError(f"图像目录不存在：{image_dir}")
    if not image_dir.is_dir():
        raise NotADirectoryError(f"--image-dir 不是目录：{image_dir}")

    images = sorted(
        (
            path
            for path in image_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: path.name.lower(),
    )
    if not images:
        raise ValueError(f"图像目录中未找到支持的图像：{image_dir}")
    return images


def read_image(path: Path) -> np.ndarray | None:
    """Read an image while supporting non-ASCII paths on Windows."""
    try:
        encoded = np.fromfile(path, dtype=np.uint8)
        if encoded.size == 0:
            return None
        return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    except (OSError, cv2.error):
        return None


def write_image(path: Path, image: np.ndarray) -> None:
    """Write an image while supporting non-ASCII paths on Windows."""
    success, encoded = cv2.imencode(path.suffix, image)
    if not success:
        raise RuntimeError(f"OpenCV 无法编码图像：{path}")
    try:
        encoded.tofile(path)
    except OSError as exc:
        raise OSError(f"无法写入图像：{path}") from exc


def detect_corners(
    gray: np.ndarray,
    pattern_size: tuple[int, int],
) -> tuple[bool, np.ndarray | None]:
    if hasattr(cv2, "findChessboardCornersSB"):
        try:
            found, corners = cv2.findChessboardCornersSB(
                gray,
                pattern_size,
                flags=cv2.CALIB_CB_NORMALIZE_IMAGE,
            )
        except cv2.error:
            found, corners = False, None
        if found:
            return True, corners.astype(np.float32)

    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCorners(gray, pattern_size, flags)
    if not found:
        return False, None

    criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.001,
    )
    refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    return True, refined


def create_object_points(
    pattern_cols: int,
    pattern_rows: int,
    square_size_mm: float,
) -> np.ndarray:
    points = np.zeros((pattern_cols * pattern_rows, 3), dtype=np.float32)
    points[:, :2] = (
        np.mgrid[0:pattern_cols, 0:pattern_rows].T.reshape(-1, 2)
        * square_size_mm
    )
    return points


def calculate_reprojection_errors(
    object_points: list[np.ndarray],
    image_points: list[np.ndarray],
    rotation_vectors: tuple[np.ndarray, ...],
    translation_vectors: tuple[np.ndarray, ...],
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> list[float]:
    errors: list[float] = []
    for object_point, observed, rvec, tvec in zip(
        object_points,
        image_points,
        rotation_vectors,
        translation_vectors,
        strict=True,
    ):
        projected, _ = cv2.projectPoints(
            object_point,
            rvec,
            tvec,
            camera_matrix,
            dist_coeffs,
        )
        residual = observed.reshape(-1, 2) - projected.reshape(-1, 2)
        rmse = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
        errors.append(rmse)
    return errors


def write_failed_images(output_dir: Path, failed_paths: list[Path]) -> None:
    content = "".join(f"{path.name}\n" for path in failed_paths)
    (output_dir / "failed_images.txt").write_text(content, encoding="utf-8")


def write_error_csv(
    output_dir: Path,
    successful_paths: list[Path],
    errors: list[float],
) -> None:
    with (output_dir / "per_image_error.csv").open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["image", "reprojection_error_pixels"])
        for path, error in zip(successful_paths, errors, strict=True):
            writer.writerow([path.name, f"{error:.9f}"])


def write_yaml(
    output_dir: Path,
    image_size: tuple[int, int],
    pattern_cols: int,
    pattern_rows: int,
    square_size_mm: float,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    mean_error: float,
) -> None:
    matrix_rows = [
        "  - [" + ", ".join(f"{value:.17g}" for value in row) + "]"
        for row in camera_matrix
    ]
    distortion_values = ", ".join(
        f"{value:.17g}" for value in dist_coeffs.reshape(-1)
    )
    content = "\n".join(
        [
            f"image_width: {image_size[0]}",
            f"image_height: {image_size[1]}",
            f"pattern_cols: {pattern_cols}",
            f"pattern_rows: {pattern_rows}",
            f"square_size_mm: {square_size_mm:.17g}",
            "camera_matrix:",
            *matrix_rows,
            f"dist_coeffs: [{distortion_values}]",
            f"mean_reprojection_error: {mean_error:.17g}",
            "",
        ]
    )
    (output_dir / "calibration_result.yaml").write_text(content, encoding="utf-8")


def write_report(
    output_dir: Path,
    total_count: int,
    successful_paths: list[Path],
    failed_paths: list[Path],
    errors: list[float],
) -> None:
    mean_error = float(np.mean(errors))
    max_index = int(np.argmax(errors))
    report = "\n".join(
        [
            "OpenCV 单目棋盘格相机标定报告",
            "=" * 34,
            f"输入图像数量: {total_count}",
            f"使用图像数量: {len(successful_paths)}",
            f"失败图像数量: {len(failed_paths)}",
            f"平均重投影误差 (pixels): {mean_error:.9f}",
            f"最大单张误差 (pixels): {errors[max_index]:.9f}",
            f"最大误差图像: {successful_paths[max_index].name}",
            "",
        ]
    )
    (output_dir / "calibration_report.txt").write_text(report, encoding="utf-8-sig")


def save_undistorted_images(
    successful_paths: list[Path],
    output_dir: Path,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> None:
    for path in successful_paths:
        image = read_image(path)
        if image is None:
            raise RuntimeError(f"生成去畸变图时无法重新读取：{path}")
        undistorted = cv2.undistort(image, camera_matrix, dist_coeffs)
        write_image(output_dir / path.name, undistorted)


def calibrate(args: argparse.Namespace) -> None:
    image_paths = list_images(args.image_dir)
    output_dir = args.output
    detected_dir = output_dir / "detected"
    undistort_dir = output_dir / "undistort_check"
    detected_dir.mkdir(parents=True, exist_ok=True)
    undistort_dir.mkdir(parents=True, exist_ok=True)

    pattern_size = (args.pattern_cols, args.pattern_rows)
    object_point_template = create_object_points(
        args.pattern_cols,
        args.pattern_rows,
        args.square_size_mm,
    )
    object_points: list[np.ndarray] = []
    image_points: list[np.ndarray] = []
    successful_paths: list[Path] = []
    failed_paths: list[Path] = []
    expected_size: tuple[int, int] | None = None
    expected_size_path: Path | None = None

    for path in image_paths:
        image = read_image(path)
        if image is None:
            print(f"[失败] 无法读取：{path.name}", file=sys.stderr)
            failed_paths.append(path)
            continue

        image_size = (image.shape[1], image.shape[0])
        if expected_size is None:
            expected_size = image_size
            expected_size_path = path
        elif image_size != expected_size:
            raise ValueError(
                "图像尺寸不一致："
                f"{expected_size_path.name} 为 {expected_size[0]}x{expected_size[1]}，"
                f"{path.name} 为 {image_size[0]}x{image_size[1]}"
            )

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        try:
            found, corners = detect_corners(gray, pattern_size)
        except cv2.error as exc:
            print(f"[失败] 角点检测异常：{path.name} ({exc})", file=sys.stderr)
            failed_paths.append(path)
            continue

        if not found or corners is None:
            print(f"[失败] 未检测到完整棋盘格：{path.name}")
            failed_paths.append(path)
            continue

        object_points.append(object_point_template.copy())
        image_points.append(corners)
        successful_paths.append(path)

        overlay = image.copy()
        cv2.drawChessboardCorners(overlay, pattern_size, corners, True)
        write_image(detected_dir / path.name, overlay)
        print(f"[成功] {path.name}")

    write_failed_images(output_dir, failed_paths)
    if expected_size is None:
        raise RuntimeError("所有输入图像均无法读取")
    if not successful_paths:
        raise RuntimeError("没有图像成功检测到棋盘格内角点，无法进行标定")

    _, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        object_points,
        image_points,
        expected_size,
        None,
        None,
    )
    errors = calculate_reprojection_errors(
        object_points,
        image_points,
        tuple(rvecs),
        tuple(tvecs),
        camera_matrix,
        dist_coeffs,
    )
    mean_error = float(np.mean(errors))

    write_error_csv(output_dir, successful_paths, errors)
    write_yaml(
        output_dir,
        expected_size,
        args.pattern_cols,
        args.pattern_rows,
        args.square_size_mm,
        camera_matrix,
        dist_coeffs,
        mean_error,
    )
    np.save(output_dir / "camera_matrix.npy", camera_matrix)
    np.save(output_dir / "dist_coeffs.npy", dist_coeffs)
    save_undistorted_images(
        successful_paths,
        undistort_dir,
        camera_matrix,
        dist_coeffs,
    )
    write_report(
        output_dir,
        len(image_paths),
        successful_paths,
        failed_paths,
        errors,
    )

    print(f"标定完成，结果已保存到：{output_dir.resolve()}")
    print(f"平均重投影误差：{mean_error:.9f} pixels")


def main() -> int:
    args = parse_args()
    try:
        calibrate(args)
    except (OSError, ValueError, RuntimeError, cv2.error) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
