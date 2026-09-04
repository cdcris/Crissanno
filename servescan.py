"""Executable entry point for the ServeScan camera interface."""

from app import ServeScanApp


def main() -> None:
    ServeScanApp().mainloop()


if __name__ == "__main__":
    main()
