"""Background lossless fixed-length frame recording with metadata."""

from __future__ import annotations

import csv
import queue
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2

from .models import CameraConfig, CapturedFrame


FRAME_FIELDS = (
    "filename",
    "camera_frame_number",
    "camera_timestamp_ticks",
    "host_timestamp_ns",
    "host_monotonic_ns",
    "frame_gap",
    "exposure_us",
    "gain_db",
    "pixel_format",
    "offset_x",
    "offset_y",
    "width",
    "height",
)


@dataclass(frozen=True, slots=True)
class RecordingResult:
    output_dir: Path
    saved_frames: int
    detected_frame_gaps: int
    queue_drops: int


class FrameRecorder:
    """Save camera frames away from the acquisition thread."""

    def __init__(self, queue_capacity: int = 64) -> None:
        self._queue: queue.Queue[CapturedFrame | None] = queue.Queue(queue_capacity)
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._active = False
        self._target = 0
        self._config: CameraConfig | None = None
        self._temp_dir: Path | None = None
        self._final_dir: Path | None = None
        self._result: RecordingResult | None = None
        self._error: BaseException | None = None
        self._queue_drops = 0

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active

    @property
    def result(self) -> RecordingResult | None:
        return self._result

    @property
    def error(self) -> BaseException | None:
        return self._error

    def start(self, root: str | Path, frame_count: int, config: CameraConfig) -> Path:
        if frame_count <= 0:
            raise ValueError("frame_count 必须为正数")
        with self._lock:
            if self._active:
                raise RuntimeError("已有录制任务正在运行")
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            output_root = Path(root).resolve()
            output_root.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            final_dir = _next_available(output_root / f"recording_{stamp}")
            temp_dir = Path(tempfile.mkdtemp(prefix=".recording_", dir=output_root))
            self._target = frame_count
            self._config = config
            self._temp_dir = temp_dir
            self._final_dir = final_dir
            self._result = None
            self._error = None
            self._queue_drops = 0
            self._active = True
            self._thread = threading.Thread(
                target=self._writer_loop, name="frame-recorder", daemon=True
            )
            self._thread.start()
            return final_dir

    def enqueue(self, frame: CapturedFrame) -> bool:
        if not self.active:
            return False
        try:
            self._queue.put_nowait(frame)
            return True
        except queue.Full:
            self._queue_drops += 1
            return False

    def cancel(self) -> None:
        if not self.active:
            return
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._queue.put_nowait(None)

    def wait(self, timeout_s: float | None = None) -> RecordingResult | None:
        thread = self._thread
        if thread is not None:
            thread.join(timeout_s)
        if self._error is not None:
            raise RuntimeError(f"录制失败: {self._error}") from self._error
        return self._result

    def _writer_loop(self) -> None:
        assert self._temp_dir is not None
        assert self._final_dir is not None
        assert self._config is not None
        rows: list[dict[str, object]] = []
        previous_frame_number: int | None = None
        total_gaps = 0
        try:
            while len(rows) < self._target:
                frame = self._queue.get()
                if frame is None:
                    raise RuntimeError("录制在达到目标帧数前被取消")
                suffix = ".png" if frame.image.dtype.name == "uint8" else ".tiff"
                filename = f"frame_{len(rows) + 1:06d}{suffix}"
                path = self._temp_dir / filename
                if not cv2.imwrite(str(path), frame.image):
                    raise OSError(f"无法保存图像: {path}")
                gap = (
                    0
                    if previous_frame_number is None
                    else max(0, frame.camera_frame_number - previous_frame_number - 1)
                )
                total_gaps += gap
                previous_frame_number = frame.camera_frame_number
                rows.append(
                    {
                        "filename": filename,
                        "camera_frame_number": frame.camera_frame_number,
                        "camera_timestamp_ticks": frame.camera_timestamp_ticks or "",
                        "host_timestamp_ns": frame.host_timestamp_ns,
                        "host_monotonic_ns": frame.host_monotonic_ns,
                        "frame_gap": gap,
                        "exposure_us": self._config.exposure_us,
                        "gain_db": self._config.gain_db,
                        "pixel_format": self._config.pixel_format,
                        "offset_x": frame.offset_x,
                        "offset_y": frame.offset_y,
                        "width": frame.image.shape[1],
                        "height": frame.image.shape[0],
                    }
                )
            with (self._temp_dir / "frames.csv").open(
                "x", encoding="utf-8-sig", newline=""
            ) as stream:
                writer = csv.DictWriter(stream, fieldnames=FRAME_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            self._temp_dir.rename(self._final_dir)
            self._result = RecordingResult(
                output_dir=self._final_dir,
                saved_frames=len(rows),
                detected_frame_gaps=total_gaps,
                queue_drops=self._queue_drops,
            )
        except BaseException as error:
            self._error = error
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        finally:
            with self._lock:
                self._active = False


def _next_available(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.name}_{index:03d}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("无法分配新的录制目录")
