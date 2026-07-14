"""Per-frame failure accounting for video pipelines.

Individual frame failures are recorded and skipped so one bad frame cannot
abort a run, but a streak of more than `max_consecutive_failures` failures
means the video is systematically broken and processing must stop.
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MAX_CONSECUTIVE_FAILURES = 5


@dataclass(frozen=True)
class FrameFailure:
    frame_index: int
    error: str


class ExcessiveFrameFailuresError(RuntimeError):
    """Raised when more than the allowed number of consecutive frames fail."""


class FrameFailurePolicy:
    def __init__(self, max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES) -> None:
        if max_consecutive_failures < 1:
            raise ValueError("max_consecutive_failures must be at least 1")
        self._max_consecutive_failures = max_consecutive_failures
        self._consecutive_failures = 0
        self._failures: list[FrameFailure] = []

    def record_failure(self, frame_index: int, error: Exception) -> None:
        self._failures.append(FrameFailure(frame_index=frame_index, error=str(error) or type(error).__name__))
        self._consecutive_failures += 1
        if self._consecutive_failures > self._max_consecutive_failures:
            raise ExcessiveFrameFailuresError(
                f"Aborting: more than {self._max_consecutive_failures} consecutive frames failed"
                f" (last error at frame {frame_index}: {self._failures[-1].error})"
            )

    def record_success(self) -> None:
        self._consecutive_failures = 0

    @property
    def failures(self) -> list[FrameFailure]:
        return list(self._failures)
