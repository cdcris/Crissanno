# ServeScan

A touch-friendly Tkinter camera recorder designed for a Raspberry Pi 5 with a
7-inch, 1024×600 display.

## Raspberry Pi setup

Connect a UVC-compatible USB webcam before launching ServeScan. OpenCV handles
the USB camera, video encoding, and capture while Pillow renders the preview.

```bash
sudo apt update
sudo apt install -y python3-opencv python3-pil.imagetk
python3 main.py
```

For a USB camera or desktop development, install the Python dependencies in a
virtual environment:

```bash
python -m pip install -r requirements.txt
python main.py
```

Press **Capture** to begin, use the same button to pause/resume, and press
**Stop & Save** to finalize the recording. Videos are saved under `captures/`
using a timestamp such as `2026-09-04_14-32-08.mp4`. Space toggles
capture/pause/resume; Escape stops and saves. Press F11 to enter or leave
full-screen mode on the 7-inch display.

Saved captures automatically play at 0.50× speed (2× slow motion). Every
captured frame retains the horizontal reference line and its selected point,
then object-detection boxes and labels are added using the bundled NCNN model.
Processing follows that priority, so a detection error does not prevent the
line or slow-motion video from being saved.

The interface starts in **Capture Mode**, where the Capture and Stop & Save
controls are available. Select **Upload Mode** to show the separate Upload
Video control, which accepts MP4, AVI, MOV, MKV, M4V, or WebM files. Use the
same mode switch to return to camera capture.

An uploaded video plays in the main preview in place of the live camera, with
the same object-detection boxes, labels, and horizontal reference line applied
to each frame. The processed video is also saved automatically under
`captures/` at the configured 0.50× slow-motion speed. Detection runs in the
background so the preview remains responsive, and the status line reports its
percentage and frame-count progress. Camera capture controls are unavailable
in Upload Mode, while the reference line can still be repositioned.

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
python -m unittest -v tests.test_capture
python -m unittest -v tests.test_capture.VideoRecorderTests.test_start_pause_write_resume_and_stop
```

On a Raspberry Pi where Python is exposed as `python3`, replace `python` with
`python3`. A successful run ends with `OK`; failures include the test name and
traceback. The GUI can also be smoke-tested manually with `python main.py`.

## Code structure

ServeScan uses a small feature-first architecture. Start reading at `main.py`,
then `app.py`. The application shell connects the features but leaves their
implementation to focused classes:

```text
main.py                  Start the process and catch fatal errors
app.py                   Connect UI events to feature controllers
config.py                Application settings and project paths

capture/controller.py    Decide when capture starts, pauses, and stops
capture/worker.py        Read camera frames on a background thread
capture/recorder.py      Write processed frames to a video file
capture/frame_processor.py
                         Draw the marker and run object detection
capture/camera.py        Access the USB camera

upload/controller.py     Select and preview uploaded videos
detection/detector.py    Load YOLO and annotate frames
marker/model.py          Convert and format marker coordinates
marker/store.py          Save marker coordinates as JSON
ui/window.py             Build and update the main window
ui/touch_button.py       Draw the custom touch button
ui/theme.py              Colors and fonts
shared/errors.py         Application-specific errors
shared/error_log.py      Rotating exception log
```

The dependency rule is `UI -> controller -> hardware/storage`. Hardware and
storage modules never update Tkinter widgets. Each class should have one simple
answer to “What is this responsible for?”

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
