from __future__ import annotations

from pathlib import Path

import numpy as np

from src.ports.video_reader import VideoMeta, VideoReaderPort
from src.ports.video_writer import VideoWriterPort


class CompareVideos:
    def __init__(
        self,
        left_reader: VideoReaderPort,
        right_reader: VideoReaderPort,
        writer: VideoWriterPort,
    ) -> None:
        self._left_reader = left_reader
        self._right_reader = right_reader
        self._writer = writer

    def execute(self, left_path: str, right_path: str, output_path: str) -> str:
        left_meta = self._left_reader.open(left_path)
        try:
            right_meta = self._right_reader.open(right_path)
            output_meta = self._build_output_meta(left_meta, right_meta)
            self._writer.open(output_path, output_meta)
            try:
                self._stitch(output_meta.height)
            finally:
                self._writer.close()
        finally:
            self._left_reader.close()
            self._right_reader.close()
        return str(Path(output_path).resolve())

    def _stitch(self, target_height: int) -> None:
        while True:
            left_ok, left_frame = self._left_reader.read_frame()
            right_ok, right_frame = self._right_reader.read_frame()
            if not (left_ok and right_ok) or left_frame is None or right_frame is None:
                return
            stitched = np.hstack(
                [
                    _pad_to_height(left_frame, target_height),
                    _pad_to_height(right_frame, target_height),
                ]
            )
            self._writer.write_frame(stitched)

    @staticmethod
    def _build_output_meta(left: VideoMeta, right: VideoMeta) -> VideoMeta:
        return VideoMeta(
            fps=left.fps,
            width=left.width + right.width,
            height=max(left.height, right.height),
            total_frames=min(left.total_frames, right.total_frames),
        )


def _pad_to_height(frame: np.ndarray, target_height: int) -> np.ndarray:
    current_height = frame.shape[0]
    if current_height >= target_height:
        return frame
    pad_rows = target_height - current_height
    padding = np.zeros((pad_rows, frame.shape[1], frame.shape[2]), dtype=frame.dtype)
    return np.vstack([frame, padding])
