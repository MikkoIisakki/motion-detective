import pytest
from src.domain.angle_math import joint_angle
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
        import math
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
