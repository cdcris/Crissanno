"""Main Tkinter application for ServeScan."""

from __future__ import annotations

import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from camera_worker import CameraWorker
from color import COLORS, FONT_FAMILY, MONO_FONT_FAMILY, ServeScanTheme
from error_log import get_error_log
from errors import ErrorHandler
from marker_store import MarkerStore
from touch_button import TouchButton


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
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(800, 480)
        self.theme = ServeScanTheme(self)
        self.error_log = get_error_log()
        self.errors = ErrorHandler(messagebox.showerror, self.error_log)
        self.marker_store = MarkerStore(MARKER_PATH, CAMERA_SIZE)
        self.state_name = self.READY
        self.recorded_seconds = 0.0
        self.segment_started = 0.0
        self.last_frame_number = -1
        self.preview_photo = None
        self.preview_image_id = None
        self.last_rgb_frame = None
        self.marker_position = self.errors.protect(self.marker_store.load)
        self.camera_reported = False
        self.closing = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<space>", lambda _event: self.toggle_capture())
        self.bind("<Escape>", lambda _event: self.stop_capture())
        self.bind("<F11>", self._toggle_fullscreen)

        self.camera = CameraWorker(CAMERA_SIZE, CAMERA_FPS, self.error_log)
        self.camera.set_marker_position(self.marker_position)
        self.camera.start()
        self.after(40, self._update_preview)
        self.after(200, self._update_elapsed)

    def report_callback_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Log exceptions raised by Tk event and timer callbacks."""
        self.errors.handle(exc_value, "Application callback error", exc_traceback)

    def _build_ui(self) -> None:
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=COLORS["surface"], height=66)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(1, weight=1)

        brand = tk.Canvas(header, width=36, height=36, bg=COLORS["surface"], highlightthickness=0)
        brand.grid(row=0, column=0, padx=(22, 10), pady=15)
        brand.create_rectangle(3, 7, 33, 29, outline=COLORS["primary"], width=2)
        brand.create_oval(13, 10, 23, 20, outline=COLORS["primary"], width=2)
        brand.create_line(8, 26, 28, 26, fill=COLORS["primary"], width=2)

        title_box = tk.Frame(header, bg=COLORS["surface"])
        title_box.grid(row=0, column=1, sticky="w")
        tk.Label(
            title_box, text="SERVESCAN", bg=COLORS["surface"], fg=COLORS["text"],
            font=(FONT_FAMILY, 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_box, text="CAMERA CAPTURE", bg=COLORS["surface"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 8, "bold"),
        ).pack(anchor="w")

        self.header_status = tk.Label(
            header,
            text="  READY  ",
            bg=COLORS["surface_soft"],
            fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 9, "bold"),
            padx=12,
            pady=6,
        )
        self.header_status.grid(row=0, column=2, padx=(10, 22))

        content = tk.Frame(self, bg=COLORS["background"])
        content.grid(row=1, column=0, sticky="nsew", padx=22, pady=(16, 12))
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        preview_shell = tk.Frame(
            content,
            bg=COLORS["surface_raised"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        preview_shell.grid(row=0, column=0, sticky="nsew")
        preview_shell.rowconfigure(0, weight=1)
        preview_shell.columnconfigure(0, weight=1)
        self.preview = tk.Canvas(
            preview_shell,
            bg=COLORS["preview"],
            highlightthickness=0,
        )
        self.preview.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.preview.bind("<Configure>", lambda _event: self._render_preview())
        self.preview.bind("<Button-1>", self._set_marker_position)
        self.preview.configure(cursor="crosshair")
        self._render_preview()

        controls = tk.Frame(self, bg=COLORS["surface"], height=90)
        controls.grid(row=2, column=0, sticky="ew")
        controls.grid_propagate(False)
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(3, weight=1)

        info = tk.Frame(controls, bg=COLORS["surface"])
        info.grid(row=0, column=0, sticky="w", padx=(22, 12))
        self.elapsed_label = tk.Label(
            info,
            text="00:00",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(MONO_FONT_FAMILY, 18, "bold"),
        )
        self.elapsed_label.pack(anchor="w")
        self.detail_label = tk.Label(
            info,
            text="Camera starting...",
            bg=COLORS["surface"],
            fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 8),
        )
        self.detail_label.pack(anchor="w")

        self.capture_button = TouchButton(
            controls,
            text="Capture",
            icon="capture",
            command=self.toggle_capture,
            color=COLORS["primary"],
            hover=COLORS["primary_hover"],
            width=210,
        )
        self.capture_button.grid(row=0, column=1, padx=6, pady=13)
        self.capture_button.set_enabled(False)

        self.stop_button = TouchButton(
            controls,
            text="Stop & Save",
            icon="stop",
            command=self.stop_capture,
            color=COLORS["danger"],
            hover=COLORS["danger_hover"],
            width=170,
        )
        self.stop_button.grid(row=0, column=2, padx=6, pady=13)
        self.stop_button.set_enabled(False)

        save_box = tk.Frame(controls, bg=COLORS["surface"])
        save_box.grid(row=0, column=3, sticky="e", padx=(12, 22))
        tk.Label(
            save_box, text="LINE POSITION", bg=COLORS["surface"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 7, "bold"),
        ).pack(anchor="e")
        self.position_label = tk.Label(
            save_box, text=self._marker_text(), bg=COLORS["surface"], fg=COLORS["text"],
            font=(MONO_FONT_FAMILY, 9),
        )
        self.position_label.pack(anchor="e")

    def _marker_text(self) -> str:
        if self.marker_position is None:
            return "Click preview"
        x, y = self.marker_position
        return f"x: {x}  y: {y}"

    @staticmethod
    def _preview_bounds(width: int, height: int) -> tuple[float, float, float, float]:
        scale = min(width / CAMERA_SIZE[0], height / CAMERA_SIZE[1])
        image_width = CAMERA_SIZE[0] * scale
        image_height = CAMERA_SIZE[1] * scale
        return (
            (width - image_width) / 2,
            (height - image_height) / 2,
            image_width,
            image_height,
        )

    def _set_marker_position(self, event: tk.Event) -> None:
        width = max(self.preview.winfo_width(), 1)
        height = max(self.preview.winfo_height(), 1)
        left, top, image_width, image_height = self._preview_bounds(width, height)
        if not (left <= event.x <= left + image_width and top <= event.y <= top + image_height):
            return

        x = min(CAMERA_SIZE[0] - 1, max(0, round((event.x - left) * CAMERA_SIZE[0] / image_width)))
        y = min(CAMERA_SIZE[1] - 1, max(0, round((event.y - top) * CAMERA_SIZE[1] / image_height)))
        self.marker_position = (x, y)
        self.camera.set_marker_position(self.marker_position)
        self.position_label.configure(text=self._marker_text())
        try:
            self.marker_store.save(self.marker_position)
        except Exception as error:
            message = self.errors.handle(error, "Line position error")
            self.detail_label.configure(text=message)
        self._render_preview()

    def _toggle_fullscreen(self, _event=None) -> None:
        self.attributes("-fullscreen", not bool(self.attributes("-fullscreen")))

    def _render_preview(self) -> None:
        if not hasattr(self, "preview"):
            return
        canvas = self.preview
        width, height = max(canvas.winfo_width(), 100), max(canvas.winfo_height(), 100)
        canvas.delete("all")

        if self.last_rgb_frame is not None and Image is not None and ImageTk is not None:
            frame = Image.fromarray(self.last_rgb_frame)
            frame.thumbnail((width, height), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(frame)
            canvas.create_image(width / 2, height / 2, image=self.preview_photo)
        else:
            canvas.create_oval(
                width / 2 - 27, height / 2 - 27, width / 2 + 27, height / 2 + 27,
                outline=COLORS["preview_border"], width=2,
            )
            canvas.create_oval(
                width / 2 - 9, height / 2 - 9, width / 2 + 9, height / 2 + 9,
                outline=COLORS["preview_border"], width=2,
            )
            canvas.create_text(
                width / 2,
                height / 2 + 50,
                text="WAITING FOR CAMERA",
                fill=COLORS["preview_text"],
                font=(FONT_FAMILY, 9, "bold"),
            )

        if self.marker_position is not None:
            marker_x, marker_y = self.marker_position
            left, top, image_width, image_height = self._preview_bounds(width, height)
            canvas_x = left + marker_x * image_width / CAMERA_SIZE[0]
            canvas_y = top + marker_y * image_height / CAMERA_SIZE[1]
            canvas.create_line(
                left, canvas_y, left + image_width, canvas_y,
                fill=COLORS["primary"], width=3,
            )
            canvas.create_oval(
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5,
                fill=COLORS["white"], outline=COLORS["primary"], width=2,
            )
            canvas.create_text(
                left + 10,
                canvas_y - 9 if canvas_y >= top + 30 else canvas_y + 10,
                text=f"x: {marker_x}  y: {marker_y}",
                anchor="sw" if canvas_y >= top + 30 else "nw",
                fill=COLORS["white"],
                font=(MONO_FONT_FAMILY, 9, "bold"),
            )

        if self.state_name in (self.RECORDING, self.PAUSED):
            badge_color = COLORS["danger"] if self.state_name == self.RECORDING else COLORS["warning"]
            badge_text = "●  REC" if self.state_name == self.RECORDING else "Ⅱ  PAUSED"
            canvas.create_rectangle(
                18, 18, 111 if self.state_name == self.RECORDING else 130, 50,
                fill=COLORS["preview_overlay"], outline="",
            )
            canvas.create_text(
                30, 34, text=badge_text, anchor="w", fill=badge_color,
                font=(FONT_FAMILY, 9, "bold"),
            )
        canvas.create_text(
            width - 18,
            height - 17,
            text="1280 × 720  •  30 FPS",
            anchor="e",
            fill=COLORS["preview_text"],
            font=(MONO_FONT_FAMILY, 8),
        )

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
                self.detail_label.configure(text=f"{source_name} connected")
                self.capture_button.set_enabled(cv2 is not None)
                self.camera_reported = True
        elif self.camera.error and not self.camera_reported:
            self.camera_reported = True
            self.detail_label.configure(text="Camera unavailable")
            self.capture_button.set_enabled(False)
            self._render_preview()
        self.after(33, self._update_preview)

    def toggle_capture(self) -> None:
        if self.last_rgb_frame is None:
            self.detail_label.configure(text="Waiting for a camera frame...")
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
        if self.state_name == self.READY:
            self.header_status.configure(
                text="  READY  ", bg=COLORS["surface_soft"], fg=COLORS["text_muted"]
            )
            self.capture_button.configure_content(
                "Capture", "capture", COLORS["primary"], COLORS["primary_hover"]
            )
            self.stop_button.set_enabled(False)
        elif self.state_name == self.RECORDING:
            self.header_status.configure(
                text="  ● RECORDING  ", bg=COLORS["danger"], fg=COLORS["white"]
            )
            self.capture_button.configure_content(
                "Pause", "pause", COLORS["warning"], COLORS["warning_hover"]
            )
            self.stop_button.set_enabled(True)
            self.detail_label.configure(text="Recording in progress")
        else:
            self.header_status.configure(
                text="  Ⅱ PAUSED  ", bg=COLORS["warning"], fg=COLORS["white"]
            )
            self.capture_button.configure_content(
                "Resume", "resume", COLORS["success"], COLORS["success_hover"]
            )
            self.stop_button.set_enabled(True)
            self.detail_label.configure(text="Capture paused • press Resume to continue")
        self._render_preview()

    def _elapsed(self) -> float:
        if self.state_name == self.RECORDING:
            return self.recorded_seconds + time.monotonic() - self.segment_started
        return self.recorded_seconds

    def _update_elapsed(self) -> None:
        if self.closing:
            return
        seconds = max(0, int(self._elapsed()))
        self.elapsed_label.configure(text=f"{seconds // 60:02d}:{seconds % 60:02d}")
        self.after(200, self._update_elapsed)

    def stop_capture(self) -> None:
        if self.state_name == self.READY:
            return
        if self.state_name == self.RECORDING:
            self.recorded_seconds += time.monotonic() - self.segment_started
        saved_path = self.camera.stop_recording()
        self.state_name = self.READY
        self._sync_state_ui()
        self.elapsed_label.configure(text="00:00")
        self.recorded_seconds = 0.0
        if saved_path:
            try:
                shown = saved_path.relative_to(Path.cwd())
            except ValueError:
                shown = saved_path
            self.detail_label.configure(text=f"Saved • {shown}")

    def close(self) -> None:
        self.closing = True
        if self.state_name != self.READY:
            self.stop_capture()
        self.camera.stop()
        self.destroy()
