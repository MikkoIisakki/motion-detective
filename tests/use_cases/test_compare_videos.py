from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.ports.video_reader import VideoMeta, VideoReaderPort
from src.ports.video_writer import VideoWriterPort
from src.use_cases.compare_videos import CompareVideos


class FakeReader(VideoReaderPort):
    def __init__(self, frames: list[np.ndarray], meta: VideoMeta | None = None):
        self._frames = frames
        if meta is None and frames:
            h, w = frames[0].shape[:2]
            meta = VideoMeta(fps=30.0, width=w, height=h, total_frames=len(frames))
        elif meta is None:
            meta = VideoMeta(fps=30.0, width=0, height=0, total_frames=0)
        self._meta = meta
        self._index = 0
        self.closed = False

    def open(self, path: str) -> VideoMeta:
        self._index = 0
        return self._meta

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._index >= len(self._frames):
            return False, None
        frame = self._frames[self._index]
        self._index += 1
        return True, frame

    def close(self) -> None:
        self.closed = True


class FakeWriter(VideoWriterPort):
    def __init__(self):
        self.written_frames: list[np.ndarray] = []
        self.opened_path: str | None = None
        self.opened_meta: VideoMeta | None = None
        self.closed = False

    def open(self, path: str, meta: VideoMeta) -> None:
        self.opened_path = path
        self.opened_meta = meta

    def write_frame(self, frame: np.ndarray) -> None:
        self.written_frames.append(frame)

    def close(self) -> None:
        self.closed = True


def _frame(height: int, width: int, fill: int) -> np.ndarray:
    return np.full((height, width, 3), fill, dtype=np.uint8)


class TestCompareVideosHappyPath:
    def test_stitches_same_size_frames_horizontally(self, tmp_path):
        left_frames = [_frame(20, 30, 10), _frame(20, 30, 20)]
        right_frames = [_frame(20, 30, 100), _frame(20, 30, 200)]
        left_reader = FakeReader(left_frames)
        right_reader = FakeReader(right_frames)
        writer = FakeWriter()

        uc = CompareVideos(left_reader=left_reader, right_reader=right_reader, writer=writer)
        uc.execute("left.mp4", "right.mp4", str(tmp_path / "out.mp4"))

        assert len(writer.written_frames) == 2
        first = writer.written_frames[0]
        assert first.shape == (20, 60, 3)
        # Left half pixels carry the left fill, right half pixels carry the right fill.
        assert np.all(first[:, :30, :] == 10)
        assert np.all(first[:, 30:, :] == 100)

    def test_writer_opened_with_summed_width_and_left_fps(self, tmp_path):
        left_reader = FakeReader(
            [_frame(20, 30, 0)],
            meta=VideoMeta(fps=24.0, width=30, height=20, total_frames=1),
        )
        right_reader = FakeReader(
            [_frame(20, 40, 0)],
            meta=VideoMeta(fps=60.0, width=40, height=20, total_frames=1),
        )
        writer = FakeWriter()

        CompareVideos(left_reader, right_reader, writer).execute(
            "l.mp4", "r.mp4", str(tmp_path / "o.mp4")
        )

        assert writer.opened_meta is not None
        assert writer.opened_meta.fps == 24.0
        assert writer.opened_meta.width == 70
        assert writer.opened_meta.height == 20
        assert writer.opened_meta.total_frames == 1


class TestCompareVideosPadding:
    def test_shorter_frame_is_padded_with_zeros_at_bottom(self, tmp_path):
        # Left is 20 tall, right is 30 tall — left should be padded by 10 rows of zeros at the bottom.
        left_frames = [_frame(20, 30, 50)]
        right_frames = [_frame(30, 30, 200)]
        writer = FakeWriter()

        CompareVideos(
            FakeReader(left_frames),
            FakeReader(right_frames),
            writer,
        ).execute("l.mp4", "r.mp4", str(tmp_path / "o.mp4"))

        frame = writer.written_frames[0]
        assert frame.shape == (30, 60, 3)
        # Top 20 rows of left half preserve the left content.
        assert np.all(frame[:20, :30, :] == 50)
        # Bottom 10 rows of left half are zero (padding).
        assert np.all(frame[20:, :30, :] == 0)
        # Right half is the right frame unchanged.
        assert np.all(frame[:, 30:, :] == 200)

    def test_taller_left_pads_right_frame_at_bottom(self, tmp_path):
        left_frames = [_frame(30, 30, 50)]
        right_frames = [_frame(20, 30, 200)]
        writer = FakeWriter()

        CompareVideos(
            FakeReader(left_frames),
            FakeReader(right_frames),
            writer,
        ).execute("l.mp4", "r.mp4", str(tmp_path / "o.mp4"))

        frame = writer.written_frames[0]
        assert frame.shape == (30, 60, 3)
        assert np.all(frame[:, :30, :] == 50)
        assert np.all(frame[:20, 30:, :] == 200)
        assert np.all(frame[20:, 30:, :] == 0)

    def test_output_meta_height_is_max_of_inputs(self, tmp_path):
        writer = FakeWriter()
        CompareVideos(
            FakeReader(
                [_frame(20, 30, 0)],
                meta=VideoMeta(fps=30.0, width=30, height=20, total_frames=1),
            ),
            FakeReader(
                [_frame(40, 30, 0)],
                meta=VideoMeta(fps=30.0, width=30, height=40, total_frames=1),
            ),
            writer,
        ).execute("l.mp4", "r.mp4", str(tmp_path / "o.mp4"))

        assert writer.opened_meta is not None
        assert writer.opened_meta.height == 40


class TestCompareVideosWidthDifference:
    def test_output_width_is_sum_when_widths_differ(self, tmp_path):
        left_frames = [_frame(20, 30, 10)]
        right_frames = [_frame(20, 50, 20)]
        writer = FakeWriter()

        CompareVideos(
            FakeReader(left_frames),
            FakeReader(right_frames),
            writer,
        ).execute("l.mp4", "r.mp4", str(tmp_path / "o.mp4"))

        assert writer.written_frames[0].shape == (20, 80, 3)
        assert writer.opened_meta is not None
        assert writer.opened_meta.width == 80


class TestCompareVideosEarlyTermination:
    def test_stops_at_shorter_video_length(self, tmp_path):
        left_frames = [_frame(20, 30, i) for i in range(5)]
        right_frames = [_frame(20, 30, i) for i in range(2)]
        writer = FakeWriter()

        CompareVideos(
            FakeReader(left_frames),
            FakeReader(right_frames),
            writer,
        ).execute("l.mp4", "r.mp4", str(tmp_path / "o.mp4"))

        assert len(writer.written_frames) == 2

    def test_stops_when_left_is_shorter(self, tmp_path):
        left_frames = [_frame(20, 30, i) for i in range(1)]
        right_frames = [_frame(20, 30, i) for i in range(5)]
        writer = FakeWriter()

        CompareVideos(
            FakeReader(left_frames),
            FakeReader(right_frames),
            writer,
        ).execute("l.mp4", "r.mp4", str(tmp_path / "o.mp4"))

        assert len(writer.written_frames) == 1


class TestCompareVideosCleanup:
    def test_closes_both_readers_and_writer_on_success(self, tmp_path):
        left_reader = FakeReader([_frame(20, 30, 0)])
        right_reader = FakeReader([_frame(20, 30, 0)])
        writer = FakeWriter()

        CompareVideos(left_reader, right_reader, writer).execute(
            "l.mp4", "r.mp4", str(tmp_path / "o.mp4")
        )

        assert left_reader.closed is True
        assert right_reader.closed is True
        assert writer.closed is True

    def test_closes_resources_even_when_writer_raises_mid_stream(self, tmp_path):
        class ExplodingWriter(FakeWriter):
            def write_frame(self, frame):
                raise RuntimeError("writer exploded")

        left_reader = FakeReader([_frame(20, 30, 0)])
        right_reader = FakeReader([_frame(20, 30, 0)])
        writer = ExplodingWriter()

        with pytest.raises(RuntimeError):
            CompareVideos(left_reader, right_reader, writer).execute(
                "l.mp4", "r.mp4", str(tmp_path / "o.mp4")
            )

        assert left_reader.closed is True
        assert right_reader.closed is True
        assert writer.closed is True

    def test_propagates_reader_value_error_when_left_unreadable(self, tmp_path):
        class BadReader(VideoReaderPort):
            def open(self, path):
                raise ValueError(f"Unable to open: {path}")

            def read_frame(self):
                return False, None

            def close(self):
                pass

        right_reader = FakeReader([_frame(20, 30, 0)])
        writer = FakeWriter()

        with pytest.raises(ValueError, match="Unable to open"):
            CompareVideos(BadReader(), right_reader, writer).execute(
                "l.mp4", "r.mp4", str(tmp_path / "o.mp4")
            )


class TestCompareVideosResult:
    def test_returns_resolved_absolute_output_path(self, tmp_path):
        left_reader = FakeReader([_frame(20, 30, 0)])
        right_reader = FakeReader([_frame(20, 30, 0)])
        writer = FakeWriter()
        target = tmp_path / "out.mp4"

        result = CompareVideos(left_reader, right_reader, writer).execute(
            "l.mp4", "r.mp4", str(target)
        )

        assert result == str(Path(target).resolve())
        assert Path(result).is_absolute()
