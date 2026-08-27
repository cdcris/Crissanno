import os
import sys
from pathlib import Path

from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from export_bridge import DatasetExporter

# Import here the Python files that define QML elements


def main():
    project_root = Path(__file__).resolve().parent.parent
    os.environ["QT_QUICK_CONTROLS_CONF"] = str(
        project_root / "qtquickcontrols2.conf"
    )
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()
    dataset_exporter = DatasetExporter()
    engine.rootContext().setContextProperty("datasetExporter", dataset_exporter)
    engine.warnings.connect(lambda warnings: [print("[QML WARNING]", w.toString()) for w in warnings])
    if "__compiled__" in globals():
        import autogen.resources  # noqa: F401

        engine.addImportPath(":/")
        engine.load(":/CrissannoContent/App.qml")
    else:
        engine.addImportPath(str(project_root))
        engine.load(str(project_root / "CrissannoContent" / "App.qml"))
    if not engine.rootObjects():
        sys.exit(-1)
    ex = app.exec()
    del engine
    return ex



if __name__ == "__main__":
    sys.exit(main())
