"""Sanity tests for the side-view synthetic pose builder.

The builder must turn requested joint angles into Keypoint coordinates that the
production `joint_angle` function measures back to within tolerance. Tolerance
is loose (~2°) because keypoints are quantised to integer pixels.
"""
from __future__ import annotations

import pytest

from src.domain.angle_math import joint_angle
from tests.regression.synthetic_pose import PoseSpec, build_side_pose


def _hip_angle(pose):
    return joint_angle(
        pose.get("left_shoulder"), pose.get("left_hip"), pose.get("left_knee")
    )


def _knee_angle(pose):
    return joint_angle(
        pose.get("left_hip"), pose.get("left_knee"), pose.get("left_ankle")
    )


def _elbow_angle(pose):
    return joint_angle(
        pose.get("left_shoulder"), pose.get("left_elbow"), pose.get("left_wrist")
    )


class TestBuildSidePose:
    @pytest.mark.parametrize("requested", [60.0, 90.0, 120.0, 150.0, 175.0])
    def test_knee_angle_matches_request(self, requested):
        pose = build_side_pose(
            PoseSpec(knee_angle=requested, hip_angle=90.0, elbow_angle=180.0)
        )
        assert _knee_angle(pose) == pytest.approx(requested, abs=2.0)

    @pytest.mark.parametrize("requested", [45.0, 70.0, 100.0, 140.0, 175.0])
    def test_hip_angle_matches_request(self, requested):
        pose = build_side_pose(
            PoseSpec(knee_angle=100.0, hip_angle=requested, elbow_angle=180.0)
        )
        assert _hip_angle(pose) == pytest.approx(requested, abs=2.0)

    @pytest.mark.parametrize("requested", [45.0, 90.0, 135.0, 170.0])
    def test_elbow_angle_matches_request(self, requested):
        pose = build_side_pose(
            PoseSpec(knee_angle=100.0, hip_angle=70.0, elbow_angle=requested)
        )
        assert _elbow_angle(pose) == pytest.approx(requested, abs=2.0)

    def test_all_required_keypoints_present(self):
        pose = build_side_pose(PoseSpec(knee_angle=90, hip_angle=60, elbow_angle=170))
        for name in [
            "left_ankle", "right_ankle",
            "left_knee", "right_knee",
            "left_hip", "right_hip",
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
        ]:
            assert pose.get(name) is not None, f"missing keypoint: {name}"

    def test_wrist_y_offset_overrides_wrist_position(self):
        pose = build_side_pose(
            PoseSpec(
                knee_angle=90,
                hip_angle=60,
                elbow_angle=180,
                anchor_y=400,
                wrist_y_offset=-5,
            )
        )
        # wrist_y_offset is applied relative to ankle_y (anchor_y)
        assert pose.get("left_wrist").y == pytest.approx(400 - 5, abs=1)

    def test_anchor_shifts_pose_in_image(self):
        a = build_side_pose(PoseSpec(knee_angle=90, hip_angle=60, elbow_angle=170, anchor_x=200))
        b = build_side_pose(PoseSpec(knee_angle=90, hip_angle=60, elbow_angle=170, anchor_x=400))
        # ankle x should reflect the anchor shift
        assert (b.get("left_ankle").x - a.get("left_ankle").x) == pytest.approx(200, abs=1)

    @pytest.mark.parametrize("elbow_request", [120.0, 150.0, 180.0])
    def test_wrist_y_offset_keeps_requested_elbow_angle(self, elbow_request):
        # Anchored-wrist mode must still hit the elbow_angle spec — otherwise
        # phase-driving fixtures would create false elbow faults. Tolerance is
        # loose because the wrist-shoulder span is short (<40px) so integer
        # pixel quantisation amplifies into a few degrees of angle drift.
        pose = build_side_pose(
            PoseSpec(
                knee_angle=130,
                hip_angle=130,
                elbow_angle=elbow_request,
                anchor_y=400,
                wrist_y_offset=-230,
            )
        )
        assert _elbow_angle(pose) == pytest.approx(elbow_request, abs=5.0)


class TestHumanProportions:
    """The synthetic figure should look recognisably human, not a thin stick.

    Two visual properties matter for the rendered MP4s:
    - shoulders are wider than hips (taper, not a vertical line)
    - a `nose` keypoint exists above the shoulders so the overlay renderer
      can draw the head segments.
    """

    def test_shoulder_width_greater_than_hip_width(self):
        pose = build_side_pose(PoseSpec(knee_angle=100, hip_angle=90, elbow_angle=170))
        shoulder_width = abs(
            pose.get("left_shoulder").x - pose.get("right_shoulder").x
        )
        hip_width = abs(pose.get("left_hip").x - pose.get("right_hip").x)
        assert shoulder_width > hip_width

    def test_nose_keypoint_present(self):
        pose = build_side_pose(PoseSpec(knee_angle=100, hip_angle=90, elbow_angle=170))
        assert pose.get("nose") is not None

    def test_nose_above_shoulders(self):
        # "Above" in image coords means smaller y.
        pose = build_side_pose(PoseSpec(knee_angle=100, hip_angle=90, elbow_angle=170))
        nose = pose.get("nose")
        shoulder_y = pose.get("left_shoulder").y
        assert nose.y < shoulder_y

    def test_nose_tracks_torso_lean(self):
        # In a setup pose the back is angled forward (shoulder x ahead of hip
        # x); the head extends in the same direction past the shoulders, so
        # nose x must lie forward of (>) the shoulder midpoint x.
        pose = build_side_pose(PoseSpec(knee_angle=90, hip_angle=45, elbow_angle=180))
        left_shoulder_x = pose.get("left_shoulder").x
        right_shoulder_x = pose.get("right_shoulder").x
        hip_x = pose.get("left_hip").x
        shoulder_mid_x = (left_shoulder_x + right_shoulder_x) / 2.0
        assert left_shoulder_x > hip_x  # sanity: torso leans forward
        nose_x = pose.get("nose").x
        # Head leans forward with the torso (further from the hip than the
        # shoulder midpoint is).
        assert nose_x > shoulder_mid_x
