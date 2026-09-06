"""Application logic and camera workflow for ServeScan."""

from __future__ import annotations

import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import cv2
except ImportError:
    cv2 = None

from app_ui import ServeScanUI
from camera_worker import CameraWorker
from error_log import get_error_log
from errors import ErrorHandler
from marker_store import MarkerStore


APP_TITLE = "ServeScan"
WINDOW_SIZE = "1024x600"
CAMERA_SIZE = (1280, 720)
CAMERA_FPS = 30
MARKER_PATH = Path(__file__).with_name("marker_position.json")


class ServeScanApp(tk.Tk):
    READY = "ready"
    RECORDING = "recording"
    PAUSED = "paused"

    def __init__(self) -> None:
        super().__init__()
        self.error_log = get_error_log()
        self.errors = ErrorHandler(messagebox.showerror, self.error_log)
        self.marker_store = MarkerStore(MARKER_PATH, CAMERA_SIZE)
        self.state_name = self.READY
        self.recorded_seconds = 0.0
        self.segment_started = 0.0
        self.last_frame_number = -1
        self.last_rgb_frame = None
        self.marker_position = self.errors.protect(self.marker_store.load)
        self.selected_video_path: Path | None = None
        self.upload_capture = None
        self.upload_after_id = None
        self.upload_rgb_frame = None
        self.upload_size = CAMERA_SIZE
        self.upload_fps = CAMERA_FPS
        self.camera_reported = False
        self.closing = False

        self.ui = ServeScanUI(
            self,
            title=APP_TITLE,
            window_size=WINDOW_SIZE,
            camera_size=CAMERA_SIZE,
            camera_fps=CAMERA_FPS,
            marker_position=self.marker_position,
            on_upload_video=self.upload_video,
            on_mode_changed=self._on_feature_mode_changed,
            on_toggle_capture=self.toggle_capture,
            on_stop_capture=self.stop_capture,
            on_marker_click=self._set_marker_position,
        )
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<space>", lambda _event: self.toggle_capture())
        self.bind("<Escape>", lambda _event: self.stop_capture())
        self.bind("<F11>", self._toggle_fullscreen)

        self.camera = CameraWorker(CAMERA_SIZE, CAMERA_FPS, self.error_log)
        self.camera.set_marker_position(self.marker_position)
        self.camera.start()
        self.after(40, self._update_preview)
        self.after(200, self._update_elapsed)

    def upload_video(self) -> None:
        """Let the user choose an existing video for the next processing step."""
        selected = filedialog.askopenfilename(
            parent=self,
            title="Upload video",
            filetypes=(
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.m4v *.webm"),
                ("All files", "*.*"),
            ),
        )
        if not selected:
            return
        selected_path = Path(selected)
        try:
            self._start_uploaded_video(selected_path)
        except Exception as error:
            self.errors.handle(error, "Video upload error")
            return
        self.selected_video_path = selected_path
        self.ui.set_detail(f"Playing • {selected_path.name}")

    def _on_feature_mode_changed(self, mode: str) -> None:
        if mode == "upload":
            if self.selected_video_path is not None:
                try:
                    self._start_uploaded_video(self.selected_video_path)
                    self.ui.set_detail(f"Playing • {self.selected_video_path.name}")
                except Exception as error:
                    self.errors.handle(error, "Video upload error")
            else:
                self.upload_rgb_frame = None
                self.ui.render_preview(None, self.READY)
        else:
            self._stop_uploaded_video()
            self._render_preview()

    def _start_uploaded_video(self, path: Path) -> None:
        if cv2 is None:
            raise RuntimeError("Install python3-opencv to preview uploaded video.")
        self._stop_uploaded_video()
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open video: {path.name}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        self.upload_fps = fps if fps > 0 else CAMERA_FPS
        self.upload_capture = capture
        self._update_uploaded_video()

    def _update_uploaded_video(self) -> None:
        self.upload_after_id = None
        if self.closing or self.ui.feature_mode != "upload" or self.upload_capture is None:
            return
        ok, frame = self.upload_capture.read()
        if not ok:
            self.ui.set_detail("Uploaded video finished")
            return
        height, width = frame.shape[:2]
        self.upload_size = (width, height)
        self.upload_rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.ui.render_preview(
            self.upload_rgb_frame, self.READY, self.upload_size, round(self.upload_fps, 1)
        )
        delay_ms = max(15, round(1000 / self.upload_fps))
        self.upload_after_id = self.after(delay_ms, self._update_uploaded_video)

    def _stop_uploaded_video(self) -> None:
        if self.upload_after_id is not None:
            try:
                self.after_cancel(self.upload_after_id)
            except tk.TclError:
                pass
            self.upload_after_id = None
        if self.upload_capture is not None:
            self.upload_capture.release()
            self.upload_capture = None

    def report_callback_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Log exceptions raised by Tk event and timer callbacks."""
        self.errors.handle(exc_value, "Application callback error", exc_traceback)

    @staticmethod
    def _preview_bounds(width: int, height: int) -> tuple[float, float, float, float]:
        """Return the displayed camera bounds within a potentially letterboxed preview."""
        return ServeScanUI.preview_bounds(width, height, CAMERA_SIZE)

    def _marker_text(self) -> str:
        """Format the current marker for logs or non-UI callers."""
        return ServeScanUI.marker_text(self.marker_position)

    def _set_marker_position(
        self, canvas_x: int, canvas_y: int, width: int, height: int
    ) -> None:
        media_size = self.upload_size if self.ui.feature_mode == "upload" else CAMERA_SIZE
        left, top, image_width, image_height = ServeScanUI.preview_bounds(
            width, height, media_size
        )
        if not (
            left <= canvas_x <= left + image_width
            and top <= canvas_y <= top + image_height
        ):
            return

        x = min(
            CAMERA_SIZE[0] - 1,
            max(0, round((canvas_x - left) * CAMERA_SIZE[0] / image_width)),
        )
        y = min(
            CAMERA_SIZE[1] - 1,
            max(0, round((canvas_y - top) * CAMERA_SIZE[1] / image_height)),
        )
        self.marker_position = (x, y)
        self.camera.set_marker_position(self.marker_position)
        self.ui.set_marker(self.marker_position)
        try:
            self.marker_store.save(self.marker_position)
        except Exception as error:
            message = self.errors.handle(error, "Line position error")
            self.ui.set_detail(message)
        self._render_preview()

    def _toggle_fullscreen(self, _event=None) -> None:
        self.attributes("-fullscreen", not bool(self.attributes("-fullscreen")))

    def _render_preview(self) -> None:
        if self.ui.feature_mode == "upload":
            self.ui.render_preview(
                self.upload_rgb_frame, self.READY, self.upload_size, round(self.upload_fps, 1)
            )
        else:
            self.ui.render_preview(self.last_rgb_frame, self.state_name)

    def _update_preview(self) -> None:
        if self.closing:
            return
        frame_number, frame = self.camera.latest()
        if frame is not None and frame_number != self.last_frame_number:
            self.last_frame_number = frame_number
            self.last_rgb_frame = frame
            self._render_preview()
            if not self.camera_reported:
                source_name = self.camera.source.name if self.camera.source else "Camera"
                self.ui.set_camera_connected(source_name, cv2 is not None)
                self.camera_reported = True
        elif self.camera.error and not self.camera_reported:
            self.camera_reported = True
            self.ui.set_camera_unavailable()
            self._render_preview()
        self.after(33, self._update_preview)

    def toggle_capture(self) -> None:
        if self.ui.feature_mode != "capture":
            return
        if self.last_rgb_frame is None:
            self.ui.set_detail("Waiting for a camera frame...")
            return

        if self.state_name == self.READY:
            try:
                self.camera.start_recording(Path.cwd() / "captures")
            except Exception as error:
                self.errors.handle(error, "Recording error")
                return
            self.recorded_seconds = 0.0
            self.segment_started = time.monotonic()
            self.state_name = self.RECORDING
        elif self.state_name == self.RECORDING:
            self.recorded_seconds += time.monotonic() - self.segment_started
            self.camera.set_recording(False)
            self.state_name = self.PAUSED
        else:
            self.segment_started = time.monotonic()
            self.camera.set_recording(True)
            self.state_name = self.RECORDING
        self._sync_state_ui()

    def _sync_state_ui(self) -> None:
        self.ui.sync_capture_state(self.state_name)
        self._render_preview()

    def _elapsed(self) -> float:
        if self.state_name == self.RECORDING:
            return self.recorded_seconds + time.monotonic() - self.segment_started
        return self.recorded_seconds

    def _update_elapsed(self) -> None:
        if self.closing:
            return
        self.ui.set_elapsed(max(0, int(self._elapsed())))
        self.after(200, self._update_elapsed)

    def stop_capture(self) -> None:
        if self.state_name == self.READY:
            return
        if self.state_name == self.RECORDING:
            self.recorded_seconds += time.monotonic() - self.segment_started
        saved_path = self.camera.stop_recording()
        self.state_name = self.READY
        self._sync_state_ui()
        self.ui.set_elapsed(0)
        self.recorded_seconds = 0.0
        if saved_path:
            try:
                shown = saved_path.relative_to(Path.cwd())
            except ValueError:
                shown = saved_path
            self.ui.set_detail(f"Saved • {shown}")

    def close(self) -> None:
        self.closing = True
        self._stop_uploaded_video()
        if self.state_name != self.READY:
            self.stop_capture()
        self.camera.stop()
        self.destroy()
