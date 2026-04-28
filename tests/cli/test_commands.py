import io
import pytest

from src.cli.commands import (
    AnalyzeCommand,
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
        exit_code = RulesCommand(kb=kb, lift="snatch", phase="catch", out=out).run()
        assert exit_code != 0


class TestValidateCommand:
    def test_prints_ok_for_valid_video(self, tmp_path, out):
        from unittest.mock import patch
        f = tmp_path / "video.mp4"
        f.write_bytes(b"\x00" * 64)

        with patch("src.adapters.file_validator.cv2.VideoCapture") as mock_cap:
            mock_cap.return_value.isOpened.return_value = True
            exit_code = ValidateCommand(video_path=str(f), out=out).run()

        assert exit_code == 0
        assert "ok" in out.getvalue().lower() or "valid" in out.getvalue().lower()

    def test_returns_nonzero_for_missing_file(self, tmp_path, out):
        exit_code = ValidateCommand(video_path=str(tmp_path / "missing.mp4"), out=out).run()
        assert exit_code != 0


class TestAnalyzeCommand:
    def test_dispatches_to_use_case_and_prints_output_path(self, out):
        captured = {}

        class FakeUseCase:
            def execute(self, input_path, output_path):
                captured["input"] = input_path
                captured["output"] = output_path
                return f"/abs/{output_path}"

        cmd = AnalyzeCommand(use_case=FakeUseCase(), input_path="in.mp4", output_path="out.mp4", out=out)
        exit_code = cmd.run()
        assert exit_code == 0
        assert captured == {"input": "in.mp4", "output": "out.mp4"}
        assert "/abs/out.mp4" in out.getvalue()

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
