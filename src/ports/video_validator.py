from __future__ import annotations

from abc import ABC, abstractmethod


class VideoValidatorPort(ABC):
    @abstractmethod
    def validate(self, path: str) -> None:
        """Validate the video file at path. Raises ValueError with a descriptive message if invalid."""
