from __future__ import annotations

import mimetypes
import os

import cv2

from src.ports.video_validator import VideoValidatorPort


class FileVideoValidator(VideoValidatorPort):
    def validate(self, path: str) -> None:
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            raise ValueError(f"File not found: {abs_path}")
        if not os.path.isfile(abs_path):
            raise ValueError(f"Not a file: {abs_path}")
        if not os.access(abs_path, os.R_OK):
            raise ValueError(f"File is not readable: {abs_path}")

        mime_type, _ = mimetypes.guess_type(abs_path)
        if mime_type is None or not mime_type.startswith("video"):
            raise ValueError(f"Not a recognised video format: {abs_path}")

        cap = cv2.VideoCapture(abs_path)
        try:
            if not cap.isOpened():
                raise ValueError(f"OpenCV cannot open video file: {abs_path}")
        finally:
            cap.release()
