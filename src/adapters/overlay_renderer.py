from __future__ import annotations

import cv2
import numpy as np

from src.domain.angle_math import joint_angle
from src.domain.faults import FaultSeverity
from src.domain.models import BBox, Pose
from src.ports.frame_renderer import FrameRendererPort
from src.use_cases.analyze_lift import FrameAnalysis

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
    ("left_shoulder", "nose"),
    ("right_shoulder", "nose"),
]

# (label, vertex_a, vertex_b, vertex_c, joint_name_in_kb)
_ANGLE_SPECS = [
    ("Knee L", "left_hip", "left_knee", "left_ankle", "knee_angle"),
    ("Knee R", "right_hip", "right_knee", "right_ankle", "knee_angle"),
    ("Hip L", "left_shoulder", "left_hip", "left_knee", "hip_angle"),
    ("Hip R", "right_shoulder", "right_hip", "right_knee", "hip_angle"),
    ("Elbow L", "left_shoulder", "left_elbow", "left_wrist", "elbow_angle"),
    ("Elbow R", "right_shoulder", "right_elbow", "right_wrist", "elbow_angle"),
]

# BGR colours per severity
_SEVERITY_COLOR = {
    FaultSeverity.GOOD: (0, 255, 0),       # green
    FaultSeverity.WARNING: (0, 200, 255),  # amber
    FaultSeverity.FAULT: (0, 0, 255),      # red
}
_DEFAULT_COLOR = (0, 255, 255)  # cyan when no analysis


class OverlayRenderer(FrameRendererPort):
    def render(
        self,
        frame: np.ndarray,
        bbox: BBox | None,
        pose: Pose | None,
        analysis: FrameAnalysis | None = None,
    ) -> np.ndarray:
        output = frame.copy()
        if pose is not None:
            self._draw_skeleton(output, pose)
            self._draw_angles(output, pose, analysis)
        if analysis is not None:
            self._draw_phase_banner(output, analysis)
        return output

    @staticmethod
    def _draw_skeleton(frame: np.ndarray, pose: Pose) -> None:
        for name_a, name_b in _SKELETON_SEGMENTS:
            kp_a, kp_b = pose.get(name_a), pose.get(name_b)
            if kp_a and kp_b:
                cv2.line(frame, kp_a.as_tuple(), kp_b.as_tuple(), (255, 255, 255), 4)
                cv2.line(frame, kp_a.as_tuple(), kp_b.as_tuple(), (0, 255, 255), 2)
        for kp in pose.keypoints:
            cv2.circle(frame, kp.as_tuple(), 8, (0, 255, 255), -1)
            cv2.circle(frame, kp.as_tuple(), 10, (255, 255, 255), 2)

    @staticmethod
    def _draw_angles(frame: np.ndarray, pose: Pose, analysis: FrameAnalysis | None) -> None:
        severity_by_joint = OverlayRenderer._severity_by_joint(analysis)
        rows: list[tuple[str, float, tuple[int, int, int]]] = []
        for label, name_a, name_b, name_c, kb_joint in _ANGLE_SPECS:
            if not pose.has_all([name_a, name_b, name_c]):
                continue
            a, b, c = pose.get(name_a), pose.get(name_b), pose.get(name_c)
            angle = joint_angle(a, b, c)
            color = _SEVERITY_COLOR.get(severity_by_joint.get(kb_joint), _DEFAULT_COLOR)
            rows.append((label, angle, color))
        if rows:
            OverlayRenderer._draw_angle_panel(frame, rows)

    @staticmethod
    def _severity_by_joint(analysis: FrameAnalysis | None) -> dict[str, FaultSeverity]:
        if analysis is None:
            return {}
        return {f.joint: f.severity for f in analysis.faults}

    @staticmethod
    def _draw_angle_panel(
        frame: np.ndarray,
        rows: list[tuple[str, float, tuple[int, int, int]]],
    ) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale, thickness, outline = 0.7, 2, 4
        line_height = 28
        padding = 12
        frame_h = frame.shape[0]

        # Bottom-left anchor: bottom of last row sits 'padding' above frame bottom.
        first_row_baseline_y = frame_h - padding - line_height * (len(rows) - 1)

        for i, (label, angle, color) in enumerate(rows):
            text = f"{label}: {int(round(angle))} deg"
            x = padding
            y = first_row_baseline_y + i * line_height
            cv2.putText(frame, text, (x, y), font, font_scale, (0, 0, 0), outline, cv2.LINE_AA)
            cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)

    @staticmethod
    def _draw_phase_banner(frame: np.ndarray, analysis: FrameAnalysis) -> None:
        text = f"Phase: {analysis.phase.value.upper()}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, text, (15, 35), font, 1.0, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(frame, text, (15, 35), font, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
