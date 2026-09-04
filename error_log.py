"""Persistent, rotating exception log for ServeScan."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import threading
import traceback
from types import TracebackType


ERROR_LOG_PATH = Path(__file__).with_name("logs") / "servescan-error.log"


class ErrorLog:
    """Write exception diagnostics without allowing logging to crash the app."""

    def __init__(
        self,
        path: Path = ERROR_LOG_PATH,
        *,
        max_bytes: int = 1_000_000,
        backup_count: int = 3,
    ) -> None:
        self.path = path
        self._logger: logging.Logger | None = None
        self._hooks_installed = False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            logger = logging.getLogger(f"servescan.error.{path.resolve()}")
            logger.setLevel(logging.ERROR)
            logger.propagate = False
            if not logger.handlers:
                handler = RotatingFileHandler(
                    path,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding="utf-8",
                )
                handler.setFormatter(
                    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
                )
                logger.addHandler(handler)
            self._logger = logger
        except Exception:
            # Error reporting must never become another reason for the app to exit.
            self._logger = None

    def write(
        self,
        error: BaseException,
        context: str,
        error_traceback: TracebackType | None = None,
    ) -> None:
        """Append an error type, context, message, and full traceback."""
        if self._logger is None:
            return
        try:
            trace = "".join(
                traceback.format_exception(
                    type(error), error, error_traceback or error.__traceback__
                )
            ).rstrip()
            self._logger.error(
                "%s | %s: %s\n%s",
                context,
                type(error).__name__,
                error,
                trace,
            )
            for handler in self._logger.handlers:
                handler.flush()
        except Exception:
            pass

    def install_global_hooks(self) -> None:
        """Log otherwise-uncaught errors from the main and worker threads."""
        if self._hooks_installed:
            return
        self._hooks_installed = True
        previous_sys_hook = sys.excepthook
        previous_thread_hook = threading.excepthook

        def system_hook(exc_type, exc_value, exc_traceback):
            self.write(exc_value, "Uncaught application exception", exc_traceback)
            previous_sys_hook(exc_type, exc_value, exc_traceback)

        def thread_hook(args):
            thread_name = args.thread.name if args.thread is not None else "unknown"
            self.write(
                args.exc_value,
                f"Uncaught thread exception ({thread_name})",
                args.exc_traceback,
            )
            previous_thread_hook(args)

        sys.excepthook = system_hook
        threading.excepthook = thread_hook


_default_error_log: ErrorLog | None = None


def get_error_log() -> ErrorLog:
    """Return the process-wide error log instance."""
    global _default_error_log
    if _default_error_log is None:
        _default_error_log = ErrorLog()
    return _default_error_log
