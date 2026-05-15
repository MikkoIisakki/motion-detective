"""Fixture loader for synthetic-clip regression tests.

A fixture YAML describes:
  - clip metadata (name, lift, fps, width, height)
  - a sequence of frame groups (each "count: N" repeats one pose spec N times)
  - expected findings the AnalyzeVideo summary must contain

Each pose entry is the field-for-field kwargs of `synthetic_pose.PoseSpec`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from src.domain.models import Pose
from tests.regression.synthetic_pose import PoseSpec, build_side_pose


@dataclass(frozen=True)
class ExpectedFinding:
    phase: str
    severity: str
    priority: str
    feedback_substring: str


@dataclass(frozen=True)
class ClipFixture:
    name: str
    lift: str
    fps: float
    width: int
    height: int
    poses: list[Pose]
    expected: list[ExpectedFinding]


def load_fixture(path: str | Path) -> ClipFixture:
    data = yaml.safe_load(Path(path).read_text())
    clip = data["clip"]
    poses: list[Pose] = []
    for entry in data["frames"]:
        spec = PoseSpec(**entry["pose"])
        count = int(entry.get("count", 1))
        pose = build_side_pose(spec)
        poses.extend([pose] * count)
    expected = [ExpectedFinding(**e) for e in data.get("expected", [])]
    return ClipFixture(
        name=clip["name"],
        lift=clip["lift"],
        fps=float(clip["fps"]),
        width=int(clip["width"]),
        height=int(clip["height"]),
        poses=poses,
        expected=expected,
    )
