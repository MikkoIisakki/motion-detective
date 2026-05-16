"""Confidence gating for pose keypoints.

Drops keypoints whose detector-reported confidence falls below a threshold.
Dropped keypoints become absent from the returned `Pose`, which lets the
existing `KeypointSmoother` bridge over them from prior frames.
"""
from __future__ import annotations

from src.domain.models import Pose


def gate_keypoints(pose: Pose, min_confidence: float) -> Pose:
    """Return a Pose containing only keypoints with confidence >= min_confidence."""
    return Pose([kp for kp in pose.keypoints if kp.confidence >= min_confidence])
