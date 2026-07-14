"""Groups per-frame fault findings into a timeline and renders summary lines.

Pure domain logic: `AnalyzeVideo` feeds actionable findings in frame order via
`observe`; the aggregator merges consecutive hits of the same finding into
`FaultGroup` spans and formats the human-readable feedback summary.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from src.domain.faults import FaultPriority, FaultResult, FaultSeverity

NO_FAULTS_MESSAGE = "No actionable faults detected."

_SEVERITY_RANK = {
    FaultSeverity.FAULT: 0,
    FaultSeverity.WARNING: 1,
    FaultSeverity.GOOD: 2,
}


@dataclass
class FaultGroup:
    phase: str
    feedback: str
    severity: FaultSeverity
    priority: FaultPriority
    start_seconds: float
    end_seconds: float
    hit_count: int = 1

    def observe(self, ts_seconds: float) -> None:
        self.end_seconds = ts_seconds
        self.hit_count += 1


def format_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    minutes = total_ms // 60000
    remaining_ms = total_ms % 60000
    whole_seconds = remaining_ms // 1000
    millis = remaining_ms % 1000
    return f"{minutes:02d}:{whole_seconds:02d}.{millis:03d}"


class FaultAggregator:
    def __init__(self) -> None:
        self._groups: dict[tuple[str, str, FaultSeverity, FaultPriority], FaultGroup] = {}

    def observe(self, phase: str, faults: Iterable[FaultResult], ts_seconds: float) -> None:
        for fault in faults:
            if not fault.is_actionable:
                continue
            key = (phase, fault.feedback, fault.severity, fault.priority)
            if key in self._groups:
                self._groups[key].observe(ts_seconds)
            else:
                self._groups[key] = FaultGroup(
                    phase=phase,
                    feedback=fault.feedback,
                    severity=fault.severity,
                    priority=fault.priority,
                    start_seconds=ts_seconds,
                    end_seconds=ts_seconds,
                )

    @property
    def groups(self) -> list[FaultGroup]:
        return list(self._groups.values())

    def summary_lines(self) -> list[str]:
        if not self._groups:
            return [NO_FAULTS_MESSAGE]

        ordered = sorted(
            self._groups.values(),
            key=lambda g: (_SEVERITY_RANK[g.severity], g.start_seconds),
        )
        return [
            f"{format_timestamp(g.start_seconds)}-{format_timestamp(g.end_seconds)}"
            f" [{g.severity.name}/{g.priority.value}] {g.phase}: {g.feedback} ({g.hit_count} frames)"
            for g in ordered
        ]
