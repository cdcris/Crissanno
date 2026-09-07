import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import detection.detector as detector_module
from detection.detector import ObjectDetector


class ObjectDetectorTests(unittest.TestCase):
    def test_loads_model_lazily_and_returns_plotted_frame(self):
        result = Mock()
        result.plot.return_value = "annotated"
        model = Mock()
        model.predict.return_value = [result]
        detector = ObjectDetector(Path("model"), confidence=0.4)

        with patch.object(detector_module, "load_model", return_value=model) as load:
            self.assertEqual(detector.annotate("frame-1"), "annotated")
            self.assertEqual(detector.annotate("frame-2"), "annotated")

        load.assert_called_once_with(Path("model"))
        model.predict.assert_called_with(
            source="frame-2", conf=0.4, verbose=False
        )

    def test_returns_original_frame_when_model_has_no_result(self):
        model = Mock()
        model.predict.return_value = []
        detector = ObjectDetector()
        detector.model = model

        self.assertEqual(detector.annotate("original"), "original")


if __name__ == "__main__":
    unittest.main()
