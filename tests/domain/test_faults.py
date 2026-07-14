from src.domain.faults import (
    AngleThreshold,
    FaultPriority,
    FaultResult,
    FaultSeverity,
    JointMeasurement,
    LiftPhase,
)


class TestLiftPhase:
    def test_all_phases_defined(self):
        phases = {p.value for p in LiftPhase}
        assert phases == {
            "idle",
            "setup",
            "first_pull",
            "transition",
            "second_pull",
            "catch",
            "recovery",
            "jerk_dip",
            "jerk_catch",
        }


class TestFaultSeverity:
    def test_all_severities_defined(self):
        assert {s.name for s in FaultSeverity} == {"GOOD", "WARNING", "FAULT"}

    def test_ordering_good_lt_warning_lt_fault(self):
        assert FaultSeverity.GOOD < FaultSeverity.WARNING < FaultSeverity.FAULT


class TestFaultPriority:
    def test_all_priorities_defined(self):
        assert {p.value for p in FaultPriority} == {"safety", "performance", "efficiency"}


class TestAngleThreshold:
    def test_classify_good_when_angle_in_good_range(self):
        threshold = AngleThreshold(good=(70, 110), warning=(50, 70), fault=(0, 50))
        assert threshold.classify(90) == FaultSeverity.GOOD

    def test_classify_warning_when_angle_in_warning_range(self):
        threshold = AngleThreshold(good=(70, 110), warning=(50, 70), fault=(0, 50))
        assert threshold.classify(60) == FaultSeverity.WARNING

    def test_classify_fault_when_angle_below_fault_range(self):
        threshold = AngleThreshold(good=(70, 110), warning=(50, 70), fault=(0, 50))
        assert threshold.classify(30) == FaultSeverity.FAULT

    def test_classify_good_at_boundary(self):
        threshold = AngleThreshold(good=(70, 110), warning=(50, 70), fault=(0, 50))
        assert threshold.classify(70) == FaultSeverity.GOOD
        assert threshold.classify(110) == FaultSeverity.GOOD

    def test_classify_returns_worst_matching_severity(self):
        # angle outside all ranges → fault
        threshold = AngleThreshold(good=(70, 110), warning=(50, 70), fault=(0, 50))
        assert threshold.classify(150) == FaultSeverity.FAULT


class TestJointMeasurement:
    def test_creation(self):
        m = JointMeasurement(joint="left_knee", angle=85.0)
        assert m.joint == "left_knee"
        assert m.angle == 85.0


class TestFaultResult:
    def test_creation(self):
        result = FaultResult(
            joint="left_knee",
            severity=FaultSeverity.WARNING,
            priority=FaultPriority.PERFORMANCE,
            feedback="Keep your hips from rising before the bar passes the knee",
        )
        assert result.joint == "left_knee"
        assert result.severity == FaultSeverity.WARNING
        assert result.priority == FaultPriority.PERFORMANCE

    def test_is_actionable_for_warning_and_fault(self):
        warning = FaultResult("j", FaultSeverity.WARNING, FaultPriority.PERFORMANCE, "fix this")
        fault = FaultResult("j", FaultSeverity.FAULT, FaultPriority.SAFETY, "fix this now")
        good = FaultResult("j", FaultSeverity.GOOD, FaultPriority.EFFICIENCY, "")
        assert warning.is_actionable is True
        assert fault.is_actionable is True
        assert good.is_actionable is False
