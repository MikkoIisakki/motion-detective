from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.ports.video_reader import VideoMeta


class VideoWriterPort(ABC):
    @abstractmethod
    def open(self, path: str, meta: VideoMeta) -> None:
        """Open output file for writing with the given video properties."""

    @abstractmethod
    def write_frame(self, frame: np.ndarray) -> None:
        """Write a single frame to the output."""

    @abstractmethod
    def close(self) -> None:
        """Finalise and release the output file."""
