from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LiftPhase(str, Enum):
    IDLE = "idle"
    SETUP = "setup"
    FIRST_PULL = "first_pull"
    TRANSITION = "transition"
    SECOND_PULL = "second_pull"
    CATCH = "catch"
    RECOVERY = "recovery"


class FaultSeverity(int, Enum):
    GOOD = 0
    WARNING = 1
    FAULT = 2


class FaultPriority(str, Enum):
    SAFETY = "safety"
    PERFORMANCE = "performance"
    EFFICIENCY = "efficiency"


@dataclass(frozen=True)
class AngleThreshold:
    good: tuple[float, float]
    warning: tuple[float, float]
    fault: tuple[float, float]

    def classify(self, angle: float) -> FaultSeverity:
        if self.good[0] <= angle <= self.good[1]:
            return FaultSeverity.GOOD
        if self.warning[0] <= angle <= self.warning[1]:
            return FaultSeverity.WARNING
        return FaultSeverity.FAULT


@dataclass(frozen=True)
class JointMeasurement:
    joint: str
    angle: float


@dataclass(frozen=True)
class FaultResult:
    joint: str
    severity: FaultSeverity
    priority: FaultPriority
    feedback: str

    @property
    def is_actionable(self) -> bool:
        return self.severity > FaultSeverity.GOOD
