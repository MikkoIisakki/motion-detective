from __future__ import annotations

from src.domain.models import Keypoint, Pose


class KeypointSmoother:
    """Exponential moving average over keypoint positions.

    For each keypoint name, smoothed = alpha * new + (1 - alpha) * previous.
    alpha=1.0 disables smoothing; alpha=0.0 freezes at the first value.
    Missing keypoints in a new pose are filled from the last known state
    (handles brief occlusions / detection dropouts).
    """

    def __init__(self, alpha: float = 0.5) -> None:
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"alpha must be in [0, 1], got {alpha}")
        self._alpha = alpha
        self._state: dict[str, Keypoint] = {}

    def reset(self) -> None:
        self._state.clear()

    def smooth(self, pose: Pose) -> Pose:
        smoothed: dict[str, Keypoint] = {}

        for kp in pose.keypoints:
            previous = self._state.get(kp.name)
            if previous is None:
                smoothed[kp.name] = kp
            else:
                smoothed[kp.name] = Keypoint(
                    name=kp.name,
                    x=int(round(self._alpha * kp.x + (1 - self._alpha) * previous.x)),
                    y=int(round(self._alpha * kp.y + (1 - self._alpha) * previous.y)),
                )

        # Carry over keypoints that disappeared this frame
        for name, kp in self._state.items():
            smoothed.setdefault(name, kp)

        self._state = smoothed
        return Pose(list(smoothed.values()))
