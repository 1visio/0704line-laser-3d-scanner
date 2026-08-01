"""Two-thread online acquisition/processing controller for the Qt UI."""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, Signal

from .models import CameraSession, FrameResult
from .pipeline import FramePipeline
from .recording import FrameRecorder
from .runtime import LatestFrameSlot


class OnlineController(QObject):
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
        self._captured = 0
        self._processed = 0
        self._camera_gaps = 0
        self._last_camera_frame: int | None = None
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
            self._running = True
        self._session = session
        self._pipeline = pipeline
        self._recorder = recorder
        self._slot = LatestFrameSlot()
        self._stop_event.clear()
        self._captured = self._processed = self._camera_gaps = 0
        self._last_camera_frame = None
        self._started_at = time.monotonic()
        session.start()
        self._acquisition_thread = threading.Thread(
            target=self._acquire_loop, name="camera-acquisition", daemon=True
        )
        self._processing_thread = threading.Thread(
            target=self._process_loop, name="frame-processing", daemon=True
        )
        self._acquisition_thread.start()
        self._processing_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._slot is not None:
            self._slot.close()
        for thread in (self._acquisition_thread, self._processing_thread):
            if thread is not None and thread is not threading.current_thread():
                thread.join(3.0)
        if self._session is not None:
            try:
                self._session.stop()
            except Exception as error:
                self.failed.emit(str(error))
        with self._lock:
            was_running = self._running
            self._running = False
        if was_running:
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
                self.result_ready.emit(result)
                self._emit_stats_if_due(force=True)
        except Exception as error:
            if not self._stop_event.is_set():
                self.failed.emit(f"逐帧处理失败: {error}")
                self._stop_event.set()

    def _emit_stats_if_due(self, force: bool = False) -> None:
        elapsed = max(time.monotonic() - self._started_at, 1e-9)
        if not force and self._captured % 10:
            return
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
