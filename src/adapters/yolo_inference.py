from __future__ import annotations

import importlib.util
from typing import Any

import numpy as np


def ultralytics_available() -> bool:
    return importlib.util.find_spec("ultralytics") is not None


class CachedYoloInference:
    """Loads one YOLO pose model and runs at most one inference per frame.

    YoloPoseDetector and YoloPoseEstimator both consume the same prediction,
    so sharing one instance between them halves the per-frame inference cost.
    Caching keys on frame identity; holding a reference to the cached frame
    keeps the identity check safe against object reuse.
    """

    def __init__(self, yolo_model: str = "yolov8n-pose.pt", yolo_conf: float = 0.35) -> None:
        if not ultralytics_available():
            raise RuntimeError(
                "CachedYoloInference requires `ultralytics`. Install with: pip install ultralytics"
            )
        self._yolo = self._load_model(yolo_model)
        self._yolo_conf = yolo_conf
        self._cached_frame: np.ndarray | None = None
        self._cached_result: Any = None

    @staticmethod
    def _load_model(yolo_model: str) -> Any:
        from ultralytics import YOLO

        return YOLO(yolo_model)

    def predict(self, frame: np.ndarray) -> Any:
        if frame is not self._cached_frame:
            self._cached_result = self._yolo.predict(
                frame, classes=[0], conf=self._yolo_conf, verbose=False
            )
            self._cached_frame = frame
        return self._cached_result
