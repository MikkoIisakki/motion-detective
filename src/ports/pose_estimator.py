from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from src.domain.models import BBox, Pose


class PoseEstimatorPort(ABC):
    @abstractmethod
    def estimate(self, frame: np.ndarray, bbox: BBox) -> Pose | None:
        """Estimate pose keypoints for the subject within bbox. Returns None if estimation fails."""
