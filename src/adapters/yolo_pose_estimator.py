from __future__ import annotations

import importlib.util

import numpy as np

from src.domain.models import BBox, Keypoint, Pose
from src.ports.pose_estimator import PoseEstimatorPort

# COCO 17-keypoint index → name mapping (only joints relevant to lifting)
_COCO_NAMES: dict[int, str] = {
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


class YoloPoseEstimator(PoseEstimatorPort):
    def __init__(self, yolo_model: str = "yolov8n-pose.pt", yolo_conf: float = 0.35) -> None:
        if not importlib.util.find_spec("ultralytics"):
            raise RuntimeError("YoloPoseEstimator requires `ultralytics`. Install with: pip install ultralytics")
        from ultralytics import YOLO  # type: ignore
        self._yolo = YOLO(yolo_model)
        self._yolo_conf = yolo_conf

    def estimate(self, frame: np.ndarray, bbox: BBox) -> Pose | None:
        result = self._yolo.predict(frame, classes=[0], conf=self._yolo_conf, verbose=False)
        if not result:
            return None
        r = result[0]
        if r.boxes is None or getattr(r, "keypoints", None) is None or r.keypoints.xy is None:
            return None

        best_idx = self._closest_detection_index(r.boxes.xyxy.cpu().numpy(), bbox)
        if best_idx is None:
            return None

        kp_array = r.keypoints.xy.cpu().numpy()
        if best_idx >= len(kp_array):
            return None

        conf_array = None
        if getattr(r.keypoints, "conf", None) is not None:
            conf_all = r.keypoints.conf.cpu().numpy()
            if best_idx < len(conf_all):
                conf_array = conf_all[best_idx]

        return self._build_pose(kp_array[best_idx], conf_array)

    @staticmethod
    def _closest_detection_index(xyxy: np.ndarray, bbox: BBox) -> int | None:
        if len(xyxy) == 0:
            return None
        target_cx, target_cy = bbox.center
        best_idx, best_dist = 0, float("inf")
        for i, (x1, y1, x2, y2) in enumerate(xyxy):
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            dist = float(np.hypot(cx - target_cx, cy - target_cy))
            if dist < best_dist:
                best_dist, best_idx = dist, i
        return best_idx

    @staticmethod
    def _build_pose(
        keypoints_xy: np.ndarray, keypoints_conf: np.ndarray | None = None
    ) -> Pose:
        def confidence_for(idx: int) -> float:
            if keypoints_conf is None:
                return 1.0
            return float(keypoints_conf[idx])

        kps = [
            Keypoint(
                name,
                int(keypoints_xy[idx][0]),
                int(keypoints_xy[idx][1]),
                confidence=confidence_for(idx),
            )
            for idx, name in _COCO_NAMES.items()
            if idx < len(keypoints_xy)
            and (keypoints_conf is None or idx < len(keypoints_conf))
        ]
        return Pose(kps)
