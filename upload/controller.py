"""Control uploaded-video selection and preview playback for ServeScan."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from typing import Callable

try:
    import cv2
except ImportError:
    cv2 = None


class VideoUploadController:
    """Own uploaded-video resources and scheduled preview frames."""

    def __init__(
        self,
        root: tk.Misc,
        *,
        default_size: tuple[int, int],
        default_fps: int,
        render_frame: Callable[[object | None, tuple[int, int], float], None],
        set_detail: Callable[[str], None],
        is_upload_mode: Callable[[], bool],
    ) -> None:
        self.root = root
        self.default_size = default_size
        self.default_fps = default_fps
        self.render_frame = render_frame
        self.set_detail = set_detail
        self.is_upload_mode = is_upload_mode
        self.selected_path: Path | None = None
        self.capture = None
        self.after_id = None
        self.rgb_frame = None
        self.size = default_size
        self.fps = float(default_fps)
        self.closing = False

    def choose_video(self) -> Path | None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Upload video",
            filetypes=(
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.m4v *.webm"),
                ("All files", "*.*"),
            ),
        )
        if not selected:
            return None
        path = Path(selected)
        self.start(path)
        self.selected_path = path
        self.set_detail(f"Playing • {path.name}")
        return path

    def start(self, path: Path) -> None:
        if cv2 is None:
            raise RuntimeError("Install python3-opencv to preview uploaded video.")
        self.stop()
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open video: {path.name}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        self.fps = fps if fps > 0 else float(self.default_fps)
        self.capture = capture
        self._update()

    def resume_selected(self) -> None:
        if self.selected_path is None:
            self.rgb_frame = None
            self.render_frame(None, self.default_size, float(self.default_fps))
            return
        self.start(self.selected_path)
        self.set_detail(f"Playing • {self.selected_path.name}")

    def _update(self) -> None:
        self.after_id = None
        if self.closing or not self.is_upload_mode() or self.capture is None:
            return
        ok, frame = self.capture.read()
        if not ok:
            self.set_detail("Uploaded video finished")
            return
        height, width = frame.shape[:2]
        self.size = (width, height)
        self.rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.render_frame(self.rgb_frame, self.size, round(self.fps, 1))
        delay_ms = max(15, round(1000 / self.fps))
        self.after_id = self.root.after(delay_ms, self._update)

    def stop(self) -> None:
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def close(self) -> None:
        self.closing = True
        self.stop()
