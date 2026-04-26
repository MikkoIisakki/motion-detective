from __future__ import annotations

from dataclasses import dataclass

from src.domain.faults import LiftPhase
from src.domain.models import Pose


@dataclass(frozen=True)
class PoseSignal:
    wrist_y: float | None
    ankle_y: float | None
    hip_y: float | None
    shoulder_y: float | None

    @classmethod
    def from_pose(cls, pose: Pose) -> PoseSignal:
        return cls(
            wrist_y=cls._mean_y(pose, "left_wrist", "right_wrist"),
            ankle_y=cls._mean_y(pose, "left_ankle", "right_ankle"),
            hip_y=cls._mean_y(pose, "left_hip", "right_hip"),
            shoulder_y=cls._mean_y(pose, "left_shoulder", "right_shoulder"),
        )

    @staticmethod
    def _mean_y(pose: Pose, *names: str) -> float | None:
        values = [pose.get(n).y for n in names if pose.get(n) is not None]
        return sum(values) / len(values) if values else None

    @property
    def is_complete(self) -> bool:
        return all(v is not None for v in (self.wrist_y, self.ankle_y, self.hip_y, self.shoulder_y))


class PhaseDetector:
    """Stateful detector that classifies the current LiftPhase per frame.

    Image coordinates: lower y = higher in the image. Wrist rising means y decreases.
    """

    def __init__(self, rise_threshold_px: float = 5.0) -> None:
        self._phase = LiftPhase.IDLE
        self._rise_threshold = rise_threshold_px
        self._prev_signal: PoseSignal | None = None

    @property
    def current_phase(self) -> LiftPhase:
        return self._phase

    def update(self, pose: Pose) -> LiftPhase:
        signal = PoseSignal.from_pose(pose)
        if not signal.is_complete:
            return self._phase

        # Chain transitions until stable so a single fast update can advance
        # multiple phases (e.g. first_pull → second_pull → catch).
        for _ in range(len(LiftPhase)):
            next_phase = self._next_phase(signal)
            if next_phase == self._phase:
                break
            self._phase = next_phase

        self._prev_signal = signal
        return self._phase

    def _next_phase(self, signal: PoseSignal) -> LiftPhase:
        prev = self._prev_signal

        if self._phase == LiftPhase.IDLE:
            if signal.wrist_y >= signal.ankle_y - 10:
                return LiftPhase.SETUP
            return LiftPhase.IDLE

        if self._phase == LiftPhase.SETUP:
            if prev and (prev.wrist_y - signal.wrist_y) >= self._rise_threshold:
                return LiftPhase.FIRST_PULL
            return LiftPhase.SETUP

        if self._phase == LiftPhase.FIRST_PULL:
            if signal.wrist_y < signal.shoulder_y + 50:
                return LiftPhase.SECOND_PULL
            return LiftPhase.FIRST_PULL

        if self._phase == LiftPhase.SECOND_PULL:
            if signal.wrist_y < signal.shoulder_y:
                return LiftPhase.CATCH
            return LiftPhase.SECOND_PULL

        if self._phase == LiftPhase.CATCH:
            if prev and (prev.hip_y - signal.hip_y) >= self._rise_threshold:
                return LiftPhase.RECOVERY
            return LiftPhase.CATCH

        return self._phase
