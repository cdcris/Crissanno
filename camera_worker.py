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
from error_log import ErrorLog
from errors import CameraError, ErrorHandler, RecordingError
from usb_camera_source import open_usb_camera


class CameraWorker:
    """Read camera frames away from Tk's UI thread."""

    def __init__(
        self,
        size: tuple[int, int],
        fps: int,
        error_log: ErrorLog | None = None,
        playback_speed: float = 0.5,
        detector=None,
    ) -> None:
        if playback_speed <= 0:
            raise ValueError("Playback speed must be greater than zero.")
        self.size = size
        self.fps = fps
        self.playback_speed = playback_speed
        self.detector = detector
        self.detection_error = ""
        self.source: Optional[CameraSource] = None
        self.error = ""
        self.errors = ErrorHandler(error_log=error_log)
        self._frame = None
        self._frame_number = 0
        self._lock = threading.Lock()
        self._record_lock = threading.Lock()
        self._stop = threading.Event()
        self._writer = None
        self._recording = False
        self._marker_position: Optional[tuple[int, int]] = None
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
                        video_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        # Preserve capture priorities: draw the reference first;
                        # slow motion is set on the writer; detection comes last.
                        if self._marker_position is not None:
                            self._draw_recording_marker(video_frame, self._marker_position)
                        if self.detector is not None:
                            try:
                                video_frame = self.detector.annotate(video_frame)
                            except Exception as error:
                                self.detection_error = str(error)
                                self.errors.handle(error, "Object detection error")
                                self.detector = None
                        self._writer.write(video_frame)
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
        with self._lock:
            return self._frame_number, self._frame

    def _draw_recording_marker(self, frame, position: tuple[int, int]) -> None:
        """Draw the preview marker onto a BGR video frame in place."""
        marker_x, marker_y = position
        height, width = frame.shape[:2]
        video_x = min(width - 1, max(0, round(marker_x * width / self.size[0])))
        video_y = min(height - 1, max(0, round(marker_y * height / self.size[1])))
        cv2.line(frame, (0, video_y), (width - 1, video_y), (28, 38, 218), 4)
        cv2.circle(frame, (video_x, video_y), 6, (255, 255, 255), -1)
        cv2.circle(frame, (video_x, video_y), 6, (28, 38, 218), 2)

    def start_recording(self, capture_dir: Path) -> Path:
        """Start a timestamped recording or raise ``RecordingError``."""
        if cv2 is None:
            raise RecordingError("Install python3-opencv to record video.")
        _, frame = self.latest()
        if frame is None:
            raise RecordingError("The camera has not supplied a frame yet.")

        try:
            capture_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise RecordingError(f"Could not create the capture directory: {error}") from error
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
            try:
                output_fps = self.fps * self.playback_speed
                writer = cv2.VideoWriter(
                    str(path), cv2.VideoWriter_fourcc(*codec), output_fps, (width, height)
                )
            except Exception as error:
                raise RecordingError(f"Could not initialize the video writer: {error}") from error
            if writer.isOpened():
                with self._record_lock:
                    self._writer = writer
                    self._recording = True
                    self.output_path = path
                return path
            writer.release()
        raise RecordingError("ServeScan could not create an MP4 or AVI video file.")

    def set_recording(self, recording: bool) -> None:
        with self._record_lock:
            self._recording = recording and self._writer is not None

    def set_marker_position(self, position: Optional[tuple[int, int]]) -> None:
        """Set the camera-space marker burned into subsequently recorded frames."""
        with self._record_lock:
            self._marker_position = position

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
