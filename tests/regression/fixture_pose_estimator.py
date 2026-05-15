"""Deterministic PoseEstimatorPort implementation used by regression-clip tests.

YOLO is bypassed so tests don't depend on model accuracy. The estimator
returns the authored pose for each successive frame; after the sequence ends
it repeats the last pose so trailing frames don't raise.
"""
from __future__ import annotations

import numpy as np

from src.domain.models import BBox, Pose
from src.ports.pose_estimator import PoseEstimatorPort


class FixturePoseEstimator(PoseEstimatorPort):
    def __init__(self, poses: list[Pose | None]) -> None:
        self._poses = poses
        self._index = 0

    def estimate(self, frame: np.ndarray, bbox: BBox) -> Pose | None:
        if not self._poses:
            return None
        if self._index >= len(self._poses):
            return self._poses[-1]
        pose = self._poses[self._index]
        self._index += 1
        return pose
