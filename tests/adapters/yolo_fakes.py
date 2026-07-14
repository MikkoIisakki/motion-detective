"""Test doubles mimicking the ultralytics result shape, so YOLO adapters run without weights."""

from unittest.mock import patch

import numpy as np

from src.adapters.yolo_inference import CachedYoloInference


class FakeTensor:
    def __init__(self, array):
        self._array = np.asarray(array, dtype=np.float32)

    def cpu(self):
        return self

    def numpy(self):
        return self._array


class FakeBoxes:
    def __init__(self, xyxy):
        self.xyxy = FakeTensor(xyxy)


class FakeKeypoints:
    def __init__(self, xy, conf=None):
        self.xy = FakeTensor(xy)
        self.conf = FakeTensor(conf) if conf is not None else None


class FakeResult:
    def __init__(self, boxes=None, keypoints=None):
        self.boxes = boxes
        self.keypoints = keypoints


class FakeYoloModel:
    """Counts predict calls and returns a canned ultralytics-shaped result."""

    def __init__(self, result):
        self._result = result
        self.predict_calls = 0
        self.last_kwargs = None

    def predict(self, frame, **kwargs):
        self.predict_calls += 1
        self.last_kwargs = kwargs
        return self._result


def person_result(xyxy, keypoints_xy=None, keypoints_conf=None) -> list[FakeResult]:
    """Build a one-result list like ultralytics returns for a single frame."""
    keypoints = FakeKeypoints(keypoints_xy, keypoints_conf) if keypoints_xy is not None else None
    return [FakeResult(boxes=FakeBoxes(xyxy), keypoints=keypoints)]


def cached_inference(model: FakeYoloModel) -> CachedYoloInference:
    """Build a CachedYoloInference around a fake model, skipping real weight loading."""
    with patch.object(CachedYoloInference, "_load_model", staticmethod(lambda path: model)):
        return CachedYoloInference()
