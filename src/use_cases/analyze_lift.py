from __future__ import annotations

from src.domain.analysis import FrameAnalysis
from src.domain.angle_math import ANGLE_DEFINITIONS, joint_angle
from src.domain.faults import JointMeasurement
from src.domain.knowledge_base import KnowledgeBase
from src.domain.models import Pose
from src.domain.phase_detector import PhaseDetector
from src.use_cases.classify_frame import ClassifyFrame


class AnalyzeLift:
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        phase_detector: PhaseDetector,
        lift: str,
    ) -> None:
        self._lift = lift
        self._phase_detector = phase_detector
        self._phase_detector.configure_for_lift(lift)
        self._classify = ClassifyFrame(knowledge_base=knowledge_base)

    def analyse_frame(self, pose: Pose) -> FrameAnalysis:
        phase = self._phase_detector.update(pose)
        measurements = self._extract_measurements(pose)
        faults = self._classify.execute(self._lift, phase, measurements)
        return FrameAnalysis(phase=phase, measurements=measurements, faults=faults)

    @staticmethod
    def _extract_measurements(pose: Pose) -> list[JointMeasurement]:
        seen: dict[str, list[float]] = {}
        for definition in ANGLE_DEFINITIONS:
            ka = pose.get(definition.vertex_a)
            kb = pose.get(definition.vertex_b)
            kc = pose.get(definition.vertex_c)
            if ka is None or kb is None or kc is None:
                continue
            angle = joint_angle(ka, kb, kc)
            seen.setdefault(definition.joint, []).append(angle)
        # Average left+right for each joint type
        return [JointMeasurement(joint=j, angle=sum(v) / len(v)) for j, v in seen.items()]
