"""Persistence object for the preview reference marker."""

from __future__ import annotations

import json
from pathlib import Path

from marker.model import FrameSize, MarkerPosition
from shared.errors import MarkerStorageError


class MarkerStore:
    """Load and save a marker while keeping file handling outside the UI."""

    def __init__(self, path: Path, frame_size: FrameSize) -> None:
        self.path = path
        self.frame_size = frame_size

    def load(self) -> MarkerPosition | None:
        """Return a valid saved position, or ``None`` for absent/invalid data."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            x, y = int(data["x"]), int(data["y"])
        except FileNotFoundError:
            return None
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None
        except OSError as error:
            raise MarkerStorageError(f"Could not read line position: {error}") from error

        width, height = self.frame_size
        return (x, y) if 0 <= x < width and 0 <= y < height else None

    def save(self, position: MarkerPosition) -> None:
        """Persist *position*, raising a domain error if writing fails."""
        x, y = position
        try:
            self.path.write_text(
                json.dumps({"x": x, "y": y}, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            raise MarkerStorageError(f"Could not save line position: {error}") from error
