import pytest

from src.domain.faults import LiftPhase
from src.domain.models import Keypoint, Pose
from src.domain.phase_detector import PhaseDetector, PoseSignal


def pose_with(wrist_y: int, ankle_y: int, knee_angle_left: int = 180, knee_angle_right: int = 180,
              hip_y: int = 100, shoulder_y: int = 50) -> Pose:
    """Build a pose where wrist/ankle/hip/shoulder are at given y-coords."""
    return Pose([
        Keypoint("left_wrist", 100, wrist_y),
        Keypoint("right_wrist", 110, wrist_y),
        Keypoint("left_ankle", 100, ankle_y),
        Keypoint("right_ankle", 110, ankle_y),
        Keypoint("left_hip", 100, hip_y),
        Keypoint("right_hip", 110, hip_y),
        Keypoint("left_shoulder", 100, shoulder_y),
        Keypoint("right_shoulder", 110, shoulder_y),
        Keypoint("left_knee", 100, hip_y + 40),
        Keypoint("right_knee", 110, hip_y + 40),
    ])


class TestPoseSignal:
    def test_extracts_average_wrist_height(self):
        pose = pose_with(wrist_y=200, ankle_y=300)
        signal = PoseSignal.from_pose(pose)
        assert signal.wrist_y == 200

    def test_extracts_average_ankle_height(self):
        pose = pose_with(wrist_y=200, ankle_y=300)
        signal = PoseSignal.from_pose(pose)
        assert signal.ankle_y == 300

    def test_returns_none_for_signal_when_keypoints_missing(self):
        pose = Pose([Keypoint("nose", 0, 0)])
        signal = PoseSignal.from_pose(pose)
        assert signal.wrist_y is None
        assert signal.ankle_y is None


class TestPhaseDetector:
    def test_initial_state_is_idle(self):
        detector = PhaseDetector()
        assert detector.current_phase == LiftPhase.IDLE

    def test_idle_to_setup_when_wrist_at_or_below_ankle(self):
        # wrist y >= ankle y in image coords (lower = higher y)
        detector = PhaseDetector()
        pose = pose_with(wrist_y=300, ankle_y=300)
        phase = detector.update(pose)
        assert phase == LiftPhase.SETUP

    def test_setup_to_first_pull_when_wrist_starts_rising(self):
        detector = PhaseDetector(rise_threshold_px=5)
        # establish setup
        detector.update(pose_with(wrist_y=300, ankle_y=300))
        # wrist rising rapidly (lower y = higher in image)
        phase = detector.update(pose_with(wrist_y=290, ankle_y=300))
        phase = detector.update(pose_with(wrist_y=275, ankle_y=300))
        assert phase == LiftPhase.FIRST_PULL

    def test_second_pull_to_catch_when_wrist_above_shoulder(self):
        detector = PhaseDetector()
        # walk through phases
        detector.update(pose_with(wrist_y=300, ankle_y=300))  # setup
        detector.update(pose_with(wrist_y=270, ankle_y=300))  # first_pull
        detector.update(pose_with(wrist_y=240, ankle_y=300))  # transition/second_pull
        detector.update(pose_with(wrist_y=200, ankle_y=300))
        # wrist now above shoulder (smaller y)
        phase = detector.update(pose_with(wrist_y=30, ankle_y=300, shoulder_y=50))
        assert phase == LiftPhase.CATCH

    def test_recovery_when_hip_rising_after_catch(self):
        detector = PhaseDetector()
        detector._phase = LiftPhase.CATCH
        # hip rising (smaller y after catch)
        pose = pose_with(wrist_y=30, ankle_y=300, shoulder_y=50, hip_y=180)
        detector.update(pose)
        pose = pose_with(wrist_y=30, ankle_y=300, shoulder_y=50, hip_y=120)
        phase = detector.update(pose)
        assert phase == LiftPhase.RECOVERY

    def test_skips_phase_change_when_pose_signal_incomplete(self):
        detector = PhaseDetector()
        detector.update(pose_with(wrist_y=300, ankle_y=300))  # setup
        # incomplete pose → keep current phase
        empty = Pose([Keypoint("nose", 0, 0)])
        phase = detector.update(empty)
        assert phase == LiftPhase.SETUP
