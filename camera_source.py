"""Camera source interface for ServeScan."""

from abc import ABC, abstractmethod


class CameraSource(ABC):
    """Small interface for an RGB camera source."""

    name = "Camera"

    @abstractmethod
    def read_rgb(self):
        """Return the next RGB frame, or ``None`` when no frame is ready."""

    @abstractmethod
    def close(self) -> None:
        """Release resources owned by the source."""
