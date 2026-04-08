from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple

import cv2
import numpy as np

from src.input_validator import InputValidator


Point = Tuple[int, int]
BBox = Tuple[int, int, int, int]
Keypoints = dict[str, Point]


class WeightlifterDetector:
    """Validate input video and detect a primary weightlifter per frame."""

    def __init__(
        self,
        video_path: str,
        output_path: str,
        backend: str = "auto",
        yolo_model: str = "yolov8n-pose.pt",
        yolo_conf: float = 0.35,
        min_motion_area: int = 3000,
        max_missing_frames: int = 8,
    ) -> None:
        self.video_path = video_path
        self.output_path = output_path
        self.backend = backend
        self.yolo_model = yolo_model
        self.yolo_conf = yolo_conf
        self.min_motion_area = min_motion_area
        self.max_missing_frames = max_missing_frames

        self._validator = InputValidator(video_path)
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=400, varThreshold=32, detectShadows=False
        )
        self._yolo = None
        if self.backend == "yolo":
            self._yolo = self._load_yolo_model()
        elif self.backend == "auto" and self._ultralytics_available():
            self._yolo = self._load_yolo_model()
        elif self.backend not in {"auto", "hog", "yolo"}:
            raise ValueError(f"Unsupported backend: {self.backend}")
        self._last_bbox: Optional[BBox] = None
        self._last_keypoints: Optional[Keypoints] = None
        self._missing_frames = 0

    def validate_input(self) -> bool:
        return self._validator.validate()

    @staticmethod
    def _ultralytics_available() -> bool:
        return importlib.util.find_spec("ultralytics") is not None

    def _load_yolo_model(self):
        if not self._ultralytics_available():
            raise RuntimeError(
                "YOLO backend requires `ultralytics`. Install it with: pip install ultralytics"
            )
        from ultralytics import YOLO  # type: ignore

        return YOLO(self.yolo_model)

    @staticmethod
    def _yolo_keypoints_to_dict(keypoints_xy: np.ndarray) -> Keypoints:
        # COCO 17-keypoint order.
        names = {
            0: "nose",
            5: "left_shoulder",
            6: "right_shoulder",
            7: "left_elbow",
            8: "right_elbow",
            9: "left_wrist",
            10: "right_wrist",
            11: "left_hip",
            12: "right_hip",
            13: "left_knee",
            14: "right_knee",
            15: "left_ankle",
            16: "right_ankle",
        }
        points: Keypoints = {}
        for idx, name in names.items():
            if idx < len(keypoints_xy):
                x, y = keypoints_xy[idx]
                points[name] = (int(x), int(y))
        return points

    def _detect_people_yolo(self, frame: np.ndarray) -> list[tuple[BBox, Optional[Keypoints]]]:
        if self._yolo is None:
            return []
        result = self._yolo.predict(frame, classes=[0], conf=self.yolo_conf, verbose=False)
        if not result:
            return []
        boxes = result[0].boxes
        if boxes is None:
            return []

        xyxy = boxes.xyxy.cpu().numpy()
        keypoints_xy = None
        if getattr(result[0], "keypoints", None) is not None and result[0].keypoints.xy is not None:
            keypoints_xy = result[0].keypoints.xy.cpu().numpy()

        out: list[tuple[BBox, Optional[Keypoints]]] = []
        for i, (x1, y1, x2, y2) in enumerate(xyxy):
            w = max(0, int(x2 - x1))
            h = max(0, int(y2 - y1))
            kps = None
            if keypoints_xy is not None and i < len(keypoints_xy):
                kps = self._yolo_keypoints_to_dict(keypoints_xy[i])
            out.append(((int(x1), int(y1), w, h), kps))
        return out

    @staticmethod
    def _bbox_center(bbox: BBox) -> Point:
        x, y, w, h = bbox
        return (x + (w // 2), y + (h // 2))

    def _detect_people_hog(self, frame: np.ndarray) -> list[BBox]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        boxes, _weights = self._hog.detectMultiScale(
            gray,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in boxes]

    def _detect_motion_bbox(self, frame: np.ndarray) -> Optional[BBox]:
        mask = self._bg_subtractor.apply(frame)
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < self.min_motion_area:
            return None

        x, y, w, h = cv2.boundingRect(largest)
        return (int(x), int(y), int(w), int(h))

    def _choose_best_bbox(self, boxes: Iterable[BBox], previous_center: Optional[Point]) -> Optional[BBox]:
        candidates = list(boxes)
        if not candidates:
            return None

        if previous_center is None:
            return max(candidates, key=lambda box: box[2] * box[3])

        def score(box: BBox) -> float:
            center = self._bbox_center(box)
            distance = float(np.hypot(center[0] - previous_center[0], center[1] - previous_center[1]))
            area_bonus = 0.001 * (box[2] * box[3])
            return distance - area_bonus

        return min(candidates, key=score)

    def detect_weightlifter(self, frame: np.ndarray) -> Optional[BBox]:
        previous_center = self._bbox_center(self._last_bbox) if self._last_bbox else None
        if self._yolo is not None:
            yolo_candidates = self._detect_people_yolo(frame)
            person_boxes = [bbox for bbox, _kps in yolo_candidates]
        else:
            yolo_candidates = []
            person_boxes = self._detect_people_hog(frame)
        best = self._choose_best_bbox(person_boxes, previous_center)

        best_keypoints = None
        if best is not None and yolo_candidates:
            for bbox, kps in yolo_candidates:
                if bbox == best:
                    best_keypoints = kps
                    break

        if best is None:
            best = self._detect_motion_bbox(frame)
            best_keypoints = None

        if best is not None:
            self._last_bbox = best
            self._last_keypoints = best_keypoints
            self._missing_frames = 0
            return best

        if self._last_bbox is not None and self._missing_frames < self.max_missing_frames:
            self._missing_frames += 1
            return self._last_bbox

        self._last_bbox = None
        self._last_keypoints = None
        return None

    @staticmethod
    def _calculate_angle(a: Point, b: Point, c: Point) -> float:
        """
        Calculate joint angle ABC in degrees.
        """
        ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=np.float32)
        bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=np.float32)

        denom = (np.linalg.norm(ba) * np.linalg.norm(bc))
        if denom == 0:
            return 0.0
        cos_angle = float(np.clip(np.dot(ba, bc) / denom, -1.0, 1.0))
        angle = float(np.degrees(np.arccos(cos_angle)))
        return angle

    @staticmethod
    def _draw_angle_label(
        frame: np.ndarray,
        joint: Point,
        label: str,
        angle: float,
        occupied_boxes: list[tuple[int, int, int, int]],
    ) -> None:
        text = f"{label}: {int(round(angle))} deg"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.9
        thickness = 2
        outline_thickness = 5
        (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)

        # Candidate offsets around joint (try in order); skip if overlapping existing labels.
        candidates = [(10, -10), (10, 20), (-tw - 10, -10), (-tw - 10, 20), (0, -20)]
        frame_h, frame_w = frame.shape[:2]

        def intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

        for dx, dy in candidates:
            x = joint[0] + dx
            y = joint[1] + dy

            left = x - 2
            top = y - th - 2
            right = x + tw + 2
            bottom = y + baseline + 2

            if left < 0 or top < 0 or right >= frame_w or bottom >= frame_h:
                continue

            box = (left, top, right, bottom)
            if any(intersects(box, prev) for prev in occupied_boxes):
                continue

            cv2.putText(frame, text, (x, y), font, font_scale, (0, 0, 0), outline_thickness, cv2.LINE_AA)
            cv2.putText(frame, text, (x, y), font, font_scale, (0, 255, 255), thickness, cv2.LINE_AA)
            occupied_boxes.append(box)
            return

    @staticmethod
    def draw_overlay(frame: np.ndarray, bbox: Optional[BBox], keypoints: Optional[Keypoints] = None) -> np.ndarray:
        output = frame.copy()
        if bbox is None:
            return output

        x, y, w, h = bbox
        center = (x + (w // 2), y + (h // 2))

        cv2.rectangle(output, (x, y), (x + w, y + h), (255, 255, 255), 4)
        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 180, 255), 2)
        cv2.circle(output, center, 6, (0, 255, 255), -1)
        if keypoints:
            segments = [
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
            for a, b in segments:
                if a in keypoints and b in keypoints:
                    cv2.line(output, keypoints[a], keypoints[b], (255, 255, 255), 4)
                    cv2.line(output, keypoints[a], keypoints[b], (0, 255, 255), 2)
            for px, py in keypoints.values():
                cv2.circle(output, (px, py), 8, (0, 255, 255), -1)
                cv2.circle(output, (px, py), 10, (255, 255, 255), 2)

            # Most relevant lifting angles ("asteet").
            angle_specs = [
                ("Knee L", "left_hip", "left_knee", "left_ankle"),
                ("Knee R", "right_hip", "right_knee", "right_ankle"),
                ("Hip L", "left_shoulder", "left_hip", "left_knee"),
                ("Hip R", "right_shoulder", "right_hip", "right_knee"),
                ("Elbow L", "left_shoulder", "left_elbow", "left_wrist"),
                ("Elbow R", "right_shoulder", "right_elbow", "right_wrist"),
            ]
            occupied_boxes: list[tuple[int, int, int, int]] = []
            for label, a, b, c in angle_specs:
                if a in keypoints and b in keypoints and c in keypoints:
                    angle = WeightlifterDetector._calculate_angle(keypoints[a], keypoints[b], keypoints[c])
                    WeightlifterDetector._draw_angle_label(
                        output, keypoints[b], label, angle, occupied_boxes
                    )
        return output

    @staticmethod
    def _print_progress(frame_idx: int, total_frames: int) -> None:
        if total_frames > 0:
            pct = min(100.0, (100.0 * frame_idx) / total_frames)
            msg = f"\rProcessing video: {pct:6.2f}% ({frame_idx}/{total_frames} frames)"
        else:
            msg = f"\rProcessing video: {frame_idx} frames"
        print(msg, end="", file=sys.stdout, flush=True)

    def process(self) -> str:
        if not self.validate_input():
            raise ValueError("Input video failed validation.")

        output = Path(self.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise ValueError(f"Unable to open input video: {self.video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        writer = cv2.VideoWriter(
            str(output),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )

        frame_idx = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame_idx += 1

                bbox = self.detect_weightlifter(frame)
                writer.write(self.draw_overlay(frame, bbox, self._last_keypoints))

                if frame_idx == 1 or frame_idx % 10 == 0:
                    self._print_progress(frame_idx, total_frames)
        finally:
            cap.release()
            writer.release()

        if frame_idx > 0:
            self._print_progress(frame_idx, total_frames)
        print(file=sys.stdout, flush=True)
        return str(output.resolve())
