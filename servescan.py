"""Executable entry point for the ServeScan camera interface."""

import sys

from app import ServeScanApp
from error_log import get_error_log
from errors import ErrorHandler


def main() -> int:
    """Run ServeScan behind a final exception boundary."""
    error_log = get_error_log()
    error_log.install_global_hooks()
    errors = ErrorHandler(
        lambda title, message: print(f"{title}: {message}", file=sys.stderr),
        error_log,
    )
    try:
        ServeScanApp().mainloop()
    except Exception as error:
        errors.handle(error, "ServeScan failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
