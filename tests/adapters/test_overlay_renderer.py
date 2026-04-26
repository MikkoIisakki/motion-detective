import numpy as np
import pytest

from src.adapters.overlay_renderer import OverlayRenderer
from src.domain.faults import FaultPriority, FaultResult, FaultSeverity, JointMeasurement, LiftPhase
from src.domain.models import BBox, Keypoint, Pose
from src.use_cases.analyze_lift import FrameAnalysis


def blank_frame(h=240, w=320):
    return np.zeros((h, w, 3), dtype=np.uint8)


def full_pose():
    return Pose([
        Keypoint("nose", 160, 40),
        Keypoint("left_shoulder", 140, 70),
        Keypoint("right_shoulder", 180, 70),
        Keypoint("left_elbow", 130, 100),
        Keypoint("right_elbow", 190, 100),
        Keypoint("left_wrist", 120, 130),
        Keypoint("right_wrist", 200, 130),
        Keypoint("left_hip", 145, 140),
        Keypoint("right_hip", 175, 140),
        Keypoint("left_knee", 145, 180),
        Keypoint("right_knee", 175, 180),
        Keypoint("left_ankle", 145, 220),
        Keypoint("right_ankle", 175, 220),
    ])


class TestOverlayRenderer:
    def setup_method(self):
        self.renderer = OverlayRenderer()

    def test_render_returns_same_shape_as_input(self):
        frame = blank_frame()
        out = self.renderer.render(frame, None, None)
        assert out.shape == frame.shape

    def test_render_does_not_mutate_input_frame(self):
        frame = blank_frame()
        original = frame.copy()
        self.renderer.render(frame, BBox(10, 10, 80, 120), None)
        np.testing.assert_array_equal(frame, original)

    def test_render_with_bbox_only_returns_unmodified_copy(self):
        # bbox alone draws nothing — skeleton is the visual indicator
        frame = blank_frame()
        out = self.renderer.render(frame, BBox(10, 10, 80, 120), None)
        np.testing.assert_array_equal(out, frame)

    def test_render_with_no_bbox_returns_unmodified_copy(self):
        frame = blank_frame()
        out = self.renderer.render(frame, None, None)
        np.testing.assert_array_equal(out, frame)

    def test_render_with_pose_modifies_output(self):
        frame = blank_frame()
        out = self.renderer.render(frame, BBox(100, 20, 120, 210), full_pose())
        assert not np.array_equal(out, frame)

    def test_render_with_pose_preserves_shape(self):
        frame = blank_frame()
        out = self.renderer.render(frame, BBox(100, 20, 120, 210), full_pose())
        assert out.shape == frame.shape

    def test_render_with_empty_pose_does_not_crash(self):
        frame = blank_frame()
        out = self.renderer.render(frame, BBox(10, 10, 80, 120), Pose([]))
        assert out.shape == frame.shape

    def test_render_with_partial_pose_skips_missing_joints(self):
        frame = blank_frame()
        partial = Pose([Keypoint("left_knee", 145, 180)])
        out = self.renderer.render(frame, BBox(10, 10, 80, 120), partial)
        assert out.shape == frame.shape

    def test_render_with_full_pose_draws_all_angles(self):
        frame = blank_frame(480, 640)
        out = self.renderer.render(frame, BBox(100, 20, 200, 400), full_pose())
        # Output should differ from blank — angles were drawn somewhere
        assert not np.array_equal(out, frame)

    def test_render_with_analysis_draws_phase_label(self):
        frame = blank_frame(480, 640)
        analysis = FrameAnalysis(phase=LiftPhase.FIRST_PULL, measurements=[], faults=[])
        out = self.renderer.render(frame, BBox(100, 20, 200, 400), full_pose(), analysis)
        # phase text appears somewhere in the top-left area
        assert not np.array_equal(out[:50, :300], frame[:50, :300])

    def test_render_with_faults_modifies_output(self):
        frame = blank_frame(480, 640)
        analysis = FrameAnalysis(
            phase=LiftPhase.SETUP,
            measurements=[JointMeasurement("knee_angle", 90.0)],
            faults=[
                FaultResult(
                    joint="knee_angle",
                    severity=FaultSeverity.FAULT,
                    priority=FaultPriority.PERFORMANCE,
                    feedback="Bend the knees more",
                )
            ],
        )
        out = self.renderer.render(frame, BBox(100, 20, 200, 400), full_pose(), analysis)
        assert not np.array_equal(out, frame)

    def test_render_without_analysis_still_works(self):
        # backwards-compatible: no analysis arg → no phase/fault labels, but still renders skeleton
        frame = blank_frame(480, 640)
        out = self.renderer.render(frame, BBox(100, 20, 200, 400), full_pose())
        assert out.shape == frame.shape
