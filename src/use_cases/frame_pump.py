"""Shared read → process → write frame pump for video use cases.

Owns the frame loop and the try/finally release of the already-opened readers
and writer. With a `FrameFailurePolicy`, decode errors from a reader and
exceptions from the per-frame processor are recorded and skipped instead of
aborting the run; the policy itself aborts on excessive consecutive failures.
Writer errors always propagate — losing the output file is never recoverable.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

from src.domain.frame_failure_policy import FrameFailurePolicy
from src.ports.video_reader import VideoDecodeError, VideoReaderPort
from src.ports.video_writer import VideoWriterPort

FrameProcessor = Callable[[Sequence[np.ndarray], int], np.ndarray]


def pump_frames(
    readers: Sequence[VideoReaderPort],
    writer: VideoWriterPort,
    process: FrameProcessor,
    failure_policy: FrameFailurePolicy | None = None,
) -> int:
    """Pump frames from `readers` (in lock-step) through `process` into `writer`.

    Expects `readers` and `writer` to be open; always closes them. Stops when
    any reader reaches end of stream. Returns the number of frames attempted
    (failed frames included), so frame indices stay aligned with the source.
    """
    frame_index = 0
    try:
        while True:
            try:
                frames = _read_lock_step(readers)
            except VideoDecodeError as error:
                _record_or_raise(failure_policy, frame_index, error)
                frame_index += 1
                continue
            if frames is None:
                break
            try:
                rendered = process(frames, frame_index)
            except Exception as error:
                _record_or_raise(failure_policy, frame_index, error)
                frame_index += 1
                continue
            writer.write_frame(rendered)
            if failure_policy is not None:
                failure_policy.record_success()
            frame_index += 1
    finally:
        for reader in readers:
            reader.close()
        writer.close()
    return frame_index


def _read_lock_step(readers: Sequence[VideoReaderPort]) -> list[np.ndarray] | None:
    frames: list[np.ndarray] = []
    for reader in readers:
        ok, frame = reader.read_frame()
        if not ok or frame is None:
            return None
        frames.append(frame)
    return frames


def _record_or_raise(policy: FrameFailurePolicy | None, frame_index: int, error: Exception) -> None:
    if policy is None:
        raise error
    policy.record_failure(frame_index, error)
