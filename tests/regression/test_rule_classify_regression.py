"""Per-rule regression: every rule in `config/knowledge_base.yml` must
classify the band midpoints into the correct severity, and have a non-empty
feedback string with a known priority.

This is the comprehensive coverage net. The end-to-end clip tests in
`test_rule_regression.py` complement this by exercising the phase detector +
summary formatting on actual MP4s. Every phase in the YAML (including
transition, jerk_dip and jerk_catch) is reachable by the phase detector, so
this suite and the clip suite together keep all rules honest.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.faults import (
    FaultPriority,
    FaultSeverity,
    JointMeasurement,
    LiftPhase,
)
from src.domain.knowledge_base import KnowledgeBase, RuleSpec
from src.use_cases.classify_frame import ClassifyFrame

KB_PATH = Path(__file__).resolve().parents[2] / "config" / "knowledge_base.yml"


def _kb() -> KnowledgeBase:
    return KnowledgeBase.from_file(str(KB_PATH))


def _rule_params() -> list:
    kb = _kb()
    params = []
    for lift in kb.lifts():
        for phase_name, joints in kb.phases_for(lift).items():
            for joint, rule in joints.items():
                params.append(
                    pytest.param(
                        lift, phase_name, joint, rule,
                        id=f"{lift}::{phase_name}::{joint}",
                    )
                )
    return params


def _midpoint(band: tuple[float, float]) -> float:
    return (band[0] + band[1]) / 2.0


@pytest.mark.parametrize(("lift", "phase_name", "joint", "rule"), _rule_params())
class TestRuleClassifies:
    def test_good_midpoint_is_good(
        self, lift: str, phase_name: str, joint: str, rule: RuleSpec
    ) -> None:
        assert rule.classify(_midpoint(rule.good)) == FaultSeverity.GOOD

    def test_warning_midpoint_is_warning(
        self, lift: str, phase_name: str, joint: str, rule: RuleSpec
    ) -> None:
        # Skip rules whose warning band is degenerate (lo == hi) — the classify
        # method still works but the midpoint test isn't informative.
        if rule.warning[0] == rule.warning[1]:
            pytest.skip("degenerate warning band")
        assert rule.classify(_midpoint(rule.warning)) == FaultSeverity.WARNING

    def test_fault_midpoint_is_fault(
        self, lift: str, phase_name: str, joint: str, rule: RuleSpec
    ) -> None:
        if rule.fault[0] == rule.fault[1]:
            pytest.skip("degenerate fault band")
        assert rule.classify(_midpoint(rule.fault)) == FaultSeverity.FAULT

    def test_has_nonempty_feedback(
        self, lift: str, phase_name: str, joint: str, rule: RuleSpec
    ) -> None:
        assert rule.feedback.strip(), "rule feedback must be non-empty"

    def test_priority_is_known(
        self, lift: str, phase_name: str, joint: str, rule: RuleSpec
    ) -> None:
        assert rule.priority in {
            FaultPriority.SAFETY,
            FaultPriority.PERFORMANCE,
            FaultPriority.EFFICIENCY,
        }


def test_classify_frame_uses_kb_rules() -> None:
    """End-to-end smoke for the ClassifyFrame use case against the real KB —
    one fault and one good measurement, asserts severities are propagated."""
    kb = _kb()
    classify = ClassifyFrame(kb)
    # Snatch first_pull hip_angle FAULT band = [0, 50] -> 25 is FAULT.
    results = classify.execute(
        "snatch",
        LiftPhase.FIRST_PULL,
        [JointMeasurement("hip_angle", 25.0), JointMeasurement("knee_angle", 120.0)],
    )
    by_joint = {r.joint: r for r in results}
    assert by_joint["hip_angle"].severity == FaultSeverity.FAULT
    assert by_joint["knee_angle"].severity == FaultSeverity.GOOD
    assert by_joint["hip_angle"].feedback
    assert by_joint["hip_angle"].priority in {
        FaultPriority.SAFETY, FaultPriority.PERFORMANCE, FaultPriority.EFFICIENCY,
    }
