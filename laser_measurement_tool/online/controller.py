"""Two-thread online acquisition/processing controller for the Qt UI."""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, Signal

from .models import CameraSession, FrameResult
from .pipeline import FramePipeline
from .recording import FrameRecorder
from .runtime import LatestFrameSlot


RESULT_EMIT_INTERVAL_S = 0.075
STATS_EMIT_INTERVAL_S = 0.25


class OnlineController(QObject):
    raw_frame_ready = Signal(object)
    result_ready = Signal(object)
    stats_updated = Signal(object)
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session: CameraSession | None = None
        self._pipeline: FramePipeline | None = None
        self._recorder: FrameRecorder | None = None
        self._slot: LatestFrameSlot | None = None
        self._stop_event = threading.Event()
        self._acquisition_thread: threading.Thread | None = None
        self._processing_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._running = False
        self._stopping = False
        self._captured = 0
        self._processed = 0
        self._camera_gaps = 0
        self._last_camera_frame: int | None = None
        self._last_raw_emit_at = 0.0
        self._last_result_emit_at = 0.0
        self._last_stats_emit_at = 0.0
        self._stats_lock = threading.Lock()
        self._started_at = 0.0
        self._last_result: FrameResult | None = None

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def last_result(self) -> FrameResult | None:
        return self._last_result

    def start(
        self,
        session: CameraSession,
        pipeline: FramePipeline,
        recorder: FrameRecorder,
    ) -> None:
        with self._lock:
            if self._running:
                raise RuntimeError("在线取流已经运行")
            if self._stopping:
                raise RuntimeError("在线取流正在停止")
            self._running = True
        self._session = session
        self._pipeline = pipeline
        self._recorder = recorder
        self._slot = LatestFrameSlot()
        self._stop_event.clear()
        self._captured = self._processed = self._camera_gaps = 0
        self._last_camera_frame = None
        self._last_raw_emit_at = 0.0
        self._last_result_emit_at = 0.0
        self._last_stats_emit_at = 0.0
        self._last_result = None
        self._started_at = time.monotonic()
        try:
            session.start()
            self._acquisition_thread = threading.Thread(
                target=self._acquire_loop, name="camera-acquisition", daemon=True
            )
            self._processing_thread = threading.Thread(
                target=self._process_loop, name="frame-processing", daemon=True
            )
            self._acquisition_thread.start()
            self._processing_thread.start()
        except Exception:
            self._stop_event.set()
            self._slot.close()
            try:
                session.stop()
            except Exception:
                pass
            for thread in (
                self._acquisition_thread,
                self._processing_thread,
            ):
                if thread is not None and thread.is_alive():
                    thread.join(1.0)
            with self._lock:
                self._running = False
            raise

    def stop(self) -> None:
        with self._lock:
            if not self._running or self._stopping:
                return
            self._stopping = True
        self._stop_event.set()
        if self._slot is not None:
            self._slot.close()
        errors: list[str] = []
        timeout_s = 3.0
        if self._session is not None:
            timeout_s = max(
                timeout_s,
                self._session.config.timeout_ms / 1000.0 + 1.0,
            )
        for thread in (self._acquisition_thread, self._processing_thread):
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout_s)
        if self._session is not None:
            try:
                self._session.stop()
            except Exception as error:
                errors.append(f"停止相机取流失败: {error}")
        alive_threads = [
            thread
            for thread in (self._acquisition_thread, self._processing_thread)
            if thread is not None and thread.is_alive()
        ]
        for thread in alive_threads:
            thread.join(1.0)
        alive_names = [thread.name for thread in alive_threads if thread.is_alive()]
        if alive_names:
            errors.append(f"线程未按时退出: {', '.join(alive_names)}")
        with self._lock:
            self._running = False
            self._stopping = False
        self._emit_stats_if_due(force=True)
        if errors:
            self.failed.emit("；".join(errors))
        self.stopped.emit()

    def _acquire_loop(self) -> None:
        assert self._session is not None
        assert self._slot is not None
        try:
            while not self._stop_event.is_set():
                frame = self._session.get_frame()
                if self._last_camera_frame is not None:
                    self._camera_gaps += max(
                        0, frame.camera_frame_number - self._last_camera_frame - 1
                    )
                self._last_camera_frame = frame.camera_frame_number
                self._captured += 1
                now = time.monotonic()
                if now - self._last_raw_emit_at >= 0.05:
                    self._last_raw_emit_at = now
                    self.raw_frame_ready.emit(frame)
                if self._recorder is not None and self._recorder.active:
                    self._recorder.enqueue(frame)
                self._slot.put(frame)
                self._emit_stats_if_due()
        except Exception as error:
            if not self._stop_event.is_set():
                self.failed.emit(f"相机取流失败: {error}")
                self._stop_event.set()
                self._slot.close()

    def _process_loop(self) -> None:
        assert self._pipeline is not None
        assert self._slot is not None
        try:
            while not self._stop_event.is_set():
                frame = self._slot.take()
                if frame is None:
                    continue
                result = self._pipeline.run_frame(frame)
                self._last_result = result
                self._processed += 1
                now = time.monotonic()
                if now - self._last_result_emit_at >= RESULT_EMIT_INTERVAL_S:
                    self._last_result_emit_at = now
                    self.result_ready.emit(result)
                self._emit_stats_if_due()
        except Exception as error:
            if not self._stop_event.is_set():
                self.failed.emit(f"逐帧处理失败: {error}")
                self._stop_event.set()

    def _emit_stats_if_due(self, force: bool = False) -> None:
        now = time.monotonic()
        with self._stats_lock:
            if not force and now - self._last_stats_emit_at < STATS_EMIT_INTERVAL_S:
                return
            self._last_stats_emit_at = now
        elapsed = max(now - self._started_at, 1e-9)
        result = self._last_result
        self.stats_updated.emit(
            {
                "capture_fps": self._captured / elapsed,
                "process_fps": self._processed / elapsed,
                "captured": self._captured,
                "processed": self._processed,
                "camera_gaps": self._camera_gaps,
                "queue_overwrites": self._slot.overwritten if self._slot else 0,
                "processing_ms": result.total_ms if result is not None else 0.0,
            }
        )
