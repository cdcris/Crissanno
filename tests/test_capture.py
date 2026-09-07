import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

import capture.camera as camera_module
import capture.frame_processor as processor_module
import capture.recorder as recorder_module
import capture.worker as worker_module
from capture.camera import USBCameraSource
from capture.frame_processor import FrameProcessor
from capture.recorder import VideoRecorder
from capture.worker import CameraWorker
from shared.errors import CameraOpenError, CameraReadError, RecordingError


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
        cvtColor=Mock(side_effect=lambda frame, _code: frame),
        line=Mock(),
        circle=Mock(),
    )


class USBSourceTests(unittest.TestCase):
    def test_missing_opencv_raises_typed_error(self):
        with patch.object(camera_module, "cv2", None):
            with self.assertRaisesRegex(CameraOpenError, "OpenCV"):
                USBCameraSource((640, 480), 30)

    def test_falls_back_to_default_backend_and_configures_camera(self):
        preferred = FakeCapture(opened=False)
        fallback = FakeCapture(opened=True)
        cv = fake_cv2([preferred, fallback])

        with patch.object(camera_module, "cv2", cv):
            source = USBCameraSource((640, 480), 25, index=3)

        self.assertTrue(preferred.released)
        self.assertIs(source.camera, fallback)
        self.assertEqual(cv.VideoCapture.call_count, 2)
        self.assertEqual(len(fallback.settings), 4)

    def test_read_converts_frame_and_close_releases_camera(self):
        capture = FakeCapture(True, (True, "pixels"))
        cv = fake_cv2([capture])
        cv.cvtColor.side_effect = None
        cv.cvtColor.return_value = "converted"
        with patch.object(camera_module, "cv2", cv):
            source = USBCameraSource((640, 480), 30)
            self.assertEqual(source.read_rgb(), "converted")
            source.close()
        self.assertTrue(capture.released)

    def test_read_failure_becomes_typed_error(self):
        capture = FakeCapture(True, RuntimeError("disconnected"))
        with patch.object(camera_module, "cv2", fake_cv2([capture])):
            source = USBCameraSource((640, 480), 30)
            with self.assertRaisesRegex(CameraReadError, "disconnected"):
                source.read_rgb()

    def test_missing_camera_raises_typed_error(self):
        cv = fake_cv2([FakeCapture(False), FakeCapture(False)])
        with patch.object(camera_module, "cv2", cv):
            with self.assertRaisesRegex(CameraOpenError, "index 4"):
                USBCameraSource((640, 480), 30, index=4)


class FrameProcessorTests(unittest.TestCase):
    def test_marker_is_scaled_and_detection_runs(self):
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        detector = Mock()
        detector.annotate.return_value = "detected-frame"
        processor = FrameProcessor((1280, 720), detector=detector)
        processor.set_marker((2000, -20))
        cv = fake_cv2()

        with patch.object(processor_module, "cv2", cv):
            result = processor.process(frame)

        cv.line.assert_called_once_with(frame, (0, 0), (639, 0), (28, 38, 218), 4)
        self.assertEqual(cv.circle.call_count, 2)
        detector.annotate.assert_called_once_with(frame)
        self.assertEqual(result, "detected-frame")

    def test_bgr_frame_can_be_processed_without_color_conversion(self):
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        detector = Mock()
        detector.annotate.return_value = "detected-frame"
        processor = FrameProcessor((1280, 720), detector=detector)
        cv = fake_cv2()

        with patch.object(processor_module, "cv2", cv):
            result = processor.process_bgr(frame)

        cv.cvtColor.assert_not_called()
        detector.annotate.assert_called_once_with(frame)
        self.assertEqual(result, "detected-frame")

    def test_detection_failure_keeps_frame_and_disables_detector(self):
        frame = np.zeros((10, 20, 3), dtype=np.uint8)
        detector = Mock()
        detector.annotate.side_effect = RuntimeError("model failed")
        error_log = Mock()
        processor = FrameProcessor((20, 10), detector=detector, error_log=error_log)

        with patch.object(processor_module, "cv2", fake_cv2()):
            self.assertIs(processor.process(frame), frame)

        self.assertIsNone(processor.detector)
        self.assertEqual(processor.detection_error, "model failed")
        self.assertEqual(error_log.write.call_args.args[1], "Object detection error")


class VideoRecorderTests(unittest.TestCase):
    def setUp(self):
        self.processor = Mock()
        self.processor.process.side_effect = lambda frame: f"processed:{frame}"
        self.recorder = VideoRecorder(30, 0.5, self.processor)
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_rejects_invalid_playback_speed(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            VideoRecorder(30, 0, self.processor)

    def test_start_pause_write_resume_and_stop(self):
        writer = FakeWriter(True)
        cv = fake_cv2(writers=[writer])
        with patch.object(recorder_module, "cv2", cv), patch.object(Path, "mkdir"):
            path = self.recorder.start(Path("captures"), self.frame)
            self.recorder.write("frame-1")
            self.recorder.set_recording(False)
            self.recorder.write("ignored")
            self.recorder.set_recording(True)
            self.recorder.write("frame-2")
            self.assertEqual(self.recorder.stop(), path)

        self.assertEqual(path.suffix, ".mp4")
        self.assertEqual(writer.frames, ["processed:frame-1", "processed:frame-2"])
        self.assertTrue(writer.released)
        cv.VideoWriter.assert_called_once_with(str(path), 1234, 15.0, (640, 480))

    def test_uploaded_source_fps_controls_slow_motion_output(self):
        writer = FakeWriter(True)
        cv = fake_cv2(writers=[writer])
        with patch.object(recorder_module, "cv2", cv), patch.object(Path, "mkdir"):
            path = self.recorder.start(
                Path("captures"), self.frame, source_fps=24.0
            )
            self.recorder.write_processed("annotated-frame")
            self.recorder.stop()

        cv.VideoWriter.assert_called_once_with(str(path), 1234, 12.0, (640, 480))
        self.assertEqual(writer.frames, ["annotated-frame"])
        self.processor.process.assert_not_called()

    def test_requires_opencv_and_a_first_frame(self):
        with patch.object(recorder_module, "cv2", None):
            with self.assertRaisesRegex(RecordingError, "opencv"):
                self.recorder.start(Path("captures"), self.frame)
        with self.assertRaisesRegex(RecordingError, "frame"):
            self.recorder.start(Path("captures"), None)

    def test_uses_avi_fallback_and_avoids_existing_name(self):
        failed, successful = FakeWriter(False), FakeWriter(True)
        cv = fake_cv2(writers=[failed, successful])
        fake_datetime = Mock()
        fake_datetime.now.return_value.strftime.return_value = "fixed"
        with patch.object(recorder_module, "cv2", cv), patch.object(
            recorder_module, "datetime", fake_datetime
        ), patch.object(Path, "mkdir"), patch.object(
            Path, "exists", side_effect=[False, True, False]
        ):
            path = self.recorder.start(Path("captures"), self.frame)

        self.assertEqual(path.name, "fixed_001.avi")
        self.assertTrue(failed.released)
        self.recorder.stop()

    def test_all_writer_failures_raise_recording_error(self):
        cv = fake_cv2(writers=[FakeWriter(False), FakeWriter(False)])
        with patch.object(recorder_module, "cv2", cv), patch.object(Path, "mkdir"):
            with self.assertRaisesRegex(RecordingError, "MP4 or AVI"):
                self.recorder.start(Path("captures"), self.frame)


class CameraWorkerTests(unittest.TestCase):
    def test_latest_starts_empty(self):
        self.assertEqual(CameraWorker((1280, 720), 30).latest(), (0, None))

    def test_reader_publishes_frames_and_always_closes_source(self):
        on_frame = Mock()
        worker = CameraWorker((1280, 720), 30, on_frame=on_frame)
        source = Mock()
        source.read_rgb.side_effect = ["frame", CameraReadError("done")]
        with patch.object(worker_module, "open_usb_camera", return_value=source):
            worker._run()

        self.assertEqual(worker.latest(), (1, "frame"))
        on_frame.assert_called_once_with("frame")
        self.assertEqual(worker.error, "done")
        source.close.assert_called_once_with()

    def test_cleanup_failure_is_logged(self):
        error_log = Mock()
        worker = CameraWorker((1280, 720), 30, error_log)
        worker._stop.set()
        source = Mock()
        source.close.side_effect = OSError("release failed")
        with patch.object(worker_module, "open_usb_camera", return_value=source):
            worker._run()

        self.assertEqual(error_log.write.call_args.args[1], "Camera cleanup error")
        self.assertIn("release failed", worker.error)


if __name__ == "__main__":
    unittest.main()
