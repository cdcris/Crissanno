"""Frame decorations applied before a captured frame is saved."""

from __future__ import annotations

try:
    import cv2
except ImportError:
    cv2 = None

from marker.model import FrameSize, MarkerPosition
from shared.error_log import ErrorLog
from shared.errors import ErrorHandler


class FrameProcessor:
    """Convert, mark, and detect one frame in a predictable order."""

    def __init__(
        self,
        camera_size: FrameSize,
        *,
        detector=None,
        error_log: ErrorLog | None = None,
    ) -> None:
        self.camera_size = camera_size
        self.detector = detector
        self.errors = ErrorHandler(error_log=error_log)
        self.marker_position: MarkerPosition | None = None
        self.detection_error = ""

    def set_marker(self, position: MarkerPosition | None) -> None:
        """Set the marker drawn on future frames."""
        self.marker_position = position

    def process(self, rgb_frame):
        """Return a BGR frame with marker and optional detections applied."""
        if cv2 is None:
            return rgb_frame

        video_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        if self.marker_position is not None:
            self._draw_marker(video_frame, self.marker_position)

        if self.detector is not None:
            try:
                video_frame = self.detector.annotate(video_frame)
            except Exception as error:
                self.detection_error = str(error)
                self.errors.handle(error, "Object detection error")
                self.detector = None
        return video_frame

    def _draw_marker(self, frame, position: MarkerPosition) -> None:
        """Draw the horizontal reference marker on a BGR frame in place."""
        marker_x, marker_y = position
        height, width = frame.shape[:2]
        camera_width, camera_height = self.camera_size
        video_x = min(width - 1, max(0, round(marker_x * width / camera_width)))
        video_y = min(height - 1, max(0, round(marker_y * height / camera_height)))
        cv2.line(frame, (0, video_y), (width - 1, video_y), (28, 38, 218), 4)
        cv2.circle(frame, (video_x, video_y), 6, (255, 255, 255), -1)
        cv2.circle(frame, (video_x, video_y), 6, (28, 38, 218), 2)
