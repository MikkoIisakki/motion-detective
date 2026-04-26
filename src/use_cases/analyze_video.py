from __future__ import annotations

from pathlib import Path

from src.ports.detector import DetectorPort
from src.ports.frame_renderer import FrameRendererPort
from src.ports.pose_estimator import PoseEstimatorPort
from src.ports.video_reader import VideoReaderPort
from src.ports.video_validator import VideoValidatorPort
from src.ports.video_writer import VideoWriterPort
from src.use_cases.analyze_lift import AnalyzeLift


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
    ) -> None:
        self._validator = validator
        self._reader = reader
        self._writer = writer
        self._detector = detector
        self._pose_estimator = pose_estimator
        self._renderer = renderer
        self._analyzer = analyzer

    def execute(self, input_path: str, output_path: str) -> str:
        self._validator.validate(input_path)

        meta = self._reader.open(input_path)
        self._writer.open(output_path, meta)
        try:
            while True:
                ok, frame = self._reader.read_frame()
                if not ok:
                    break
                bbox = self._detector.detect(frame)
                pose = self._pose_estimator.estimate(frame, bbox) if bbox is not None else None
                analysis = self._analyzer.analyse_frame(pose) if self._analyzer and pose else None
                rendered = self._renderer.render(frame, bbox, pose, analysis)
                self._writer.write_frame(rendered)
        finally:
            self._reader.close()
            self._writer.close()

        return str(Path(output_path).resolve())
