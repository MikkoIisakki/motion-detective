import pytest
import yaml

from src.domain.faults import AngleThreshold, FaultPriority, FaultSeverity, LiftPhase
from src.domain.knowledge_base import KnowledgeBase, KnowledgeBaseError, RuleSpec

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


def _rule_spec() -> RuleSpec:
    return RuleSpec(
        threshold=AngleThreshold(good=(70, 110), warning=(50, 70), fault=(0, 50)),
        feedback="fix this",
        priority=FaultPriority.PERFORMANCE,
    )


class TestRuleSpec:
    def test_classify_good(self):
        assert _rule_spec().classify(90) == FaultSeverity.GOOD

    def test_classify_warning(self):
        assert _rule_spec().classify(60) == FaultSeverity.WARNING

    def test_classify_fault(self):
        assert _rule_spec().classify(30) == FaultSeverity.FAULT

    def test_exposes_bands_from_threshold(self):
        rule = _rule_spec()
        assert rule.good == (70, 110)
        assert rule.warning == (50, 70)
        assert rule.fault == (0, 50)


def _yaml_with_rule(joint: str = "hip_angle", phase: str = "first_pull", **overrides) -> str:
    spec = {
        "good": [70, 110],
        "warning": [50, 70],
        "fault": [0, 50],
        "feedback": "Keep hips from rising early",
        "priority": "performance",
    }
    for key, value in overrides.items():
        if value is None:
            spec.pop(key, None)
        else:
            spec[key] = value
    return yaml.safe_dump({"snatch": {phase: {joint: spec}}})


class TestLoadValidation:
    def test_missing_required_key_names_rule_and_key(self):
        content = _yaml_with_rule(priority=None)
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)
        assert "priority" in str(exc.value)

    @pytest.mark.parametrize("band", ["good", "warning", "fault"])
    def test_range_must_have_two_elements(self, band):
        content = _yaml_with_rule(**{band: [70]})
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)
        assert band in str(exc.value)

    def test_range_must_be_numeric(self):
        content = _yaml_with_rule(good=["low", "high"])
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)
        assert "good" in str(exc.value)

    def test_range_must_be_a_list(self):
        content = _yaml_with_rule(good="70-110")
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)

    def test_range_lo_must_not_exceed_hi(self):
        content = _yaml_with_rule(good=[110, 70])
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)
        assert "good" in str(exc.value)

    def test_joint_must_be_measurable_by_analyzer(self):
        content = _yaml_with_rule(joint="ankle_angle")
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/ankle_angle" in str(exc.value)
        assert "knee_angle" in str(exc.value)

    def test_priority_must_be_known(self):
        content = _yaml_with_rule(priority="urgency")
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)
        assert "urgency" in str(exc.value)

    def test_feedback_must_be_nonempty(self):
        content = _yaml_with_rule(feedback="  ")
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)
        assert "feedback" in str(exc.value)

    def test_phase_must_be_a_known_lift_phase(self):
        content = _yaml_with_rule(phase="jerk_drive")
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/jerk_drive" in str(exc.value)

    def test_root_must_be_a_mapping(self):
        with pytest.raises(KnowledgeBaseError):
            KnowledgeBase.from_yaml("")

    def test_rule_must_be_a_mapping(self):
        content = yaml.safe_dump({"snatch": {"first_pull": {"hip_angle": "nope"}}})
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)


class TestBandConsistencyValidation:
    """The declared fault/warning bands must agree with what classify returns:
    classify checks good, then warning, then falls back to FAULT — so a
    declared band whose interior overlaps a higher-precedence band would lie.
    """

    def test_fault_band_overlapping_good_is_rejected(self):
        # 105 is inside both fault [100, 180] and good [70, 110] → classify
        # would say GOOD for a declared-fault angle.
        content = _yaml_with_rule(good=[70, 110], warning=[50, 70], fault=[100, 180])
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "snatch/first_pull/hip_angle" in str(exc.value)
        assert "fault" in str(exc.value)

    def test_fault_band_overlapping_warning_is_rejected(self):
        content = _yaml_with_rule(good=[70, 110], warning=[50, 70], fault=[60, 180])
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "fault" in str(exc.value)

    def test_warning_band_overlapping_good_is_rejected(self):
        content = _yaml_with_rule(good=[70, 110], warning=[60, 90], fault=[0, 60])
        with pytest.raises(KnowledgeBaseError) as exc:
            KnowledgeBase.from_yaml(content)
        assert "warning" in str(exc.value)

    def test_contiguous_bands_sharing_endpoints_are_accepted(self):
        # The shape the real knowledge base uses: bands touch at endpoints.
        content = _yaml_with_rule(good=[70, 110], warning=[110, 130], fault=[130, 180])
        kb = KnowledgeBase.from_yaml(content)
        assert kb.rules_for("snatch", LiftPhase.FIRST_PULL) != {}

    def test_real_knowledge_base_passes_validation(self):
        kb = KnowledgeBase.from_file("config/knowledge_base.yml")
        assert kb.lifts() == ["clean_and_jerk", "snatch"]


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
