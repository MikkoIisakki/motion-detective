"""Unit tests for the FixturePoseEstimator used in clip regression tests."""
from __future__ import annotations

import numpy as np

from src.domain.models import BBox, Keypoint, Pose
from tests.regression.fixture_pose_estimator import FixturePoseEstimator


def _pose(x: int) -> Pose:
    return Pose([Keypoint("left_ankle", x, 400)])


def _frame() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


class TestFixturePoseEstimator:
    def test_returns_authored_poses_in_order(self):
        estimator = FixturePoseEstimator([_pose(10), _pose(20), _pose(30)])
        bbox = BBox(0, 0, 640, 480)
        assert estimator.estimate(_frame(), bbox).get("left_ankle").x == 10
        assert estimator.estimate(_frame(), bbox).get("left_ankle").x == 20
        assert estimator.estimate(_frame(), bbox).get("left_ankle").x == 30

    def test_returns_last_pose_when_called_past_end(self):
        estimator = FixturePoseEstimator([_pose(10), _pose(20)])
        bbox = BBox(0, 0, 640, 480)
        estimator.estimate(_frame(), bbox)
        estimator.estimate(_frame(), bbox)
        # Extra call past the end repeats the final pose so the use case can
        # continue iterating without raising on a trailing frame.
        assert estimator.estimate(_frame(), bbox).get("left_ankle").x == 20

    def test_empty_sequence_returns_none(self):
        estimator = FixturePoseEstimator([])
        assert estimator.estimate(_frame(), BBox(0, 0, 640, 480)) is None

    def test_returns_none_when_pose_entry_is_none(self):
        estimator = FixturePoseEstimator([_pose(10), None, _pose(30)])
        bbox = BBox(0, 0, 640, 480)
        assert estimator.estimate(_frame(), bbox).get("left_ankle").x == 10
        assert estimator.estimate(_frame(), bbox) is None
        assert estimator.estimate(_frame(), bbox).get("left_ankle").x == 30

    def test_ignores_input_frame_and_bbox(self):
        # FixturePoseEstimator must be deterministic regardless of inputs —
        # it's a regression-test stand-in for YOLO that returns authored poses.
        estimator = FixturePoseEstimator([_pose(10)])
        assert estimator.estimate(_frame(), BBox(0, 0, 1, 1)).get("left_ankle").x == 10

        estimator2 = FixturePoseEstimator([_pose(20)])
        unusual_frame = np.full((10, 10, 3), 255, dtype=np.uint8)
        assert estimator2.estimate(unusual_frame, BBox(5, 5, 5, 5)).get("left_ankle").x == 20
