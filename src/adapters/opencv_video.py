from __future__ import annotations

import cv2
import numpy as np

from src.ports.video_reader import VideoDecodeError, VideoMeta, VideoReaderPort
from src.ports.video_writer import VideoWriterPort


class OpenCVVideoReader(VideoReaderPort):
    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._expected_frames = 0
        self._frames_delivered = 0
        self._decode_failure_signalled = False

    def open(self, path: str) -> VideoMeta:
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise ValueError(f"Unable to open video: {path}")
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # CAP_PROP_FRAME_COUNT is unreliable for some containers (-1/0);
        # in that case decode errors cannot be told apart from EOF.
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self._expected_frames = max(total_frames, 0)
        self._frames_delivered = 0
        self._decode_failure_signalled = False
        return VideoMeta(fps=fps, width=width, height=height, total_frames=total_frames)

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._cap is None:
            return False, None
        ok, frame = self._cap.read()
        if ok:
            self._frames_delivered += 1
            self._decode_failure_signalled = False
            return True, frame
        if self._is_decode_failure():
            # Signal once per failure streak: if OpenCV cannot advance past the
            # broken frame, subsequent reads report end-of-stream instead of
            # raising forever (frame-count metadata may also simply overcount).
            self._decode_failure_signalled = True
            raise VideoDecodeError(
                f"Failed to decode frame {self._frames_delivered}"
                f" (expected {self._expected_frames} frames)"
            )
        return False, None

    def _is_decode_failure(self) -> bool:
        return (
            not self._decode_failure_signalled
            and self._expected_frames > 0
            and self._frames_delivered < self._expected_frames
        )

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
            cv2.VideoWriter.fourcc(*"mp4v"),
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
