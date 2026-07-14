"""Shared fixtures for adapter tests.

The integration tests exercise real OpenCV I/O against a sample lift video.
The real recording lives at ``data/sample_video_side.mp4`` and is gitignored,
so on machines without it (e.g. CI) a synthetic stick-figure stand-in is
rendered once per session via the regression-suite clip machinery. When the
real file exists it is used untouched.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.regression.synthetic_clip import render_clip
from tests.regression.synthetic_pose import PoseSpec, build_side_pose

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_SAMPLE_VIDEO = _REPO_ROOT / "data" / "sample_video_side.mp4"

_STAND_IN_FRAME_COUNT = 30
_STAND_IN_FPS = 30.0
_STAND_IN_WIDTH = 640
_STAND_IN_HEIGHT = 480


@pytest.fixture(scope="session")
def sample_video_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    if _REAL_SAMPLE_VIDEO.exists():
        return str(_REAL_SAMPLE_VIDEO)
    return str(_render_stand_in(tmp_path_factory.mktemp("sample-video")))


def _render_stand_in(directory: Path) -> Path:
    clip_path = directory / "sample_video_side.mp4"
    poses = [
        build_side_pose(PoseSpec(knee_angle=120.0 + index, hip_angle=100.0, elbow_angle=170.0))
        for index in range(_STAND_IN_FRAME_COUNT)
    ]
    render_clip(
        poses,
        clip_path,
        fps=_STAND_IN_FPS,
        width=_STAND_IN_WIDTH,
        height=_STAND_IN_HEIGHT,
    )
    return clip_path
