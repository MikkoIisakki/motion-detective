import numpy as np
import pytest

from src.adapters.yolo_pose_estimator import YoloPoseEstimator
from src.domain.models import BBox


class TestClosestDetectionIndex:
    def test_returns_none_for_empty_array(self):
        bbox = BBox(50, 50, 100, 100)
        result = YoloPoseEstimator._closest_detection_index(np.empty((0, 4)), bbox)
        assert result is None

    def test_returns_index_of_closest_box(self):
        # bbox center = (100, 100)
        bbox = BBox(50, 50, 100, 100)
        xyxy = np.array([
            [200, 200, 300, 300],  # center (250, 250) — far
            [70,  70,  130, 130], # center (100, 100) — exact match
        ], dtype=np.float32)
        assert YoloPoseEstimator._closest_detection_index(xyxy, bbox) == 1

    def test_single_detection_always_returns_zero(self):
        bbox = BBox(0, 0, 10, 10)
        xyxy = np.array([[100, 100, 200, 200]], dtype=np.float32)
        assert YoloPoseEstimator._closest_detection_index(xyxy, bbox) == 0


class TestBuildPose:
    def test_builds_pose_with_expected_keypoint_names(self):
        arr = np.zeros((17, 2), dtype=np.float32)
        arr[0] = [10, 20]    # nose
        arr[5] = [30, 40]    # left_shoulder
        arr[16] = [50, 60]   # right_ankle
        pose = YoloPoseEstimator._build_pose(arr)
        assert pose.get("nose").as_tuple() == (10, 20)
        assert pose.get("left_shoulder").as_tuple() == (30, 40)
        assert pose.get("right_ankle").as_tuple() == (50, 60)

    def test_skips_indices_beyond_array_length(self):
        arr = np.zeros((3, 2), dtype=np.float32)  # only indices 0-2 valid
        pose = YoloPoseEstimator._build_pose(arr)
        assert pose.get("nose") is not None       # index 0 — present
        assert pose.get("left_shoulder") is None  # index 5 — beyond array

    def test_returns_pose_with_integer_coordinates(self):
        arr = np.array([[1.7, 2.9]] * 17, dtype=np.float32)
        pose = YoloPoseEstimator._build_pose(arr)
        kp = pose.get("nose")
        assert isinstance(kp.x, int)
        assert isinstance(kp.y, int)

    def test_defaults_confidence_to_one_when_not_provided(self):
        arr = np.zeros((17, 2), dtype=np.float32)
        pose = YoloPoseEstimator._build_pose(arr)
        assert pose.get("nose").confidence == 1.0

    def test_threads_confidence_values_onto_keypoints(self):
        xy = np.zeros((17, 2), dtype=np.float32)
        conf = np.zeros((17,), dtype=np.float32)
        conf[0] = 0.95   # nose
        conf[5] = 0.3    # left_shoulder
        conf[16] = 0.7   # right_ankle
        pose = YoloPoseEstimator._build_pose(xy, conf)
        assert pose.get("nose").confidence == pytest.approx(0.95, abs=1e-6)
        assert pose.get("left_shoulder").confidence == pytest.approx(0.3, abs=1e-6)
        assert pose.get("right_ankle").confidence == pytest.approx(0.7, abs=1e-6)

    def test_skips_when_confidence_array_shorter_than_xy(self):
        xy = np.zeros((17, 2), dtype=np.float32)
        conf = np.array([0.9, 0.8, 0.7], dtype=np.float32)
        pose = YoloPoseEstimator._build_pose(xy, conf)
        # index 0 present and uses the supplied confidence
        assert pose.get("nose") is not None
        assert pose.get("nose").confidence == pytest.approx(0.9, abs=1e-6)
        # index 5 beyond conf array → keypoint omitted
        assert pose.get("left_shoulder") is None
