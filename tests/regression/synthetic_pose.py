"""Side-view 2D pose builder used to author regression-clip fixtures.

Given a `PoseSpec` (joint angles + anchor), produces a `Pose` whose measured
joint angles match the spec to within a pixel-quantisation tolerance (~2 deg).

Conventions:
- Image coordinates (x right, y down). Lifter faces +x.
- Joint angles follow the production `joint_angle` definition:
    knee_angle  = angle(hip, knee, ankle)
    hip_angle   = angle(shoulder, hip, knee)
    elbow_angle = angle(shoulder, elbow, wrist)
- The construction is not biomechanically faithful; it just maps angles to
  keypoints deterministically.

Arm placement modes:
- Natural mode (default): the upper arm hangs from the shoulder and the
  forearm rotates so that elbow_angle is correct, with the wrist forward of
  the elbow.
- Anchored-wrist mode (when `wrist_y_offset` is provided): the wrist is
  placed at (shoulder_x, anchor_y + wrist_y_offset) and the elbow is solved
  via an isoceles triangle (UPPER == FOREARM) so the requested elbow_angle
  still holds. This lets a clip drive the phase detector by pinning wrist_y
  without distorting the elbow rule.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.models import Keypoint, Pose

SHIN_LEN = 100
THIGH_LEN = 100
TORSO_LEN = 100
UPPER_ARM_LEN = 50
FOREARM_LEN = 50

# Per-joint left-to-right widths in pixels. Shoulders are wider than hips and
# limbs taper inward so the rendered figure reads as a body rather than a
# vertical stick.
#
# The L-side x is the angle-math source of truth: it sits a small fixed offset
# (`_LEFT_OFFSET`) inside the centerline geometry produced by the limb math.
# The R-side x is then placed `width` pixels to the right of the L-side. This
# keeps all `left_*` keypoints shifted by the *same* amount from the limb-math
# centerline, so the production `joint_angle` reads back the requested angles
# (the L-side triangle is a pure translation of the centerline triangle).
_LR_WIDTHS = {
    "ankle": 24,
    "knee": 24,
    "hip": 32,
    "shoulder": 50,
    "elbow": 50,
    "wrist": 50,
}
_LEFT_OFFSET = 5

# Head sits above the shoulder midpoint along the torso axis. ~30% of torso
# length matches typical human head-to-shoulder offset and is large enough to
# stay clearly above the shoulder line at the line-thickness used by the
# renderer.
HEAD_OFFSET = 30


@dataclass(frozen=True)
class PoseSpec:
    knee_angle: float
    hip_angle: float
    elbow_angle: float
    anchor_x: int = 320
    anchor_y: int = 400
    wrist_y_offset: float | None = None


def build_side_pose(spec: PoseSpec) -> Pose:
    ankle_x = float(spec.anchor_x)
    ankle_y = float(spec.anchor_y)

    knee_x = ankle_x
    knee_y = ankle_y - SHIN_LEN

    knee_rad = math.radians(spec.knee_angle)
    hip_x = knee_x - THIGH_LEN * math.sin(knee_rad)
    hip_y = knee_y + THIGH_LEN * math.cos(knee_rad)

    bc_math_angle = math.atan2(-(knee_y - hip_y), knee_x - hip_x)
    ba_math_angle = bc_math_angle + math.radians(spec.hip_angle)
    shoulder_x = hip_x + TORSO_LEN * math.cos(ba_math_angle)
    shoulder_y = hip_y - TORSO_LEN * math.sin(ba_math_angle)

    if spec.wrist_y_offset is None:
        elbow_x, elbow_y, wrist_x, wrist_y = _natural_arm(
            shoulder_x, shoulder_y, spec.elbow_angle
        )
    else:
        wrist_x = shoulder_x
        wrist_y = ankle_y + float(spec.wrist_y_offset)
        elbow_x, elbow_y = _isoceles_elbow(
            shoulder_x, shoulder_y, wrist_x, wrist_y, spec.elbow_angle
        )

    keypoints = _build_lr(
        ankle=(ankle_x, ankle_y),
        knee=(knee_x, knee_y),
        hip=(hip_x, hip_y),
        shoulder=(shoulder_x, shoulder_y),
        elbow=(elbow_x, elbow_y),
        wrist=(wrist_x, wrist_y),
    )
    nose = _nose_keypoint(keypoints, ba_math_angle)
    keypoints.append(nose)
    return Pose(keypoints)


def _nose_keypoint(keypoints: list[Keypoint], torso_math_angle: float) -> Keypoint:
    """Place the nose `HEAD_OFFSET` px past the shoulder midpoint, along the
    torso axis. Using the midpoint of `left_shoulder` and `right_shoulder` keeps
    the head visually centred on the (asymmetric) shoulder line. The math-frame
    `torso_math_angle` is the hip→shoulder vector; extending in that direction
    makes the head tilt with the back.
    """
    left = next(kp for kp in keypoints if kp.name == "left_shoulder")
    right = next(kp for kp in keypoints if kp.name == "right_shoulder")
    mid_x = (left.x + right.x) / 2.0
    mid_y = (left.y + right.y) / 2.0
    nose_x = mid_x + HEAD_OFFSET * math.cos(torso_math_angle)
    nose_y = mid_y - HEAD_OFFSET * math.sin(torso_math_angle)
    return Keypoint("nose", int(round(nose_x)), int(round(nose_y)))


def _natural_arm(
    shoulder_x: float, shoulder_y: float, elbow_angle: float
) -> tuple[float, float, float, float]:
    elbow_x = shoulder_x
    elbow_y = shoulder_y + UPPER_ARM_LEN
    ba_elbow_math_angle = math.radians(90.0 - elbow_angle)
    wrist_x = elbow_x + FOREARM_LEN * math.cos(ba_elbow_math_angle)
    wrist_y = elbow_y - FOREARM_LEN * math.sin(ba_elbow_math_angle)
    return elbow_x, elbow_y, wrist_x, wrist_y


def _isoceles_elbow(
    sx: float, sy: float, wx: float, wy: float, elbow_angle: float
) -> tuple[float, float]:
    """Solve elbow position on the perpendicular bisector of (S, W) so that
    angle(S, E, W) == elbow_angle. Picks the side with positive x (forward)
    when shoulder and wrist share an x; otherwise picks the +x perpendicular.
    """
    mx, my = (sx + wx) / 2.0, (sy + wy) / 2.0
    dx, dy = wx - sx, wy - sy
    d = math.hypot(dx, dy)
    if d == 0.0:
        return sx, sy
    half_apex_rad = math.radians((180.0 - elbow_angle) / 2.0)
    h = (d / 2.0) * math.tan(half_apex_rad)
    perp1 = (-dy / d, dx / d)
    perp2 = (dy / d, -dx / d)
    perp = perp1 if perp1[0] >= perp2[0] else perp2
    return mx + h * perp[0], my + h * perp[1]


def _build_lr(*, ankle, knee, hip, shoulder, elbow, wrist) -> list[Keypoint]:
    def pair(name: str, point: tuple[float, float]) -> list[Keypoint]:
        x, y = point
        left_x = x - _LEFT_OFFSET
        right_x = left_x + _LR_WIDTHS[name]
        return [
            Keypoint(f"left_{name}", int(round(left_x)), int(round(y))),
            Keypoint(f"right_{name}", int(round(right_x)), int(round(y))),
        ]
    return (
        pair("ankle", ankle)
        + pair("knee", knee)
        + pair("hip", hip)
        + pair("shoulder", shoulder)
        + pair("elbow", elbow)
        + pair("wrist", wrist)
    )
