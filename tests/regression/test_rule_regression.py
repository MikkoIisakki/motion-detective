"""End-to-end rule-regression tests driven by curated synthetic clips.

Each fixture under ``tests/regression/fixtures/`` describes a synthetic stick-
figure clip + a list of expected findings. The clip MP4 is rendered (and
cached) under ``tests/regression/clips/``. The test runs ``AnalyzeVideo``
through the real OpenCV reader/writer with a ``FixturePoseEstimator`` injected
in place of YOLO, then asserts the expected findings appear in the feedback
summary and no unexpected findings sneak in.

YOLO/HOG are bypassed on purpose: the goal is to regress the rule + phase
engine, not the model. The MP4s are checked into the repo so contributors can
inspect them visually; they are regenerated automatically if missing.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.adapters.file_validator import FileVideoValidator
from src.adapters.opencv_video import OpenCVVideoReader, OpenCVVideoWriter
from src.adapters.overlay_renderer import OverlayRenderer
from src.domain.knowledge_base import KnowledgeBase
from src.domain.models import BBox
from src.domain.phase_detector import PhaseDetector
from src.ports.detector import DetectorPort
from src.use_cases.analyze_lift import AnalyzeLift
from src.use_cases.analyze_video import AnalyzeVideo, AnalyzeVideoResult
from tests.regression.clip_fixture import ClipFixture, ExpectedFinding, load_fixture
from tests.regression.fixture_pose_estimator import FixturePoseEstimator
from tests.regression.synthetic_clip import render_clip


REGRESSION_DIR = Path(__file__).parent
FIXTURES_DIR = REGRESSION_DIR / "fixtures"
CLIPS_DIR = REGRESSION_DIR / "clips"
KB_PATH = Path(__file__).resolve().parents[2] / "config" / "knowledge_base.yml"

_NO_FAULTS_SUMMARY = "No actionable faults detected."


class _FullFrameDetector(DetectorPort):
    def __init__(self, width: int, height: int) -> None:
        self._bbox = BBox(0, 0, width, height)

    def detect(self, frame: np.ndarray) -> BBox:
        return self._bbox


def _ensure_clip(fixture: ClipFixture) -> Path:
    clip_path = CLIPS_DIR / f"{fixture.name}.mp4"
    if not clip_path.exists():
        render_clip(
            fixture.poses,
            clip_path,
            fps=fixture.fps,
            width=fixture.width,
            height=fixture.height,
        )
    return clip_path


def _run_clip(fixture: ClipFixture, tmp_path: Path) -> AnalyzeVideoResult:
    clip_path = _ensure_clip(fixture)
    kb = KnowledgeBase.from_file(str(KB_PATH))
    use_case = AnalyzeVideo(
        validator=FileVideoValidator(),
        reader=OpenCVVideoReader(),
        writer=OpenCVVideoWriter(),
        detector=_FullFrameDetector(fixture.width, fixture.height),
        pose_estimator=FixturePoseEstimator(fixture.poses),
        renderer=OverlayRenderer(),
        analyzer=AnalyzeLift(kb, PhaseDetector(), fixture.lift),
    )
    output_path = tmp_path / f"{fixture.name}_annotated.mp4"
    return use_case.execute(str(clip_path), str(output_path))


def _matches(line: str, expected: ExpectedFinding) -> bool:
    return (
        expected.severity in line
        and expected.priority in line
        and f" {expected.phase}:" in line
        and expected.feedback_substring in line
    )


def _fixture_paths() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.yaml"))


@pytest.mark.parametrize(
    "fixture_path", _fixture_paths(), ids=lambda p: p.stem
)
def test_clip_produces_expected_findings(fixture_path: Path, tmp_path: Path) -> None:
    fixture = load_fixture(fixture_path)
    result = _run_clip(fixture, tmp_path)

    if not fixture.expected:
        assert result.feedback_summary == [_NO_FAULTS_SUMMARY], (
            f"[{fixture.name}] expected no findings, got:\n  "
            + "\n  ".join(result.feedback_summary)
        )
        return

    for expected in fixture.expected:
        assert any(_matches(line, expected) for line in result.feedback_summary), (
            f"[{fixture.name}] expected finding not in summary:\n  "
            f"want: {expected}\n  got:\n    "
            + "\n    ".join(result.feedback_summary)
        )

    unmatched = [
        line for line in result.feedback_summary
        if line != _NO_FAULTS_SUMMARY
        and not any(_matches(line, e) for e in fixture.expected)
    ]
    assert not unmatched, (
        f"[{fixture.name}] unexpected findings in summary:\n  "
        + "\n  ".join(unmatched)
    )
