import numpy as np
import pytest

from src.domain.frame_failure_policy import ExcessiveFrameFailuresError, FrameFailurePolicy
from src.ports.video_reader import VideoDecodeError, VideoMeta, VideoReaderPort
from src.ports.video_writer import VideoWriterPort
from src.use_cases.frame_pump import pump_frames


def _frame(fill: int) -> np.ndarray:
    return np.full((4, 4, 3), fill, dtype=np.uint8)


class FakeReader(VideoReaderPort):
    """Reader whose read results are scripted: a frame, or an exception to raise."""

    def __init__(self, script: list[np.ndarray | Exception]):
        self._script = script
        self._index = 0
        self.closed = False

    def open(self, path: str) -> VideoMeta:
        return VideoMeta(fps=30.0, width=4, height=4, total_frames=len(self._script))

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._index >= len(self._script):
            return False, None
        item = self._script[self._index]
        self._index += 1
        if isinstance(item, Exception):
            raise item
        return True, item

    def close(self) -> None:
        self.closed = True


class FakeWriter(VideoWriterPort):
    def __init__(self):
        self.written_frames: list[np.ndarray] = []
        self.closed = False

    def open(self, path: str, meta: VideoMeta) -> None:
        pass

    def write_frame(self, frame: np.ndarray) -> None:
        self.written_frames.append(frame)

    def close(self) -> None:
        self.closed = True


class TestPumpHappyPath:
    def test_writes_each_processed_frame_and_reports_count(self):
        reader = FakeReader([_frame(1), _frame(2)])
        writer = FakeWriter()

        count = pump_frames([reader], writer, lambda frames, index: frames[0])

        assert count == 2
        assert len(writer.written_frames) == 2

    def test_passes_running_frame_index_to_process(self):
        reader = FakeReader([_frame(1), _frame(2)])
        indices: list[int] = []

        def record(frames, index):
            indices.append(index)
            return frames[0]

        pump_frames([reader], FakeWriter(), record)

        assert indices == [0, 1]

    def test_closes_reader_and_writer_after_pumping(self):
        reader = FakeReader([_frame(1)])
        writer = FakeWriter()

        pump_frames([reader], writer, lambda frames, index: frames[0])

        assert reader.closed is True
        assert writer.closed is True


class TestPumpLockStep:
    def test_reads_all_readers_in_lock_step(self):
        left = FakeReader([_frame(1), _frame(2)])
        right = FakeReader([_frame(10), _frame(20)])
        writer = FakeWriter()

        pump_frames([left, right], writer, lambda frames, index: frames[0] + frames[1])

        assert len(writer.written_frames) == 2
        assert np.all(writer.written_frames[0] == 11)

    def test_stops_when_any_reader_is_exhausted(self):
        left = FakeReader([_frame(1)])
        right = FakeReader([_frame(10), _frame(20)])
        writer = FakeWriter()

        count = pump_frames([left, right], writer, lambda frames, index: frames[0])

        assert count == 1
        assert len(writer.written_frames) == 1


class TestPumpErrorPropagationWithoutPolicy:
    def test_process_error_propagates_and_resources_close(self):
        reader = FakeReader([_frame(1)])
        writer = FakeWriter()

        def explode(frames, index):
            raise RuntimeError("process exploded")

        with pytest.raises(RuntimeError, match="process exploded"):
            pump_frames([reader], writer, explode)

        assert reader.closed is True
        assert writer.closed is True

    def test_decode_error_propagates_and_resources_close(self):
        reader = FakeReader([VideoDecodeError("corrupt frame")])
        writer = FakeWriter()

        with pytest.raises(VideoDecodeError):
            pump_frames([reader], writer, lambda frames, index: frames[0])

        assert reader.closed is True
        assert writer.closed is True


class TestPumpFailurePolicy:
    def test_process_failure_is_recorded_and_pumping_continues(self):
        reader = FakeReader([_frame(1), _frame(2), _frame(3)])
        writer = FakeWriter()
        policy = FrameFailurePolicy()

        def fail_on_second(frames, index):
            if index == 1:
                raise RuntimeError("estimator exploded")
            return frames[0]

        count = pump_frames([reader], writer, fail_on_second, failure_policy=policy)

        assert count == 3
        assert len(writer.written_frames) == 2
        assert [f.frame_index for f in policy.failures] == [1]
        assert policy.failures[0].error == "estimator exploded"

    def test_decode_error_is_recorded_and_pumping_continues(self):
        reader = FakeReader([_frame(1), VideoDecodeError("corrupt frame"), _frame(3)])
        writer = FakeWriter()
        policy = FrameFailurePolicy()

        count = pump_frames([reader], writer, lambda frames, index: frames[0], failure_policy=policy)

        assert count == 3
        assert len(writer.written_frames) == 2
        assert [f.frame_index for f in policy.failures] == [1]

    def test_frame_index_keeps_advancing_past_failed_frames(self):
        reader = FakeReader([_frame(1), _frame(2), _frame(3)])
        indices: list[int] = []
        policy = FrameFailurePolicy()

        def fail_first(frames, index):
            indices.append(index)
            if index == 0:
                raise RuntimeError("boom")
            return frames[0]

        pump_frames([reader], FakeWriter(), fail_first, failure_policy=policy)

        assert indices == [0, 1, 2]

    def test_excessive_consecutive_failures_abort_and_close_resources(self):
        reader = FakeReader([_frame(i) for i in range(10)])
        writer = FakeWriter()
        policy = FrameFailurePolicy(max_consecutive_failures=2)

        def always_fail(frames, index):
            raise RuntimeError("boom")

        with pytest.raises(ExcessiveFrameFailuresError):
            pump_frames([reader], writer, always_fail, failure_policy=policy)

        assert reader.closed is True
        assert writer.closed is True

    def test_successful_frames_reset_the_consecutive_count(self):
        script: list[np.ndarray | Exception] = [
            _frame(1),
            VideoDecodeError("bad"),
            VideoDecodeError("bad"),
            _frame(2),
            VideoDecodeError("bad"),
            VideoDecodeError("bad"),
            _frame(3),
        ]
        reader = FakeReader(script)
        writer = FakeWriter()
        policy = FrameFailurePolicy(max_consecutive_failures=2)

        count = pump_frames([reader], writer, lambda frames, index: frames[0], failure_policy=policy)

        assert count == 7
        assert len(writer.written_frames) == 3
        assert len(policy.failures) == 4

    def test_writer_errors_are_not_swallowed_by_the_policy(self):
        class ExplodingWriter(FakeWriter):
            def write_frame(self, frame):
                raise RuntimeError("writer exploded")

        reader = FakeReader([_frame(1)])
        writer = ExplodingWriter()

        with pytest.raises(RuntimeError, match="writer exploded"):
            pump_frames([reader], writer, lambda frames, index: frames[0], failure_policy=FrameFailurePolicy())

        assert writer.closed is True
