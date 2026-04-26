from __future__ import annotations

import importlib.util
from typing import Optional

import cv2
import numpy as np

from src.domain.models import BBox
from src.ports.detector import DetectorPort


class YoloPoseDetector(DetectorPort):
    """YOLO-based person detector with HOG + motion fallback and temporal tracking."""

    def __init__(
        self,
        yolo_model: str = "yolov8n-pose.pt",
        yolo_conf: float = 0.35,
        min_motion_area: int = 3000,
        max_missing_frames: int = 8,
    ) -> None:
        self._yolo_model_path = yolo_model
        self._yolo_conf = yolo_conf
        self._min_motion_area = min_motion_area
        self._max_missing_frames = max_missing_frames

        self._yolo = self._load_yolo() if self._ultralytics_available() else None
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=400, varThreshold=32, detectShadows=False
        )
        self._last_bbox: Optional[BBox] = None
        self._missing_frames = 0

    @staticmethod
    def _ultralytics_available() -> bool:
        return importlib.util.find_spec("ultralytics") is not None

    def _load_yolo(self):
        from ultralytics import YOLO  # type: ignore
        return YOLO(self._yolo_model_path)

    def detect(self, frame: np.ndarray) -> BBox | None:
        previous_center = self._last_bbox.center if self._last_bbox else None

        if self._yolo is not None:
            candidates = self._detect_yolo(frame)
        else:
            candidates = self._detect_hog(frame)

        best = self._choose_best(candidates, previous_center)

        if best is None:
            best = self._detect_motion(frame)

        if best is not None:
            self._last_bbox = best
            self._missing_frames = 0
            return best

        if self._last_bbox is not None and self._missing_frames < self._max_missing_frames:
            self._missing_frames += 1
            return self._last_bbox

        self._last_bbox = None
        return None

    def _detect_yolo(self, frame: np.ndarray) -> list[BBox]:
        result = self._yolo.predict(frame, classes=[0], conf=self._yolo_conf, verbose=False)
        if not result or result[0].boxes is None:
            return []
        boxes = []
        for x1, y1, x2, y2 in result[0].boxes.xyxy.cpu().numpy():
            w, h = max(0, int(x2 - x1)), max(0, int(y2 - y1))
            boxes.append(BBox(int(x1), int(y1), w, h))
        return boxes

    def _detect_hog(self, frame: np.ndarray) -> list[BBox]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        boxes, _ = self._hog.detectMultiScale(gray, winStride=(8, 8), padding=(8, 8), scale=1.05)
        return [BBox(int(x), int(y), int(w), int(h)) for x, y, w, h in boxes]

    def _detect_motion(self, frame: np.ndarray) -> BBox | None:
        mask = self._bg_subtractor.apply(frame)
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < self._min_motion_area:
            return None
        x, y, w, h = cv2.boundingRect(largest)
        return BBox(int(x), int(y), int(w), int(h))

    @staticmethod
    def _choose_best(candidates: list[BBox], previous_center: tuple[int, int] | None) -> BBox | None:
        if not candidates:
            return None
        if previous_center is None:
            return max(candidates, key=lambda b: b.area)

        def score(bbox: BBox) -> float:
            cx, cy = bbox.center
            dist = float(np.hypot(cx - previous_center[0], cy - previous_center[1]))
            return dist - 0.001 * bbox.area

        return min(candidates, key=score)
