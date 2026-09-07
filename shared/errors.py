"""Typed exceptions and centralized error handling for ServeScan."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import TypeVar

from shared.error_log import ErrorLog


class ServeScanError(Exception):
    """Base class for errors that ServeScan can present to a user."""


class CameraError(ServeScanError):
    """Base class for camera-related failures."""


class CameraOpenError(CameraError):
    """Raised when a camera cannot be initialized."""


class CameraReadError(CameraError):
    """Raised when a camera frame cannot be converted or read."""


class RecordingError(ServeScanError):
    """Raised when recording cannot be started or written."""


class MarkerStorageError(ServeScanError):
    """Raised when the marker position cannot be persisted."""


T = TypeVar("T")


class ErrorHandler:
    """Object-oriented exception boundary shared by UI actions.

    ``reporter`` is deliberately injected so the application can use a Tk
    dialog while tests and command-line entry points can use another target.
    """

    def __init__(
        self,
        reporter: Callable[[str, str], None] | None = None,
        error_log: ErrorLog | None = None,
    ) -> None:
        self.reporter = reporter
        self.error_log = error_log
        self.last_error = ""

    def handle(
        self,
        error: Exception,
        title: str = "ServeScan error",
        error_traceback: TracebackType | None = None,
    ) -> str:
        """Record, report, and return a safe message for *error*."""
        if isinstance(error, ServeScanError):
            message = str(error)
        else:
            message = f"Unexpected error: {error}"
        self.last_error = message
        if self.error_log is not None:
            self.error_log.write(error, title, error_traceback)
        if self.reporter is not None:
            self.reporter(title, message)
        return message

    def protect(
        self,
        action: Callable[[], T],
        *,
        title: str = "ServeScan error",
        fallback: T | None = None,
    ) -> T | None:
        """Run an action and route any exception through this handler."""
        try:
            return action()
        except Exception as error:
            self.handle(error, title)
            return fallback
