"""Capture workflow: start, pause, resume, and stop."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from capture.recorder import VideoRecorder
from capture.state import CaptureState
from shared.errors import ErrorHandler


class CaptureController:
    """Own recording decisions while leaving file writing to ``VideoRecorder``."""

    def __init__(
        self,
        recorder: VideoRecorder,
        errors: ErrorHandler,
        capture_dir: Path,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.recorder = recorder
        self.errors = errors
        self.capture_dir = capture_dir
        self.clock = clock
        self.state = CaptureState.READY
        self.recorded_seconds = 0.0
        self.segment_started = 0.0

    def toggle(self, *, current_frame) -> bool | str:
        """Start, pause, or resume capture."""
        if current_frame is None:
            return "Waiting for a camera frame..."

        if self.state is CaptureState.READY:
            try:
                self.recorder.start(self.capture_dir, current_frame)
            except Exception as error:
                self.errors.handle(error, "Recording error")
                return False
            self.recorded_seconds = 0.0
            self.segment_started = self.clock()
            self.state = CaptureState.RECORDING
        elif self.state is CaptureState.RECORDING:
            self.recorded_seconds += self.clock() - self.segment_started
            self.recorder.set_recording(False)
            self.state = CaptureState.PAUSED
        else:
            self.segment_started = self.clock()
            self.recorder.set_recording(True)
            self.state = CaptureState.RECORDING
        return True

    def elapsed(self) -> float:
        """Return seconds captured, excluding time spent paused."""
        if self.state is CaptureState.RECORDING:
            return self.recorded_seconds + self.clock() - self.segment_started
        return self.recorded_seconds

    def stop(self) -> Path | None:
        """Finalize the recording and return to the ready state."""
        if self.state is CaptureState.READY:
            return None
        if self.state is CaptureState.RECORDING:
            self.recorded_seconds += self.clock() - self.segment_started
        saved_path = self.recorder.stop()
        self.state = CaptureState.READY
        self.recorded_seconds = 0.0
        self.segment_started = 0.0
        return saved_path
