import io

import pytest

from src.cli.commands import (
    AnalyzeCommand,
    CompareCommand,
    LiftsCommand,
    PhasesCommand,
    RulesCommand,
    ValidateCommand,
)
from src.domain.knowledge_base import KnowledgeBase
from src.use_cases.analyze_video import AnalyzeVideoResult

KB_YAML = """
snatch:
  setup:
    knee_angle:
      good: [70, 110]
      warning: [110, 130]
      fault: [130, 180]
      feedback: "Bend the knees more"
      priority: performance
  first_pull:
    hip_angle:
      good: [70, 110]
      warning: [50, 70]
      fault: [0, 50]
      feedback: "Keep hips low"
      priority: performance

clean_and_jerk:
  setup:
    knee_angle:
      good: [70, 100]
      warning: [60, 70]
      fault: [0, 60]
      feedback: "Bend knees"
      priority: performance
  jerk_dip:
    hip_angle:
      good: [155, 180]
      warning: [140, 155]
      fault: [0, 140]
      feedback: "Keep the torso vertical in the dip"
      priority: performance
  jerk_catch:
    elbow_angle:
      good: [170, 180]
      warning: [160, 170]
      fault: [0, 160]
      feedback: "Lock out the elbows overhead"
      priority: safety
"""


@pytest.fixture()
def kb_file(tmp_path):
    f = tmp_path / "kb.yml"
    f.write_text(KB_YAML)
    return str(f)


@pytest.fixture()
def out():
    return io.StringIO()


class TestLiftsCommand:
    def test_lists_all_lifts_from_kb(self, kb_file, out):
        kb = KnowledgeBase.from_file(kb_file)
        exit_code = LiftsCommand(kb=kb, out=out).run()
        assert exit_code == 0
        output = out.getvalue()
        assert "snatch" in output
        assert "clean_and_jerk" in output


class TestPhasesCommand:
    def test_lists_phases_for_a_lift(self, kb_file, out):
        kb = KnowledgeBase.from_file(kb_file)
        exit_code = PhasesCommand(kb=kb, lift="snatch", out=out).run()
        assert exit_code == 0
        output = out.getvalue()
        assert "setup" in output
        assert "first_pull" in output

    def test_unknown_lift_returns_nonzero_exit(self, kb_file, out):
        kb = KnowledgeBase.from_file(kb_file)
        exit_code = PhasesCommand(kb=kb, lift="deadlift", out=out).run()
        assert exit_code != 0


class TestRulesCommand:
    def test_prints_rules_for_lift_and_phase(self, kb_file, out):
        kb = KnowledgeBase.from_file(kb_file)
        exit_code = RulesCommand(kb=kb, lift="snatch", phase="setup", out=out).run()
        assert exit_code == 0
        output = out.getvalue()
        assert "knee_angle" in output
        assert "Bend the knees more" in output
        assert "performance" in output

    def test_includes_severity_ranges(self, kb_file, out):
        kb = KnowledgeBase.from_file(kb_file)
        RulesCommand(kb=kb, lift="snatch", phase="setup", out=out).run()
        output = out.getvalue()
        assert "70" in output and "110" in output  # good range
        assert "good" in output.lower()
        assert "warning" in output.lower()
        assert "fault" in output.lower()

    def test_unknown_phase_returns_nonzero_exit(self, kb_file, out):
        kb = KnowledgeBase.from_file(kb_file)
        exit_code = RulesCommand(kb=kb, lift="snatch", phase="jerk_drive", out=out).run()
        assert exit_code != 0

    def test_phase_without_rules_returns_nonzero_exit(self, kb_file, out):
        kb = KnowledgeBase.from_file(kb_file)
        exit_code = RulesCommand(kb=kb, lift="snatch", phase="catch", out=out).run()
        assert exit_code != 0

    @pytest.mark.parametrize(
        ("phase", "expected_feedback"),
        [
            ("jerk_dip", "Keep the torso vertical in the dip"),
            ("jerk_catch", "Lock out the elbows overhead"),
        ],
    )
    def test_every_kb_phase_is_displayable(self, kb_file, out, phase, expected_feedback):
        kb = KnowledgeBase.from_file(kb_file)
        exit_code = RulesCommand(kb=kb, lift="clean_and_jerk", phase=phase, out=out).run()
        assert exit_code == 0
        output = out.getvalue()
        assert "Unknown phase" not in output
        assert expected_feedback in output


class AcceptingValidator:
    def __init__(self):
        self.validated_paths = []

    def validate(self, path):
        self.validated_paths.append(path)


class RejectingValidator:
    def validate(self, path):
        raise ValueError(f"File not found: {path}")


class TestValidateCommand:
    def test_prints_ok_when_injected_validator_accepts(self, out):
        validator = AcceptingValidator()
        exit_code = ValidateCommand(validator=validator, video_path="video.mp4", out=out).run()
        assert exit_code == 0
        assert validator.validated_paths == ["video.mp4"]
        assert "ok" in out.getvalue().lower() or "valid" in out.getvalue().lower()

    def test_prints_fail_and_returns_one_when_validator_rejects(self, out):
        exit_code = ValidateCommand(
            validator=RejectingValidator(), video_path="missing.mp4", out=out
        ).run()
        assert exit_code == 1
        assert "FAIL: File not found: missing.mp4" in out.getvalue()


class TestAnalyzeCommand:
    def test_dispatches_to_use_case_and_prints_output_path(self, out):
        captured = {}

        class FakeUseCase:
            def execute(self, input_path, output_path):
                captured["input"] = input_path
                captured["output"] = output_path
                return AnalyzeVideoResult(output_path=f"/abs/{output_path}", feedback_summary=[])

        cmd = AnalyzeCommand(use_case=FakeUseCase(), input_path="in.mp4", output_path="out.mp4", out=out)
        exit_code = cmd.run()
        assert exit_code == 0
        assert captured == {"input": "in.mp4", "output": "out.mp4"}
        assert "/abs/out.mp4" in out.getvalue()

    def test_prints_fail_and_returns_one_when_use_case_raises_value_error(self, out):
        class ExplodingUseCase:
            def execute(self, input_path, output_path):
                raise ValueError("File not found: in.mp4")

        cmd = AnalyzeCommand(
            use_case=ExplodingUseCase(), input_path="in.mp4", output_path="out.mp4", out=out
        )
        exit_code = cmd.run()

        assert exit_code == 1
        assert "FAIL: File not found: in.mp4" in out.getvalue()

    def test_prints_session_feedback_when_use_case_returns_structured_result(self, out):
        class FakeUseCase:
            def execute(self, input_path, output_path):
                return AnalyzeVideoResult(
                    output_path="/abs/out.mp4",
                    feedback_summary=[
                        "00:01.000-00:01.500 [FAULT/safety] setup: Keep knees out (10 frames)"
                    ],
                    report_json_path="/abs/out_report.json",
                    report_summary_path="/abs/out_summary.txt",
                )

        cmd = AnalyzeCommand(use_case=FakeUseCase(), input_path="in.mp4", output_path="out.mp4", out=out)
        exit_code = cmd.run()

        assert exit_code == 0
        output = out.getvalue()
        assert "Output written to: /abs/out.mp4" in output
        assert "JSON report: /abs/out_report.json" in output
        assert "Summary report: /abs/out_summary.txt" in output
        assert "Session feedback:" in output
        assert "00:01.000-00:01.500" in output


class TestCompareCommand:
    def test_dispatches_to_use_case_with_both_inputs_and_output(self, out):
        captured = {}

        class FakeUseCase:
            def execute(self, left_path, right_path, output_path):
                captured["left"] = left_path
                captured["right"] = right_path
                captured["output"] = output_path
                return f"/abs/{output_path}"

        cmd = CompareCommand(
            use_case=FakeUseCase(),
            left_path="left.mp4",
            right_path="right.mp4",
            output_path="compare.mp4",
            out=out,
        )
        exit_code = cmd.run()

        assert exit_code == 0
        assert captured == {
            "left": "left.mp4",
            "right": "right.mp4",
            "output": "compare.mp4",
        }
        assert "Side-by-side written to: /abs/compare.mp4" in out.getvalue()

    def test_prints_fail_and_returns_one_when_use_case_raises_value_error(self, out):
        class ExplodingUseCase:
            def execute(self, left_path, right_path, output_path):
                raise ValueError("Unable to open video: missing.mp4")

        cmd = CompareCommand(
            use_case=ExplodingUseCase(),
            left_path="left.mp4",
            right_path="missing.mp4",
            output_path="compare.mp4",
            out=out,
        )
        exit_code = cmd.run()

        assert exit_code == 1
        assert "FAIL: Unable to open video: missing.mp4" in out.getvalue()
