import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
import threading
from unittest.mock import Mock, patch

from capture.camera import CameraSource
from marker.model import canvas_to_camera, marker_text, preview_bounds
from marker.store import MarkerStore
from shared.error_log import ErrorLog
from shared.errors import ErrorHandler, MarkerStorageError, RecordingError


class ErrorHandlerTests(unittest.TestCase):
    def test_handle_reports_domain_error(self):
        reporter = Mock()
        error_log = Mock()
        handler = ErrorHandler(reporter, error_log)

        message = handler.handle(RecordingError("disk is full"), "Recording error")

        self.assertEqual(message, "disk is full")
        self.assertEqual(handler.last_error, "disk is full")
        reporter.assert_called_once_with("Recording error", "disk is full")
        error_log.write.assert_called_once_with(
            unittest.mock.ANY, "Recording error", None
        )

    def test_protect_returns_result_or_fallback(self):
        handler = ErrorHandler()

        self.assertEqual(handler.protect(lambda: 42), 42)
        self.assertEqual(
            handler.protect(lambda: (_ for _ in ()).throw(ValueError("bad")), fallback=7),
            7,
        )
        self.assertEqual(handler.last_error, "Unexpected error: bad")

    def test_camera_source_is_an_abstract_interface(self):
        with self.assertRaises(TypeError):
            CameraSource()


class ErrorLogTests(unittest.TestCase):
    def test_write_records_context_type_message_and_traceback(self):
        error_log = ErrorLog.__new__(ErrorLog)
        logger = Mock()
        logger.handlers = [Mock()]
        error_log._logger = logger
        error = ValueError("invalid value")

        try:
            raise error
        except ValueError as caught:
            error_log.write(caught, "Test operation")

        arguments = logger.error.call_args.args
        self.assertEqual(arguments[1:3], ("Test operation", "ValueError"))
        self.assertEqual(str(arguments[3]), "invalid value")
        self.assertIn("ValueError: invalid value", arguments[4])
        logger.handlers[0].flush.assert_called_once_with()

    def test_log_setup_failure_is_safely_disabled(self):
        with patch.object(Path, "mkdir", side_effect=OSError("read only")):
            error_log = ErrorLog(Path("unwritable/error.log"))

        self.assertIsNone(error_log._logger)
        error_log.write(RuntimeError("ignored"), "Test")

    def test_global_hooks_log_main_and_thread_exceptions_once(self):
        error_log = ErrorLog.__new__(ErrorLog)
        error_log._hooks_installed = False
        error_log.write = Mock()
        previous_system_hook = Mock()
        previous_thread_hook = Mock()

        with patch.object(sys, "excepthook", previous_system_hook), patch.object(
            threading, "excepthook", previous_thread_hook
        ):
            error_log.install_global_hooks()
            system_hook = sys.excepthook
            thread_hook = threading.excepthook
            error_log.install_global_hooks()
            self.assertIs(sys.excepthook, system_hook)
            self.assertIs(threading.excepthook, thread_hook)

            system_error = RuntimeError("main failed")
            system_hook(RuntimeError, system_error, None)
            thread_error = ValueError("thread failed")
            thread_hook(
                SimpleNamespace(
                    exc_value=thread_error,
                    exc_traceback=None,
                    thread=SimpleNamespace(name="capture-thread"),
                )
            )

        error_log.write.assert_any_call(
            system_error, "Uncaught application exception", None
        )
        error_log.write.assert_any_call(
            thread_error, "Uncaught thread exception (capture-thread)", None
        )
        previous_system_hook.assert_called_once()
        previous_thread_hook.assert_called_once()


class MarkerStoreTests(unittest.TestCase):
    def setUp(self):
        self.path = Mock(spec=Path)
        self.store = MarkerStore(self.path, (1280, 720))

    def test_missing_and_invalid_marker_return_none(self):
        self.path.read_text.side_effect = FileNotFoundError
        self.assertIsNone(self.store.load())
        self.path.read_text.side_effect = None
        self.path.read_text.return_value = "not json"
        self.assertIsNone(self.store.load())
        self.path.read_text.return_value = json.dumps({"x": 1280, "y": 10})
        self.assertIsNone(self.store.load())

    def test_round_trip_marker(self):
        saved = {}
        self.path.write_text.side_effect = lambda data, **_kwargs: saved.update(text=data)
        self.path.read_text.side_effect = lambda **_kwargs: saved["text"]
        self.store.save((321, 654))

        self.assertEqual(self.store.load(), (321, 654))
        self.assertEqual(json.loads(saved["text"]), {"x": 321, "y": 654})

    def test_read_and_write_os_errors_become_domain_errors(self):
        self.path.read_text.side_effect = OSError("denied")
        with self.assertRaisesRegex(MarkerStorageError, "Could not read"):
            self.store.load()
        self.path.write_text.side_effect = OSError("full")
        with self.assertRaisesRegex(MarkerStorageError, "Could not save"):
            self.store.save((1, 2))


class MarkerModelTests(unittest.TestCase):
    def test_marker_text(self):
        self.assertEqual(marker_text(None), "Click preview")
        self.assertEqual(marker_text((12, 34)), "x: 12  y: 34")

    def test_preview_bounds_letterbox_wide_and_tall_canvases(self):
        self.assertEqual(
            preview_bounds(1280, 720, (1280, 720)),
            (0.0, 0.0, 1280.0, 720.0),
        )
        left, top, width, height = preview_bounds(1000, 1000, (1280, 720))
        self.assertEqual((left, width), (0.0, 1000.0))
        self.assertAlmostEqual(top, 218.75)
        self.assertAlmostEqual(height, 562.5)

    def test_canvas_click_converts_to_camera_coordinates(self):
        self.assertEqual(
            canvas_to_camera(500, 500, (1000, 1000), (1280, 720), (1280, 720)),
            (640, 360),
        )
        self.assertIsNone(
            canvas_to_camera(500, 100, (1000, 1000), (1280, 720), (1280, 720))
        )


if __name__ == "__main__":
    unittest.main()
