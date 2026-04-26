from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.angle_math import joint_angle
from src.domain.faults import FaultResult, JointMeasurement, LiftPhase
from src.domain.knowledge_base import KnowledgeBase
from src.domain.models import Pose
from src.domain.phase_detector import PhaseDetector
from src.use_cases.classify_frame import ClassifyFrame


# (joint_name, vertex_a, vertex_b, vertex_c) — angle ABC at vertex B
_ANGLE_DEFINITIONS = [
    ("knee_angle", "left_hip", "left_knee", "left_ankle"),
    ("knee_angle", "right_hip", "right_knee", "right_ankle"),
    ("hip_angle", "left_shoulder", "left_hip", "left_knee"),
    ("hip_angle", "right_shoulder", "right_hip", "right_knee"),
    ("elbow_angle", "left_shoulder", "left_elbow", "left_wrist"),
    ("elbow_angle", "right_shoulder", "right_elbow", "right_wrist"),
]


@dataclass(frozen=True)
class FrameAnalysis:
    phase: LiftPhase
    measurements: list[JointMeasurement] = field(default_factory=list)
    faults: list[FaultResult] = field(default_factory=list)


class AnalyzeLift:
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        phase_detector: PhaseDetector,
        lift: str,
    ) -> None:
        self._lift = lift
        self._phase_detector = phase_detector
        self._classify = ClassifyFrame(knowledge_base=knowledge_base)

    def analyse_frame(self, pose: Pose) -> FrameAnalysis:
        phase = self._phase_detector.update(pose)
        measurements = self._extract_measurements(pose)
        faults = self._classify.execute(self._lift, phase, measurements)
        return FrameAnalysis(phase=phase, measurements=measurements, faults=faults)

    @staticmethod
    def _extract_measurements(pose: Pose) -> list[JointMeasurement]:
        seen: dict[str, list[float]] = {}
        for joint_name, a, b, c in _ANGLE_DEFINITIONS:
            ka, kb, kc = pose.get(a), pose.get(b), pose.get(c)
            if ka is None or kb is None or kc is None:
                continue
            angle = joint_angle(ka, kb, kc)
            seen.setdefault(joint_name, []).append(angle)
        # Average left+right for each joint type
        return [JointMeasurement(joint=j, angle=sum(v) / len(v)) for j, v in seen.items()]
