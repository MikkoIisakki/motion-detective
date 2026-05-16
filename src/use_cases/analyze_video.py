from __future__ import annotations

import json
from datetime import datetime, UTC
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable

from src.domain.faults import FaultPriority, FaultSeverity
from src.domain.keypoint_smoother import KeypointSmoother
from src.ports.detector import DetectorPort
from src.ports.frame_renderer import FrameRendererPort
from src.ports.pose_estimator import PoseEstimatorPort
from src.ports.video_reader import VideoReaderPort
from src.ports.video_validator import VideoValidatorPort
from src.ports.video_writer import VideoWriterPort
from src.use_cases.analyze_lift import AnalyzeLift


@dataclass(frozen=True)
class AnalyzeVideoResult:
    output_path: str
    feedback_summary: list[str]
    report_json_path: str | None = None
    report_summary_path: str | None = None


@dataclass
class _FaultGroup:
    phase: str
    feedback: str
    severity: FaultSeverity
    priority: FaultPriority
    start_seconds: float
    end_seconds: float
    hit_count: int = 1

    def observe(self, ts_seconds: float) -> None:
        self.end_seconds = ts_seconds
        self.hit_count += 1


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

    def execute(self, input_path: str, output_path: str) -> AnalyzeVideoResult:
        self._validator.validate(input_path)
        if self._smoother is not None:
            self._smoother.reset()

        meta = self._reader.open(input_path)
        self._writer.open(output_path, meta)
        fps = meta.fps if meta.fps > 0 else 30.0
        frame_index = 0
        groups: dict[tuple[str, str, FaultSeverity, FaultPriority], _FaultGroup] = {}
        try:
            while True:
                ok, frame = self._reader.read_frame()
                if not ok:
                    break
                bbox = self._detector.detect(frame)
                pose = self._pose_estimator.estimate(frame, bbox) if bbox is not None else None
                if pose is not None and self._smoother is not None:
                    pose = self._smoother.smooth(pose)
                analysis = self._analyzer.analyse_frame(pose) if self._analyzer and pose else None
                if analysis is not None and analysis.faults:
                    ts_seconds = frame_index / fps
                    for fault in analysis.faults:
                        if not fault.is_actionable:
                            continue
                        key = (
                            analysis.phase.value,
                            fault.feedback,
                            fault.severity,
                            fault.priority,
                        )
                        if key in groups:
                            groups[key].observe(ts_seconds)
                        else:
                            groups[key] = _FaultGroup(
                                phase=analysis.phase.value,
                                feedback=fault.feedback,
                                severity=fault.severity,
                                priority=fault.priority,
                                start_seconds=ts_seconds,
                                end_seconds=ts_seconds,
                            )
                rendered = self._renderer.render(frame, bbox, pose, analysis)
                self._writer.write_frame(rendered)
                frame_index += 1
        finally:
            self._reader.close()
            self._writer.close()

        summary = self._format_feedback_summary(groups.values())
        output_resolved = str(Path(output_path).resolve())
        report_json_resolved: str | None = None
        report_summary_resolved: str | None = None
        if self._report_json_path and self._report_summary_path:
            report_json_resolved = str(Path(self._report_json_path).resolve())
            report_summary_resolved = str(Path(self._report_summary_path).resolve())
            self._write_reports(
                input_path=input_path,
                output_path=output_resolved,
                frame_count=frame_index,
                fps=fps,
                groups=groups.values(),
                summary=summary,
                report_json_path=report_json_resolved,
                report_summary_path=report_summary_resolved,
            )
        return AnalyzeVideoResult(
            output_path=output_resolved,
            feedback_summary=summary,
            report_json_path=report_json_resolved,
            report_summary_path=report_summary_resolved,
        )

    @staticmethod
    def _format_feedback_summary(groups: Iterable[_FaultGroup]) -> list[str]:
        entries = list(groups)
        if not entries:
            return ["No actionable faults detected."]

        severity_rank = {
            FaultSeverity.FAULT: 0,
            FaultSeverity.WARNING: 1,
            FaultSeverity.GOOD: 2,
        }
        ordered = sorted(
            entries,
            key=lambda g: (severity_rank[g.severity], g.start_seconds),
        )

        lines: list[str] = []
        for g in ordered:
            start = AnalyzeVideo._format_time(g.start_seconds)
            end = AnalyzeVideo._format_time(g.end_seconds)
            lines.append(
                f"{start}-{end} [{g.severity.name}/{g.priority.value}] {g.phase}: {g.feedback} ({g.hit_count} frames)"
            )
        return lines

    @staticmethod
    def _format_time(seconds: float) -> str:
        total_ms = int(round(seconds * 1000))
        minutes = total_ms // 60000
        remaining_ms = total_ms % 60000
        whole_seconds = remaining_ms // 1000
        millis = remaining_ms % 1000
        return f"{minutes:02d}:{whole_seconds:02d}.{millis:03d}"

    @staticmethod
    def _write_reports(
        input_path: str,
        output_path: str,
        frame_count: int,
        fps: float,
        groups: Iterable[_FaultGroup],
        summary: list[str],
        report_json_path: str,
        report_summary_path: str,
    ) -> None:
        entries = sorted(
            groups,
            key=lambda g: (g.start_seconds, g.severity.value * -1),
        )
        findings = [
            {
                "phase": g.phase,
                "feedback": g.feedback,
                "severity": g.severity.name,
                "priority": g.priority.value,
                "start_seconds": round(g.start_seconds, 3),
                "end_seconds": round(g.end_seconds, 3),
                "start_timestamp": AnalyzeVideo._format_time(g.start_seconds),
                "end_timestamp": AnalyzeVideo._format_time(g.end_seconds),
                "frames": g.hit_count,
            }
            for g in entries
        ]
        report = {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "input_video": str(Path(input_path).resolve()),
            "annotated_video": output_path,
            "video": {
                "fps": round(fps, 3),
                "processed_frames": frame_count,
                "duration_seconds": round(frame_count / fps if fps > 0 else 0.0, 3),
            },
            "summary": summary,
            "findings": findings,
        }

        json_path = Path(report_json_path)
        summary_path = Path(report_summary_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        lines = [
            "Motion Detective Session Report",
            f"Generated (UTC): {report['generated_at_utc']}",
            f"Input video: {report['input_video']}",
            f"Annotated video: {report['annotated_video']}",
            f"Processed frames: {frame_count}",
            f"FPS: {round(fps, 3)}",
            "",
            "Feedback Summary:",
        ]
        lines.extend([f"- {line}" for line in summary])
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
