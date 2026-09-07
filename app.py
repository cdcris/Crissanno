"""Application shell that connects ServeScan's independent features."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

try:
    import cv2
except ImportError:
    cv2 = None

from capture.controller import CaptureController
from capture.frame_processor import FrameProcessor
from capture.recorder import VideoRecorder
from capture.state import CaptureState
from capture.worker import CameraWorker
from config import (
    APP_TITLE,
    CAMERA_FPS,
    CAMERA_SIZE,
    CAPTURE_DIR,
    MARKER_PATH,
    PROJECT_DIR,
    SLOW_MOTION_SPEED,
    WINDOW_SIZE,
)
from detection.detector import ObjectDetector
from marker.model import canvas_to_camera
from marker.store import MarkerStore
from shared.error_log import get_error_log
from shared.errors import ErrorHandler
from ui.window import ServeScanUI
from upload.controller import VideoUploadController


class ServeScanApp(tk.Tk):
    """Coordinate UI events without implementing camera or storage details."""

    def __init__(self) -> None:
        super().__init__()
        self.error_log = get_error_log()
        self.errors = ErrorHandler(messagebox.showerror, self.error_log)
        self.marker_store = MarkerStore(MARKER_PATH, CAMERA_SIZE)
        self.marker_position = self.errors.protect(self.marker_store.load)
        self.last_frame_number = -1
        self.last_rgb_frame = None
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

        self.frame_processor = FrameProcessor(
            CAMERA_SIZE,
            detector=ObjectDetector(),
            error_log=self.error_log,
        )
        self.frame_processor.set_marker(self.marker_position)
        self.recorder = VideoRecorder(
            CAMERA_FPS,
            SLOW_MOTION_SPEED,
            self.frame_processor,
        )
        self.upload_recorder = VideoRecorder(
            CAMERA_FPS,
            SLOW_MOTION_SPEED,
            self.frame_processor,
        )
        self.camera = CameraWorker(
            CAMERA_SIZE,
            CAMERA_FPS,
            self.error_log,
            on_frame=self.recorder.write,
        )
        self.capture_control = CaptureController(
            self.recorder,
            self.errors,
            CAPTURE_DIR,
        )
        self.video_upload = VideoUploadController(
            self,
            default_size=CAMERA_SIZE,
            default_fps=CAMERA_FPS,
            render_frame=self._render_uploaded_frame,
            set_detail=self.ui.set_detail,
            is_upload_mode=lambda: self.ui.feature_mode == "upload",
            process_frame=self.frame_processor.process_bgr,
            recorder=self.upload_recorder,
            capture_dir=CAPTURE_DIR,
            on_saved=self._show_saved_uploaded_video,
        )

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<space>", lambda _event: self.toggle_capture())
        self.bind("<Escape>", lambda _event: self.stop_capture())
        self.bind("<F11>", self._toggle_fullscreen)
        self.camera.start()
        self.after(40, self._update_preview)
        self.after(200, self._update_elapsed)

    def upload_video(self) -> None:
        """Open the upload picker and report failures at the UI boundary."""
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
        self.ui.render_preview(frame, CaptureState.READY, size, fps)

    def _show_saved_uploaded_video(self, saved_path) -> None:
        """Report the annotated slow-motion copy created from an upload."""
        self.ui.show_saved_capture(
            saved_path,
            speed=SLOW_MOTION_SPEED,
            detection_error=self.frame_processor.detection_error,
            project_dir=PROJECT_DIR,
        )

    def report_callback_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Log exceptions raised by Tk event and timer callbacks."""
        self.errors.handle(exc_value, "Application callback error", exc_traceback)

    def _set_marker_position(
        self, canvas_x: int, canvas_y: int, width: int, height: int
    ) -> None:
        media_size = (
            self.video_upload.size if self.ui.feature_mode == "upload" else CAMERA_SIZE
        )
        position = canvas_to_camera(
            canvas_x,
            canvas_y,
            (width, height),
            media_size,
            CAMERA_SIZE,
        )
        if position is None:
            return

        self.marker_position = position
        self.frame_processor.set_marker(position)
        self.ui.set_marker(position)
        try:
            self.marker_store.save(position)
        except Exception as error:
            self.ui.set_detail(self.errors.handle(error, "Line position error"))
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
        """Pass the latest frame to the capture workflow and refresh the UI."""
        if self.ui.feature_mode != "capture":
            return
        result = self.capture_control.toggle(current_frame=self.last_rgb_frame)
        if isinstance(result, str):
            self.ui.set_detail(result)
        elif result:
            self._sync_state_ui()

    def _sync_state_ui(self) -> None:
        self.ui.sync_capture_state(self.capture_control.state)
        self._render_preview()

    def _update_elapsed(self) -> None:
        if self.closing:
            return
        self.ui.set_elapsed(max(0, int(self.capture_control.elapsed())))
        self.after(200, self._update_elapsed)

    def stop_capture(self) -> None:
        """Finalize an active capture and tell the UI what was saved."""
        if self.capture_control.state is CaptureState.READY:
            return
        saved_path = self.capture_control.stop()
        self._sync_state_ui()
        self.ui.set_elapsed(0)
        if saved_path:
            self.ui.show_saved_capture(
                saved_path,
                speed=SLOW_MOTION_SPEED,
                detection_error=self.frame_processor.detection_error,
                project_dir=PROJECT_DIR,
            )

    def close(self) -> None:
        """Release playback, recording, and camera resources before exit."""
        self.closing = True
        self.video_upload.close()
        if self.capture_control.state is not CaptureState.READY:
            self.stop_capture()
        self.camera.stop()
        self.destroy()
