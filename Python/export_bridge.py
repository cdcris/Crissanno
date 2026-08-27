"""Qt bridge for the Ultralytics YOLO dataset exporter."""

from pathlib import Path

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QFileDialog

from yolo_exporter import FORMAT_NAME, export_dataset


class DatasetExporter(QObject):
    """Expose a native save dialog and dataset export operation to QML."""

    @Slot("QVariant", result="QVariant")
    def exportUltralyticsYoloDetection(self, payload):  # noqa: N802
        archive_name, _ = QFileDialog.getSaveFileName(
            None,
            f"Export {FORMAT_NAME}",
            "crissanno-ultralytics-yolo-detection.zip",
            "ZIP archives (*.zip)",
        )
        if not archive_name:
            return {"ok": False, "cancelled": True}
        try:
            return export_dataset(Path(archive_name), dict(payload))
        except (OSError, TypeError, ValueError) as error:
            return {"ok": False, "cancelled": False, "error": str(error)}
