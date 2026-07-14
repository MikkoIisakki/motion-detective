from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.domain.angle_math import MEASURABLE_JOINTS
from src.domain.faults import AngleThreshold, FaultPriority, FaultSeverity, LiftPhase


class KnowledgeBaseError(ValueError):
    """Raised when the knowledge-base YAML is malformed or inconsistent."""


_REQUIRED_KEYS = ("good", "warning", "fault", "feedback", "priority")
_BAND_KEYS = ("good", "warning", "fault")

_KNOWN_PHASES = frozenset(p.value for p in LiftPhase)
_KNOWN_PRIORITIES = frozenset(p.value for p in FaultPriority)


@dataclass(frozen=True)
class RuleSpec:
    threshold: AngleThreshold
    feedback: str
    priority: FaultPriority

    @property
    def good(self) -> tuple[float, float]:
        return self.threshold.good

    @property
    def warning(self) -> tuple[float, float]:
        return self.threshold.warning

    @property
    def fault(self) -> tuple[float, float]:
        return self.threshold.fault

    def classify(self, angle: float) -> FaultSeverity:
        return self.threshold.classify(angle)


class KnowledgeBase:
    def __init__(self, rules: dict[str, dict[str, dict[str, RuleSpec]]]) -> None:
        # rules[lift][phase][joint] -> RuleSpec
        self._rules = rules

    def rules_for(self, lift: str, phase: LiftPhase) -> dict[str, RuleSpec]:
        return self._rules.get(lift, {}).get(phase.value, {})

    def lifts(self) -> list[str]:
        return sorted(self._rules.keys())

    def phases_for(self, lift: str) -> dict[str, dict[str, RuleSpec]]:
        return self._rules.get(lift, {})

    def has_lift(self, lift: str) -> bool:
        return lift in self._rules

    @classmethod
    def from_yaml(cls, content: str) -> KnowledgeBase:
        data = yaml.safe_load(content)
        return cls(_parse(data))

    @classmethod
    def from_file(cls, path: str) -> KnowledgeBase:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {path}")
        return cls.from_yaml(p.read_text())


def _parse(data: object) -> dict[str, dict[str, dict[str, RuleSpec]]]:
    if not isinstance(data, dict):
        raise KnowledgeBaseError("Knowledge base root must be a mapping of lifts")
    rules: dict[str, dict[str, dict[str, RuleSpec]]] = {}
    for lift, phases in data.items():
        if not isinstance(phases, dict):
            raise KnowledgeBaseError(f"{lift}: phases must be a mapping")
        rules[lift] = {}
        for phase, joints in phases.items():
            _validate_phase(lift, phase)
            if not isinstance(joints, dict):
                raise KnowledgeBaseError(f"{lift}/{phase}: joints must be a mapping")
            rules[lift][phase] = {
                joint: _parse_rule(f"{lift}/{phase}/{joint}", joint, spec)
                for joint, spec in joints.items()
            }
    return rules


def _validate_phase(lift: str, phase: str) -> None:
    if phase not in _KNOWN_PHASES:
        raise KnowledgeBaseError(
            f"{lift}/{phase}: unknown phase; known phases: "
            + ", ".join(sorted(_KNOWN_PHASES))
        )


def _parse_rule(context: str, joint: str, spec: object) -> RuleSpec:
    if joint not in MEASURABLE_JOINTS:
        raise KnowledgeBaseError(
            f"{context}: joint '{joint}' is not measurable by the analyzer; "
            "measurable joints: " + ", ".join(sorted(MEASURABLE_JOINTS))
        )
    if not isinstance(spec, dict):
        raise KnowledgeBaseError(f"{context}: rule must be a mapping")
    missing = [key for key in _REQUIRED_KEYS if key not in spec]
    if missing:
        raise KnowledgeBaseError(
            f"{context}: missing required key(s): " + ", ".join(missing)
        )
    bands = {key: _parse_band(context, key, spec[key]) for key in _BAND_KEYS}
    _validate_band_consistency(context, **bands)
    return RuleSpec(
        threshold=AngleThreshold(**bands),
        feedback=_parse_feedback(context, spec["feedback"]),
        priority=_parse_priority(context, spec["priority"]),
    )


def _parse_band(context: str, name: str, value: object) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise KnowledgeBaseError(
            f"{context}: '{name}' range must be a 2-element [lo, hi] list, got {value!r}"
        )
    lo, hi = value
    if not _is_number(lo) or not _is_number(hi):
        raise KnowledgeBaseError(
            f"{context}: '{name}' range bounds must be numeric, got {value!r}"
        )
    if lo > hi:
        raise KnowledgeBaseError(
            f"{context}: '{name}' range lo must be <= hi, got [{lo}, {hi}]"
        )
    return (float(lo), float(hi))


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_band_consistency(
    context: str,
    good: tuple[float, float],
    warning: tuple[float, float],
    fault: tuple[float, float],
) -> None:
    """Classification checks good, then warning, then falls back to FAULT.

    A declared band whose interior overlaps a higher-precedence band would
    therefore lie about how those angles classify. Bands may share endpoints
    (the contiguous shape the knowledge base uses); interiors must be disjoint.
    """
    if _interiors_overlap(warning, good):
        raise KnowledgeBaseError(
            f"{context}: warning band {list(warning)} overlaps good band "
            f"{list(good)}; angles in the overlap would classify as GOOD"
        )
    for name, band in (("good", good), ("warning", warning)):
        if _interiors_overlap(fault, band):
            raise KnowledgeBaseError(
                f"{context}: fault band {list(fault)} overlaps {name} band "
                f"{list(band)}; angles in the overlap would not classify as FAULT"
            )


def _interiors_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return max(a[0], b[0]) < min(a[1], b[1])


def _parse_feedback(context: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeBaseError(f"{context}: feedback must be a non-empty string")
    return value


def _parse_priority(context: str, value: object) -> FaultPriority:
    if value not in _KNOWN_PRIORITIES:
        raise KnowledgeBaseError(
            f"{context}: unknown priority {value!r}; valid priorities: "
            + ", ".join(sorted(_KNOWN_PRIORITIES))
        )
    return FaultPriority(value)
