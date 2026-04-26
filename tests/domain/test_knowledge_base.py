import pytest
import yaml

from src.domain.faults import FaultPriority, FaultSeverity, LiftPhase
from src.domain.knowledge_base import KnowledgeBase, RuleSpec


MINIMAL_YAML = """
snatch:
  first_pull:
    hip_angle:
      good: [70, 110]
      warning: [50, 70]
      fault: [0, 50]
      feedback: "Keep hips from rising early"
      priority: performance
"""


class TestRuleSpec:
    def test_classify_good(self):
        rule = RuleSpec(
            good=(70, 110), warning=(50, 70), fault=(0, 50),
            feedback="fix this", priority=FaultPriority.PERFORMANCE,
        )
        assert rule.classify(90) == FaultSeverity.GOOD

    def test_classify_warning(self):
        rule = RuleSpec(
            good=(70, 110), warning=(50, 70), fault=(0, 50),
            feedback="fix this", priority=FaultPriority.PERFORMANCE,
        )
        assert rule.classify(60) == FaultSeverity.WARNING

    def test_classify_fault(self):
        rule = RuleSpec(
            good=(70, 110), warning=(50, 70), fault=(0, 50),
            feedback="fix this", priority=FaultPriority.PERFORMANCE,
        )
        assert rule.classify(30) == FaultSeverity.FAULT


class TestKnowledgeBase:
    def test_load_from_yaml_string(self):
        kb = KnowledgeBase.from_yaml(MINIMAL_YAML)
        assert kb is not None

    def test_rules_for_known_phase(self):
        kb = KnowledgeBase.from_yaml(MINIMAL_YAML)
        rules = kb.rules_for("snatch", LiftPhase.FIRST_PULL)
        assert "hip_angle" in rules

    def test_rules_for_unknown_phase_returns_empty(self):
        kb = KnowledgeBase.from_yaml(MINIMAL_YAML)
        rules = kb.rules_for("snatch", LiftPhase.CATCH)
        assert rules == {}

    def test_rules_for_unknown_lift_returns_empty(self):
        kb = KnowledgeBase.from_yaml(MINIMAL_YAML)
        rules = kb.rules_for("deadlift", LiftPhase.FIRST_PULL)
        assert rules == {}

    def test_rule_spec_has_correct_thresholds(self):
        kb = KnowledgeBase.from_yaml(MINIMAL_YAML)
        rule = kb.rules_for("snatch", LiftPhase.FIRST_PULL)["hip_angle"]
        assert rule.good == (70, 110)
        assert rule.warning == (50, 70)
        assert rule.fault == (0, 50)

    def test_rule_spec_has_feedback_and_priority(self):
        kb = KnowledgeBase.from_yaml(MINIMAL_YAML)
        rule = kb.rules_for("snatch", LiftPhase.FIRST_PULL)["hip_angle"]
        assert rule.feedback == "Keep hips from rising early"
        assert rule.priority == FaultPriority.PERFORMANCE

    def test_load_from_file(self, tmp_path):
        f = tmp_path / "kb.yml"
        f.write_text(MINIMAL_YAML)
        kb = KnowledgeBase.from_file(str(f))
        assert kb.rules_for("snatch", LiftPhase.FIRST_PULL) != {}

    def test_raises_for_missing_file(self):
        with pytest.raises(FileNotFoundError):
            KnowledgeBase.from_file("does_not_exist.yml")
