"""Application settings kept in one easy-to-find place."""

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent

APP_TITLE = "ServeScan"
WINDOW_SIZE = "1024x600"

CAMERA_SIZE = (1280, 720)
CAMERA_FPS = 30
SLOW_MOTION_SPEED = 0.5

CAPTURE_DIR = PROJECT_DIR / "captures"
MARKER_PATH = PROJECT_DIR / "marker_position.json"
MODEL_DIR = PROJECT_DIR / "yolo26n_ncnn_model"
