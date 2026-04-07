---
name: pose-estimation
description: YOLOv8 pose estimation integration patterns for motion-detective. Covers keypoint extraction, confidence filtering, angle computation, temporal smoothing, and bar path tracking limitations.
---

# Pose Estimation

Technical patterns for the pose estimation layer in motion-detective. Used by the engineer when working on keypoint extraction, angle computation, and phase detection.

---

## YOLOv8 Pose — Current Model

Model in use: `yolov8n-pose.pt` (nano, fast). Upgrade path: `yolov8s-pose.pt` → `yolov8m-pose.pt` for higher accuracy at cost of speed.

### COCO 17 Keypoints

```python
COCO_KEYPOINTS = {
    0:  "nose",
    1:  "left_eye",
    2:  "right_eye",
    3:  "left_ear",
    4:  "right_ear",
    5:  "left_shoulder",
    6:  "right_shoulder",
    7:  "left_elbow",
    8:  "right_elbow",
    9:  "left_wrist",
    10: "right_wrist",
    11: "left_hip",
    12: "right_hip",
    13: "left_knee",
    14: "right_knee",
    15: "left_ankle",
    16: "right_ankle",
}
```

### Keypoint Confidence

YOLOv8 returns `keypoints.xyn` (normalized) and `keypoints.conf` (confidence per keypoint, 0–1). Always filter by confidence before using a keypoint for angle computation:

```python
MIN_KEYPOINT_CONFIDENCE = 0.5  # config value, not magic number

def get_keypoint(
    keypoints_xy: np.ndarray,
    keypoints_conf: np.ndarray,
    index: int,
) -> tuple[float, float] | None:
    if keypoints_conf[index] < MIN_KEYPOINT_CONFIDENCE:
        return None
    x, y = keypoints_xy[index]
    return float(x), float(y)
```

If a required keypoint has confidence below threshold, mark the corresponding angle as unavailable (`None`), not zero. A zero angle is a valid angle.

---

## Angle Computation

### Three-Point Joint Angle

Angle at joint B, formed by segments BA and BC:

```python
import numpy as np

def joint_angle(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    """Angle at B in degrees. Returns 0.0 if degenerate."""
    ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=np.float64)
    bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=np.float64)
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom < 1e-6:
        return 0.0
    cos_angle = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))
```

### Torso Angle (Back Angle)

Back angle = angle of the torso relative to vertical (or horizontal). Use shoulder midpoint and hip midpoint:

```python
def torso_angle_from_vertical(
    shoulder_mid: tuple[float, float],
    hip_mid: tuple[float, float],
) -> float:
    """0° = vertical torso, 90° = horizontal (lying down)."""
    dx = shoulder_mid[0] - hip_mid[0]
    dy = shoulder_mid[1] - hip_mid[1]  # y increases downward in image coords
    # dy is negative when shoulder is above hip (normal standing)
    angle_from_vertical = float(np.degrees(np.arctan2(abs(dx), abs(dy))))
    return angle_from_vertical
```

Note: image coordinates have y=0 at top. Correct for this in all angle computations.

---

## Temporal Smoothing

Raw keypoint outputs are noisy, especially at high movement speeds (second pull is very fast). Apply a sliding window mean or exponential moving average:

```python
from collections import deque

class KeypointSmoother:
    def __init__(self, window: int = 5) -> None:
        self._buffers: dict[str, deque[tuple[float, float]]] = {}
        self._window = window

    def update(self, name: str, point: tuple[float, float]) -> tuple[float, float]:
        if name not in self._buffers:
            self._buffers[name] = deque(maxlen=self._window)
        self._buffers[name].append(point)
        xs = [p[0] for p in self._buffers[name]]
        ys = [p[1] for p in self._buffers[name]]
        return float(np.mean(xs)), float(np.mean(ys))
```

Use shorter windows (3 frames) for fast phases (second pull, catch) and longer windows (7 frames) for slow phases (setup, first pull).

---

## Bar Path Tracking

**Critical limitation**: YOLOv8 COCO pose does not detect the barbell. Options in order of implementation complexity:

### Option 1 (current approximation): Wrist midpoint proxy

```python
def bar_position_proxy(
    left_wrist: tuple[float, float] | None,
    right_wrist: tuple[float, float] | None,
) -> tuple[float, float] | None:
    if left_wrist is None or right_wrist is None:
        return None
    return (
        (left_wrist[0] + right_wrist[0]) / 2,
        (left_wrist[1] + right_wrist[1]) / 2,
    )
```

Good enough for most phases. Inaccurate during turnover/rack when wrists diverge from bar.

### Option 2 (better): Color-based bar tracking

The barbell is typically silver/chrome. Track a bright circular region between the hands using `cv2.inRange` on HSV. Works well in controlled lighting (gym setting).

### Option 3 (best): Fine-tuned YOLO object detection

Train a YOLOv8 detect model on barbell annotations. Needs a dataset. Use Roboflow if available.

Implement Option 1 first. Document Options 2 and 3 in the architect's design for Phase 2.

---

## Skeleton Drawing

### Segment Definitions (for stick figure)

```python
SKELETON_SEGMENTS = [
    # Lower body
    ("left_ankle", "left_knee"),
    ("left_knee", "left_hip"),
    ("right_ankle", "right_knee"),
    ("right_knee", "right_hip"),
    ("left_hip", "right_hip"),
    # Upper body
    ("left_hip", "left_shoulder"),
    ("right_hip", "right_shoulder"),
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    # Head
    ("left_shoulder", "nose"),
    ("right_shoulder", "nose"),
]
```

### Color Coding by Quality

```python
from enum import Enum

class AngleQuality(Enum):
    GOOD = "good"        # within target range
    WARNING = "warning"  # approaching fault threshold
    FAULT = "fault"      # outside acceptable range
    UNKNOWN = "unknown"  # keypoint missing or low confidence

QUALITY_COLORS = {
    AngleQuality.GOOD:    (0, 200, 0),    # green
    AngleQuality.WARNING: (0, 165, 255),  # orange
    AngleQuality.FAULT:   (0, 0, 220),    # red
    AngleQuality.UNKNOWN: (128, 128, 128), # gray
}
```

Color-code joint circles and adjacent segments by the quality of the angle at that joint. Threshold values come from the `weightlifting-biomechanics` skill.

---

## Phase Detection

Classify the current lift phase from a sequence of keypoint frames. Use a state machine:

```
IDLE → SETUP → FIRST_PULL → TRANSITION → SECOND_PULL → CATCH/RACK → RECOVERY → IDLE
```

Transition conditions:
- **IDLE → SETUP**: wrist height stabilizes near ankle level, person detected
- **SETUP → FIRST_PULL**: wrist height starts increasing
- **FIRST_PULL → TRANSITION**: knee angle starts decreasing (re-bend)
- **TRANSITION → SECOND_PULL**: rapid joint extension velocity exceeds threshold
- **SECOND_PULL → CATCH**: wrist height exceeds shoulder height (snatch) or wrist approaches shoulder height (clean)
- **CATCH → RECOVERY**: hip height starts rising from catch position
- **RECOVERY → IDLE**: hip height stable at standing level

Buffer 5–10 frames before confirming a phase transition (prevents oscillation).

---

## Video Processing Pipeline

```
Input video (phone upload)
  → frame extraction (cv2.VideoCapture)
  → person detection + tracking (WeightlifterDetector)
  → pose estimation (YOLOv8)
  → keypoint smoothing
  → phase classification
  → angle computation per frame
  → fault detection (thresholds from biomechanics skill)
  → overlay rendering (skeleton + angles + quality colors)
  → output video (cv2.VideoWriter)
  → feedback generation (worst faults per phase)
```

Each stage is a pure function or stateful class. No stage reads from disk inside the frame loop (all config loaded upfront).

---

## Performance Notes

- YOLOv8n-pose: ~30 FPS on CPU (M-series Mac), ~120 FPS on GPU
- Target: process a 10-second lift video in < 30 seconds on CPU (acceptable for async upload)
- If real-time is needed in Phase 2, switch to `yolov8n-pose` with frame skip on CPU or `yolov8n-pose` on CoreML (iOS)
- Batch frames through YOLO where possible: `model.predict(batch_of_frames)` is faster than per-frame calls
