"""Control uploaded-video selection and preview playback for ServeScan."""

from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog
from typing import Callable

try:
    import cv2
except ImportError:
    cv2 = None

class VideoUploadController:
    """Seek to and detect individual frames from an uploaded video."""

    def __init__(
        self,
        root: tk.Misc,
        *,
        default_size: tuple[int, int],
        default_fps: int,
        render_frame: Callable[[object | None, tuple[int, int], float], None],
        set_detail: Callable[[str], None],
        is_upload_mode: Callable[[], bool],
        process_frame: Callable[[object], object] | None = None,
        set_timeline: Callable[[int, int], None] | None = None,
    ) -> None:
        self.root = root
        self.default_size = default_size
        self.default_fps = default_fps
        self.render_frame = render_frame
        self.set_detail = set_detail
        self.is_upload_mode = is_upload_mode
        self.process_frame = process_frame or (lambda frame: frame)
        self.set_timeline = set_timeline or (lambda _total, _current: None)
        self.selected_path: Path | None = None
        self.capture = None
        self.after_id = None
        self.rgb_frame = None
        self.size = default_size
        self.fps = float(default_fps)
        self.total_frames = 0
        self.processed_frames = 0
        self.closing = False
        self._frame_version = 0
        self._rendered_version = 0
        self._worker_error: Exception | None = None
        self._worker_done = True
        self._terminal_delivered = True
        self._detection_requested = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._processing_lock = threading.Lock()
        self.current_frame = 0
        self._active_name = ""

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
        self.set_detail(f"Loading video • {path.name}")
        self.start(path)
        return path

    def start(self, path: Path) -> None:
        if cv2 is None:
            raise RuntimeError("Install python3-opencv to preview uploaded video.")
        self.stop()
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Wait for the previous video processing to stop.")
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open video: {path.name}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        self.fps = fps if fps > 0 else float(self.default_fps)
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.total_frames = max(0, total_frames)
        if self.total_frames == 0:
            capture.release()
            raise RuntimeError(f"Video contains no readable frames: {path.name}")
        self.processed_frames = 0
        capture.release()
        self.capture = None
        self.selected_path = path
        self.current_frame = 0
        self._active_name = path.name
        self._worker_error = None
        self._worker_done = True
        self._terminal_delivered = True
        self.set_timeline(self.total_frames, 0)
        self.seek_frame(0)

    def resume_selected(self) -> None:
        if self.selected_path is None:
            self.rgb_frame = None
            self.render_frame(None, self.default_size, float(self.default_fps))
            return
        self.start(self.selected_path)

    def seek_frame(self, frame_number: int) -> None:
        """Start detection for one frame, cancelling publication of stale work."""
        self._request_frame(frame_number, detect=True)

    def preview_frame(self, frame_number: int) -> None:
        """Display one raw frame while the upload slider is moving."""
        self._request_frame(frame_number, detect=False)

    def _request_frame(self, frame_number: int, *, detect: bool) -> None:
        if self.selected_path is None:
            return
        frame_number = min(self.total_frames - 1, max(0, int(frame_number)))
        self._stop_event.set()
        stop_event = threading.Event()
        self._stop_event = stop_event
        self.current_frame = frame_number
        self.processed_frames = frame_number + 1
        self._worker_error = None
        self._worker_done = False
        self._terminal_delivered = False
        self._detection_requested = detect
        if detect:
            self.set_detail(
                f"Detecting frame {frame_number + 1}/{self.total_frames} • "
                f"{self._active_name}"
            )
        self._thread = threading.Thread(
            target=self._process_selected_frame,
            args=(self.selected_path, frame_number, stop_event, detect),
            daemon=True,
        )
        self._thread.start()
        self._schedule_poll()

    def _process_selected_frame(
        self,
        path: Path,
        frame_number: int,
        stop_event: threading.Event,
        detect: bool,
    ) -> None:
        """Read and annotate one requested frame away from Tk's event loop."""
        capture = None
        worker_error = None
        try:
            with self._processing_lock:
                if stop_event.is_set():
                    return
                capture = cv2.VideoCapture(str(path))
                if not capture.isOpened():
                    raise RuntimeError(f"Could not open video: {path.name}")
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Could not read frame {frame_number + 1}.")
                height, width = frame.shape[:2]
                processed_frame = self.process_frame(frame) if detect else frame
                if stop_event.is_set():
                    return
                rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                with self._lock:
                    if stop_event is not self._stop_event or stop_event.is_set():
                        return
                    self.rgb_frame = rgb_frame
                    self.size = (width, height)
                    self._frame_version += 1
        except Exception as error:
            worker_error = error
        finally:
            if capture is not None:
                capture.release()
            with self._lock:
                if stop_event is self._stop_event:
                    self.capture = None
                    self._worker_error = worker_error
                    self._worker_done = True

    def _schedule_poll(self) -> None:
        if not self.closing and self.after_id is None:
            self.after_id = self.root.after(33, self._update)

    def _update(self) -> None:
        """Render worker results and update progress from Tk's main thread."""
        self.after_id = None
        if self.closing:
            return

        with self._lock:
            frame_version = self._frame_version
            rgb_frame = self.rgb_frame
            size = self.size
            worker_done = self._worker_done
            worker_error = self._worker_error
            detection_requested = self._detection_requested

        if self.is_upload_mode() and frame_version != self._rendered_version:
            self._rendered_version = frame_version
            self.render_frame(rgb_frame, size, round(self.fps, 1))

        if worker_done:
            if not self._terminal_delivered:
                self._terminal_delivered = True
                if worker_error is not None:
                    raise worker_error
                if self.is_upload_mode() and detection_requested:
                    self.set_detail(
                        f"Frame {self.current_frame + 1}/{self.total_frames} • "
                        f"{self._active_name}"
                    )
            return

        self._schedule_poll()

    def stop(self) -> None:
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        if self._thread is not None and self._thread.is_alive():
            self._schedule_poll()
        elif not self.closing:
            self._update()

    def clear(self) -> None:
        """Stop processing and discard the selected video's preview state."""
        with self._lock:
            self._terminal_delivered = True
        self.stop()
        self._discard_preview_state()

    def _discard_preview_state(self) -> None:
        """Restore upload state without rendering or stopping the worker."""
        self.selected_path = None
        with self._lock:
            self.rgb_frame = None
            self.size = self.default_size
            self.fps = float(self.default_fps)
            self.total_frames = 0
            self.processed_frames = 0
            self.current_frame = 0
            self._worker_error = None
            self._terminal_delivered = True
            self._detection_requested = False
            self._active_name = ""
            self._frame_version += 1
            self._rendered_version = self._frame_version
        self.set_timeline(0, 0)

    def close(self) -> None:
        self.closing = True
        self.stop()
        self._discard_preview_state()
