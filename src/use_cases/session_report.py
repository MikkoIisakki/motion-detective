"""Writes the JSON and plain-text session reports for an analysis run."""
from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from src.domain.fault_aggregator import FaultGroup, format_timestamp


def write_session_reports(
    *,
    input_path: str,
    output_path: str,
    frame_count: int,
    fps: float,
    groups: Iterable[FaultGroup],
    summary: list[str],
    report_json_path: str,
    report_summary_path: str,
) -> None:
    report = _build_report(input_path, output_path, frame_count, fps, groups, summary)

    json_path = Path(report_json_path)
    summary_path = Path(report_summary_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_path.write_text(_render_summary_text(report), encoding="utf-8")


def _build_report(
    input_path: str,
    output_path: str,
    frame_count: int,
    fps: float,
    groups: Iterable[FaultGroup],
    summary: list[str],
) -> dict:
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
            "start_timestamp": format_timestamp(g.start_seconds),
            "end_timestamp": format_timestamp(g.end_seconds),
            "frames": g.hit_count,
        }
        for g in entries
    ]
    return {
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


def _render_summary_text(report: dict) -> str:
    lines = [
        "Motion Detective Session Report",
        f"Generated (UTC): {report['generated_at_utc']}",
        f"Input video: {report['input_video']}",
        f"Annotated video: {report['annotated_video']}",
        f"Processed frames: {report['video']['processed_frames']}",
        f"FPS: {report['video']['fps']}",
        "",
        "Feedback Summary:",
    ]
    lines.extend([f"- {line}" for line in report["summary"]])
    return "\n".join(lines) + "\n"
