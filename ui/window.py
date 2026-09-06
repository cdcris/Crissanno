"""Tkinter view for the ServeScan application."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from capture.state import CaptureState
from marker.model import marker_text, preview_bounds
from ui.theme import COLORS, FONT_FAMILY, MONO_FONT_FAMILY, ServeScanTheme
from ui.touch_button import TouchButton


class ServeScanUI:
    """Build and update the widgets without owning application state."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        title: str,
        window_size: str,
        camera_size: tuple[int, int],
        camera_fps: int,
        marker_position: tuple[int, int] | None,
        on_upload_video: Callable[[], None],
        on_mode_changed: Callable[[str], None],
        on_toggle_capture: Callable[[], None],
        on_stop_capture: Callable[[], None],
        on_marker_click: Callable[[int, int, int, int], None],
    ) -> None:
        self.root = root
        self.camera_size = camera_size
        self.camera_fps = camera_fps
        self.marker_position = marker_position
        self.preview_photo = None
        self.rgb_frame = None
        self.capture_state = CaptureState.READY
        self.feature_mode = "capture"
        self.media_size = camera_size
        self.media_fps = camera_fps
        self.on_mode_changed = on_mode_changed

        root.title(title)
        root.geometry(window_size)
        root.minsize(800, 480)
        self.theme = ServeScanTheme(root)
        self._build(on_upload_video, on_toggle_capture, on_stop_capture, on_marker_click)

    def _build(
        self,
        on_upload_video: Callable[[], None],
        on_toggle_capture: Callable[[], None],
        on_stop_capture: Callable[[], None],
        on_marker_click: Callable[[int, int, int, int], None],
    ) -> None:
        root = self.root
        root.rowconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)

        header = tk.Frame(root, bg=COLORS["surface"], height=66)
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
        self.feature_label = tk.Label(
            title_box, text="CAMERA CAPTURE", bg=COLORS["surface"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 8, "bold"),
        )
        self.feature_label.pack(anchor="w")

        self.header_status = tk.Label(
            header, text="  READY  ", bg=COLORS["surface_soft"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 9, "bold"), padx=12, pady=6,
        )
        self.header_status.grid(row=0, column=2, padx=(10, 22))

        content = tk.Frame(root, bg=COLORS["background"])
        content.grid(row=1, column=0, sticky="nsew", padx=22, pady=(16, 12))
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        preview_shell = tk.Frame(
            content, bg=COLORS["surface_raised"],
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        preview_shell.grid(row=0, column=0, sticky="nsew")
        preview_shell.rowconfigure(0, weight=1)
        preview_shell.columnconfigure(0, weight=1)
        self.preview = tk.Canvas(preview_shell, bg=COLORS["preview"], highlightthickness=0)
        self.preview.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.preview.bind("<Configure>", lambda _event: self._redraw_preview())
        self.preview.bind(
            "<Button-1>",
            lambda event: on_marker_click(
                event.x, event.y, max(self.preview.winfo_width(), 1), max(self.preview.winfo_height(), 1)
            ),
        )
        self.preview.configure(cursor="crosshair")

        controls = tk.Frame(root, bg=COLORS["surface"], height=90)
        controls.grid(row=2, column=0, sticky="ew")
        controls.grid_propagate(False)
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1, minsize=110, uniform="action")
        controls.columnconfigure(2, weight=1, minsize=110, uniform="action")
        controls.columnconfigure(3, weight=1, minsize=110, uniform="action")
        controls.columnconfigure(4, weight=1)

        info = tk.Frame(controls, bg=COLORS["surface"])
        info.grid(row=0, column=0, sticky="w", padx=(22, 12))
        self.elapsed_label = tk.Label(
            info, text="00:00", bg=COLORS["surface"], fg=COLORS["text"],
            font=(MONO_FONT_FAMILY, 18, "bold"),
        )
        self.elapsed_label.pack(anchor="w")
        self.detail_label = tk.Label(
            info, text="Camera starting...", bg=COLORS["surface"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 8),
        )
        self.detail_label.pack(anchor="w")

        self.mode_button = TouchButton(
            controls, text="Upload Mode", icon="switch", command=self.toggle_feature_mode,
            color=COLORS["text_muted"], hover=COLORS["text"], width=110,
        )
        self.mode_button.grid(row=0, column=1, sticky="ew", padx=6, pady=13)

        self.upload_button = TouchButton(
            controls, text="Upload Video", icon="upload", command=on_upload_video,
            color=COLORS["primary"], hover=COLORS["primary_hover"], width=110,
        )
        self.upload_button.grid(row=0, column=2, columnspan=2, sticky="ew", padx=6, pady=13)

        self.capture_button = TouchButton(
            controls, text="Capture", icon="capture", command=on_toggle_capture,
            color=COLORS["primary"], hover=COLORS["primary_hover"], width=110,
        )
        self.capture_button.grid(row=0, column=2, sticky="ew", padx=6, pady=13)
        self.capture_button.set_enabled(False)

        self.stop_button = TouchButton(
            controls, text="Stop & Save", icon="stop", command=on_stop_capture,
            color=COLORS["danger"], hover=COLORS["danger_hover"], width=110,
        )
        self.stop_button.grid(row=0, column=3, sticky="ew", padx=6, pady=13)
        self.stop_button.set_enabled(False)
        self.upload_button.grid_remove()

        save_box = tk.Frame(controls, bg=COLORS["surface"])
        save_box.grid(row=0, column=4, sticky="e", padx=(12, 22))
        tk.Label(
            save_box, text="LINE POSITION", bg=COLORS["surface"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, 7, "bold"),
        ).pack(anchor="e")
        self.position_label = tk.Label(
            save_box, text=self.marker_text(self.marker_position), bg=COLORS["surface"],
            fg=COLORS["text"], font=(MONO_FONT_FAMILY, 9),
        )
        self.position_label.pack(anchor="e")

    @staticmethod
    def marker_text(marker_position: tuple[int, int] | None) -> str:
        return marker_text(marker_position)

    @staticmethod
    def preview_bounds(
        width: int, height: int, camera_size: tuple[int, int]
    ) -> tuple[float, float, float, float]:
        return preview_bounds(width, height, camera_size)

    def set_detail(self, text: str) -> None:
        self.detail_label.configure(text=text)

    def set_elapsed(self, seconds: int) -> None:
        self.elapsed_label.configure(text=f"{seconds // 60:02d}:{seconds % 60:02d}")

    def set_marker(self, marker_position: tuple[int, int]) -> None:
        self.marker_position = marker_position
        self.position_label.configure(text=self.marker_text(marker_position))

    def set_camera_connected(self, source_name: str, capture_enabled: bool) -> None:
        if self.feature_mode == "capture":
            self.set_detail(f"{source_name} connected")
        self.capture_button.set_enabled(capture_enabled)

    def set_camera_unavailable(self) -> None:
        if self.feature_mode == "capture":
            self.set_detail("Camera unavailable")
        self.capture_button.set_enabled(False)

    def show_saved_capture(
        self,
        path: Path,
        *,
        speed: float,
        detection_error: str,
        project_dir: Path,
    ) -> None:
        """Show a friendly summary after a recording is finalized."""
        try:
            shown = path.relative_to(project_dir)
        except ValueError:
            shown = path
        if detection_error:
            detail = f"Saved line + {speed:.2f}× speed; detection unavailable • {shown}"
        else:
            detail = f"Saved line + {speed:.2f}× + detection • {shown}"
        self.set_detail(detail)

    def toggle_feature_mode(self) -> None:
        """Switch between the separate capture and upload controls."""
        if self.feature_mode == "capture":
            self.feature_mode = "upload"
            self.capture_button.grid_remove()
            self.stop_button.grid_remove()
            self.upload_button.grid()
            self.mode_button.configure_content(
                "Capture Mode", "switch", COLORS["text_muted"], COLORS["text"]
            )
            self.feature_label.configure(text="VIDEO UPLOAD")
            self.set_detail("Choose an existing video to upload")
        else:
            self.feature_mode = "capture"
            self.upload_button.grid_remove()
            self.capture_button.grid()
            self.stop_button.grid()
            self.mode_button.configure_content(
                "Upload Mode", "switch", COLORS["text_muted"], COLORS["text"]
            )
            self.feature_label.configure(text="CAMERA CAPTURE")
            self.set_detail("Ready for camera capture")
        self.on_mode_changed(self.feature_mode)

    def sync_capture_state(self, state: CaptureState) -> None:
        if state is CaptureState.READY:
            self.header_status.configure(
                text="  READY  ", bg=COLORS["surface_soft"], fg=COLORS["text_muted"]
            )
            self.capture_button.configure_content(
                "Capture", "capture", COLORS["primary"], COLORS["primary_hover"]
            )
            self.stop_button.set_enabled(False)
            self.upload_button.set_enabled(True)
            self.mode_button.set_enabled(True)
        elif state is CaptureState.RECORDING:
            self.header_status.configure(text="  ● RECORDING  ", bg=COLORS["danger"], fg=COLORS["white"])
            self.capture_button.configure_content(
                "Pause", "pause", COLORS["warning"], COLORS["warning_hover"]
            )
            self.stop_button.set_enabled(True)
            self.upload_button.set_enabled(False)
            self.mode_button.set_enabled(False)
            self.set_detail("Recording in progress")
        else:
            self.header_status.configure(text="  Ⅱ PAUSED  ", bg=COLORS["warning"], fg=COLORS["white"])
            self.capture_button.configure_content(
                "Resume", "resume", COLORS["success"], COLORS["success_hover"]
            )
            self.stop_button.set_enabled(True)
            self.upload_button.set_enabled(False)
            self.mode_button.set_enabled(False)
            self.set_detail("Capture paused • press Resume to continue")

    def render_preview(
        self,
        rgb_frame,
        state: CaptureState,
        media_size: tuple[int, int] | None = None,
        media_fps: int | float | None = None,
    ) -> None:
        self.rgb_frame = rgb_frame
        self.capture_state = state
        self.media_size = media_size or self.camera_size
        self.media_fps = media_fps or self.camera_fps
        self._redraw_preview()

    def _redraw_preview(self) -> None:
        canvas = self.preview
        width, height = max(canvas.winfo_width(), 100), max(canvas.winfo_height(), 100)
        canvas.delete("all")

        if self.rgb_frame is not None and Image is not None and ImageTk is not None:
            frame = Image.fromarray(self.rgb_frame)
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
                width / 2, height / 2 + 50, text="WAITING FOR CAMERA",
                fill=COLORS["preview_text"], font=(FONT_FAMILY, 9, "bold"),
            )

        if self.marker_position is not None:
            marker_x, marker_y = self.marker_position
            left, top, image_width, image_height = self.preview_bounds(width, height, self.media_size)
            camera_width, camera_height = self.camera_size
            canvas_x = left + marker_x * image_width / camera_width
            canvas_y = top + marker_y * image_height / camera_height
            canvas.create_line(left, canvas_y, left + image_width, canvas_y, fill=COLORS["primary"], width=3)
            canvas.create_oval(
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5,
                fill=COLORS["white"], outline=COLORS["primary"], width=2,
            )
            canvas.create_text(
                left + 10, canvas_y - 9 if canvas_y >= top + 30 else canvas_y + 10,
                text=self.marker_text(self.marker_position),
                anchor="sw" if canvas_y >= top + 30 else "nw",
                fill=COLORS["white"], font=(MONO_FONT_FAMILY, 9, "bold"),
            )

        if self.capture_state in (CaptureState.RECORDING, CaptureState.PAUSED):
            is_recording = self.capture_state is CaptureState.RECORDING
            badge_color = COLORS["danger"] if is_recording else COLORS["warning"]
            badge_text = "●  REC" if is_recording else "Ⅱ  PAUSED"
            canvas.create_rectangle(
                18, 18, 111 if is_recording else 130, 50,
                fill=COLORS["preview_overlay"], outline="",
            )
            canvas.create_text(
                30, 34, text=badge_text, anchor="w", fill=badge_color,
                font=(FONT_FAMILY, 9, "bold"),
            )
        canvas.create_text(
            width - 18, height - 17,
            text=f"{self.media_size[0]} × {self.media_size[1]}  •  {self.media_fps:g} FPS",
            anchor="e", fill=COLORS["preview_text"], font=(MONO_FONT_FAMILY, 8),
        )
