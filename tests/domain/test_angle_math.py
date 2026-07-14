import pytest

from src.domain.angle_math import ANGLE_DEFINITIONS, MEASURABLE_JOINTS, joint_angle
from src.domain.models import Keypoint


class TestJointAngle:
    def test_right_angle(self):
        # a=top, b=corner, c=right → 90°
        a = Keypoint("a", 0, 0)
        b = Keypoint("b", 0, 1)
        c = Keypoint("c", 1, 1)
        assert 89.0 <= joint_angle(a, b, c) <= 91.0

    def test_straight_line_is_180_degrees(self):
        a = Keypoint("a", 0, 0)
        b = Keypoint("b", 1, 0)
        c = Keypoint("c", 2, 0)
        assert joint_angle(a, b, c) == pytest.approx(180.0, abs=0.1)

    def test_equilateral_triangle_is_60_degrees(self):
        a = Keypoint("a", 0, 0)
        b = Keypoint("b", 1, 0)
        c = Keypoint("c", 0, 1)
        angle = joint_angle(a, b, c)
        assert 44.0 <= angle <= 46.0  # 45° for this specific triangle

    def test_angle_is_symmetric(self):
        # joint_angle(a, b, c) == joint_angle(c, b, a)
        a = Keypoint("a", 10, 50)
        b = Keypoint("b", 30, 80)
        c = Keypoint("c", 60, 40)
        assert joint_angle(a, b, c) == pytest.approx(joint_angle(c, b, a), abs=0.001)

    def test_coincident_points_return_zero(self):
        # zero-length vector → undefined, returns 0.0 safely
        a = Keypoint("a", 5, 5)
        b = Keypoint("b", 5, 5)
        c = Keypoint("c", 10, 10)
        assert joint_angle(a, b, c) == 0.0

    def test_returns_float(self):
        a = Keypoint("a", 0, 0)
        b = Keypoint("b", 1, 0)
        c = Keypoint("c", 2, 1)
        result = joint_angle(a, b, c)
        assert isinstance(result, float)


class TestAngleDefinitions:
    def test_pins_the_six_measured_triplets(self):
        triplets = [(d.joint, d.vertex_a, d.vertex_b, d.vertex_c) for d in ANGLE_DEFINITIONS]
        assert triplets == [
            ("knee_angle", "left_hip", "left_knee", "left_ankle"),
            ("knee_angle", "right_hip", "right_knee", "right_ankle"),
            ("hip_angle", "left_shoulder", "left_hip", "left_knee"),
            ("hip_angle", "right_shoulder", "right_hip", "right_knee"),
            ("elbow_angle", "left_shoulder", "left_elbow", "left_wrist"),
            ("elbow_angle", "right_shoulder", "right_elbow", "right_wrist"),
        ]

    def test_each_joint_is_measured_on_both_sides(self):
        sides_by_joint: dict[str, set[str]] = {}
        for definition in ANGLE_DEFINITIONS:
            sides_by_joint.setdefault(definition.joint, set()).add(definition.side)
        assert all(sides == {"left", "right"} for sides in sides_by_joint.values())

    def test_measurable_joints_derives_from_the_definitions(self):
        assert frozenset({"knee_angle", "hip_angle", "elbow_angle"}) == MEASURABLE_JOINTS
        assert frozenset(d.joint for d in ANGLE_DEFINITIONS) == MEASURABLE_JOINTS
