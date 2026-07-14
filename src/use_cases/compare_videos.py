from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from src.ports.video_reader import VideoMeta, VideoReaderPort
from src.ports.video_writer import VideoWriterPort
from src.use_cases.frame_pump import pump_frames


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
        output_meta = self._open_streams(left_path, right_path, output_path)
        pump_frames(
            readers=(self._left_reader, self._right_reader),
            writer=self._writer,
            process=lambda frames, index: self._stitch(frames, output_meta.height),
        )
        return str(Path(output_path).resolve())

    def _open_streams(self, left_path: str, right_path: str, output_path: str) -> VideoMeta:
        left_meta = self._left_reader.open(left_path)
        try:
            right_meta = self._right_reader.open(right_path)
            output_meta = self._build_output_meta(left_meta, right_meta)
            self._writer.open(output_path, output_meta)
        except Exception:
            self._left_reader.close()
            self._right_reader.close()
            raise
        return output_meta

    @staticmethod
    def _stitch(frames: Sequence[np.ndarray], target_height: int) -> np.ndarray:
        return np.hstack([_pad_to_height(frame, target_height) for frame in frames])

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
