from pathlib import Path

import cv2
import numpy as np

from src.adapters.overlay_renderer import OverlayRenderer, _angle_label
from src.domain.analysis import FrameAnalysis
from src.domain.angle_math import ANGLE_DEFINITIONS
from src.domain.faults import FaultPriority, FaultResult, FaultSeverity, JointMeasurement, LiftPhase
from src.domain.models import BBox, Keypoint, Pose


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

    def test_angle_labels_are_drawn_in_bottom_left_panel(self):
        frame = blank_frame(480, 640)
        out = self.renderer.render(frame, BBox(100, 20, 200, 400), full_pose())
        h, w = frame.shape[:2]
        bottom_left = out[h // 2 :, : w // 3]
        top_right = out[: h // 2, 2 * w // 3 :]
        # angle panel must mark bottom-left, not top-right
        assert not np.array_equal(bottom_left, frame[h // 2 :, : w // 3])
        np.testing.assert_array_equal(top_right, frame[: h // 2, 2 * w // 3 :])

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


_GOLDEN_PATH = Path(__file__).parent / "golden" / "overlay_full_frame.png"


def gradient_background(h=240, w=320):
    """Deterministic non-uniform background so the golden also pins blending
    against real pixel content, not just drawing onto black."""
    yy, xx = np.mgrid[0:h, 0:w]
    blue = (xx * 255 // (w - 1)).astype(np.uint8)
    green = (yy * 255 // (h - 1)).astype(np.uint8)
    red = ((xx + yy) * 255 // (w + h - 2)).astype(np.uint8)
    return np.dstack([blue, green, red])


def full_frame_analysis():
    return FrameAnalysis(
        phase=LiftPhase.CATCH,
        measurements=[JointMeasurement("knee_angle", 90.0), JointMeasurement("elbow_angle", 150.0)],
        faults=[
            FaultResult(
                joint="knee_angle",
                severity=FaultSeverity.FAULT,
                priority=FaultPriority.SAFETY,
                feedback="Catch deeper",
            ),
            FaultResult(
                joint="elbow_angle",
                severity=FaultSeverity.WARNING,
                priority=FaultPriority.EFFICIENCY,
                feedback="Lock out the elbows",
            ),
        ],
    )


class TestOverlayGoldenFrame:
    """Pins the exact rendered pixels of a fully-populated frame (bbox + pose
    + analysis with a FAULT and a WARNING) against a committed reference PNG.

    Exact pixel equality is used: OpenCV's Hershey fonts and anti-aliased
    primitives are drawn with its own fixed-point integer rasterizer (no
    system font stack), so output is deterministic for the pinned
    opencv-contrib-python version — verified by the determinism test below.

    To regenerate after an intentional rendering change: delete
    tests/adapters/golden/overlay_full_frame.png and rerun this test (a
    missing golden is rewritten from the current renderer output — inspect
    the new PNG visually and commit it).
    """

    def _render_full_frame(self):
        renderer = OverlayRenderer()
        return renderer.render(
            gradient_background(),
            BBox(100, 20, 120, 210),
            full_pose(),
            full_frame_analysis(),
        )

    def test_render_is_deterministic(self):
        np.testing.assert_array_equal(self._render_full_frame(), self._render_full_frame())

    def test_full_frame_render_matches_golden(self):
        out = self._render_full_frame()
        if not _GOLDEN_PATH.exists():
            _GOLDEN_PATH.parent.mkdir(exist_ok=True)
            cv2.imwrite(str(_GOLDEN_PATH), out)
        golden = cv2.imread(str(_GOLDEN_PATH), cv2.IMREAD_COLOR)
        assert golden is not None, f"unreadable golden file: {_GOLDEN_PATH}"
        np.testing.assert_array_equal(out, golden)


class TestAngleLabel:
    def test_derives_panel_labels_from_the_shared_angle_definitions(self):
        assert [_angle_label(d) for d in ANGLE_DEFINITIONS] == [
            "Knee L",
            "Knee R",
            "Hip L",
            "Hip R",
            "Elbow L",
            "Elbow R",
        ]
