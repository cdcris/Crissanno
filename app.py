"""Application logic and camera workflow for ServeScan."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox

try:
    import cv2
except ImportError:
    cv2 = None

from app_ui import ServeScanUI
from control_capture import CaptureController
from camera_worker import CameraWorker
from error_log import get_error_log
from errors import ErrorHandler
from marker_store import MarkerStore
from control_video_upload import VideoUploadController
from detect import ObjectDetector


APP_TITLE = "ServeScan"
WINDOW_SIZE = "1024x600"
CAMERA_SIZE = (1280, 720)
CAMERA_FPS = 30
SLOW_MOTION_SPEED = 0.5
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
        self.last_frame_number = -1
        self.last_rgb_frame = None
        self.marker_position = self.errors.protect(self.marker_store.load)
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

        self.camera = CameraWorker(
            CAMERA_SIZE,
            CAMERA_FPS,
            self.error_log,
            playback_speed=SLOW_MOTION_SPEED,
            detector=ObjectDetector(),
        )
        self.capture_control = CaptureController(
            self.camera, self.errors, Path.cwd() / "captures"
        )
        self.video_upload = VideoUploadController(
            self,
            default_size=CAMERA_SIZE,
            default_fps=CAMERA_FPS,
            render_frame=self._render_uploaded_frame,
            set_detail=self.ui.set_detail,
            is_upload_mode=lambda: self.ui.feature_mode == "upload",
        )
        self.camera.set_marker_position(self.marker_position)
        self.camera.start()
        self.after(40, self._update_preview)
        self.after(200, self._update_elapsed)

    def upload_video(self) -> None:
        """Let the user choose an existing video for the next processing step."""
        try:
            self.video_upload.choose_video()
        except Exception as error:
            self.errors.handle(error, "Video upload error")

    def _on_feature_mode_changed(self, mode: str) -> None:
        if mode == "upload":
            try:
                self.video_upload.resume_selected()
            except Exception as error:
                self.errors.handle(error, "Video upload error")
        else:
            self.video_upload.stop()
            self._render_preview()

    def _render_uploaded_frame(self, frame, size: tuple[int, int], fps: float) -> None:
        self.ui.render_preview(frame, self.READY, size, fps)

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
        media_size = (
            self.video_upload.size if self.ui.feature_mode == "upload" else CAMERA_SIZE
        )
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
            self._render_uploaded_frame(
                self.video_upload.rgb_frame,
                self.video_upload.size,
                round(self.video_upload.fps, 1),
            )
        else:
            self.ui.render_preview(self.last_rgb_frame, self.capture_control.state)

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
        result = self.capture_control.toggle(
            frame_available=self.last_rgb_frame is not None
        )
        if isinstance(result, str):
            self.ui.set_detail(result)
            return
        if not result:
            return
        self._sync_state_ui()

    def _sync_state_ui(self) -> None:
        self.ui.sync_capture_state(self.capture_control.state)
        self._render_preview()

    def _elapsed(self) -> float:
        return self.capture_control.elapsed()

    def _update_elapsed(self) -> None:
        if self.closing:
            return
        self.ui.set_elapsed(max(0, int(self._elapsed())))
        self.after(200, self._update_elapsed)

    def stop_capture(self) -> None:
        if self.capture_control.state == self.READY:
            return
        saved_path = self.capture_control.stop()
        self._sync_state_ui()
        self.ui.set_elapsed(0)
        if saved_path:
            try:
                shown = saved_path.relative_to(Path.cwd())
            except ValueError:
                shown = saved_path
            if self.camera.detection_error:
                self.ui.set_detail(
                    f"Saved line + {SLOW_MOTION_SPEED:.2f}× speed; "
                    f"detection unavailable • {shown}"
                )
            else:
                self.ui.set_detail(
                    f"Saved line + {SLOW_MOTION_SPEED:.2f}× + detection • {shown}"
                )

    def close(self) -> None:
        self.closing = True
        self.video_upload.close()
        if self.capture_control.state != self.READY:
            self.stop_capture()
        self.camera.stop()
        self.destroy()
