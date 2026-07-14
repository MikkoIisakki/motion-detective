from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VideoMeta:
    fps: float
    width: int
    height: int
    total_frames: int


class VideoDecodeError(ValueError):
    """A frame failed to decode before the expected end of the stream.

    Subclasses ValueError so callers that already treat ValueError as
    "problem with the video" (validator, CLI) degrade gracefully.
    """


class VideoReaderPort(ABC):
    @abstractmethod
    def open(self, path: str) -> VideoMeta:
        """Open video file and return metadata. Raises ValueError if file cannot be opened."""

    @abstractmethod
    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        """Read the next frame. Returns (True, frame) or (False, None) at end of video.

        May raise VideoDecodeError when a frame fails to decode before the
        expected end of the stream (i.e. the failure is corruption, not EOF).
        """

    @abstractmethod
    def close(self) -> None:
        """Release video resources."""
