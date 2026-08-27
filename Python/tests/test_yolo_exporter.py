import sys
import unittest
import zipfile
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))

from yolo_exporter import export_dataset  # noqa: E402


class YoloExporterTests(unittest.TestCase):
    def test_writes_cvat_compatible_detection_archive(self):
        root = Path(__file__).resolve().parents[2]
        image_path = next((root / "Images").glob("*.jpg"))
        archive_path = Path(__file__).parent / "_test_dataset.zip"
        try:
            result = export_dataset(
                archive_path,
                {
                    "classes": [
                        {"classId": "class0", "label": "A"},
                        {"classId": "class1", "label": "B"},
                    ],
                    "images": [
                        {
                            "source": image_path.as_uri(),
                            "name": "sample image.jpg",
                            "canvasWidth": 200,
                            "canvasHeight": 100,
                            "annotations": [
                                {
                                    "classId": "class1",
                                    "shape": "box",
                                    "boxX": 20,
                                    "boxY": 10,
                                    "boxW": 80,
                                    "boxH": 40,
                                },
                                {"classId": "class0", "shape": "polygon"},
                            ],
                        }
                    ],
                },
            )

            self.assertEqual(result["images"], 1)
            self.assertEqual(result["boxes"], 1)
            self.assertEqual(result["skipped"], 1)
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(
                    archive.read("labels/train/sample image.txt").decode(),
                    "1 0.300000 0.300000 0.400000 0.400000\n",
                )
                self.assertEqual(
                    archive.read("train.txt").decode(),
                    "images/train/sample image.jpg\n",
                )
                self.assertIn('  0: "A"', archive.read("data.yaml").decode())
        finally:
            archive_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
