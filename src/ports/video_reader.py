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


class VideoReaderPort(ABC):
    @abstractmethod
    def open(self, path: str) -> VideoMeta:
        """Open video file and return metadata. Raises ValueError if file cannot be opened."""

    @abstractmethod
    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        """Read the next frame. Returns (True, frame) or (False, None) at end of video."""

    @abstractmethod
    def close(self) -> None:
        """Release video resources."""
