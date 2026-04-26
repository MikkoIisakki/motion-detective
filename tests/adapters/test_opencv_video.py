"""Integration tests for OpenCVVideoReader and OpenCVVideoWriter.

These tests require a real video file and are marked with @pytest.mark.integration.
Run them with: pytest -m integration
They are excluded from the fast unit test suite by default.
"""
import numpy as np
import pytest

from src.adapters.opencv_video import OpenCVVideoReader, OpenCVVideoWriter
from src.ports.video_reader import VideoMeta

SAMPLE_VIDEO = "data/sample_video_side.mp4"


@pytest.mark.integration
class TestOpenCVVideoReader:
    def setup_method(self):
        self.reader = OpenCVVideoReader()

    def teardown_method(self):
        self.reader.close()

    def test_open_returns_valid_meta(self):
        meta = self.reader.open(SAMPLE_VIDEO)
        assert meta.fps > 0
        assert meta.width > 0
        assert meta.height > 0
        assert meta.total_frames > 0

    def test_read_frame_returns_numpy_array(self):
        self.reader.open(SAMPLE_VIDEO)
        ok, frame = self.reader.read_frame()
        assert ok is True
        assert isinstance(frame, np.ndarray)
        assert frame.ndim == 3

    def test_read_frame_dimensions_match_meta(self):
        meta = self.reader.open(SAMPLE_VIDEO)
        ok, frame = self.reader.read_frame()
        assert ok
        assert frame.shape == (meta.height, meta.width, 3)

    def test_read_frame_returns_false_at_end_of_video(self):
        meta = self.reader.open(SAMPLE_VIDEO)
        for _ in range(meta.total_frames):
            self.reader.read_frame()
        ok, frame = self.reader.read_frame()
        assert ok is False
        assert frame is None

    def test_raises_for_nonexistent_file(self):
        with pytest.raises(ValueError, match="Unable to open"):
            self.reader.open("data/does_not_exist.mp4")

    def test_close_is_idempotent(self):
        self.reader.open(SAMPLE_VIDEO)
        self.reader.close()
        self.reader.close()  # should not raise


@pytest.mark.integration
class TestOpenCVVideoWriter:
    def test_writes_frames_to_output_file(self, tmp_path):
        reader = OpenCVVideoReader()
        meta = reader.open(SAMPLE_VIDEO)
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

    def test_creates_output_directory_if_missing(self, tmp_path):
        reader = OpenCVVideoReader()
        meta = reader.open(SAMPLE_VIDEO)
        _, frame = reader.read_frame()
        reader.close()

        out_path = str(tmp_path / "nested" / "dir" / "out.mp4")
        writer = OpenCVVideoWriter()
        writer.open(out_path, meta)
        writer.write_frame(frame)
        writer.close()

        import os
        assert os.path.exists(out_path)

    def test_close_is_idempotent(self, tmp_path):
        reader = OpenCVVideoReader()
        meta = reader.open(SAMPLE_VIDEO)
        reader.close()

        writer = OpenCVVideoWriter()
        writer.open(str(tmp_path / "out.mp4"), meta)
        writer.close()
        writer.close()  # should not raise
