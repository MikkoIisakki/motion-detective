from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.domain.analysis import FrameAnalysis
from src.domain.models import BBox, Pose


class FrameRendererPort(ABC):
    @abstractmethod
    def render(
        self,
        frame: np.ndarray,
        bbox: BBox | None,
        pose: Pose | None,
        analysis: FrameAnalysis | None = None,
    ) -> np.ndarray:
        """Return a new frame with overlay drawn (skeleton, angles, phase, faults)."""
