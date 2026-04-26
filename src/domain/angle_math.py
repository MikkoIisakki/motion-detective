from __future__ import annotations

import math

from src.domain.models import Keypoint


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
