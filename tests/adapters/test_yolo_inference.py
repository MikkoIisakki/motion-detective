from unittest.mock import patch

import numpy as np
import pytest

import src.adapters.yolo_inference as yolo_inference
from src.adapters.yolo_detector import YoloPoseDetector
from src.adapters.yolo_inference import CachedYoloInference, ultralytics_available
from src.adapters.yolo_pose_estimator import YoloPoseEstimator
from tests.adapters.yolo_fakes import FakeYoloModel, cached_inference, person_result


def make_frame(seed: int = 0) -> np.ndarray:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[0, 0, 0] = seed
    return frame


def single_person_result():
    keypoints_xy = np.tile([[60.0, 120.0]], (17, 1)).reshape(1, 17, 2)
    return person_result([[10, 20, 110, 220]], keypoints_xy=keypoints_xy)


class TestUltralyticsAvailable:
    def test_reports_installed_ultralytics(self):
        assert ultralytics_available() is True


class TestCachedYoloInference:
    def test_raises_when_ultralytics_unavailable(self):
        with (
            patch.object(yolo_inference, "ultralytics_available", lambda: False),
            pytest.raises(RuntimeError, match="ultralytics"),
        ):
            CachedYoloInference()

    def test_predicts_once_for_repeated_calls_on_same_frame(self):
        model = FakeYoloModel(single_person_result())
        inference = cached_inference(model)
        frame = make_frame()

        first = inference.predict(frame)
        second = inference.predict(frame)

        assert model.predict_calls == 1
        assert first is second

    def test_predicts_again_for_new_frame(self):
        model = FakeYoloModel(single_person_result())
        inference = cached_inference(model)

        inference.predict(make_frame(seed=1))
        inference.predict(make_frame(seed=2))

        assert model.predict_calls == 2

    def test_passes_person_class_and_confidence_to_model(self):
        model = FakeYoloModel(single_person_result())
        inference = cached_inference(model)

        inference.predict(make_frame())

        assert model.last_kwargs == {"classes": [0], "conf": 0.35, "verbose": False}


class TestSharedInferenceAcrossAdapters:
    def make_adapters(self, model):
        inference = cached_inference(model)
        detector = YoloPoseDetector(inference=inference)
        estimator = YoloPoseEstimator(inference=inference)
        return detector, estimator

    def test_detect_then_estimate_runs_exactly_one_inference(self):
        model = FakeYoloModel(single_person_result())
        detector, estimator = self.make_adapters(model)
        frame = make_frame()

        bbox = detector.detect(frame)
        pose = estimator.estimate(frame, bbox)

        assert model.predict_calls == 1
        assert bbox is not None
        assert pose is not None
        assert pose.get("left_wrist").as_tuple() == (60, 120)

    def test_each_frame_runs_exactly_one_inference(self):
        model = FakeYoloModel(single_person_result())
        detector, estimator = self.make_adapters(model)

        for seed in (1, 2, 3):
            frame = make_frame(seed=seed)
            bbox = detector.detect(frame)
            estimator.estimate(frame, bbox)

        assert model.predict_calls == 3
