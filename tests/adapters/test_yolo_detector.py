from unittest.mock import patch

import numpy as np

from src.adapters.yolo_detector import YoloPoseDetector
from src.domain.models import BBox
from tests.adapters.yolo_fakes import FakeYoloModel, cached_inference, person_result


def make_detector(**kwargs):
    """Create detector with YOLO loading patched out."""
    with patch.object(YoloPoseDetector, "_ultralytics_available", staticmethod(lambda: False)):
        return YoloPoseDetector(**kwargs)


class TestConstructorWiring:
    def test_builds_own_inference_when_ultralytics_available(self):
        with patch("src.adapters.yolo_detector.CachedYoloInference") as ctor:
            detector = YoloPoseDetector(yolo_model="m.pt", yolo_conf=0.5)
        ctor.assert_called_once_with("m.pt", 0.5)
        assert detector._inference is ctor.return_value


class TestDetectWithInjectedInference:
    def test_returns_bbox_from_shared_inference(self):
        model = FakeYoloModel(person_result([[10, 20, 110, 220]]))
        detector = YoloPoseDetector(inference=cached_inference(model))
        frame = np.zeros((240, 320, 3), dtype=np.uint8)

        assert detector.detect(frame) == BBox(10, 20, 100, 200)
        assert model.predict_calls == 1

    def test_empty_result_yields_no_candidates(self):
        model = FakeYoloModel([])
        detector = YoloPoseDetector(inference=cached_inference(model))
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        detector._detect_motion = lambda _: None

        assert detector.detect(frame) is None

    def test_empty_boxes_falls_back_to_motion(self):
        model = FakeYoloModel(person_result(np.empty((0, 4))))
        detector = YoloPoseDetector(inference=cached_inference(model))
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        fallback = BBox(30, 40, 80, 140)
        detector._detect_motion = lambda _: fallback

        assert detector.detect(frame) == fallback


class TestChooseBest:
    def test_returns_none_for_empty_candidates(self):
        result = YoloPoseDetector._choose_best([], previous_center=None)
        assert result is None

    def test_without_previous_center_picks_largest_area(self):
        small = BBox(0, 0, 10, 10)
        large = BBox(0, 0, 100, 100)
        assert YoloPoseDetector._choose_best([small, large], None) == large

    def test_with_previous_center_picks_closest(self):
        near = BBox(10, 10, 20, 20)   # center (20, 20)
        far = BBox(200, 200, 20, 20)  # center (210, 210)
        result = YoloPoseDetector._choose_best([near, far], previous_center=(25, 25))
        assert result == near

    def test_single_candidate_always_returned(self):
        bbox = BBox(5, 5, 30, 40)
        assert YoloPoseDetector._choose_best([bbox], previous_center=None) == bbox
        assert YoloPoseDetector._choose_best([bbox], previous_center=(0, 0)) == bbox


class TestDetectMotion:
    def test_returns_none_when_no_motion(self):
        detector = make_detector(min_motion_area=100)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        # Feed several identical frames so background model stabilises
        for _ in range(5):
            detector._detect_motion(frame)
        result = detector._detect_motion(frame)
        assert result is None

    def test_returns_bbox_when_motion_exceeds_threshold(self):
        detector = make_detector(min_motion_area=100)
        background = np.zeros((240, 320, 3), dtype=np.uint8)
        # Prime the background subtractor
        for _ in range(10):
            detector._detect_motion(background)
        # Introduce a large bright region to trigger motion
        foreground = background.copy()
        foreground[50:150, 50:200] = 255
        result = detector._detect_motion(foreground)
        assert result is not None
        assert isinstance(result, BBox)

    def test_returns_none_when_motion_below_min_area(self):
        detector = make_detector(min_motion_area=50000)  # unreachably large threshold
        background = np.zeros((240, 320, 3), dtype=np.uint8)
        for _ in range(10):
            detector._detect_motion(background)
        foreground = background.copy()
        foreground[50:150, 50:200] = 255
        result = detector._detect_motion(foreground)
        assert result is None


class TestDetectWithHogFallback:
    def test_uses_motion_fallback_when_hog_finds_nothing(self):
        detector = make_detector(min_motion_area=100)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        fallback = BBox(30, 40, 80, 140)

        detector._detect_people_hog = lambda _: []
        detector._detect_motion = lambda _: fallback

        assert detector.detect(frame) == fallback

    def test_returns_none_when_all_methods_fail(self):
        detector = make_detector()
        frame = np.zeros((240, 320, 3), dtype=np.uint8)

        detector._detect_people_hog = lambda _: []
        detector._detect_motion = lambda _: None

        assert detector.detect(frame) is None

    def test_returns_last_bbox_within_max_missing_frames(self):
        detector = make_detector(max_missing_frames=3)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        last = BBox(10, 10, 50, 80)
        detector._last_bbox = last

        detector._detect_people_hog = lambda _: []
        detector._detect_motion = lambda _: None

        assert detector.detect(frame) == last

    def test_returns_none_after_max_missing_frames_exceeded(self):
        detector = make_detector(max_missing_frames=2)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        detector._last_bbox = BBox(10, 10, 50, 80)
        detector._missing_frames = 2

        detector._detect_people_hog = lambda _: []
        detector._detect_motion = lambda _: None

        assert detector.detect(frame) is None
