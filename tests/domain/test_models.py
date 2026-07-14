import pytest

from src.domain.models import BBox, Keypoint, Pose


class TestBBox:
    def test_creation_with_valid_values(self):
        bbox = BBox(x=10, y=20, width=100, height=200)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 100
        assert bbox.height == 200

    def test_center(self):
        bbox = BBox(x=10, y=20, width=100, height=200)
        assert bbox.center == (60, 120)

    def test_area(self):
        bbox = BBox(x=0, y=0, width=50, height=40)
        assert bbox.area == 2000

    def test_negative_width_raises(self):
        with pytest.raises(ValueError):
            BBox(x=0, y=0, width=-1, height=10)

    def test_negative_height_raises(self):
        with pytest.raises(ValueError):
            BBox(x=0, y=0, width=10, height=-1)

    def test_equality(self):
        assert BBox(0, 0, 10, 20) == BBox(0, 0, 10, 20)
        assert BBox(0, 0, 10, 20) != BBox(1, 0, 10, 20)


class TestKeypoint:
    def test_creation(self):
        kp = Keypoint(name="left_knee", x=100, y=200)
        assert kp.name == "left_knee"
        assert kp.x == 100
        assert kp.y == 200

    def test_as_tuple(self):
        kp = Keypoint(name="nose", x=50, y=75)
        assert kp.as_tuple() == (50, 75)

    def test_equality(self):
        assert Keypoint("nose", 50, 75) == Keypoint("nose", 50, 75)
        assert Keypoint("nose", 50, 75) != Keypoint("nose", 51, 75)

    def test_confidence_defaults_to_one(self):
        kp = Keypoint(name="nose", x=0, y=0)
        assert kp.confidence == 1.0

    def test_confidence_can_be_set_explicitly(self):
        kp = Keypoint(name="nose", x=0, y=0, confidence=0.42)
        assert kp.confidence == 0.42


class TestPose:
    def test_get_existing_keypoint(self):
        kps = [Keypoint("left_knee", 10, 20), Keypoint("right_knee", 30, 40)]
        pose = Pose(keypoints=kps)
        assert pose.get("left_knee") == Keypoint("left_knee", 10, 20)

    def test_get_missing_keypoint_returns_none(self):
        pose = Pose(keypoints=[])
        assert pose.get("left_knee") is None

    def test_has_all_returns_true_when_all_present(self):
        kps = [Keypoint("a", 0, 0), Keypoint("b", 1, 1)]
        pose = Pose(keypoints=kps)
        assert pose.has_all(["a", "b"]) is True

    def test_has_all_returns_false_when_any_missing(self):
        kps = [Keypoint("a", 0, 0)]
        pose = Pose(keypoints=kps)
        assert pose.has_all(["a", "b"]) is False
