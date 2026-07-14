import pytest

from main import build_parser, main


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


class TestMainDispatch:
    """Smoke tests for the composition root — subcommands that need no YOLO/ffmpeg."""

    def test_rules_prints_rules_and_exits_zero(self, capsys):
        exit_code = main(["rules", "snatch", "first_pull"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Rules for snatch" in out
        assert "first_pull" in out

    def test_rules_rejects_unknown_phase_with_exit_one(self, capsys):
        exit_code = main(["rules", "snatch", "not_a_phase"])
        assert exit_code == 1
        assert "Unknown phase" in capsys.readouterr().out

    def test_lifts_lists_supported_lifts_and_exits_zero(self, capsys):
        exit_code = main(["lifts"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "snatch" in out

    def test_phases_lists_phases_for_lift_and_exits_zero(self, capsys):
        exit_code = main(["phases", "snatch"])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Phases for snatch" in out

    def test_validate_fails_for_missing_file_with_exit_one(self, capsys):
        exit_code = main(["validate", "data/does_not_exist.mp4"])
        assert exit_code == 1
        assert "FAIL" in capsys.readouterr().out

    def test_missing_knowledge_base_file_prints_fail_with_exit_one(self, capsys):
        exit_code = main(["lifts", "--knowledge-base", "config/does_not_exist.yml"])
        assert exit_code == 1
        out = capsys.readouterr().out
        assert "FAIL" in out
        assert "not found" in out

    def test_malformed_knowledge_base_prints_fail_with_exit_one(self, tmp_path, capsys):
        bad_kb = tmp_path / "kb.yml"
        bad_kb.write_text("snatch:\n  setup:\n    knee_angle: not-a-mapping\n")
        exit_code = main(["rules", "snatch", "setup", "--knowledge-base", str(bad_kb)])
        assert exit_code == 1
        out = capsys.readouterr().out
        assert "FAIL" in out
        assert "rule must be a mapping" in out

    def test_analyze_with_bad_knowledge_base_fails_before_pipeline_wiring(self, capsys):
        exit_code = main(["analyze", "lift.mp4", "--knowledge-base", "config/does_not_exist.yml"])
        assert exit_code == 1
        assert "FAIL" in capsys.readouterr().out

    def test_compare_fails_for_missing_inputs_with_exit_one(self, capsys):
        exit_code = main(["compare", "data/missing_left.mp4", "data/missing_right.mp4"])
        assert exit_code == 1
        assert "FAIL" in capsys.readouterr().out
