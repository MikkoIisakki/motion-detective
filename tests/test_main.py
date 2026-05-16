import pytest

from main import build_parser


class TestAnalyzeSmoothingArgument:
    def test_defaults_to_half_smoothing_alpha(self):
        args = build_parser().parse_args(["analyze", "lift.mp4"])
        assert args.smoothing == 0.5

    def test_accepts_smoothing_alpha_in_range(self):
        args = build_parser().parse_args(["analyze", "lift.mp4", "--smoothing", "0.25"])
        assert args.smoothing == 0.25

    @pytest.mark.parametrize("value", ["-0.1", "1.1", "not-a-number"])
    def test_rejects_smoothing_alpha_outside_range(self, value):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["analyze", "lift.mp4", "--smoothing", value])


class TestAnalyzeMinJointConfidenceArgument:
    def test_defaults_to_zero(self):
        args = build_parser().parse_args(["analyze", "lift.mp4"])
        assert args.min_joint_confidence == 0.0

    def test_accepts_value_in_range(self):
        args = build_parser().parse_args(
            ["analyze", "lift.mp4", "--min-joint-confidence", "0.4"]
        )
        assert args.min_joint_confidence == 0.4

    @pytest.mark.parametrize("value", ["-0.1", "1.5", "not-a-number"])
    def test_rejects_value_outside_range(self, value):
        with pytest.raises(SystemExit):
            build_parser().parse_args(
                ["analyze", "lift.mp4", "--min-joint-confidence", value]
            )
