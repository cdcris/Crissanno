"""OpenCV-backed USB camera source for ServeScan."""

from __future__ import annotations

import sys

try:
    import cv2
except ImportError:
    cv2 = None

from camera_source import CameraSource


CAMERA_INDEX = 0


class USBCameraSource(CameraSource):
    """Read RGB frames from a USB camera through OpenCV."""

    name = "USB Camera"

    def __init__(self, size: tuple[int, int], fps: int, index: int = CAMERA_INDEX) -> None:
        if cv2 is None:
            raise RuntimeError("OpenCV is not installed")

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
            raise RuntimeError(f"No USB camera was found at index {index}")

    def read_rgb(self):
        ok, frame = self.camera.read()
        if not ok:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def close(self) -> None:
        self.camera.release()


def open_usb_camera(size: tuple[int, int], fps: int) -> CameraSource:
    """Open the primary USB camera."""
    try:
        return USBCameraSource(size, fps)
    except Exception as exc:
        raise RuntimeError(f"USB camera: {exc}") from exc
