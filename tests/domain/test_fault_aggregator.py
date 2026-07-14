from src.domain.fault_aggregator import (
    NO_FAULTS_MESSAGE,
    FaultAggregator,
    format_timestamp,
)
from src.domain.faults import FaultPriority, FaultResult, FaultSeverity


def _fault(
    feedback: str = "Keep knees tracking over toes",
    severity: FaultSeverity = FaultSeverity.FAULT,
    priority: FaultPriority = FaultPriority.SAFETY,
    joint: str = "knee_angle",
) -> FaultResult:
    return FaultResult(joint=joint, severity=severity, priority=priority, feedback=feedback)


class TestFormatTimestamp:
    def test_zero_seconds(self):
        assert format_timestamp(0.0) == "00:00.000"

    def test_sub_second_value_keeps_milliseconds(self):
        assert format_timestamp(0.5) == "00:00.500"

    def test_minutes_roll_over(self):
        assert format_timestamp(61.25) == "01:01.250"

    def test_rounds_to_nearest_millisecond(self):
        assert format_timestamp(1.0004) == "00:01.000"


class TestFaultAggregatorGrouping:
    def test_no_observations_yields_no_groups(self):
        assert FaultAggregator().groups == []

    def test_single_fault_creates_group_spanning_one_timestamp(self):
        agg = FaultAggregator()
        agg.observe("setup", [_fault()], ts_seconds=0.0)

        [group] = agg.groups
        assert group.phase == "setup"
        assert group.feedback == "Keep knees tracking over toes"
        assert group.severity is FaultSeverity.FAULT
        assert group.priority is FaultPriority.SAFETY
        assert group.start_seconds == 0.0
        assert group.end_seconds == 0.0
        assert group.hit_count == 1

    def test_repeated_fault_extends_group_and_counts_hits(self):
        agg = FaultAggregator()
        agg.observe("setup", [_fault()], ts_seconds=0.0)
        agg.observe("setup", [_fault()], ts_seconds=0.5)

        [group] = agg.groups
        assert group.start_seconds == 0.0
        assert group.end_seconds == 0.5
        assert group.hit_count == 2

    def test_same_feedback_in_different_phase_creates_separate_group(self):
        agg = FaultAggregator()
        agg.observe("setup", [_fault()], ts_seconds=0.0)
        agg.observe("first_pull", [_fault()], ts_seconds=0.5)

        assert len(agg.groups) == 2

    def test_non_actionable_faults_are_ignored(self):
        agg = FaultAggregator()
        agg.observe("setup", [_fault(severity=FaultSeverity.GOOD)], ts_seconds=0.0)

        assert agg.groups == []


class TestFaultAggregatorSummary:
    def test_no_faults_yields_placeholder_message(self):
        assert FaultAggregator().summary_lines() == [NO_FAULTS_MESSAGE]

    def test_line_format_matches_severity_priority_phase_feedback_and_frames(self):
        agg = FaultAggregator()
        agg.observe("setup", [_fault()], ts_seconds=0.0)
        agg.observe("setup", [_fault()], ts_seconds=0.5)

        assert agg.summary_lines() == [
            "00:00.000-00:00.500 [FAULT/safety] setup: Keep knees tracking over toes (2 frames)"
        ]

    def test_faults_are_listed_before_warnings(self):
        agg = FaultAggregator()
        warning = _fault(
            feedback="Stay over the mid-foot longer",
            severity=FaultSeverity.WARNING,
            priority=FaultPriority.PERFORMANCE,
        )
        agg.observe("setup", [warning], ts_seconds=0.0)
        agg.observe("first_pull", [_fault()], ts_seconds=1.0)

        lines = agg.summary_lines()
        assert "[FAULT/safety]" in lines[0]
        assert "[WARNING/performance]" in lines[1]

    def test_equal_severity_orders_by_start_time(self):
        agg = FaultAggregator()
        later = _fault(feedback="Later fault")
        earlier = _fault(feedback="Earlier fault")
        agg.observe("setup", [later], ts_seconds=2.0)
        agg.observe("setup", [earlier], ts_seconds=1.0)

        lines = agg.summary_lines()
        assert "Earlier fault" in lines[0]
        assert "Later fault" in lines[1]

    def test_multiple_faults_in_single_observation_each_grouped(self):
        agg = FaultAggregator()
        agg.observe("setup", [_fault(), _fault(feedback="Other cue")], ts_seconds=0.0)

        assert len(agg.groups) == 2
