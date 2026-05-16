from src.domain.joint_gate import gate_keypoints
from src.domain.models import Keypoint, Pose


class TestGateKeypoints:
    def test_keeps_all_keypoints_when_all_meet_threshold(self):
        pose = Pose([
            Keypoint("nose", 1, 1, confidence=0.9),
            Keypoint("left_knee", 2, 2, confidence=0.8),
        ])
        gated = gate_keypoints(pose, min_confidence=0.5)
        assert gated.get("nose") is not None
        assert gated.get("left_knee") is not None

    def test_drops_keypoints_below_threshold(self):
        pose = Pose([
            Keypoint("nose", 1, 1, confidence=0.9),
            Keypoint("left_knee", 2, 2, confidence=0.2),
        ])
        gated = gate_keypoints(pose, min_confidence=0.5)
        assert gated.get("nose") is not None
        assert gated.get("left_knee") is None

    def test_min_confidence_zero_keeps_everything(self):
        pose = Pose([
            Keypoint("nose", 1, 1, confidence=0.0),
            Keypoint("left_knee", 2, 2, confidence=0.01),
        ])
        gated = gate_keypoints(pose, min_confidence=0.0)
        assert gated.get("nose") is not None
        assert gated.get("left_knee") is not None

    def test_min_confidence_one_keeps_only_full_confidence(self):
        pose = Pose([
            Keypoint("nose", 1, 1, confidence=1.0),
            Keypoint("left_knee", 2, 2, confidence=0.99),
        ])
        gated = gate_keypoints(pose, min_confidence=1.0)
        assert gated.get("nose") is not None
        assert gated.get("left_knee") is None

    def test_empty_pose_returns_empty_pose(self):
        pose = Pose([])
        gated = gate_keypoints(pose, min_confidence=0.5)
        assert gated.keypoints == ()

    def test_threshold_is_inclusive(self):
        pose = Pose([Keypoint("nose", 1, 1, confidence=0.5)])
        gated = gate_keypoints(pose, min_confidence=0.5)
        assert gated.get("nose") is not None
