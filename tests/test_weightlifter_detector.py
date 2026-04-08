import numpy as np
import pytest

from src.weightlifter_detector import WeightlifterDetector


def test_choose_best_bbox_without_previous_center_prefers_largest_area():
    detector = WeightlifterDetector("data/sample_video.mp4", "output/test.mp4")
    boxes = [
        (10, 10, 30, 30),
        (40, 40, 90, 120),
    ]

    picked = detector._choose_best_bbox(boxes, previous_center=None)
    assert picked == (40, 40, 90, 120)


def test_choose_best_bbox_with_previous_center_prefers_closest():
    detector = WeightlifterDetector("data/sample_video.mp4", "output/test.mp4")
    boxes = [
        (10, 10, 40, 100),
        (250, 160, 60, 120),
    ]

    picked = detector._choose_best_bbox(boxes, previous_center=(30, 60))
    assert picked == (10, 10, 40, 100)


def test_detect_weightlifter_uses_motion_fallback_when_hog_empty(monkeypatch):
    detector = WeightlifterDetector("data/sample_video.mp4", "output/test.mp4", min_motion_area=100)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    fallback_bbox = (30, 40, 80, 140)

    monkeypatch.setattr(detector, "_detect_people_hog", lambda _frame: [])
    monkeypatch.setattr(detector, "_detect_motion_bbox", lambda _frame: fallback_bbox)

    detected = detector.detect_weightlifter(frame)
    assert detected == fallback_bbox


def test_draw_overlay_preserves_frame_shape():
    frame = np.zeros((180, 320, 3), dtype=np.uint8)

    out = WeightlifterDetector.draw_overlay(frame, (20, 30, 80, 120))
    assert out.shape == frame.shape


def test_draw_overlay_with_keypoints_preserves_shape():
    frame = np.zeros((180, 320, 3), dtype=np.uint8)
    keypoints = {
        "nose": (100, 40),
        "left_shoulder": (85, 60),
        "right_shoulder": (115, 60),
        "left_ankle": (90, 140),
        "right_ankle": (110, 140),
    }

    out = WeightlifterDetector.draw_overlay(frame, (60, 20, 100, 140), keypoints=keypoints)
    assert out.shape == frame.shape


def test_yolo_keypoints_to_dict_contains_expected_keys():
    arr = np.zeros((17, 2), dtype=np.float32)
    arr[0] = [10, 20]
    arr[5] = [30, 40]
    arr[16] = [50, 60]

    mapped = WeightlifterDetector._yolo_keypoints_to_dict(arr)
    assert mapped["nose"] == (10, 20)
    assert mapped["left_shoulder"] == (30, 40)
    assert mapped["right_ankle"] == (50, 60)


def test_calculate_angle_returns_expected_right_angle():
    angle = WeightlifterDetector._calculate_angle((0, 0), (0, 1), (1, 1))
    assert 89.0 <= angle <= 91.0


def test_explicit_yolo_backend_requires_ultralytics(monkeypatch):
    monkeypatch.setattr(WeightlifterDetector, "_ultralytics_available", staticmethod(lambda: False))

    with pytest.raises(RuntimeError):
        WeightlifterDetector("data/sample_video.mp4", "output/test.mp4", backend="yolo")


def test_auto_backend_uses_hog_when_ultralytics_missing(monkeypatch):
    monkeypatch.setattr(WeightlifterDetector, "_ultralytics_available", staticmethod(lambda: False))
    detector = WeightlifterDetector("data/sample_video.mp4", "output/test.mp4", backend="auto")

    assert detector._yolo is None
