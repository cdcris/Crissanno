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
