"""Recording states shared by the controller, application, and UI."""

from enum import Enum


class CaptureState(str, Enum):
    """Every valid state in the capture workflow."""

    READY = "ready"
    RECORDING = "recording"
    PAUSED = "paused"
