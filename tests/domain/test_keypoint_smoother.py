import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.keypoint_smoother import KeypointSmoother
from src.domain.models import Keypoint, Pose


class TestKeypointSmoother:
    def test_first_pose_passes_through_unchanged(self):
        smoother = KeypointSmoother(alpha=0.5)
        pose = Pose([Keypoint("nose", 100, 200)])
        out = smoother.smooth(pose)
        assert out.get("nose").as_tuple() == (100, 200)

    def test_subsequent_pose_blended_with_previous(self):
        # alpha=0.5: result = 0.5 * new + 0.5 * old
        smoother = KeypointSmoother(alpha=0.5)
        smoother.smooth(Pose([Keypoint("nose", 100, 200)]))
        out = smoother.smooth(Pose([Keypoint("nose", 200, 400)]))
        assert out.get("nose").as_tuple() == (150, 300)

    def test_smoothing_reduces_jitter(self):
        # Alternating signal — smoothed values should converge toward mean
        smoother = KeypointSmoother(alpha=0.5)
        smoother.smooth(Pose([Keypoint("nose", 100, 100)]))
        smoother.smooth(Pose([Keypoint("nose", 200, 100)]))
        smoother.smooth(Pose([Keypoint("nose", 100, 100)]))
        out = smoother.smooth(Pose([Keypoint("nose", 200, 100)]))
        # After several iterations of alternating 100/200, smoothed is between
        assert 100 < out.get("nose").x < 200

    def test_alpha_one_means_no_smoothing(self):
        smoother = KeypointSmoother(alpha=1.0)
        smoother.smooth(Pose([Keypoint("nose", 100, 200)]))
        out = smoother.smooth(Pose([Keypoint("nose", 999, 999)]))
        assert out.get("nose").as_tuple() == (999, 999)

    def test_alpha_zero_freezes_at_first_value(self):
        smoother = KeypointSmoother(alpha=0.0)
        smoother.smooth(Pose([Keypoint("nose", 100, 200)]))
        out = smoother.smooth(Pose([Keypoint("nose", 999, 999)]))
        assert out.get("nose").as_tuple() == (100, 200)

    def test_invalid_alpha_below_zero_raises(self):
        with pytest.raises(ValueError):
            KeypointSmoother(alpha=-0.1)

    def test_invalid_alpha_above_one_raises(self):
        with pytest.raises(ValueError):
            KeypointSmoother(alpha=1.1)

    def test_new_keypoint_appears_unchanged(self):
        # If a keypoint wasn't in previous pose, it's used as-is
        smoother = KeypointSmoother(alpha=0.5)
        smoother.smooth(Pose([Keypoint("nose", 100, 200)]))
        out = smoother.smooth(Pose([Keypoint("nose", 200, 400), Keypoint("left_knee", 50, 80)]))
        assert out.get("left_knee").as_tuple() == (50, 80)

    def test_missing_keypoint_in_new_pose_keeps_previous(self):
        # If a keypoint disappears (occlusion), reuse last known position
        smoother = KeypointSmoother(alpha=0.5)
        smoother.smooth(Pose([Keypoint("nose", 100, 200), Keypoint("left_knee", 300, 400)]))
        out = smoother.smooth(Pose([Keypoint("nose", 200, 400)]))
        # nose smoothed normally
        assert out.get("nose").as_tuple() == (150, 300)
        # left_knee carried over from previous frame
        assert out.get("left_knee").as_tuple() == (300, 400)

    def test_reset_clears_state(self):
        smoother = KeypointSmoother(alpha=0.5)
        smoother.smooth(Pose([Keypoint("nose", 100, 200)]))
        smoother.reset()
        out = smoother.smooth(Pose([Keypoint("nose", 999, 999)]))
        assert out.get("nose").as_tuple() == (999, 999)


_pixel = st.integers(min_value=-10_000, max_value=10_000)


class TestKeypointSmootherProperties:
    """EMA invariant: a smoothed coordinate is a (rounded) convex combination
    of the previous smoothed value and the new observation, so it can never
    overshoot either — it always lies in [min(prev, new), max(prev, new)]."""

    @given(
        alpha=st.floats(min_value=0.0, max_value=1.0),
        prev_x=_pixel, prev_y=_pixel, new_x=_pixel, new_y=_pixel,
    )
    def test_smoothed_coordinates_lie_between_previous_and_new(self, alpha, prev_x, prev_y, new_x, new_y):
        smoother = KeypointSmoother(alpha=alpha)
        smoother.smooth(Pose([Keypoint("nose", prev_x, prev_y)]))
        out = smoother.smooth(Pose([Keypoint("nose", new_x, new_y)]))
        kp = out.get("nose")
        assert min(prev_x, new_x) <= kp.x <= max(prev_x, new_x)
        assert min(prev_y, new_y) <= kp.y <= max(prev_y, new_y)
