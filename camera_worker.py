"""Background frame reader and recording worker for ServeScan."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import cv2
except ImportError:
    cv2 = None

from camera_source import CameraSource
from usb_camera_source import open_usb_camera


class CameraWorker:
    """Read camera frames away from Tk's UI thread."""

    def __init__(self, size: tuple[int, int], fps: int) -> None:
        self.size = size
        self.fps = fps
        self.source: Optional[CameraSource] = None
        self.error = ""
        self._frame = None
        self._frame_number = 0
        self._lock = threading.Lock()
        self._record_lock = threading.Lock()
        self._stop = threading.Event()
        self._writer = None
        self._recording = False
        self.output_path: Optional[Path] = None
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
                with self._record_lock:
                    if self._recording and self._writer is not None and cv2 is not None:
                        self._writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        except Exception as exc:
            self.error = str(exc)
        finally:
            if self.source is not None:
                try:
                    self.source.close()
                except Exception:
                    pass

    def latest(self):
        with self._lock:
            return self._frame_number, self._frame

    def start_recording(self, capture_dir: Path) -> tuple[Optional[Path], str]:
        """Start a timestamped recording and return (path, error_message)."""
        if cv2 is None:
            return None, "Install python3-opencv to record video."
        _, frame = self.latest()
        if frame is None:
            return None, "The camera has not supplied a frame yet."

        capture_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        height, width = frame.shape[:2]
        candidates = [
            (capture_dir / f"{timestamp}.mp4", "mp4v"),
            (capture_dir / f"{timestamp}.avi", "MJPG"),
        ]
        for base_path, codec in candidates:
            path = base_path
            sequence = 1
            while path.exists():
                path = base_path.with_name(f"{base_path.stem}_{sequence:03d}{base_path.suffix}")
                sequence += 1
            writer = cv2.VideoWriter(
                str(path), cv2.VideoWriter_fourcc(*codec), self.fps, (width, height)
            )
            if writer.isOpened():
                with self._record_lock:
                    self._writer = writer
                    self._recording = True
                    self.output_path = path
                return path, ""
            writer.release()
        return None, "ServeScan could not create an MP4 or AVI video file."

    def set_recording(self, recording: bool) -> None:
        with self._record_lock:
            self._recording = recording and self._writer is not None

    def stop_recording(self) -> Optional[Path]:
        with self._record_lock:
            self._recording = False
            if self._writer is not None:
                self._writer.release()
                self._writer = None
            path = self.output_path
            self.output_path = None
            return path

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self.stop_recording()
