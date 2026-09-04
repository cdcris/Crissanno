"""OpenCV-backed USB camera source for ServeScan."""

from __future__ import annotations

import sys

try:
    import cv2
except ImportError:
    cv2 = None

from camera_source import CameraSource
from errors import CameraOpenError, CameraReadError


CAMERA_INDEX = 0


class USBCameraSource(CameraSource):
    """Read RGB frames from a USB camera through OpenCV."""

    name = "USB Camera"

    def __init__(self, size: tuple[int, int], fps: int, index: int = CAMERA_INDEX) -> None:
        if cv2 is None:
            raise CameraOpenError("OpenCV is not installed")

        try:
            preferred_api = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_DSHOW
            self.camera = cv2.VideoCapture(index, preferred_api)
            if not self.camera.isOpened():
                self.camera.release()
                self.camera = cv2.VideoCapture(index)

            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
            self.camera.set(cv2.CAP_PROP_FPS, fps)
            if not self.camera.isOpened():
                self.camera.release()
                raise CameraOpenError(f"No USB camera was found at index {index}")
        except CameraOpenError:
            raise
        except Exception as error:
            if hasattr(self, "camera"):
                self.camera.release()
            raise CameraOpenError(f"Could not initialize USB camera: {error}") from error

    def read_rgb(self):
        try:
            ok, frame = self.camera.read()
            if not ok:
                return None
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception as error:
            raise CameraReadError(f"Could not read USB camera frame: {error}") from error

    def close(self) -> None:
        self.camera.release()


def open_usb_camera(size: tuple[int, int], fps: int) -> CameraSource:
    """Open the primary USB camera."""
    return USBCameraSource(size, fps)
