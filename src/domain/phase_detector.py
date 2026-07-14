from __future__ import annotations

from dataclasses import dataclass

from src.domain.faults import LiftPhase
from src.domain.models import Pose

SNATCH = "snatch"
CLEAN_AND_JERK = "clean_and_jerk"

# All thresholds are fractions of the per-frame shoulder-to-ankle vertical
# span (``CompleteSignal.body_span``), so gates keep their meaning across
# camera distance and resolution. The fractions reproduce the previous
# absolute-pixel gates (50, 25, 40 and 5 px) at the 300 px standing span of
# the synthetic regression clips (shin + thigh + torso = 100 px each in
# tests/regression/synthetic_pose.py).
_REFERENCE_STANDING_SPAN_PX = 300.0
# The second pull begins once the bar (wrist proxy) is within this fraction
# of the body span below the shoulders.
SECOND_PULL_WRIST_BELOW_SHOULDER_FRACTION = 50.0 / _REFERENCE_STANDING_SPAN_PX
# The bar counts as racked (front-rack, pre/mid jerk dip) while the wrist is
# within this fraction of the body span of shoulder height.
RACK_WRIST_PROXIMITY_FRACTION = 25.0 / _REFERENCE_STANDING_SPAN_PX
# The bar counts as overhead (jerk catch) once the wrist is at least this
# fraction of the body span above the shoulders — clearly past the racked band.
OVERHEAD_WRIST_CLEARANCE_FRACTION = 40.0 / _REFERENCE_STANDING_SPAN_PX
# A joint must move by this fraction of the body span between frames to count
# as rising/descending (setup -> first pull, catch -> recovery, jerk dip,
# multi-rep re-entry).
RISE_THRESHOLD_FRACTION = 5.0 / _REFERENCE_STANDING_SPAN_PX


@dataclass(frozen=True)
class CompleteSignal:
    """A PoseSignal whose every joint height is known — what the state machine consumes."""

    wrist_y: float
    ankle_y: float
    knee_y: float
    hip_y: float
    shoulder_y: float

    @property
    def body_span(self) -> float:
        """Shoulder-to-ankle vertical extent — the per-frame body-scale
        reference that keeps thresholds camera-distance independent."""
        return self.ankle_y - self.shoulder_y


@dataclass(frozen=True)
class PoseSignal:
    wrist_y: float | None
    ankle_y: float | None
    knee_y: float | None
    hip_y: float | None
    shoulder_y: float | None

    @classmethod
    def from_pose(cls, pose: Pose) -> PoseSignal:
        return cls(
            wrist_y=cls._mean_y(pose, "left_wrist", "right_wrist"),
            ankle_y=cls._mean_y(pose, "left_ankle", "right_ankle"),
            knee_y=cls._mean_y(pose, "left_knee", "right_knee"),
            hip_y=cls._mean_y(pose, "left_hip", "right_hip"),
            shoulder_y=cls._mean_y(pose, "left_shoulder", "right_shoulder"),
        )

    @staticmethod
    def _mean_y(pose: Pose, *names: str) -> float | None:
        keypoints = (pose.get(n) for n in names)
        values = [kp.y for kp in keypoints if kp is not None]
        return sum(values) / len(values) if values else None

    def complete(self) -> CompleteSignal | None:
        if (
            self.wrist_y is None
            or self.ankle_y is None
            or self.knee_y is None
            or self.hip_y is None
            or self.shoulder_y is None
        ):
            return None
        return CompleteSignal(
            wrist_y=self.wrist_y,
            ankle_y=self.ankle_y,
            knee_y=self.knee_y,
            hip_y=self.hip_y,
            shoulder_y=self.shoulder_y,
        )

    @property
    def is_complete(self) -> bool:
        return self.complete() is not None


class PhaseDetector:
    """Stateful detector that classifies the current LiftPhase per frame.

    Image coordinates: lower y = higher in the image. Wrist rising means y
    decreases.

    For clean_and_jerk the detector continues past the clean's recovery into
    the jerk: hips descending while the bar stays racked at the shoulders is
    the jerk dip, the bar arriving overhead is the jerk catch, and the final
    hip rise is the closing recovery. For snatch, recovery ends the rep.

    Multi-rep clips re-enter SETUP from a rep-ending recovery (snatch
    recovery, or clean & jerk recovery once the jerk is done) when the bar
    drops below knee height while the hips descend back toward setup depth.
    The bar-below-knees signal is disjoint from the jerk dip's bar-racked
    signal, so re-entry can never shadow the RECOVERY -> JERK_DIP detection.

    All distance gates are body-relative: fractions of the per-frame
    shoulder-to-ankle span (see the module-level ``*_FRACTION`` constants), so
    detection is independent of camera distance and resolution. A frame whose
    span is not positive (shoulder detected at or below the ankles) is treated
    like an incomplete signal and keeps the current phase.

    TODO(limitation): the wrist midpoint is the only bar proxy, so the jerk
    drive cannot be told apart from the dip (both keep the bar racked); the
    drive frames classify as JERK_DIP until the bar is overhead. A split vs
    power jerk cannot be distinguished either — both land in JERK_CATCH.
    """

    def __init__(
        self,
        rise_threshold_fraction: float = RISE_THRESHOLD_FRACTION,
        lift: str = SNATCH,
    ) -> None:
        self._phase = LiftPhase.IDLE
        self._rise_threshold_fraction = rise_threshold_fraction
        self._prev_signal: CompleteSignal | None = None
        self._lift = lift
        self._jerk_completed = False

    @property
    def current_phase(self) -> LiftPhase:
        return self._phase

    @property
    def lift(self) -> str:
        return self._lift

    def configure_for_lift(self, lift: str) -> None:
        self._lift = lift

    def update(self, pose: Pose) -> LiftPhase:
        signal = PoseSignal.from_pose(pose).complete()
        if signal is None or signal.body_span <= 0:
            return self._phase

        # Chain transitions until stable so a single fast update can advance
        # multiple phases (e.g. first_pull → transition → second_pull).
        for _ in range(len(LiftPhase)):
            next_phase = self._next_phase(signal)
            if next_phase == self._phase:
                break
            if self._phase == LiftPhase.JERK_CATCH and next_phase == LiftPhase.RECOVERY:
                self._jerk_completed = True
            if self._phase == LiftPhase.RECOVERY and next_phase == LiftPhase.SETUP:
                self._jerk_completed = False
            self._phase = next_phase

        self._prev_signal = signal
        return self._phase

    def _next_phase(self, signal: CompleteSignal) -> LiftPhase:
        prev = self._prev_signal

        if self._phase == LiftPhase.IDLE:
            # Gripping a loaded bar puts the wrists at knee height (plates
            # hold the bar well off the floor); arms hanging while standing
            # keep them at mid-thigh, above the knee.
            if signal.wrist_y >= signal.knee_y:
                return LiftPhase.SETUP
            return LiftPhase.IDLE

        if self._phase == LiftPhase.SETUP:
            if prev and (prev.wrist_y - signal.wrist_y) >= self._rise_threshold(signal):
                return LiftPhase.FIRST_PULL
            return LiftPhase.SETUP

        if self._phase == LiftPhase.FIRST_PULL:
            if signal.wrist_y < signal.knee_y:
                return LiftPhase.TRANSITION
            return LiftPhase.FIRST_PULL

        if self._phase == LiftPhase.TRANSITION:
            near_shoulder = (
                signal.shoulder_y
                + SECOND_PULL_WRIST_BELOW_SHOULDER_FRACTION * signal.body_span
            )
            if signal.wrist_y < near_shoulder:
                return LiftPhase.SECOND_PULL
            return LiftPhase.TRANSITION

        if self._phase == LiftPhase.SECOND_PULL:
            if signal.wrist_y < signal.shoulder_y:
                return LiftPhase.CATCH
            return LiftPhase.SECOND_PULL

        if self._phase == LiftPhase.CATCH:
            if prev and (prev.hip_y - signal.hip_y) >= self._rise_threshold(signal):
                return LiftPhase.RECOVERY
            return LiftPhase.CATCH

        if self._phase == LiftPhase.RECOVERY:
            if self._starts_jerk_dip(signal):
                return LiftPhase.JERK_DIP
            if self._starts_next_rep(signal):
                return LiftPhase.SETUP
            return LiftPhase.RECOVERY

        if self._phase == LiftPhase.JERK_DIP:
            if self._is_bar_overhead(signal):
                return LiftPhase.JERK_CATCH
            return LiftPhase.JERK_DIP

        if self._phase == LiftPhase.JERK_CATCH:
            if prev and (prev.hip_y - signal.hip_y) >= self._rise_threshold(signal):
                return LiftPhase.RECOVERY
            return LiftPhase.JERK_CATCH

        return self._phase

    def _rise_threshold(self, signal: CompleteSignal) -> float:
        return self._rise_threshold_fraction * signal.body_span

    def _starts_next_rep(self, signal: CompleteSignal) -> bool:
        """Re-entry into SETUP: only from a rep-ending recovery, when the bar
        has come down below the knees while the hips descend toward setup
        depth. Bar-below-knees is disjoint from the jerk dip's bar-racked
        signal, so the two RECOVERY exits cannot compete."""
        if self._lift == CLEAN_AND_JERK and not self._jerk_completed:
            return False
        prev = self._prev_signal
        if prev is None:
            return False
        bar_below_knees = signal.wrist_y > signal.knee_y
        hips_descending = (signal.hip_y - prev.hip_y) >= self._rise_threshold(signal)
        return bar_below_knees and hips_descending

    def _starts_jerk_dip(self, signal: CompleteSignal) -> bool:
        if self._lift != CLEAN_AND_JERK or self._jerk_completed:
            return False
        prev = self._prev_signal
        if prev is None:
            return False
        hips_descending = (signal.hip_y - prev.hip_y) >= self._rise_threshold(signal)
        return hips_descending and self._is_bar_racked(signal)

    @staticmethod
    def _is_bar_racked(signal: CompleteSignal) -> bool:
        proximity = RACK_WRIST_PROXIMITY_FRACTION * signal.body_span
        return abs(signal.wrist_y - signal.shoulder_y) <= proximity

    @staticmethod
    def _is_bar_overhead(signal: CompleteSignal) -> bool:
        clearance = OVERHEAD_WRIST_CLEARANCE_FRACTION * signal.body_span
        return signal.wrist_y < signal.shoulder_y - clearance
