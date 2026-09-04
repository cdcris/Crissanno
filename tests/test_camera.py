import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

import camera_worker
import usb_camera_source
from camera_worker import CameraWorker
from errors import CameraOpenError, CameraReadError, RecordingError
from usb_camera_source import USBCameraSource


class FakeCapture:
    def __init__(self, opened=True, read_result=(True, "bgr")):
        self.opened = opened
        self.read_result = read_result
        self.released = False
        self.settings = []

    def isOpened(self):
        return self.opened

    def release(self):
        self.released = True

    def set(self, key, value):
        self.settings.append((key, value))

    def read(self):
        if isinstance(self.read_result, Exception):
            raise self.read_result
        return self.read_result


class FakeWriter:
    def __init__(self, opened=True):
        self.opened = opened
        self.released = False
        self.frames = []

    def isOpened(self):
        return self.opened

    def release(self):
        self.released = True

    def write(self, frame):
        self.frames.append(frame)


def fake_cv2(captures=None, writers=None):
    captures = list(captures or [])
    writers = list(writers or [])
    return SimpleNamespace(
        CAP_V4L2=1,
        CAP_DSHOW=2,
        CAP_PROP_FOURCC=3,
        CAP_PROP_FRAME_WIDTH=4,
        CAP_PROP_FRAME_HEIGHT=5,
        CAP_PROP_FPS=6,
        COLOR_BGR2RGB=7,
        COLOR_RGB2BGR=8,
        VideoCapture=Mock(side_effect=captures),
        VideoWriter=Mock(side_effect=writers),
        VideoWriter_fourcc=Mock(return_value=1234),
        cvtColor=Mock(side_effect=lambda frame, _code: f"converted:{frame}"),
        line=Mock(),
        circle=Mock(),
    )


class USBSourceTests(unittest.TestCase):
    def test_missing_opencv_raises_typed_error(self):
        with patch.object(usb_camera_source, "cv2", None):
            with self.assertRaisesRegex(CameraOpenError, "OpenCV"):
                USBCameraSource((640, 480), 30)

    def test_falls_back_to_default_backend_and_configures_camera(self):
        preferred = FakeCapture(opened=False)
        fallback = FakeCapture(opened=True)
        cv = fake_cv2([preferred, fallback])

        with patch.object(usb_camera_source, "cv2", cv):
            source = USBCameraSource((640, 480), 25, index=3)

        self.assertTrue(preferred.released)
        self.assertIs(source.camera, fallback)
        self.assertEqual(cv.VideoCapture.call_count, 2)
        self.assertEqual(len(fallback.settings), 4)

    def test_no_camera_and_read_failure_raise_typed_errors(self):
        cv = fake_cv2([FakeCapture(False), FakeCapture(False)])
        with patch.object(usb_camera_source, "cv2", cv):
            with self.assertRaisesRegex(CameraOpenError, "index 4"):
                USBCameraSource((640, 480), 30, index=4)

        capture = FakeCapture(True, RuntimeError("disconnected"))
        cv = fake_cv2([capture])
        with patch.object(usb_camera_source, "cv2", cv):
            source = USBCameraSource((640, 480), 30)
            with self.assertRaisesRegex(CameraReadError, "disconnected"):
                source.read_rgb()

    def test_read_converts_frame_and_close_releases_camera(self):
        capture = FakeCapture(True, (True, "pixels"))
        cv = fake_cv2([capture])
        with patch.object(usb_camera_source, "cv2", cv):
            source = USBCameraSource((640, 480), 30)
            self.assertEqual(source.read_rgb(), "converted:pixels")
            source.close()
        self.assertTrue(capture.released)


class CameraWorkerTests(unittest.TestCase):
    def setUp(self):
        self.worker = CameraWorker((1280, 720), 30)

    def test_latest_and_marker_position_are_thread_safe_accessors(self):
        self.assertEqual(self.worker.latest(), (0, None))
        self.worker.set_marker_position((20, 30))
        self.assertEqual(self.worker._marker_position, (20, 30))

    def test_recording_requires_opencv_and_a_frame(self):
        with patch.object(camera_worker, "cv2", None):
            with self.assertRaisesRegex(RecordingError, "opencv"):
                self.worker.start_recording(Path("captures"))

        with self.assertRaisesRegex(RecordingError, "frame"):
            self.worker.start_recording(Path("captures"))

    def test_start_pause_resume_and_stop_recording(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.worker._frame = frame
        writer = FakeWriter(True)
        cv = fake_cv2(writers=[writer])

        with patch.object(camera_worker, "cv2", cv), patch.object(Path, "mkdir"):
            path = self.worker.start_recording(Path("captures"))
            self.assertEqual(path.suffix, ".mp4")
            self.assertTrue(self.worker._recording)
            self.worker.set_recording(False)
            self.assertFalse(self.worker._recording)
            self.worker.set_recording(True)
            self.assertTrue(self.worker._recording)
            self.assertEqual(self.worker.stop_recording(), path)

        self.assertTrue(writer.released)
        self.assertIsNone(self.worker._writer)

    def test_uses_avi_fallback_and_avoids_existing_name(self):
        self.worker._frame = np.zeros((10, 20, 3), dtype=np.uint8)
        failed, successful = FakeWriter(False), FakeWriter(True)
        cv = fake_cv2(writers=[failed, successful])

        fake_datetime = Mock()
        fake_datetime.now.return_value.strftime.return_value = "fixed"
        with patch.object(camera_worker, "cv2", cv), patch.object(
            camera_worker, "datetime", fake_datetime
        ), patch.object(Path, "mkdir"), patch.object(
            Path, "exists", side_effect=[False, True, False]
        ):
            path = self.worker.start_recording(Path("captures"))

        self.assertEqual(path.name, "fixed_001.avi")
        self.assertTrue(failed.released)
        self.worker.stop_recording()

    def test_all_writer_failures_raise_recording_error(self):
        self.worker._frame = np.zeros((10, 20, 3), dtype=np.uint8)
        cv = fake_cv2(writers=[FakeWriter(False), FakeWriter(False)])
        with patch.object(camera_worker, "cv2", cv), patch.object(Path, "mkdir"):
            with self.assertRaisesRegex(RecordingError, "MP4 or AVI"):
                self.worker.start_recording(Path("captures"))

    def test_marker_is_scaled_and_clamped(self):
        cv = fake_cv2()
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        with patch.object(camera_worker, "cv2", cv):
            self.worker._draw_recording_marker(frame, (2000, -20))

        cv.line.assert_called_once_with(frame, (0, 0), (639, 0), (28, 38, 218), 4)
        self.assertEqual(cv.circle.call_count, 2)

    def test_run_records_error_and_always_closes_source(self):
        source = Mock()
        source.read_rgb.side_effect = CameraReadError("camera unplugged")
        with patch.object(camera_worker, "open_usb_camera", return_value=source):
            self.worker._run()

        self.assertEqual(self.worker.error, "camera unplugged")
        source.close.assert_called_once_with()

    def test_run_writes_camera_failure_to_error_log(self):
        error_log = Mock()
        worker = CameraWorker((1280, 720), 30, error_log)
        source = Mock()
        source.read_rgb.side_effect = CameraReadError("camera unplugged")
        with patch.object(camera_worker, "open_usb_camera", return_value=source):
            worker._run()

        logged_error = error_log.write.call_args.args
        self.assertIsInstance(logged_error[0], CameraReadError)
        self.assertEqual(logged_error[1], "Camera worker error")

    def test_run_logs_camera_cleanup_failure(self):
        error_log = Mock()
        worker = CameraWorker((1280, 720), 30, error_log)
        worker._stop.set()
        source = Mock()
        source.close.side_effect = OSError("release failed")
        with patch.object(camera_worker, "open_usb_camera", return_value=source):
            worker._run()

        logged_error = error_log.write.call_args.args
        self.assertIsInstance(logged_error[0], OSError)
        self.assertEqual(logged_error[1], "Camera cleanup error")
        self.assertIn("release failed", worker.error)


if __name__ == "__main__":
    unittest.main()
