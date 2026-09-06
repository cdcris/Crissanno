"""Background camera reader for ServeScan."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from capture.camera import CameraSource, open_usb_camera
from shared.error_log import ErrorLog
from shared.errors import CameraError, ErrorHandler


class CameraWorker:
    """Read camera frames away from Tk's UI thread."""

    def __init__(
        self,
        size: tuple[int, int],
        fps: int,
        error_log: ErrorLog | None = None,
        *,
        on_frame: Callable[[object], None] | None = None,
    ) -> None:
        self.size = size
        self.fps = fps
        self.on_frame = on_frame
        self.source: CameraSource | None = None
        self.error = ""
        self.errors = ErrorHandler(error_log=error_log)
        self._frame = None
        self._frame_number = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        try:
            self.source = open_usb_camera(self.size, self.fps)
            while not self._stop.is_set():
                frame = self.source.read_rgb()
                if frame is None:
                    time.sleep(0.03)
                    continue
                with self._lock:
                    self._frame = frame
                    self._frame_number += 1
                if self.on_frame is not None:
                    self.on_frame(frame)
        except CameraError as error:
            self.error = str(error)
            self.errors.handle(error, "Camera worker error")
        except Exception as error:
            self.error = f"Unexpected camera error: {error}"
            self.errors.handle(error, "Camera worker error")
        finally:
            if self.source is not None:
                try:
                    self.source.close()
                except Exception as error:
                    self.errors.handle(error, "Camera cleanup error")
                    if not self.error:
                        self.error = f"Could not close camera: {error}"

    def latest(self):
        """Return the latest frame number and RGB frame."""
        with self._lock:
            return self._frame_number, self._frame

    def stop(self) -> None:
        """Ask the reader thread to stop and release its camera."""
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.5)
