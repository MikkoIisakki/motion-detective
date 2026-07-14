from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.domain.fault_aggregator import FaultAggregator
from src.domain.frame_failure_policy import FrameFailure, FrameFailurePolicy
from src.domain.joint_gate import gate_keypoints
from src.domain.keypoint_smoother import KeypointSmoother
from src.ports.detector import DetectorPort
from src.ports.frame_renderer import FrameRendererPort
from src.ports.pose_estimator import PoseEstimatorPort
from src.ports.video_reader import VideoReaderPort
from src.ports.video_validator import VideoValidatorPort
from src.ports.video_writer import VideoWriterPort
from src.use_cases.analyze_lift import AnalyzeLift
from src.use_cases.frame_pump import pump_frames
from src.use_cases.session_report import write_session_reports


@dataclass(frozen=True)
class AnalyzeVideoResult:
    output_path: str
    feedback_summary: list[str]
    report_json_path: str | None = None
    report_summary_path: str | None = None
    frame_failures: tuple[FrameFailure, ...] = ()


class AnalyzeVideo:
    def __init__(
        self,
        validator: VideoValidatorPort,
        reader: VideoReaderPort,
        writer: VideoWriterPort,
        detector: DetectorPort,
        pose_estimator: PoseEstimatorPort,
        renderer: FrameRendererPort,
        analyzer: AnalyzeLift | None = None,
        smoother: KeypointSmoother | None = None,
        report_json_path: str | None = None,
        report_summary_path: str | None = None,
        min_joint_confidence: float | None = None,
    ) -> None:
        self._validator = validator
        self._reader = reader
        self._writer = writer
        self._detector = detector
        self._pose_estimator = pose_estimator
        self._renderer = renderer
        self._analyzer = analyzer
        self._smoother = smoother
        self._report_json_path = report_json_path
        self._report_summary_path = report_summary_path
        self._min_joint_confidence = min_joint_confidence

    def execute(self, input_path: str, output_path: str) -> AnalyzeVideoResult:
        self._validator.validate(input_path)
        if self._smoother is not None:
            self._smoother.reset()

        meta = self._reader.open(input_path)
        self._writer.open(output_path, meta)
        fps = meta.fps if meta.fps > 0 else 30.0
        aggregator = FaultAggregator()
        failure_policy = FrameFailurePolicy()
        frame_count = pump_frames(
            readers=(self._reader,),
            writer=self._writer,
            process=lambda frames, index: self._process_frame(frames[0], index, fps, aggregator),
            failure_policy=failure_policy,
        )
        return self._build_result(
            input_path, output_path, frame_count, fps, aggregator, tuple(failure_policy.failures)
        )

    def _process_frame(
        self, frame: np.ndarray, frame_index: int, fps: float, aggregator: FaultAggregator
    ) -> np.ndarray:
        bbox = self._detector.detect(frame)
        pose = self._pose_estimator.estimate(frame, bbox) if bbox is not None else None
        if pose is not None and self._min_joint_confidence:
            pose = gate_keypoints(pose, self._min_joint_confidence)
        if pose is not None and self._smoother is not None:
            pose = self._smoother.smooth(pose)
        analysis = self._analyzer.analyse_frame(pose) if self._analyzer and pose else None
        if analysis is not None:
            aggregator.observe(analysis.phase.value, analysis.faults, frame_index / fps)
        return self._renderer.render(frame, bbox, pose, analysis)

    def _build_result(
        self,
        input_path: str,
        output_path: str,
        frame_count: int,
        fps: float,
        aggregator: FaultAggregator,
        frame_failures: tuple[FrameFailure, ...],
    ) -> AnalyzeVideoResult:
        summary = aggregator.summary_lines()
        if frame_failures:
            summary.append(f"{len(frame_failures)} frames skipped due to errors.")
        output_resolved = str(Path(output_path).resolve())
        report_json_resolved: str | None = None
        report_summary_resolved: str | None = None
        if self._report_json_path and self._report_summary_path:
            report_json_resolved = str(Path(self._report_json_path).resolve())
            report_summary_resolved = str(Path(self._report_summary_path).resolve())
            write_session_reports(
                input_path=input_path,
                output_path=output_resolved,
                frame_count=frame_count,
                fps=fps,
                groups=aggregator.groups,
                summary=summary,
                report_json_path=report_json_resolved,
                report_summary_path=report_summary_resolved,
            )
        return AnalyzeVideoResult(
            output_path=output_resolved,
            feedback_summary=summary,
            report_json_path=report_json_resolved,
            report_summary_path=report_summary_resolved,
            frame_failures=frame_failures,
        )
