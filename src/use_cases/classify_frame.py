from __future__ import annotations

from src.domain.faults import FaultResult, JointMeasurement, LiftPhase
from src.domain.knowledge_base import KnowledgeBase


class ClassifyFrame:
    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self._kb = knowledge_base

    def execute(
        self,
        lift: str,
        phase: LiftPhase,
        measurements: list[JointMeasurement],
    ) -> list[FaultResult]:
        rules = self._kb.rules_for(lift, phase)
        results = []
        for m in measurements:
            rule = rules.get(m.joint)
            if rule is None:
                continue
            results.append(FaultResult(
                joint=m.joint,
                severity=rule.classify(m.angle),
                priority=rule.priority,
                feedback=rule.feedback,
            ))
        return results
