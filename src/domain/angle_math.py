from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.models import Keypoint


@dataclass(frozen=True)
class AngleDefinition:
    """One measurable joint angle: the angle ABC at vertex B."""

    joint: str
    vertex_a: str
    vertex_b: str
    vertex_c: str

    @property
    def side(self) -> str:
        return "left" if self.vertex_b.startswith("left_") else "right"


# The single source of truth for which joint angles the pipeline measures
# and how — consumers average or label per side as needed.
ANGLE_DEFINITIONS: tuple[AngleDefinition, ...] = (
    AngleDefinition("knee_angle", "left_hip", "left_knee", "left_ankle"),
    AngleDefinition("knee_angle", "right_hip", "right_knee", "right_ankle"),
    AngleDefinition("hip_angle", "left_shoulder", "left_hip", "left_knee"),
    AngleDefinition("hip_angle", "right_shoulder", "right_hip", "right_knee"),
    AngleDefinition("elbow_angle", "left_shoulder", "left_elbow", "left_wrist"),
    AngleDefinition("elbow_angle", "right_shoulder", "right_elbow", "right_wrist"),
)

MEASURABLE_JOINTS: frozenset[str] = frozenset(d.joint for d in ANGLE_DEFINITIONS)


def joint_angle(a: Keypoint, b: Keypoint, c: Keypoint) -> float:
    """Return the angle ABC in degrees, where B is the vertex joint.

    Returns 0.0 when either vector has zero length (coincident points).
    """
    ba_x, ba_y = a.x - b.x, a.y - b.y
    bc_x, bc_y = c.x - b.x, c.y - b.y

    denom = math.hypot(ba_x, ba_y) * math.hypot(bc_x, bc_y)
    if denom == 0.0:
        return 0.0

    cos_angle = (ba_x * bc_x + ba_y * bc_y) / denom
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))
