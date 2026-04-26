from __future__ import annotations

import numpy as np
import cv2

from src.ports.video_reader import VideoMeta, VideoReaderPort
from src.ports.video_writer import VideoWriterPort


class OpenCVVideoReader(VideoReaderPort):
    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None

    def open(self, path: str) -> VideoMeta:
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise ValueError(f"Unable to open video: {path}")
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        return VideoMeta(fps=fps, width=width, height=height, total_frames=total_frames)

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._cap is None:
            return False, None
        ok, frame = self._cap.read()
        if not ok:
            return False, None
        return True, frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class OpenCVVideoWriter(VideoWriterPort):
    def __init__(self) -> None:
        self._writer: cv2.VideoWriter | None = None

    def open(self, path: str, meta: VideoMeta) -> None:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._writer = cv2.VideoWriter(
            path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            meta.fps,
            (meta.width, meta.height),
        )

    def write_frame(self, frame: np.ndarray) -> None:
        if self._writer is not None:
            self._writer.write(frame)

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
