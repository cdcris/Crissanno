import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app as app_module
import servescan
from app import ServeScanApp
from app_ui import ServeScanUI
from errors import ErrorHandler, RecordingError
from touch_button import TouchButton


def bare_app(state=ServeScanApp.READY):
    instance = ServeScanApp.__new__(ServeScanApp)
    instance.state_name = state
    instance.last_rgb_frame = object()
    instance.recorded_seconds = 0.0
    instance.segment_started = 0.0
    instance.camera = Mock()
    instance.errors = ErrorHandler()
    instance._sync_state_ui = Mock()
    instance.ui = Mock()
    instance.ui.feature_mode = "capture"
    return instance


class AppLogicTests(unittest.TestCase):
    def test_preview_bounds_letterbox_wide_and_tall_canvases(self):
        self.assertEqual(ServeScanApp._preview_bounds(1280, 720), (0.0, 0.0, 1280.0, 720.0))
        left, top, width, height = ServeScanApp._preview_bounds(1000, 1000)
        self.assertEqual((left, width), (0.0, 1000.0))
        self.assertAlmostEqual(top, 218.75)
        self.assertAlmostEqual(height, 562.5)

    def test_marker_text(self):
        instance = bare_app()
        instance.marker_position = None
        self.assertEqual(instance._marker_text(), "Click preview")
        instance.marker_position = (12, 34)
        self.assertEqual(instance._marker_text(), "x: 12  y: 34")

    def test_capture_pause_and_resume_state_machine(self):
        instance = bare_app()
        with patch.object(app_module.time, "monotonic", return_value=10.0):
            instance.toggle_capture()
        self.assertEqual(instance.state_name, instance.RECORDING)
        instance.camera.start_recording.assert_called_once()

        with patch.object(app_module.time, "monotonic", return_value=13.5):
            instance.toggle_capture()
        self.assertEqual(instance.state_name, instance.PAUSED)
        self.assertEqual(instance.recorded_seconds, 3.5)
        instance.camera.set_recording.assert_called_with(False)

        with patch.object(app_module.time, "monotonic", return_value=20.0):
            instance.toggle_capture()
        self.assertEqual(instance.state_name, instance.RECORDING)
        instance.camera.set_recording.assert_called_with(True)

    def test_recording_error_is_handled_without_state_change(self):
        reporter = Mock()
        instance = bare_app()
        instance.errors = ErrorHandler(reporter)
        instance.camera.start_recording.side_effect = RecordingError("cannot write")

        instance.toggle_capture()

        self.assertEqual(instance.state_name, instance.READY)
        reporter.assert_called_once_with("Recording error", "cannot write")
        instance._sync_state_ui.assert_not_called()

    def test_waits_for_frame_before_recording(self):
        instance = bare_app()
        instance.last_rgb_frame = None
        instance.toggle_capture()
        instance.camera.start_recording.assert_not_called()
        instance.ui.set_detail.assert_called_with("Waiting for a camera frame...")

    def test_upload_mode_does_not_allow_camera_capture(self):
        instance = bare_app()
        instance.ui.feature_mode = "upload"

        instance.toggle_capture()

        instance.camera.start_recording.assert_not_called()
        self.assertEqual(instance.state_name, instance.READY)

    def test_upload_video_opens_picker_and_remembers_selection(self):
        instance = bare_app()
        with patch.object(
            app_module.filedialog, "askopenfilename", return_value="C:/videos/serve.mp4"
        ) as picker, patch.object(instance, "_start_uploaded_video") as start_video:
            instance.upload_video()

        picker.assert_called_once()
        self.assertEqual(instance.selected_video_path, app_module.Path("C:/videos/serve.mp4"))
        start_video.assert_called_once_with(app_module.Path("C:/videos/serve.mp4"))
        instance.ui.set_detail.assert_called_with("Playing • serve.mp4")

    def test_cancel_upload_keeps_existing_selection(self):
        instance = bare_app()
        instance.selected_video_path = app_module.Path("existing.mp4")
        with patch.object(app_module.filedialog, "askopenfilename", return_value=""):
            instance.upload_video()

        self.assertEqual(instance.selected_video_path, app_module.Path("existing.mp4"))
        instance.ui.set_detail.assert_not_called()

    def test_uploaded_frame_replaces_camera_preview(self):
        instance = bare_app()
        instance.ui.feature_mode = "upload"
        instance.closing = False
        instance.upload_after_id = None
        instance.upload_fps = 25.0
        frame = SimpleNamespace(shape=(360, 640, 3))
        instance.upload_capture = Mock()
        instance.upload_capture.read.return_value = (True, frame)
        instance.after = Mock(return_value="upload-timer")
        fake_cv = SimpleNamespace(
            COLOR_BGR2RGB=1,
            cvtColor=Mock(return_value="uploaded-rgb"),
        )

        with patch.object(app_module, "cv2", fake_cv):
            instance._update_uploaded_video()

        self.assertEqual(instance.upload_rgb_frame, "uploaded-rgb")
        self.assertEqual(instance.upload_size, (640, 360))
        instance.ui.render_preview.assert_called_once_with(
            "uploaded-rgb", instance.READY, (640, 360), 25.0
        )
        instance.after.assert_called_once_with(40, instance._update_uploaded_video)

    def test_elapsed_counts_only_active_segments(self):
        instance = bare_app(ServeScanApp.RECORDING)
        instance.recorded_seconds = 4.0
        instance.segment_started = 10.0
        with patch.object(app_module.time, "monotonic", return_value=12.5):
            self.assertEqual(instance._elapsed(), 6.5)
        instance.state_name = instance.PAUSED
        self.assertEqual(instance._elapsed(), 4.0)

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
        instance = bare_app(ServeScanApp.RECORDING)
        instance.segment_started = 10.0
        instance.camera.stop_recording.return_value = None
        with patch.object(app_module.time, "monotonic", return_value=12.0):
            instance.stop_capture()
        self.assertEqual(instance.state_name, instance.READY)
        self.assertEqual(instance.recorded_seconds, 0.0)
        instance.camera.stop_recording.assert_called_once_with()
        instance.ui.set_elapsed.assert_called_with(0)


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
        self.assertEqual(TouchButton.content_layout(180), (30, 53, 12, "w"))
        self.assertEqual(TouchButton.content_layout(120), (20, 39, 10, "w"))
        self.assertEqual(TouchButton.content_layout(90), (None, 45, 8, "center"))


class InterfaceModeTests(unittest.TestCase):
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
        with patch.object(servescan, "get_error_log", return_value=error_log), patch.object(
            servescan, "ServeScanApp", return_value=fake_app
        ):
            self.assertEqual(servescan.main(), 0)
            fake_app.mainloop.assert_called_once_with()
            error_log.install_global_hooks.assert_called_once_with()

        with patch.object(servescan, "get_error_log", return_value=error_log), patch.object(
            servescan, "ServeScanApp", side_effect=RuntimeError("boom")
        ), patch("sys.stderr"):
            self.assertEqual(servescan.main(), 1)
            self.assertTrue(error_log.write.called)


if __name__ == "__main__":
    unittest.main()
