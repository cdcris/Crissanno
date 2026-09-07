from pathlib import Path
from typing import Any

try:
    from ultralytics import YOLO
except ImportError:  # Keep the recorder usable when detection is unavailable.
    YOLO = None


from config import MODEL_DIR

CONFIDENCE = 0.25


def load_model(model_dir: Path) -> Any:
    """Validate and load the exported NCNN model."""
    if YOLO is None:
        raise RuntimeError(
            "Object detection requires the 'ultralytics' Python package."
        )
    if not model_dir.is_dir():
        raise FileNotFoundError(
            f"NCNN model directory not found: {model_dir}\n"
            "Ensure the model has been exported and its directory ends "
            "with '_ncnn_model'."
        )

    try:
        print(f"Loading model: {model_dir}")
        model = YOLO(str(model_dir), task="detect")
        print("Model loaded successfully.")
        return model
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load NCNN model from: {model_dir}"
        ) from exc


class ObjectDetector:
    """Lazily load YOLO and annotate BGR video frames."""

    def __init__(
        self,
        model_dir: Path = MODEL_DIR,
        confidence: float = CONFIDENCE,
    ) -> None:
        self.model_dir = model_dir
        self.confidence = confidence
        self.model = None

    def annotate(self, frame):
        """Return a frame with detected objects boxed and labelled."""
        if self.model is None:
            self.model = load_model(self.model_dir)

        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            verbose=False,
        )
        if not results:
            return frame
        return results[0].plot()
