"""Capture a repeatable monochrome line-laser image dataset with a Galaxy camera."""

from __future__ import annotations

import argparse
import csv
import importlib
import math
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable, Sequence

import cv2
import numpy as np


DEFAULT_DATASET = Path(__file__).resolve().parents[1]
SDK_SAMPLE_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "Daheng Imaging"
    / "GalaxySDK"
    / "Development"
    / "Samples"
    / "Python"
)

METADATA_FIELDS = (
    "exp_id",
    "image_dir",
    "exposure_us",
    "gain",
    "material",
    "distance_mm",
    "baseline_mm",
    "laser_angle_deg",
    "frame_count",
    "pixel_format",
    "roi_offset_x",
    "roi_offset_y",
    "roi_width",
    "roi_height",
    "remark",
)

PIXEL_FORMATS = {
    "mono8": "Mono8",
    "mono10": "Mono10",
    "mono12": "Mono12",
    "mono14": "Mono14",
    "mono16": "Mono16",
}


@dataclass(frozen=True)
class CameraSettings:
    exposure_us: float
    gain: float
    pixel_format: str
    offset_x: int
    offset_y: int
    width: int
    height: int


@dataclass(frozen=True)
class CaptureResult:
    saved_frames: int
    output_dir: Path


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite value greater than zero")
    return parsed


def finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("must be finite")
    return parsed


def pixel_format_arg(value: str) -> str:
    try:
        return PIXEL_FORMATS[value.casefold()]
    except KeyError as exc:
        supported = ", ".join(PIXEL_FORMATS.values())
        raise argparse.ArgumentTypeError(
            f"unsupported pixel format {value!r}; choose one of: {supported}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture monochrome line-laser images with the first Galaxy USB3 camera."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Dataset root (default: {DEFAULT_DATASET}).",
    )
    parser.add_argument("--exp-id", required=True, help="Unique experiment identifier.")
    parser.add_argument("--frames", type=positive_int, default=50)
    parser.add_argument("--exposure-us", type=positive_float, required=True)
    parser.add_argument("--gain", type=finite_float, default=0.0)
    parser.add_argument("--material", required=True)
    parser.add_argument("--distance-mm", type=positive_float, required=True)
    parser.add_argument("--baseline-mm", type=positive_float, required=True)
    parser.add_argument("--laser-angle-deg", type=finite_float, required=True)
    parser.add_argument("--pixel-format", type=pixel_format_arg, default="Mono12")
    parser.add_argument("--offset-x", type=nonnegative_int, default=0)
    parser.add_argument("--offset-y", type=nonnegative_int, default=0)
    parser.add_argument("--width", type=positive_int)
    parser.add_argument("--height", type=positive_int)
    parser.add_argument("--warmup-frames", type=nonnegative_int, default=10)
    return parser


def validate_args(args: argparse.Namespace) -> None:
    exp_id = args.exp_id
    if not exp_id or exp_id != exp_id.strip():
        raise ValueError("exp_id must be non-empty and have no surrounding whitespace")
    if exp_id in {".", ".."} or Path(exp_id).name != exp_id or "/" in exp_id or "\\" in exp_id:
        raise ValueError("exp_id must be a single safe directory name")
    if not args.material or args.material != args.material.strip():
        raise ValueError("material must be non-empty and have no surrounding whitespace")

    width_given = args.width is not None
    height_given = args.height is not None
    if width_given != height_given:
        raise ValueError("width and height must be provided together")
    if not width_given and (args.offset_x != 0 or args.offset_y != 0):
        raise ValueError("offset-x and offset-y must be zero when using full-frame mode")


def load_galaxy_sdk() -> tuple[ModuleType, type]:
    """Load gxipy, falling back to the SDK sample package in this repository."""
    try:
        gx = importlib.import_module("gxipy")
    except ModuleNotFoundError as exc:
        if exc.name != "gxipy":
            raise RuntimeError(f"Galaxy SDK dependency is missing: {exc}") from exc
        if not SDK_SAMPLE_DIR.is_dir():
            raise RuntimeError(
                "gxipy is not installed and the repository SDK sample package was not found"
            ) from exc
        sys.path.insert(0, str(SDK_SAMPLE_DIR))
        try:
            gx = importlib.import_module("gxipy")
        except Exception as fallback_exc:
            raise _sdk_load_error(fallback_exc) from fallback_exc
    except Exception as exc:
        raise _sdk_load_error(exc) from exc

    try:
        utility = importlib.import_module("gxipy.ImageProc").Utility
    except Exception as exc:
        raise _sdk_load_error(exc) from exc
    return gx, utility


def _sdk_load_error(exc: Exception) -> RuntimeError:
    detail = str(exc) or type(exc).__name__
    return RuntimeError(
        "Cannot load the Galaxy SDK runtime. Install/configure Galaxy SDK and ensure "
        f"GALAXY_GENICAM_ROOT is available. Details: {detail}"
    )


def ensure_metadata(metadata_path: Path) -> set[str]:
    """Create the metadata file if needed and return all existing experiment IDs."""
    if not metadata_path.exists():
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("x", encoding="utf-8-sig", newline="") as handle:
            csv.DictWriter(handle, fieldnames=METADATA_FIELDS).writeheader()

    try:
        handle = metadata_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise RuntimeError(f"Cannot read metadata file: {metadata_path}") from exc

    with handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != METADATA_FIELDS:
            raise RuntimeError(
                f"metadata.csv header must exactly match: {','.join(METADATA_FIELDS)}"
            )
        exp_ids: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            exp_id = (row.get("exp_id") or "").strip()
            if not exp_id and not any((value or "").strip() for value in row.values()):
                continue
            if not exp_id:
                raise RuntimeError(f"metadata.csv line {line_number}: exp_id is empty")
            if exp_id in exp_ids:
                raise RuntimeError(
                    f"metadata.csv line {line_number}: duplicate exp_id {exp_id!r}"
                )
            exp_ids.add(exp_id)
        return exp_ids


def append_metadata_atomic(metadata_path: Path, row: dict[str, object]) -> None:
    """Append one logical row by atomically replacing the complete CSV file."""
    with metadata_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != METADATA_FIELDS:
            raise RuntimeError("metadata.csv header changed during capture")
        rows = list(reader)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8-sig",
            newline="",
            dir=metadata_path.parent,
            prefix=".metadata.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, metadata_path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def write_png(path: Path, image: np.ndarray) -> None:
    if image.ndim != 2 or image.dtype not in (np.dtype(np.uint8), np.dtype(np.uint16)):
        raise RuntimeError(
            f"Expected a 2-D uint8 or uint16 image, got shape={image.shape}, dtype={image.dtype}"
        )
    try:
        saved = cv2.imwrite(str(path), np.ascontiguousarray(image))
    except cv2.error as exc:
        raise OSError(f"Failed to save PNG: {path}") from exc
    if not saved:
        raise OSError(f"Failed to save PNG: {path}")


def _writable_feature(control: object, name: str, kind: str) -> object:
    if not control.is_implemented(name):
        raise RuntimeError(f"Camera feature {name} is not implemented")
    if not control.is_writable(name):
        raise RuntimeError(f"Camera feature {name} is not writable")
    getter = getattr(control, f"get_{kind}_feature")
    return getter(name)


def _set_enum(control: object, name: str, value: str) -> tuple[int, str]:
    feature = _writable_feature(control, name, "enum")
    feature.set(value)
    return feature.get()


def _set_float(control: object, name: str, value: float) -> float:
    feature = _writable_feature(control, name, "float")
    value_range = feature.get_range()
    minimum = float(value_range["min"])
    maximum = float(value_range["max"])
    if value < minimum or value > maximum:
        raise ValueError(
            f"{name}={value:g} is outside the camera range [{minimum:g}, {maximum:g}]"
        )
    feature.set(float(value))
    return float(feature.get())


def _set_int(control: object, name: str, value: int) -> int:
    feature = _writable_feature(control, name, "int")
    value_range = feature.get_range()
    minimum = int(value_range["min"])
    maximum = int(value_range["max"])
    increment = max(1, int(value_range["inc"]))
    if value < minimum or value > maximum:
        raise ValueError(
            f"{name}={value} is outside the camera range [{minimum}, {maximum}]"
        )
    if (value - minimum) % increment != 0:
        raise ValueError(
            f"{name}={value} is not aligned to increment {increment} from minimum {minimum}"
        )
    feature.set(int(value))
    return int(feature.get())


def _int_max(control: object, name: str) -> int:
    feature = _writable_feature(control, name, "int")
    return int(feature.get_range()["max"])


def configure_camera(
    cam: object, args: argparse.Namespace, utility: type
) -> CameraSettings:
    control = cam.get_remote_device_feature_control()

    _set_enum(control, "TriggerMode", "Off")
    _set_enum(control, "ExposureAuto", "Off")
    _set_enum(control, "GainAuto", "Off")
    pixel_value, pixel_symbol = _set_enum(
        control, "PixelFormat", args.pixel_format
    )
    if not utility.is_gray(pixel_value):
        raise RuntimeError(f"Camera pixel format is not monochrome: {pixel_symbol}")

    exposure_us = _set_float(control, "ExposureTime", args.exposure_us)
    gain = _set_float(control, "Gain", args.gain)

    _set_int(control, "OffsetX", 0)
    _set_int(control, "OffsetY", 0)
    if args.width is None:
        width = _set_int(control, "Width", _int_max(control, "Width"))
        height = _set_int(control, "Height", _int_max(control, "Height"))
        offset_x = 0
        offset_y = 0
    else:
        width = _set_int(control, "Width", args.width)
        height = _set_int(control, "Height", args.height)
        offset_x = _set_int(control, "OffsetX", args.offset_x)
        offset_y = _set_int(control, "OffsetY", args.offset_y)

    return CameraSettings(
        exposure_us=exposure_us,
        gain=gain,
        pixel_format=pixel_symbol,
        offset_x=offset_x,
        offset_y=offset_y,
        width=width,
        height=height,
    )


def print_camera_parameters(
    device_info: dict[str, object], settings: CameraSettings, args: argparse.Namespace
) -> None:
    print("Current camera parameters:")
    print(f"  model: {device_info.get('model_name') or device_info.get('display_name') or 'unknown'}")
    print(f"  serial_number: {device_info.get('sn') or 'unknown'}")
    print(f"  exposure_us: {settings.exposure_us:g}")
    print(f"  gain: {settings.gain:g}")
    print(f"  pixel_format: {settings.pixel_format}")
    print(
        "  roi: "
        f"offset=({settings.offset_x}, {settings.offset_y}), "
        f"size=({settings.width}, {settings.height})"
    )
    print(f"  warmup_frames: {args.warmup_frames}")
    print(f"  frames_to_save: {args.frames}")


def _metadata_row(
    args: argparse.Namespace, settings: CameraSettings
) -> dict[str, object]:
    return {
        "exp_id": args.exp_id,
        "image_dir": f"raw/{args.exp_id}",
        "exposure_us": f"{settings.exposure_us:.12g}",
        "gain": f"{settings.gain:.12g}",
        "material": args.material,
        "distance_mm": f"{args.distance_mm:.12g}",
        "baseline_mm": f"{args.baseline_mm:.12g}",
        "laser_angle_deg": f"{args.laser_angle_deg:.12g}",
        "frame_count": args.frames,
        "pixel_format": settings.pixel_format,
        "roi_offset_x": settings.offset_x,
        "roi_offset_y": settings.offset_y,
        "roi_width": settings.width,
        "roi_height": settings.height,
        "remark": "",
    }


def _cleanup_directory(path: Path | None) -> None:
    if path is None or not path.exists():
        return
    try:
        shutil.rmtree(path)
    except OSError as exc:
        print(f"WARNING: could not clean temporary output {path}: {exc}", file=sys.stderr)


def acquire_dataset(
    args: argparse.Namespace,
    gx: ModuleType | object | None = None,
    utility: type | object | None = None,
    image_writer: Callable[[Path, np.ndarray], None] = write_png,
) -> CaptureResult:
    validate_args(args)
    dataset = args.dataset.expanduser().resolve()
    raw_root = dataset / "raw"
    metadata_path = dataset / "metadata.csv"
    raw_root.mkdir(parents=True, exist_ok=True)

    existing_ids = ensure_metadata(metadata_path)
    final_dir = raw_root / args.exp_id
    if args.exp_id in existing_ids:
        raise RuntimeError(f"exp_id already exists in metadata.csv: {args.exp_id}")
    if final_dir.exists():
        raise RuntimeError(f"experiment output directory already exists: {final_dir}")

    if gx is None or utility is None:
        gx, utility = load_galaxy_sdk()

    temp_dir = Path(tempfile.mkdtemp(prefix=f".{args.exp_id}.", dir=raw_root))
    cam: object | None = None
    stream_started = False
    published = False
    try:
        device_manager = gx.DeviceManager()
        device_count, device_info_list = device_manager.update_all_device_list()
        if device_count == 0 or not device_info_list:
            raise RuntimeError("No Galaxy camera was found")

        device_info = device_info_list[0]
        if device_info.get("device_class") != gx.GxDeviceClassList.U3V:
            raise RuntimeError("The first enumerated Galaxy camera is not a USB3 (U3V) device")

        cam = device_manager.open_device_by_index(1)
        settings = configure_camera(cam, args, utility)
        print_camera_parameters(device_info, settings, args)

        cam.stream_on()
        stream_started = True
        expected_dtype = np.dtype(np.uint8 if settings.pixel_format == "Mono8" else np.uint16)
        saved_frames = 0
        total_frames = args.warmup_frames + args.frames
        for capture_index in range(total_frames):
            raw_image = cam.data_stream[0].get_image()
            if raw_image is None:
                raise RuntimeError(f"Failed to acquire frame {capture_index + 1}")
            array = raw_image.get_numpy_array()
            if array is None:
                raise RuntimeError(f"Acquired frame {capture_index + 1} is incomplete")
            if capture_index < args.warmup_frames:
                continue

            image = np.asarray(array).copy()
            if image.dtype != expected_dtype:
                raise RuntimeError(
                    f"Unexpected dtype for {settings.pixel_format}: {image.dtype}; "
                    f"expected {expected_dtype}"
                )
            saved_frames += 1
            image_writer(temp_dir / f"frame_{saved_frames:04d}.png", image)

        cam.stream_off()
        stream_started = False
        temp_dir.rename(final_dir)
        published = True
        append_metadata_atomic(metadata_path, _metadata_row(args, settings))
        return CaptureResult(saved_frames=saved_frames, output_dir=final_dir)
    except Exception:
        if published:
            _cleanup_directory(final_dir)
        else:
            _cleanup_directory(temp_dir)
        raise
    finally:
        if stream_started and cam is not None:
            try:
                cam.stream_off()
            except Exception as exc:
                print(f"WARNING: failed to stop camera stream: {exc}", file=sys.stderr)
        if cam is not None:
            try:
                cam.close_device()
            except Exception as exc:
                print(f"WARNING: failed to close camera: {exc}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = acquire_dataset(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Saved frames: {result.saved_frames}")
    print(f"Output directory: {result.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
