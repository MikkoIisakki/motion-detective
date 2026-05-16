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


class TestCompareSubcommand:
    def test_parses_positional_left_and_right_paths(self):
        args = build_parser().parse_args(["compare", "orig.mp4", "annotated.mp4"])
        assert args.command == "compare"
        assert args.left_path == "orig.mp4"
        assert args.right_path == "annotated.mp4"

    def test_defaults_output_to_output_compare_mp4(self):
        args = build_parser().parse_args(["compare", "orig.mp4", "annotated.mp4"])
        assert args.output == "output/compare.mp4"

    def test_accepts_custom_output(self):
        args = build_parser().parse_args(
            ["compare", "orig.mp4", "annotated.mp4", "--output", "out/side.mp4"]
        )
        assert args.output == "out/side.mp4"

    def test_requires_both_positional_paths(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["compare", "orig.mp4"])
