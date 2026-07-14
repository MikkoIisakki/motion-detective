"""Regression net for phase detection on real footage.

The phase detector once spent an entire real clip in IDLE because its
IDLE -> SETUP gate demanded the wrist at ankle height — a loaded bar sits at
plate height, so real wrists only ever reach knee height. Synthetic clips
(whose arms are authored to hang to ankle level) never caught this, so this
test drives the real side-view recording through the real OpenCV reader and
the real YOLO pose estimator and asserts the detector leaves IDLE.

Unlike the other adapter integration tests this one must not fall back to the
synthetic stand-in clip (`sample_video_path` fixture): a synthetic standing
figure never reaches a setup position, so the fallback would assert nothing.
It skips instead when the real recording or the YOLO weights are unavailable.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.opencv_video import OpenCVVideoReader
from src.adapters.yolo_inference import ultralytics_available
from src.domain.faults import LiftPhase
from src.domain.keypoint_smoother import KeypointSmoother
from src.domain.phase_detector import PhaseDetector

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_SAMPLE_VIDEO = _REPO_ROOT / "data" / "sample_video_side.mp4"
_YOLO_WEIGHTS = _REPO_ROOT / "yolov8n-pose.pt"

# The lifter is over the bar within the first seconds of the clip; scanning a
# bounded prefix keeps a failing run from grinding through the whole video.
_MAX_FRAMES = 300


@pytest.mark.integration
class TestPhaseDetectionOnRealFootage:
    def test_detector_leaves_idle_on_real_side_view_clip(self):
        if not _REAL_SAMPLE_VIDEO.exists():
            pytest.skip(f"real recording not available: {_REAL_SAMPLE_VIDEO}")
        if not _YOLO_WEIGHTS.exists():
            pytest.skip(f"YOLO pose weights not available: {_YOLO_WEIGHTS}")
        if not ultralytics_available():
            pytest.skip("ultralytics is not importable in this environment")

        phases = self._detect_phases()

        assert LiftPhase.SETUP in phases, (
            "PhaseDetector never left IDLE on real footage — the IDLE -> SETUP "
            f"gate regressed (saw only: {sorted({p.value for p in phases})})"
        )

    @staticmethod
    def _detect_phases() -> list[LiftPhase]:
        # Imported lazily: constructing the estimator pulls in ultralytics.
        from src.adapters.yolo_detector import YoloPoseDetector
        from src.adapters.yolo_inference import CachedYoloInference
        from src.adapters.yolo_pose_estimator import YoloPoseEstimator

        inference = CachedYoloInference(yolo_model=str(_YOLO_WEIGHTS))
        detector = YoloPoseDetector(inference=inference)
        estimator = YoloPoseEstimator(inference=inference)
        smoother = KeypointSmoother(alpha=0.5)
        phase_detector = PhaseDetector(lift="snatch")

        reader = OpenCVVideoReader()
        reader.open(str(_REAL_SAMPLE_VIDEO))
        phases: list[LiftPhase] = []
        try:
            for _ in range(_MAX_FRAMES):
                ok, frame = reader.read_frame()
                if not ok:
                    break
                bbox = detector.detect(frame)
                pose = estimator.estimate(frame, bbox) if bbox else None
                if pose is None:
                    continue
                phases.append(phase_detector.update(smoother.smooth(pose)))
                if LiftPhase.SETUP in phases:
                    break  # proven — no need to grind through the whole clip
        finally:
            reader.close()
        return phases
