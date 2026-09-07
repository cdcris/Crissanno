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

from capture.recorder import VideoRecorder


class VideoUploadController:
    """Preview uploaded frames and save their annotated slow-motion copy."""

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
        recorder: VideoRecorder | None = None,
        capture_dir: Path | None = None,
        on_saved: Callable[[Path], None] | None = None,
    ) -> None:
        self.root = root
        self.default_size = default_size
        self.default_fps = default_fps
        self.render_frame = render_frame
        self.set_detail = set_detail
        self.is_upload_mode = is_upload_mode
        self.process_frame = process_frame or (lambda frame: frame)
        self.recorder = recorder
        self.capture_dir = capture_dir
        self.on_saved = on_saved
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
        self._saved_path: Path | None = None
        self._worker_done = True
        self._terminal_delivered = True
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
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
        self.set_detail(f"Preparing detection • {path.name}")
        self.start(path, save_output=True)
        self.selected_path = path
        return path

    def start(self, path: Path, *, save_output: bool = False) -> None:
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
        self.processed_frames = 0
        self.capture = capture
        self._active_name = path.name
        self._stop_event = threading.Event()
        self._worker_error = None
        self._saved_path = None
        self._worker_done = False
        self._terminal_delivered = False
        self._thread = threading.Thread(
            target=self._process_video,
            args=(capture, self._stop_event, save_output),
            daemon=True,
        )
        self._thread.start()
        self._schedule_poll()

    def resume_selected(self) -> None:
        if self.selected_path is None:
            self.rgb_frame = None
            self.render_frame(None, self.default_size, float(self.default_fps))
            return
        self.start(self.selected_path)
        self.set_detail(f"Detecting preview • {self.selected_path.name}")

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
            processed_frames = self.processed_frames
            total_frames = self.total_frames
            worker_done = self._worker_done
            worker_error = self._worker_error
            saved_path = self._saved_path

        if self.is_upload_mode() and frame_version != self._rendered_version:
            self._rendered_version = frame_version
            self.render_frame(rgb_frame, size, round(self.fps, 1))

        if worker_done:
            if not self._terminal_delivered:
                self._terminal_delivered = True
                if worker_error is not None:
                    raise worker_error
                if saved_path is not None and self.on_saved is not None:
                    self.on_saved(saved_path)
                elif self.is_upload_mode():
                    self.set_detail("Uploaded video finished")
            return

        if self.is_upload_mode():
            if total_frames > 0:
                percent = min(100, round(processed_frames * 100 / total_frames))
                progress = f"{percent}% • frame {processed_frames}/{total_frames}"
            else:
                progress = f"frame {processed_frames}"
            self.set_detail(f"Detecting {progress} • {self._active_name}")
        self._schedule_poll()

    def _process_video(
        self,
        capture,
        stop_event: threading.Event,
        save_output: bool,
    ) -> None:
        """Detect, annotate, and save frames away from Tk's event loop."""
        output_started = False
        saved_path = None
        worker_error = None
        processed_frames = 0
        try:
            while not stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    break
                height, width = frame.shape[:2]
                processed_frame = self.process_frame(frame)
                if save_output and not output_started:
                    if self.recorder is None or self.capture_dir is None:
                        raise RuntimeError(
                            "Uploaded-video recording is not configured."
                        )
                    self.recorder.start(
                        self.capture_dir,
                        processed_frame,
                        source_fps=self.fps,
                    )
                    output_started = True
                if output_started:
                    self.recorder.write_processed(processed_frame)
                rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                processed_frames += 1
                with self._lock:
                    self.rgb_frame = rgb_frame
                    self.size = (width, height)
                    self.processed_frames = processed_frames
                    self._frame_version += 1
        except Exception as error:
            worker_error = error
        finally:
            capture.release()
            if output_started and self.recorder is not None:
                try:
                    saved_path = self.recorder.stop()
                except Exception as error:
                    if worker_error is None:
                        worker_error = error
            with self._lock:
                self.capture = None
                self._saved_path = saved_path
                self._worker_error = worker_error
                self._worker_done = True

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

    def close(self) -> None:
        self.closing = True
        self.stop()
