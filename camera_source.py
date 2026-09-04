"""Camera source interface for ServeScan."""


class CameraSource:
    """Small interface for an RGB camera source."""

    name = "Camera"

    def read_rgb(self):
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
