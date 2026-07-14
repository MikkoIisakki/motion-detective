"""Tests for OpenCVVideoReader and OpenCVVideoWriter.

The classes exercising a real video file are marked with @pytest.mark.integration
(run them with: pytest -m integration) and are excluded from the fast unit test
suite by default. The decode-error tests run against a stubbed cv2.VideoCapture
and are part of the fast suite.
"""
import cv2
import numpy as np
import pytest

from src.adapters.opencv_video import OpenCVVideoReader, OpenCVVideoWriter
from src.ports.video_reader import VideoDecodeError


class StubCapture:
    """cv2.VideoCapture stand-in with a scripted sequence of read() results."""

    def __init__(self, reads: list[bool], frame_count: float):
        self._reads = reads
        self._index = 0
        self._frame_count = frame_count

    def isOpened(self) -> bool:
        return True

    def get(self, prop: int) -> float:
        return {
            cv2.CAP_PROP_FPS: 30.0,
            cv2.CAP_PROP_FRAME_WIDTH: 320.0,
            cv2.CAP_PROP_FRAME_HEIGHT: 240.0,
            cv2.CAP_PROP_FRAME_COUNT: self._frame_count,
        }[prop]

    def read(self):
        ok = self._reads[self._index] if self._index < len(self._reads) else False
        self._index += 1
        frame = np.zeros((240, 320, 3), dtype=np.uint8) if ok else None
        return ok, frame

    def release(self) -> None:
        pass


def _reader_with_stub(monkeypatch, reads: list[bool], frame_count: float) -> OpenCVVideoReader:
    stub = StubCapture(reads, frame_count)
    monkeypatch.setattr("src.adapters.opencv_video.cv2.VideoCapture", lambda path: stub)
    reader = OpenCVVideoReader()
    reader.open("stubbed.mp4")
    return reader


class TestOpenCVVideoReaderDecodeErrors:
    def test_read_failure_before_expected_frame_count_raises_decode_error(self, monkeypatch):
        reader = _reader_with_stub(monkeypatch, reads=[True, False], frame_count=3.0)
        assert reader.read_frame()[0] is True

        with pytest.raises(VideoDecodeError, match="frame 1"):
            reader.read_frame()

    def test_read_failure_at_expected_frame_count_is_end_of_stream(self, monkeypatch):
        reader = _reader_with_stub(monkeypatch, reads=[True, True, False], frame_count=2.0)
        reader.read_frame()
        reader.read_frame()

        assert reader.read_frame() == (False, None)

    def test_unknown_frame_count_falls_back_to_end_of_stream(self, monkeypatch):
        reader = _reader_with_stub(monkeypatch, reads=[True, False], frame_count=0.0)
        reader.read_frame()

        assert reader.read_frame() == (False, None)

    def test_negative_frame_count_falls_back_to_end_of_stream(self, monkeypatch):
        reader = _reader_with_stub(monkeypatch, reads=[True, False], frame_count=-1.0)
        reader.read_frame()

        assert reader.read_frame() == (False, None)

    def test_decode_error_is_signalled_once_per_failure_streak(self, monkeypatch):
        # A terminal mid-stream failure must not raise forever: repeated read
        # attempts after the signalled failure behave as end-of-stream, so a
        # metadata frame-count overcount cannot wedge the per-frame policy.
        reader = _reader_with_stub(monkeypatch, reads=[True, False, False], frame_count=5.0)
        reader.read_frame()

        with pytest.raises(VideoDecodeError):
            reader.read_frame()
        assert reader.read_frame() == (False, None)

    def test_successful_read_resets_the_decode_error_signal(self, monkeypatch):
        reader = _reader_with_stub(monkeypatch, reads=[False, True, False], frame_count=5.0)

        with pytest.raises(VideoDecodeError):
            reader.read_frame()
        assert reader.read_frame()[0] is True
        with pytest.raises(VideoDecodeError):
            reader.read_frame()

    def test_read_before_open_returns_end_of_stream(self):
        assert OpenCVVideoReader().read_frame() == (False, None)


@pytest.mark.integration
class TestOpenCVVideoReader:
    def setup_method(self):
        self.reader = OpenCVVideoReader()

    def teardown_method(self):
        self.reader.close()

    def test_open_returns_valid_meta(self, sample_video_path):
        meta = self.reader.open(sample_video_path)
        assert meta.fps > 0
        assert meta.width > 0
        assert meta.height > 0
        assert meta.total_frames > 0

    def test_read_frame_returns_numpy_array(self, sample_video_path):
        self.reader.open(sample_video_path)
        ok, frame = self.reader.read_frame()
        assert ok is True
        assert isinstance(frame, np.ndarray)
        assert frame.ndim == 3

    def test_read_frame_dimensions_match_meta(self, sample_video_path):
        meta = self.reader.open(sample_video_path)
        ok, frame = self.reader.read_frame()
        assert ok
        assert frame.shape == (meta.height, meta.width, 3)

    def test_read_frame_returns_false_at_end_of_video(self, sample_video_path):
        meta = self.reader.open(sample_video_path)
        for _ in range(meta.total_frames):
            self.reader.read_frame()
        ok, frame = self.reader.read_frame()
        assert ok is False
        assert frame is None

    def test_raises_for_nonexistent_file(self):
        with pytest.raises(ValueError, match="Unable to open"):
            self.reader.open("data/does_not_exist.mp4")

    def test_close_is_idempotent(self, sample_video_path):
        self.reader.open(sample_video_path)
        self.reader.close()
        self.reader.close()  # should not raise


@pytest.mark.integration
class TestOpenCVVideoWriter:
    def test_writes_frames_to_output_file(self, tmp_path, sample_video_path):
        reader = OpenCVVideoReader()
        meta = reader.open(sample_video_path)
        ok, frame = reader.read_frame()
        reader.close()
        assert ok

        out_path = str(tmp_path / "out.mp4")
        writer = OpenCVVideoWriter()
        writer.open(out_path, meta)
        writer.write_frame(frame)
        writer.close()

        import os
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0

    def test_creates_output_directory_if_missing(self, tmp_path, sample_video_path):
        reader = OpenCVVideoReader()
        meta = reader.open(sample_video_path)
        _, frame = reader.read_frame()
        reader.close()

        out_path = str(tmp_path / "nested" / "dir" / "out.mp4")
        writer = OpenCVVideoWriter()
        writer.open(out_path, meta)
        writer.write_frame(frame)
        writer.close()

        import os
        assert os.path.exists(out_path)

    def test_close_is_idempotent(self, tmp_path, sample_video_path):
        reader = OpenCVVideoReader()
        meta = reader.open(sample_video_path)
        reader.close()

        writer = OpenCVVideoWriter()
        writer.open(str(tmp_path / "out.mp4"), meta)
        writer.close()
        writer.close()  # should not raise
