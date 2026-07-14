import pytest

from src.domain.faults import FaultPriority, FaultSeverity, JointMeasurement, LiftPhase
from src.domain.knowledge_base import KnowledgeBase
from src.use_cases.classify_frame import ClassifyFrame

KB_YAML = """
snatch:
  first_pull:
    hip_angle:
      good: [70, 110]
      warning: [50, 70]
      fault: [0, 50]
      feedback: "Keep hips from rising early"
      priority: performance
    knee_angle:
      good: [80, 120]
      warning: [60, 80]
      fault: [0, 60]
      feedback: "Maintain knee bend through first pull"
      priority: performance
"""


@pytest.fixture()
def use_case():
    kb = KnowledgeBase.from_yaml(KB_YAML)
    return ClassifyFrame(knowledge_base=kb)


class TestClassifyFrame:
    def test_returns_empty_when_no_measurements(self, use_case):
        results = use_case.execute("snatch", LiftPhase.FIRST_PULL, [])
        assert results == []

    def test_returns_good_result_for_in_range_angle(self, use_case):
        measurements = [JointMeasurement("hip_angle", 90.0)]
        results = use_case.execute("snatch", LiftPhase.FIRST_PULL, measurements)
        assert len(results) == 1
        assert results[0].severity == FaultSeverity.GOOD

    def test_returns_warning_for_angle_in_warning_range(self, use_case):
        measurements = [JointMeasurement("hip_angle", 60.0)]
        results = use_case.execute("snatch", LiftPhase.FIRST_PULL, measurements)
        assert results[0].severity == FaultSeverity.WARNING

    def test_returns_fault_for_angle_below_fault_threshold(self, use_case):
        measurements = [JointMeasurement("hip_angle", 30.0)]
        results = use_case.execute("snatch", LiftPhase.FIRST_PULL, measurements)
        assert results[0].severity == FaultSeverity.FAULT

    def test_result_includes_feedback_and_priority(self, use_case):
        measurements = [JointMeasurement("hip_angle", 30.0)]
        results = use_case.execute("snatch", LiftPhase.FIRST_PULL, measurements)
        assert results[0].feedback == "Keep hips from rising early"
        assert results[0].priority == FaultPriority.PERFORMANCE

    def test_ignores_measurements_with_no_matching_rule(self, use_case):
        measurements = [JointMeasurement("elbow_angle", 90.0)]
        results = use_case.execute("snatch", LiftPhase.FIRST_PULL, measurements)
        assert results == []

    def test_returns_result_for_each_matching_measurement(self, use_case):
        measurements = [
            JointMeasurement("hip_angle", 90.0),
            JointMeasurement("knee_angle", 100.0),
        ]
        results = use_case.execute("snatch", LiftPhase.FIRST_PULL, measurements)
        assert len(results) == 2

    def test_returns_empty_for_phase_with_no_rules(self, use_case):
        measurements = [JointMeasurement("hip_angle", 90.0)]
        results = use_case.execute("snatch", LiftPhase.CATCH, measurements)
        assert results == []

    def test_returns_empty_for_unknown_lift(self, use_case):
        measurements = [JointMeasurement("hip_angle", 90.0)]
        results = use_case.execute("clean_and_jerk", LiftPhase.FIRST_PULL, measurements)
        assert results == []
