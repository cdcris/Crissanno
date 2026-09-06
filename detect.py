from pathlib import Path

import cv2
from ultralytics import YOLO


# Configuration
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "yolo26n_ncnn_model"
VIDEO_PATH = BASE_DIR / "vid" / "testR2.mp4"

CONFIDENCE = 0.25
FRAME_SKIP = 1
DISPLAY_WIDTH = 640
WINDOW_NAME = "Detector"


def load_model(model_dir: Path) -> YOLO:
    """Validate and load the exported NCNN model."""
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


def main() -> None:
    if not VIDEO_PATH.is_file():
        raise FileNotFoundError(f"Video file not found: {VIDEO_PATH}")

    model = load_model(MODEL_DIR)
    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    frame_count = 0

    try:
        print(
            "Detector started.\n"
            "A detected frame will pause automatically.\n"
            "Press any key to continue, or 'q' to quit."
        )

        while True:
            ret, frame = cap.read()

            if not ret:
                print("Video finished.")
                break

            frame_count += 1
            detection_found = False
            frame_to_show = frame

            if frame_count % FRAME_SKIP == 0:
                results = model.predict(
                    source=frame,
                    conf=CONFIDENCE,
                    verbose=False,
                )

                result = results[0]
                detection_found = (
                    result.boxes is not None and len(result.boxes) > 0
                )
                frame_to_show = result.plot()

            height, width = frame_to_show.shape[:2]
            display_height = round(height * DISPLAY_WIDTH / width)

            display_frame = cv2.resize(
                frame_to_show,
                (DISPLAY_WIDTH, display_height),
                interpolation=cv2.INTER_AREA,
            )

            if detection_found:
                cv2.putText(
                    display_frame,
                    "DETECTED - Press any key to continue",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

            cv2.imshow(WINDOW_NAME, display_frame)

            # Pause  
            delay_ms = 3000 if detection_found else 1
            key = cv2.waitKey(delay_ms) & 0xFF

            if key == ord("q"):
                break


    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()