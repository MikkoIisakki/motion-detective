from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.domain.models import BBox


class DetectorPort(ABC):
    @abstractmethod
    def detect(self, frame: np.ndarray) -> BBox | None:
        """Detect the primary subject in the frame. Returns None if not found."""
