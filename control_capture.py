"""Control capture start, pause, resume, and stop state for ServeScan."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from camera_worker import CameraWorker
from errors import ErrorHandler


class CaptureController:
    """Own the recording state machine independently of the app shell."""

    READY = "ready"
    RECORDING = "recording"
    PAUSED = "paused"

    def __init__(
        self,
        camera: CameraWorker,
        errors: ErrorHandler,
        capture_dir: Path,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.camera = camera
        self.errors = errors
        self.capture_dir = capture_dir
        self.clock = clock
        self.state = self.READY
        self.recorded_seconds = 0.0
        self.segment_started = 0.0

    def toggle(self, *, frame_available: bool) -> bool | str:
        """Start, pause, or resume capture."""
        if not frame_available:
            return "Waiting for a camera frame..."

        if self.state == self.READY:
            try:
                self.camera.start_recording(self.capture_dir)
            except Exception as error:
                self.errors.handle(error, "Recording error")
                return False
            self.recorded_seconds = 0.0
            self.segment_started = self.clock()
            self.state = self.RECORDING
        elif self.state == self.RECORDING:
            self.recorded_seconds += self.clock() - self.segment_started
            self.camera.set_recording(False)
            self.state = self.PAUSED
        else:
            self.segment_started = self.clock()
            self.camera.set_recording(True)
            self.state = self.RECORDING
        return True

    def elapsed(self) -> float:
        if self.state == self.RECORDING:
            return self.recorded_seconds + self.clock() - self.segment_started
        return self.recorded_seconds

    def stop(self) -> Path | None:
        """Finalize the current recording and reset capture state."""
        if self.state == self.READY:
            return None
        if self.state == self.RECORDING:
            self.recorded_seconds += self.clock() - self.segment_started
        saved_path = self.camera.stop_recording()
        self.state = self.READY
        self.recorded_seconds = 0.0
        self.segment_started = 0.0
        return saved_path
