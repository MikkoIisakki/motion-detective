"""Property-based tests for joint_angle.

These pin the geometric contract of the angle math rather than individual
examples: the result is a valid angle in [0, 180], it is invariant under
the rigid motions + uniform scaling a camera reframing applies, argument
order of the ray endpoints doesn't matter, and degenerate (coincident)
inputs keep returning 0.0.

Coordinates are generated as floats: `Keypoint` is annotated with int pixel
coordinates, but `joint_angle` is float-generic and rigid-motion invariance
only holds over the reals (integer grids can't rotate exactly).
"""
import math

from hypothesis import assume, given
from hypothesis import strategies as st

from src.domain.angle_math import joint_angle
from src.domain.models import Keypoint

# acos is ill-conditioned near 0/180 deg (nearly collinear points), where a
# ~1e-14 float error in the cosine becomes a ~1e-4 deg angle error. With the
# leg-length and coordinate bounds below the worst case stays under 1e-3 deg,
# so 0.01 deg keeps a comfortable margin while still being a strict check.
ANGLE_TOLERANCE_DEG = 0.01
MIN_LEG_LENGTH = 1.0

coordinates = st.floats(min_value=-100.0, max_value=100.0)


def triplet(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> tuple[Keypoint, Keypoint, Keypoint]:
    return Keypoint("a", ax, ay), Keypoint("b", bx, by), Keypoint("c", cx, cy)


@st.composite
def angle_triplets(draw: st.DrawFn) -> tuple[Keypoint, Keypoint, Keypoint]:
    """Three points forming a well-defined angle: both rays at least MIN_LEG_LENGTH long."""
    ax, ay, bx, by, cx, cy = (draw(coordinates) for _ in range(6))
    assume(math.hypot(ax - bx, ay - by) >= MIN_LEG_LENGTH)
    assume(math.hypot(cx - bx, cy - by) >= MIN_LEG_LENGTH)
    return triplet(ax, ay, bx, by, cx, cy)


class TestJointAngleProperties:
    @given(ax=coordinates, ay=coordinates, bx=coordinates, by=coordinates, cx=coordinates, cy=coordinates)
    def test_result_is_always_within_0_and_180_degrees(self, ax, ay, bx, by, cx, cy):
        a, b, c = triplet(ax, ay, bx, by, cx, cy)
        assert 0.0 <= joint_angle(a, b, c) <= 180.0

    @given(points=angle_triplets(), dx=coordinates, dy=coordinates)
    def test_invariant_under_translation(self, points, dx, dy):
        a, b, c = points
        translated = [Keypoint(p.name, p.x + dx, p.y + dy) for p in points]
        assert abs(joint_angle(*translated) - joint_angle(a, b, c)) <= ANGLE_TOLERANCE_DEG

    @given(points=angle_triplets(), theta=st.floats(min_value=0.0, max_value=2.0 * math.pi))
    def test_invariant_under_rotation_about_origin(self, points, theta):
        a, b, c = points
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        rotated = [Keypoint(p.name, p.x * cos_t - p.y * sin_t, p.x * sin_t + p.y * cos_t) for p in points]
        assert abs(joint_angle(*rotated) - joint_angle(a, b, c)) <= ANGLE_TOLERANCE_DEG

    @given(points=angle_triplets(), scale=st.floats(min_value=0.1, max_value=10.0))
    def test_invariant_under_uniform_scaling(self, points, scale):
        a, b, c = points
        scaled = [Keypoint(p.name, p.x * scale, p.y * scale) for p in points]
        assert abs(joint_angle(*scaled) - joint_angle(a, b, c)) <= ANGLE_TOLERANCE_DEG

    @given(ax=coordinates, ay=coordinates, bx=coordinates, by=coordinates, cx=coordinates, cy=coordinates)
    def test_symmetric_in_the_ray_endpoints(self, ax, ay, bx, by, cx, cy):
        # Exact equality: swapping a and c only commutes float multiplications.
        a, b, c = triplet(ax, ay, bx, by, cx, cy)
        assert joint_angle(a, b, c) == joint_angle(c, b, a)

    @given(px=coordinates, py=coordinates, ox=coordinates, oy=coordinates)
    def test_coincident_endpoint_and_vertex_returns_zero(self, px, py, ox, oy):
        # Characterizes current behavior: any zero-length ray -> 0.0, not an error.
        vertex = Keypoint("b", px, py)
        coincident = Keypoint("p", px, py)
        other = Keypoint("o", ox, oy)
        assert joint_angle(coincident, vertex, other) == 0.0
        assert joint_angle(other, vertex, coincident) == 0.0
        assert joint_angle(coincident, vertex, coincident) == 0.0
