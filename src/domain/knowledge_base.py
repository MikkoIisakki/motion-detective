from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.domain.faults import AngleThreshold, FaultPriority, FaultSeverity, LiftPhase


@dataclass(frozen=True)
class RuleSpec:
    good: tuple[float, float]
    warning: tuple[float, float]
    fault: tuple[float, float]
    feedback: str
    priority: FaultPriority

    def classify(self, angle: float) -> FaultSeverity:
        return AngleThreshold(
            good=self.good, warning=self.warning, fault=self.fault
        ).classify(angle)


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


def _parse(data: dict) -> dict[str, dict[str, dict[str, RuleSpec]]]:
    rules: dict[str, dict[str, dict[str, RuleSpec]]] = {}
    for lift, phases in data.items():
        rules[lift] = {}
        for phase, joints in phases.items():
            rules[lift][phase] = {}
            for joint, spec in joints.items():
                rules[lift][phase][joint] = RuleSpec(
                    good=tuple(spec["good"]),
                    warning=tuple(spec["warning"]),
                    fault=tuple(spec["fault"]),
                    feedback=spec["feedback"],
                    priority=FaultPriority(spec["priority"]),
                )
    return rules
