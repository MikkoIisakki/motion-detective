import pytest

from src.domain.faults import FaultSeverity, LiftPhase
from src.domain.knowledge_base import KnowledgeBase
from src.domain.models import Keypoint, Pose
from src.domain.phase_detector import PhaseDetector
from src.use_cases.analyze_lift import AnalyzeLift, FrameAnalysis


KB_YAML = """
snatch:
  setup:
    knee_angle:
      good: [70, 110]
      warning: [110, 130]
      fault: [130, 180]
      feedback: "Bend the knees more"
      priority: performance
    hip_angle:
      good: [40, 70]
      warning: [70, 90]
      fault: [90, 180]
      feedback: "Lower hips"
      priority: performance
"""


def setup_pose() -> Pose:
    """Pose with knee at ~90° and hip at ~50° — both 'good' for setup."""
    return Pose([
        # ankle directly below knee, knee directly below hip → ~90° knee bend
        Keypoint("left_ankle", 100, 300),
        Keypoint("right_ankle", 110, 300),
        Keypoint("left_knee", 100, 230),
        Keypoint("right_knee", 110, 230),
        # shoulder offset to make hip angle ~50°
        Keypoint("left_hip", 100, 200),
        Keypoint("right_hip", 110, 200),
        Keypoint("left_shoulder", 60, 170),
        Keypoint("right_shoulder", 70, 170),
        Keypoint("left_wrist", 100, 295),
        Keypoint("right_wrist", 110, 295),
    ])


@pytest.fixture()
def use_case():
    kb = KnowledgeBase.from_yaml(KB_YAML)
    return AnalyzeLift(
        knowledge_base=kb,
        phase_detector=PhaseDetector(),
        lift="snatch",
    )


class TestAnalyzeLift:
    def test_returns_frame_analysis_with_phase(self, use_case):
        analysis = use_case.analyse_frame(setup_pose())
        assert isinstance(analysis, FrameAnalysis)
        assert analysis.phase == LiftPhase.SETUP

    def test_returns_empty_faults_when_no_pose(self, use_case):
        empty_pose = Pose([])
        analysis = use_case.analyse_frame(empty_pose)
        assert analysis.faults == []

    def test_returns_faults_for_setup_phase(self, use_case):
        analysis = use_case.analyse_frame(setup_pose())
        # at least one fault classification should be present
        assert len(analysis.faults) > 0

    def test_records_measurements_for_inspection(self, use_case):
        analysis = use_case.analyse_frame(setup_pose())
        joints = {m.joint for m in analysis.measurements}
        assert "knee_angle" in joints
        assert "hip_angle" in joints

    def test_phase_persists_across_frames(self, use_case):
        use_case.analyse_frame(setup_pose())
        second = use_case.analyse_frame(setup_pose())
        assert second.phase == LiftPhase.SETUP

    def test_no_faults_for_unknown_lift(self):
        kb = KnowledgeBase.from_yaml(KB_YAML)
        uc = AnalyzeLift(
            knowledge_base=kb,
            phase_detector=PhaseDetector(),
            lift="deadlift",
        )
        analysis = uc.analyse_frame(setup_pose())
        assert analysis.faults == []
