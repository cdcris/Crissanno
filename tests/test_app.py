import unittest
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main
import upload.controller as video_upload_module
from app import ServeScanApp
from capture.controller import CaptureController
from capture.state import CaptureState
from config import APP_TITLE, CAMERA_FPS, CAMERA_SIZE
from shared.errors import ErrorHandler, RecordingError
from ui.touch_button import TouchButton
from ui.window import ServeScanUI
from upload.controller import VideoUploadController


def bare_app(state=CaptureState.READY):
    instance = ServeScanApp.__new__(ServeScanApp)
    instance.last_rgb_frame = object()
    instance.camera = Mock()
    instance.frame_processor = Mock()
    instance.errors = ErrorHandler()
    instance._sync_state_ui = Mock()
    instance.ui = Mock()
    instance.ui.feature_mode = "capture"
    instance.capture_control = Mock()
    instance.capture_control.state = state
    instance.video_upload = Mock()
    return instance


class AppLogicTests(unittest.TestCase):
    def test_capture_pause_and_resume_state_machine(self):
        recorder = Mock()
        now = [10.0]
        controller = CaptureController(
            recorder,
            ErrorHandler(),
            Path("captures"),
            clock=lambda: now[0],
        )
        frame = object()
        controller.toggle(current_frame=frame)
        self.assertIs(controller.state, CaptureState.RECORDING)
        recorder.start.assert_called_once_with(Path("captures"), frame)

        now[0] = 13.5
        controller.toggle(current_frame=frame)
        self.assertIs(controller.state, CaptureState.PAUSED)
        self.assertEqual(controller.recorded_seconds, 3.5)
        recorder.set_recording.assert_called_with(False)

        now[0] = 20.0
        controller.toggle(current_frame=frame)
        self.assertIs(controller.state, CaptureState.RECORDING)
        recorder.set_recording.assert_called_with(True)

    def test_recording_error_is_handled_without_state_change(self):
        reporter = Mock()
        recorder = Mock()
        recorder.start.side_effect = RecordingError("cannot write")
        controller = CaptureController(
            recorder, ErrorHandler(reporter), Path("captures")
        )

        controller.toggle(current_frame=object())

        self.assertIs(controller.state, CaptureState.READY)
        reporter.assert_called_once_with("Recording error", "cannot write")

    def test_waits_for_frame_before_recording(self):
        instance = bare_app()
        instance.last_rgb_frame = None
        instance.capture_control.toggle.return_value = "Waiting for a camera frame..."
        instance.toggle_capture()
        instance.capture_control.toggle.assert_called_once_with(current_frame=None)
        instance.ui.set_detail.assert_called_with("Waiting for a camera frame...")

    def test_upload_mode_does_not_allow_camera_capture(self):
        instance = bare_app()
        instance.ui.feature_mode = "upload"

        instance.toggle_capture()

        instance.capture_control.toggle.assert_not_called()
        self.assertIs(instance.capture_control.state, CaptureState.READY)

    def test_upload_video_opens_picker_and_remembers_selection(self):
        instance = bare_app()
        instance.upload_video()
        instance.video_upload.choose_video.assert_called_once_with()

    def test_cancel_upload_keeps_existing_selection(self):
        root = Mock()
        controller = VideoUploadController(
            root, default_size=(1280, 720), default_fps=30,
            render_frame=Mock(), set_detail=Mock(), is_upload_mode=lambda: True,
        )
        controller.selected_path = Path("existing.mp4")
        with patch.object(video_upload_module.filedialog, "askopenfilename", return_value=""):
            controller.choose_video()
        self.assertEqual(controller.selected_path, Path("existing.mp4"))

    def test_clearing_upload_stops_detection_and_discards_preview(self):
        controller = VideoUploadController(
            Mock(), default_size=(1280, 720), default_fps=30,
            render_frame=Mock(), set_detail=Mock(), is_upload_mode=lambda: True,
        )
        controller.selected_path = Path("existing.mp4")
        controller.rgb_frame = "detected-frame"
        controller.size = (640, 360)
        controller.fps = 25.0
        controller.total_frames = 100
        controller.processed_frames = 42

        with patch.object(controller, "stop") as stop:
            controller.clear()

        stop.assert_called_once_with()
        self.assertIsNone(controller.selected_path)
        self.assertIsNone(controller.rgb_frame)
        self.assertEqual(controller.size, (1280, 720))
        self.assertEqual(controller.fps, 30.0)
        self.assertEqual(controller.total_frames, 0)
        self.assertEqual(controller.processed_frames, 0)

    def test_cancelled_detection_does_not_publish_a_stale_frame(self):
        process_started = threading.Event()
        allow_process_to_finish = threading.Event()

        def process_frame(frame):
            process_started.set()
            allow_process_to_finish.wait(timeout=1)
            return frame

        controller = VideoUploadController(
            Mock(), default_size=(1280, 720), default_fps=30,
            render_frame=Mock(), set_detail=Mock(), is_upload_mode=lambda: True,
            process_frame=process_frame,
        )
        frame = SimpleNamespace(shape=(360, 640, 3))
        capture = Mock()
        capture.read.return_value = (True, frame)
        worker = threading.Thread(
            target=controller._process_video,
            args=(capture, controller._stop_event, False),
        )

        worker.start()
        self.assertTrue(process_started.wait(timeout=1))
        controller._stop_event.set()
        allow_process_to_finish.set()
        worker.join(timeout=1)

        self.assertFalse(worker.is_alive())
        self.assertIsNone(controller.rgb_frame)

    def test_entering_upload_mode_clears_the_previous_preview(self):
        instance = bare_app()
        instance.ui.feature_mode = "upload"

        instance._on_feature_mode_changed("upload")

        instance.video_upload.clear.assert_called_once_with()
        instance.ui.render_preview.assert_called_once_with(
            None,
            CaptureState.READY,
            CAMERA_SIZE,
            float(CAMERA_FPS),
        )

    def test_leaving_upload_mode_clears_detection_and_shows_camera(self):
        instance = bare_app()

        instance._on_feature_mode_changed("capture")

        instance.video_upload.clear.assert_called_once_with()
        instance.ui.render_preview.assert_called_once_with(
            instance.last_rgb_frame,
            instance.capture_control.state,
        )

    def test_uploaded_frame_replaces_camera_preview(self):
        root = Mock()
        render = Mock()
        process_frame = Mock(return_value="detected-bgr")
        set_detail = Mock()
        controller = VideoUploadController(
            root, default_size=(1280, 720), default_fps=30,
            render_frame=render, set_detail=set_detail,
            is_upload_mode=lambda: True,
            process_frame=process_frame,
        )
        controller.fps = 25.0
        controller.total_frames = 1
        controller._terminal_delivered = False
        frame = SimpleNamespace(shape=(360, 640, 3))
        capture = Mock()
        capture.read.side_effect = [(True, frame), (False, None)]
        fake_cv = SimpleNamespace(
            COLOR_BGR2RGB=1,
            cvtColor=Mock(return_value="uploaded-rgb"),
        )

        with patch.object(video_upload_module, "cv2", fake_cv):
            controller._process_video(capture, controller._stop_event, False)
            controller._update()

        process_frame.assert_called_once_with(frame)
        fake_cv.cvtColor.assert_called_once_with(
            "detected-bgr", fake_cv.COLOR_BGR2RGB
        )
        self.assertEqual(controller.rgb_frame, "uploaded-rgb")
        self.assertEqual(controller.size, (640, 360))
        render.assert_called_once_with("uploaded-rgb", (640, 360), 25.0)
        set_detail.assert_called_once_with("Uploaded video finished")

    def test_uploaded_frames_are_saved_and_finalized(self):
        root = Mock()
        recorder = Mock()
        recorder.stop.return_value = Path("captures/annotated.mp4")
        on_saved = Mock()
        controller = VideoUploadController(
            root,
            default_size=(1280, 720),
            default_fps=30,
            render_frame=Mock(),
            set_detail=Mock(),
            is_upload_mode=lambda: True,
            process_frame=Mock(return_value="annotated-bgr"),
            recorder=recorder,
            capture_dir=Path("captures"),
            on_saved=on_saved,
        )
        controller.fps = 24.0
        controller.total_frames = 1
        controller._terminal_delivered = False
        frame = SimpleNamespace(shape=(360, 640, 3))
        capture = Mock()
        capture.read.side_effect = [(True, frame), (False, None)]
        fake_cv = SimpleNamespace(
            COLOR_BGR2RGB=1,
            cvtColor=Mock(return_value="annotated-rgb"),
        )

        with patch.object(video_upload_module, "cv2", fake_cv):
            controller._process_video(capture, controller._stop_event, True)
            controller._update()

        recorder.start.assert_called_once_with(
            Path("captures"), "annotated-bgr", source_fps=24.0
        )
        recorder.write_processed.assert_called_once_with("annotated-bgr")
        recorder.stop.assert_called_once_with()
        on_saved.assert_called_once_with(Path("captures/annotated.mp4"))

    def test_upload_progress_reports_percentage_and_frame_count(self):
        root = Mock()
        root.after.return_value = "progress-timer"
        set_detail = Mock()
        controller = VideoUploadController(
            root,
            default_size=(1280, 720),
            default_fps=30,
            render_frame=Mock(),
            set_detail=set_detail,
            is_upload_mode=lambda: True,
        )
        controller._worker_done = False
        controller.total_frames = 20
        controller.processed_frames = 7
        controller._active_name = "serve.mp4"

        controller._update()

        set_detail.assert_called_once_with(
            "Detecting 35% • frame 7/20 • serve.mp4"
        )
        root.after.assert_called_once_with(33, controller._update)

    def test_elapsed_counts_only_active_segments(self):
        controller = CaptureController(
            Mock(),
            ErrorHandler(),
            Path("captures"),
            clock=lambda: 12.5,
        )
        controller.state = CaptureState.RECORDING
        controller.recorded_seconds = 4.0
        controller.segment_started = 10.0
        self.assertEqual(controller.elapsed(), 6.5)
        controller.state = CaptureState.PAUSED
        self.assertEqual(controller.elapsed(), 4.0)

    def test_tk_callback_exception_uses_central_handler(self):
        instance = bare_app()
        instance.errors = Mock()
        error = RuntimeError("callback failed")
        trace = Mock()

        instance.report_callback_exception(RuntimeError, error, trace)

        instance.errors.handle.assert_called_once_with(
            error, "Application callback error", trace
        )

    def test_stop_capture_finalizes_and_resets(self):
        instance = bare_app(CaptureState.RECORDING)
        instance.capture_control.stop.return_value = None
        instance.stop_capture()
        instance.capture_control.stop.assert_called_once_with()
        instance.ui.set_elapsed.assert_called_with(0)

    def test_stop_capture_reports_detection_fallback(self):
        instance = bare_app(CaptureState.RECORDING)
        instance.capture_control.stop.return_value = Path(
            "captures/test.mp4"
        )
        instance.frame_processor.detection_error = "model failed"

        instance.stop_capture()

        instance.ui.show_saved_capture.assert_called_once()
        self.assertEqual(
            instance.ui.show_saved_capture.call_args.kwargs["detection_error"],
            "model failed",
        )


class TouchButtonLogicTests(unittest.TestCase):
    def test_invoke_only_calls_command_when_enabled(self):
        button = TouchButton.__new__(TouchButton)
        button.command = Mock()
        button.enabled = False
        button.invoke()
        button.command.assert_not_called()
        button.enabled = True
        button.invoke()
        button.command.assert_called_once_with()

    def test_content_layout_compacts_for_narrow_buttons(self):
        self.assertEqual(TouchButton.content_layout(180), (25, 105, 10, "center"))
        self.assertEqual(TouchButton.content_layout(120), (17, 72, 9, "center"))
        self.assertEqual(TouchButton.content_layout(90), (None, 45, 8, "center"))

    def test_switch_icon_hides_when_it_would_overlap_centered_text(self):
        self.assertFalse(TouchButton.show_icon("switch", 120))
        self.assertTrue(TouchButton.show_icon("switch", 180))
        self.assertTrue(TouchButton.show_icon("capture", 120))

    def test_text_regions_stay_inside_button_edges(self):
        self.assertEqual(TouchButton.text_region(104, True), (66, 60))
        self.assertEqual(TouchButton.text_region(104, False), (52, 88))


class InterfaceModeTests(unittest.TestCase):
    def test_configured_app_title_is_used_by_window(self):
        root = Mock()
        with patch("ui.window.ServeScanTheme"), patch.object(
            ServeScanUI, "_build"
        ):
            ui = ServeScanUI(
                root,
                title=APP_TITLE,
                window_size="1024x600",
                camera_size=(1280, 720),
                camera_fps=30,
                marker_position=None,
                on_upload_video=Mock(),
                on_mode_changed=Mock(),
                on_toggle_capture=Mock(),
                on_stop_capture=Mock(),
                on_marker_click=Mock(),
            )

        self.assertEqual(ui.app_title, APP_TITLE)
        root.title.assert_called_once_with(APP_TITLE)

    def test_capture_is_default_and_mode_switch_separates_controls(self):
        ui = ServeScanUI.__new__(ServeScanUI)
        ui.feature_mode = "capture"
        ui.capture_button = Mock()
        ui.stop_button = Mock()
        ui.upload_button = Mock()
        ui.mode_button = Mock()
        ui.feature_label = Mock()
        ui.set_detail = Mock()
        ui.on_mode_changed = Mock()

        ui.toggle_feature_mode()
        self.assertEqual(ui.feature_mode, "upload")
        ui.capture_button.grid_remove.assert_called_once_with()
        ui.stop_button.grid_remove.assert_called_once_with()
        ui.upload_button.grid.assert_called_once_with()
        ui.feature_label.configure.assert_called_with(text="VIDEO UPLOAD")
        ui.on_mode_changed.assert_called_with("upload")

        ui.toggle_feature_mode()
        self.assertEqual(ui.feature_mode, "capture")
        ui.upload_button.grid_remove.assert_called_once_with()
        ui.capture_button.grid.assert_called_once_with()
        ui.stop_button.grid.assert_called_once_with()
        ui.feature_label.configure.assert_called_with(text="CAMERA CAPTURE")
        ui.on_mode_changed.assert_called_with("capture")


class EntryPointTests(unittest.TestCase):
    def test_main_success_and_failure_exit_codes(self):
        fake_app = Mock()
        error_log = Mock()
        with patch.object(main, "get_error_log", return_value=error_log), patch.object(
            main, "ServeScanApp", return_value=fake_app
        ):
            self.assertEqual(main.main(), 0)
            fake_app.mainloop.assert_called_once_with()
            error_log.install_global_hooks.assert_called_once_with()

        with patch.object(main, "get_error_log", return_value=error_log), patch.object(
            main, "ServeScanApp", side_effect=RuntimeError("boom")
        ), patch("sys.stderr"):
            self.assertEqual(main.main(), 1)
            self.assertTrue(error_log.write.called)


if __name__ == "__main__":
    unittest.main()
