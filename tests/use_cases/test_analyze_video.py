import json
import numpy as np
import pytest

from src.domain.faults import FaultPriority, FaultResult, FaultSeverity, LiftPhase
from src.domain.models import BBox, Keypoint, Pose
from src.ports.detector import DetectorPort
from src.ports.frame_renderer import FrameRendererPort
from src.ports.pose_estimator import PoseEstimatorPort
from src.ports.video_reader import VideoMeta, VideoReaderPort
from src.ports.video_validator import VideoValidatorPort
from src.ports.video_writer import VideoWriterPort
from src.use_cases.analyze_lift import FrameAnalysis
from src.use_cases.analyze_video import AnalyzeVideo


# --- Fakes ---

class FakeValidator(VideoValidatorPort):
    def __init__(self, should_raise: bool = False):
        self._should_raise = should_raise

    def validate(self, path: str) -> None:
        if self._should_raise:
            raise ValueError(f"Invalid video: {path}")


class FakeReader(VideoReaderPort):
    def __init__(self, frames: list[np.ndarray], meta: VideoMeta | None = None):
        self._frames = frames
        self._meta = meta or VideoMeta(fps=30.0, width=320, height=240, total_frames=len(frames))
        self._index = 0

    def open(self, path: str) -> VideoMeta:
        self._index = 0
        return self._meta

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._index >= len(self._frames):
            return False, None
        frame = self._frames[self._index]
        self._index += 1
        return True, frame

    def close(self) -> None:
        pass


class FakeWriter(VideoWriterPort):
    def __init__(self):
        self.written_frames: list[np.ndarray] = []
        self.opened_path: str | None = None
        self.closed = False

    def open(self, path: str, meta: VideoMeta) -> None:
        self.opened_path = path

    def write_frame(self, frame: np.ndarray) -> None:
        self.written_frames.append(frame)

    def close(self) -> None:
        self.closed = True


class FakeDetector(DetectorPort):
    def __init__(self, bbox: BBox | None = None):
        self._bbox = bbox

    def detect(self, frame: np.ndarray) -> BBox | None:
        return self._bbox


class FakePoseEstimator(PoseEstimatorPort):
    def __init__(self, pose: Pose | None = None):
        self._pose = pose

    def estimate(self, frame: np.ndarray, bbox: BBox) -> Pose | None:
        return self._pose


class FakeRenderer(FrameRendererPort):
    def __init__(self):
        self.calls: list[tuple] = []

    def render(self, frame: np.ndarray, bbox: BBox | None, pose: Pose | None, analysis=None) -> np.ndarray:
        self.calls.append((bbox, pose))
        return frame.copy()


class FakeAnalyzer:
    def __init__(self, analyses: list[FrameAnalysis]):
        self._analyses = analyses
        self._index = 0

    def analyse_frame(self, pose: Pose) -> FrameAnalysis:
        if self._index >= len(self._analyses):
            return self._analyses[-1]
        result = self._analyses[self._index]
        self._index += 1
        return result


# --- Tests ---

def make_use_case(**overrides):
    defaults = dict(
        validator=FakeValidator(),
        reader=FakeReader([np.zeros((240, 320, 3), dtype=np.uint8)]),
        writer=FakeWriter(),
        detector=FakeDetector(),
        pose_estimator=FakePoseEstimator(),
        renderer=FakeRenderer(),
    )
    defaults.update(overrides)
    return AnalyzeVideo(**defaults)


class TestAnalyzeVideo:
    def test_raises_when_validation_fails(self):
        uc = make_use_case(validator=FakeValidator(should_raise=True))
        with pytest.raises(ValueError, match="Invalid video"):
            uc.execute("input.mp4", "output.mp4")

    def test_writes_one_frame_per_input_frame(self):
        frames = [np.zeros((240, 320, 3), dtype=np.uint8) for _ in range(5)]
        writer = FakeWriter()
        uc = make_use_case(reader=FakeReader(frames), writer=writer)
        uc.execute("input.mp4", "output.mp4")
        assert len(writer.written_frames) == 5

    def test_writer_opened_with_correct_output_path(self):
        writer = FakeWriter()
        uc = make_use_case(writer=writer)
        uc.execute("input.mp4", "output/result.mp4")
        assert writer.opened_path == "output/result.mp4"

    def test_writer_is_closed_after_processing(self):
        writer = FakeWriter()
        uc = make_use_case(writer=writer)
        uc.execute("input.mp4", "output.mp4")
        assert writer.closed is True

    def test_writer_is_closed_even_when_renderer_raises(self):
        class BrokenRenderer(FrameRendererPort):
            def render(self, frame, bbox, pose, analysis=None):
                raise RuntimeError("renderer exploded")

        writer = FakeWriter()
        frames = [np.zeros((240, 320, 3), dtype=np.uint8)]
        uc = make_use_case(
            reader=FakeReader(frames),
            writer=writer,
            renderer=BrokenRenderer(),
        )
        with pytest.raises(RuntimeError):
            uc.execute("input.mp4", "output.mp4")
        assert writer.closed is True

    def test_renderer_receives_detected_bbox_and_pose(self):
        bbox = BBox(10, 20, 80, 120)
        pose = Pose([Keypoint("left_knee", 50, 90)])
        renderer = FakeRenderer()
        uc = make_use_case(
            detector=FakeDetector(bbox),
            pose_estimator=FakePoseEstimator(pose),
            renderer=renderer,
        )
        uc.execute("input.mp4", "output.mp4")
        assert renderer.calls[0] == (bbox, pose)

    def test_pose_estimation_skipped_when_no_detection(self):
        renderer = FakeRenderer()
        uc = make_use_case(
            detector=FakeDetector(None),
            renderer=renderer,
        )
        uc.execute("input.mp4", "output.mp4")
        assert renderer.calls[0] == (None, None)

    def test_execute_returns_resolved_output_path(self):
        uc = make_use_case()
        result = uc.execute("input.mp4", "output.mp4")
        assert result.output_path.endswith("output.mp4")

    def test_result_includes_no_fault_summary_when_no_actionable_faults(self):
        uc = make_use_case()
        result = uc.execute("input.mp4", "output.mp4")
        assert result.feedback_summary == ["No actionable faults detected."]

    def test_result_includes_timestamped_grouped_feedback(self):
        frames = [np.zeros((240, 320, 3), dtype=np.uint8) for _ in range(3)]
        pose = Pose([Keypoint("left_knee", 50, 90)])
        fault = FaultResult(
            joint="knee_angle",
            severity=FaultSeverity.FAULT,
            priority=FaultPriority.SAFETY,
            feedback="Keep knees tracking over toes",
        )
        analyzer = FakeAnalyzer(
            analyses=[
                FrameAnalysis(phase=LiftPhase.SETUP, measurements=[], faults=[fault]),
                FrameAnalysis(phase=LiftPhase.SETUP, measurements=[], faults=[fault]),
                FrameAnalysis(phase=LiftPhase.SETUP, measurements=[], faults=[]),
            ]
        )
        uc = make_use_case(
            reader=FakeReader(frames, meta=VideoMeta(fps=2.0, width=320, height=240, total_frames=3)),
            detector=FakeDetector(BBox(10, 20, 80, 120)),
            pose_estimator=FakePoseEstimator(pose),
            analyzer=analyzer,
        )

        result = uc.execute("input.mp4", "output.mp4")

        assert len(result.feedback_summary) == 1
        assert "00:00.000-00:00.500" in result.feedback_summary[0]
        assert "[FAULT/safety]" in result.feedback_summary[0]
        assert "setup" in result.feedback_summary[0]
        assert "(2 frames)" in result.feedback_summary[0]

    def test_writes_json_and_summary_report_when_paths_provided(self, tmp_path):
        frames = [np.zeros((240, 320, 3), dtype=np.uint8) for _ in range(2)]
        pose = Pose([Keypoint("left_knee", 50, 90)])
        fault = FaultResult(
            joint="knee_angle",
            severity=FaultSeverity.WARNING,
            priority=FaultPriority.PERFORMANCE,
            feedback="Stay over the mid-foot longer",
        )
        analyzer = FakeAnalyzer(
            analyses=[
                FrameAnalysis(phase=LiftPhase.FIRST_PULL, measurements=[], faults=[fault]),
                FrameAnalysis(phase=LiftPhase.FIRST_PULL, measurements=[], faults=[]),
            ]
        )
        report_json = tmp_path / "reports" / "session.json"
        report_summary = tmp_path / "reports" / "session.txt"
        uc = make_use_case(
            reader=FakeReader(frames, meta=VideoMeta(fps=2.0, width=320, height=240, total_frames=2)),
            detector=FakeDetector(BBox(10, 20, 80, 120)),
            pose_estimator=FakePoseEstimator(pose),
            analyzer=analyzer,
            report_json_path=str(report_json),
            report_summary_path=str(report_summary),
        )

        result = uc.execute("input.mp4", str(tmp_path / "annotated.mp4"))

        assert result.report_json_path == str(report_json.resolve())
        assert result.report_summary_path == str(report_summary.resolve())
        assert report_json.exists()
        assert report_summary.exists()
        data = json.loads(report_json.read_text(encoding="utf-8"))
        assert data["summary"]
        assert data["findings"][0]["phase"] == "first_pull"
        assert data["findings"][0]["severity"] == "WARNING"
        summary_text = report_summary.read_text(encoding="utf-8")
        assert "Motion Detective Session Report" in summary_text
        assert "Feedback Summary:" in summary_text
