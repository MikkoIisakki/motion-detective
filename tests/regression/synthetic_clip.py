"""Renders a sequence of `Pose` objects to a stick-figure MP4 on disk.

Used to materialise the synthetic clips committed under
`tests/regression/clips/`. The clips are deterministic by construction so a
regenerated MP4 can be diff'd against the committed one when tuning fixtures.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.domain.models import Pose


_SKELETON_SEGMENTS = [
    ("left_ankle", "left_knee"),
    ("left_knee", "left_hip"),
    ("left_hip", "left_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_ankle", "right_knee"),
    ("right_knee", "right_hip"),
    ("right_hip", "right_shoulder"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "right_shoulder"),
    ("left_hip", "right_hip"),
    # Head: mirror the production overlay renderer so the synthetic clips
    # show a head line + circle once the pose builder emits a `nose` kp.
    ("left_shoulder", "nose"),
    ("right_shoulder", "nose"),
]

_BACKGROUND = (32, 32, 32)
_LINE = (200, 220, 200)
_JOINT = (255, 255, 255)
_LINE_THICKNESS = 3
_JOINT_RADIUS = 3
_HEAD_RADIUS = 18


def render_clip(
    poses: list[Pose | None],
    output_path: str | Path,
    *,
    fps: float,
    width: int,
    height: int,
) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out), fourcc, fps, (width, height))
    try:
        background = np.full((height, width, 3), _BACKGROUND, dtype=np.uint8)
        for pose in poses:
            frame = background.copy()
            if pose is not None:
                _draw_stick_figure(frame, pose)
            writer.write(frame)
    finally:
        writer.release()


def _draw_stick_figure(frame: np.ndarray, pose: Pose) -> None:
    for a_name, b_name in _SKELETON_SEGMENTS:
        a, b = pose.get(a_name), pose.get(b_name)
        if a is None or b is None:
            continue
        cv2.line(frame, a.as_tuple(), b.as_tuple(), _LINE, _LINE_THICKNESS)
    nose = pose.get("nose")
    if nose is not None:
        cv2.circle(frame, nose.as_tuple(), _HEAD_RADIUS, _LINE, _LINE_THICKNESS)
    for kp in pose.keypoints:
        cv2.circle(frame, kp.as_tuple(), _JOINT_RADIUS, _JOINT, -1)
