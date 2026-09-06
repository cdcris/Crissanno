"""Video-file recording independent of camera acquisition and UI state."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

try:
    import cv2
except ImportError:
    cv2 = None

from capture.frame_processor import FrameProcessor
from shared.errors import RecordingError


class VideoRecorder:
    """Own the OpenCV writer used to save processed camera frames."""

    def __init__(
        self,
        fps: int,
        playback_speed: float,
        frame_processor: FrameProcessor,
    ) -> None:
        if playback_speed <= 0:
            raise ValueError("Playback speed must be greater than zero.")
        self.fps = fps
        self.playback_speed = playback_speed
        self.frame_processor = frame_processor
        self.output_path: Path | None = None
        self._writer = None
        self._recording = False
        self._lock = threading.Lock()

    def start(self, capture_dir: Path, first_frame) -> Path:
        """Start a timestamped recording or raise ``RecordingError``."""
        if cv2 is None:
            raise RecordingError("Install python3-opencv to record video.")
        if first_frame is None:
            raise RecordingError("The camera has not supplied a frame yet.")

        try:
            capture_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise RecordingError(
                f"Could not create the capture directory: {error}"
            ) from error

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        height, width = first_frame.shape[:2]
        candidates = [
            (capture_dir / f"{timestamp}.mp4", "mp4v"),
            (capture_dir / f"{timestamp}.avi", "MJPG"),
        ]
        for base_path, codec in candidates:
            path = self._unused_path(base_path)
            try:
                writer = cv2.VideoWriter(
                    str(path),
                    cv2.VideoWriter_fourcc(*codec),
                    self.fps * self.playback_speed,
                    (width, height),
                )
            except Exception as error:
                raise RecordingError(
                    f"Could not initialize the video writer: {error}"
                ) from error
            if writer.isOpened():
                with self._lock:
                    self._writer = writer
                    self._recording = True
                    self.output_path = path
                return path
            writer.release()
        raise RecordingError("ServeScan could not create an MP4 or AVI video file.")

    @staticmethod
    def _unused_path(base_path: Path) -> Path:
        """Return *base_path* or the first unused numbered variation."""
        path = base_path
        sequence = 1
        while path.exists():
            path = base_path.with_name(
                f"{base_path.stem}_{sequence:03d}{base_path.suffix}"
            )
            sequence += 1
        return path

    def write(self, rgb_frame) -> None:
        """Process and save one frame when recording is active."""
        with self._lock:
            if not self._recording or self._writer is None:
                return
            self._writer.write(self.frame_processor.process(rgb_frame))

    def set_recording(self, recording: bool) -> None:
        """Pause or resume writes without closing the output file."""
        with self._lock:
            self._recording = recording and self._writer is not None

    def stop(self) -> Path | None:
        """Close the current file and return its path."""
        with self._lock:
            self._recording = False
            if self._writer is not None:
                self._writer.release()
                self._writer = None
            path = self.output_path
            self.output_path = None
            return path
