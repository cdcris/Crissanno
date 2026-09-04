# ServeScan

A touch-friendly Tkinter camera recorder designed for a Raspberry Pi 5 with a
7-inch, 1024×600 display.

## Raspberry Pi setup

Connect a UVC-compatible USB webcam before launching ServeScan. OpenCV handles
the USB camera, video encoding, and capture while Pillow renders the preview.

```bash
sudo apt update
sudo apt install -y python3-opencv python3-pil.imagetk
python3 servescan.py
```

For a USB camera or desktop development, install the Python dependencies in a
virtual environment:

```bash
python -m pip install -r requirements.txt
python servescan.py
```

Press **Capture** to begin, use the same button to pause/resume, and press
**Stop & Save** to finalize the recording. Videos are saved under `captures/`
using a timestamp such as `2026-09-04_14-32-08.mp4`. Space toggles
capture/pause/resume; Escape stops and saves. Press F11 to enter or leave
full-screen mode on the 7-inch display.

Click anywhere inside the camera preview to place the horizontal reference
line. Its position is shown as native camera coordinates (`x`, `y`) and is
saved to `marker_position.json`, so it is restored the next time ServeScan
starts. The line and its selected point are also drawn into every saved video
frame; moving the line while recording updates subsequent frames.

## Run the automated tests manually

The test suite uses Python's built-in `unittest` runner and fake camera/video
objects, so a physical camera is not required. From the project directory run:

```bash
python -m unittest discover -s tests -v
```

To run one test file or one individual test:

```bash
python -m unittest -v tests.test_camera
python -m unittest -v tests.test_camera.CameraWorkerTests.test_start_pause_resume_and_stop_recording
```

On a Raspberry Pi where Python is exposed as `python3`, replace `python` with
`python3`. A successful run ends with `OK`; failures include the test name and
traceback. The GUI can also be smoke-tested manually with `python servescan.py`.

## Error log

ServeScan records handled and unexpected exceptions in
`logs/servescan-error.log`. Each entry contains the timestamp, error type,
context, message, and Python traceback. The log rotates at approximately 1 MB
and keeps three older files (`.log.1` through `.log.3`) so it cannot grow
without limit. Include these files when diagnosing an exception-driven app
closure. A forced power-off or operating-system process kill cannot be logged
because Python does not get an opportunity to handle those events.

View the current log manually with:

```bash
python -c "from error_log import ERROR_LOG_PATH; print(ERROR_LOG_PATH.read_text(encoding='utf-8'))"
```
