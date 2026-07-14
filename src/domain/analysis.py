from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.faults import FaultResult, JointMeasurement, LiftPhase


@dataclass(frozen=True)
class FrameAnalysis:
    phase: LiftPhase
    measurements: list[JointMeasurement] = field(default_factory=list)
    faults: list[FaultResult] = field(default_factory=list)
