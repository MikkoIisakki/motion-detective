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

YOLOv8 returns `keypoints.xy` and `keypoints.conf` (confidence per keypoint, 0–1). `YoloPoseEstimator._build_pose` (src/adapters/yolo_pose_estimator.py) carries that confidence onto each domain `Keypoint`; confidence filtering then happens in the domain via `gate_keypoints`:

```python
# src/domain/joint_gate.py — real implementation
def gate_keypoints(pose: Pose, min_confidence: float) -> Pose:
    """Return a Pose containing only keypoints with confidence >= min_confidence."""
    return Pose([kp for kp in pose.keypoints if kp.confidence >= min_confidence])
```

The threshold is a CLI flag, not a magic number: `--min-joint-confidence` (default 0.0 = gating off). Gated keypoints become *absent* from the `Pose` — downstream code sees a missing joint (angle simply not measured that frame), never a zero angle. A zero angle is a valid angle.

---

## Angle Computation

### Three-Point Joint Angle

Angle at joint B, formed by segments BA and BC — the real implementation:

```python
# src/domain/angle_math.py
def joint_angle(a: Keypoint, b: Keypoint, c: Keypoint) -> float:
    """Return the angle ABC in degrees, where B is the vertex joint.

    Returns 0.0 when either vector has zero length (coincident points).
    """
    ba_x, ba_y = a.x - b.x, a.y - b.y
    bc_x, bc_y = c.x - b.x, c.y - b.y

    denom = math.hypot(ba_x, ba_y) * math.hypot(bc_x, bc_y)
    if denom == 0.0:
        return 0.0

    cos_angle = (ba_x * bc_x + ba_y * bc_y) / denom
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))
```

### Measured Joints

The angles the pipeline actually measures are defined once, in `ANGLE_DEFINITIONS` (src/domain/angle_math.py), and averaged over left/right sides:

```python
# (joint_name, vertex_a, vertex_b, vertex_c) — angle ABC at vertex B
knee_angle  = angle(hip, knee, ankle)
hip_angle   = angle(shoulder, hip, knee)
elbow_angle = angle(shoulder, elbow, wrist)
```

A torso-from-vertical back angle is a candidate future measurement (not yet implemented) — it would need the same three-band KB treatment as the existing joints.

Note: image coordinates have y=0 at top. State the coordinate system in every geometry function.

---

## Temporal Smoothing

Raw keypoint outputs are noisy, especially at high movement speeds (second pull is very fast). The real implementation is an exponential moving average:

```python
# src/domain/keypoint_smoother.py (abridged)
class KeypointSmoother:
    """Exponential moving average over keypoint positions.

    For each keypoint name, smoothed = alpha * new + (1 - alpha) * previous.
    alpha=1.0 disables smoothing; alpha=0.0 freezes at the first value.
    Missing keypoints in a new pose are filled from the last known state
    (handles brief occlusions / detection dropouts).
    """

    def __init__(self, alpha: float = 0.5) -> None: ...
    def reset(self) -> None: ...
    def smooth(self, pose: Pose) -> Pose: ...
```

The factor is a CLI flag: `--smoothing` (default 0.5; 1.0 disables). Lower alpha = heavier smoothing but more lag — a concern in the very fast second pull. Per-phase adaptive alpha is a possible future refinement, not implemented.

---

## Bar Path Tracking

**Critical limitation**: YOLOv8 COCO pose does not detect the barbell. Bar path tracking is **not yet implemented** — options in order of implementation complexity:

### Option 1 (build first): Wrist midpoint proxy

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

Overlay drawing lives in `OverlayRenderer` (src/adapters/overlay_renderer.py). Segment definitions:

```python
# src/adapters/overlay_renderer.py
_SKELETON_SEGMENTS = [
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
```

### Color Coding by Severity

Severity comes from the domain — `FaultSeverity` (src/domain/faults.py: `GOOD`/`WARNING`/`FAULT`) — mapped to BGR in the renderer:

```python
# src/adapters/overlay_renderer.py
_SEVERITY_COLOR = {
    FaultSeverity.GOOD: (0, 255, 0),       # green
    FaultSeverity.WARNING: (0, 200, 255),  # amber
    FaultSeverity.FAULT: (0, 0, 255),      # red
}
_DEFAULT_COLOR = (0, 255, 255)  # cyan when no analysis
```

The angle panel rows (`_draw_angle_panel`) are colored by the severity of the matching KB joint for the current frame's phase. Threshold values come from `config/knowledge_base.yml` (see `knowledge-base-authoring`).

---

## Phase Detection

`PhaseDetector` (src/domain/phase_detector.py) is a stateful per-frame state machine over `LiftPhase`, configured per lift (`PhaseDetector(lift="clean_and_jerk")` / `configure_for_lift`). The full phase model:

```
IDLE → SETUP → FIRST_PULL → TRANSITION → SECOND_PULL → CATCH → RECOVERY
             (clean & jerk continues:) → JERK_DIP → JERK_CATCH → RECOVERY
```

Signals are y-coordinates averaged over left/right pairs (`PoseSignal.from_pose`): `wrist_y`, `ankle_y`, `knee_y`, `hip_y`, `shoulder_y`. Remember image coordinates: **rising means y decreases**. All distance gates are **body-relative**: fractions of the per-frame shoulder-to-ankle span (`CompleteSignal.body_span`), so detection is independent of camera distance and resolution — never reintroduce absolute pixel thresholds (an absolute IDLE gate once kept the detector in IDLE on every real clip, because a loaded bar sits at plate height and real wrists reach knee level, not ankle level). A frame with a non-positive span is treated like an incomplete signal. Transition conditions (see the module for the named `*_FRACTION` constants; below, `rise` means a per-frame delta ≥ `RISE_THRESHOLD_FRACTION * body_span`, default fraction 5/300):

- **IDLE → SETUP**: `wrist_y >= knee_y` (hands down at bar level; arms hanging while standing stay above the knee)
- **SETUP → FIRST_PULL**: wrist rises between frames
- **FIRST_PULL → TRANSITION**: wrist above knee height
- **TRANSITION → SECOND_PULL**: wrist within `SECOND_PULL_WRIST_BELOW_SHOULDER_FRACTION * body_span` of shoulder height
- **SECOND_PULL → CATCH**: wrist above shoulders
- **CATCH → RECOVERY**: hip rises between frames
- **RECOVERY → JERK_DIP** (clean & jerk only, once): hips descending while the bar stays racked (`|wrist_y - shoulder_y| <= RACK_WRIST_PROXIMITY_FRACTION * body_span`)
- **JERK_DIP → JERK_CATCH**: bar clearly overhead (`wrist_y < shoulder_y - OVERHEAD_WRIST_CLEARANCE_FRACTION * body_span`)
- **JERK_CATCH → RECOVERY**: hip rises (closes the lift)

Notes:
- An incomplete `PoseSignal` (any missing joint group) keeps the current phase — no guessing
- Transitions are chained within one `update()` so a single fast frame can advance multiple phases
- Known limitation (documented in the class docstring): the wrist midpoint is the only bar proxy, so jerk *drive* frames classify as `JERK_DIP`, and split vs power jerk both land in `JERK_CATCH`

---

## Video Processing Pipeline

The pipeline is orchestrated by `AnalyzeVideo.execute` (src/use_cases/analyze_video.py):

```
Input video
  → validation (FileVideoValidator)
  → frame extraction (OpenCVVideoReader)
  → person detection + tracking (YoloPoseDetector — YOLO, HOG fallback, motion fallback)
  → pose estimation (YoloPoseEstimator → domain Pose)
  → confidence gating (gate_keypoints, if --min-joint-confidence set)
  → keypoint smoothing (KeypointSmoother)
  → phase + angles + faults (AnalyzeLift → PhaseDetector + ClassifyFrame)
  → overlay rendering (OverlayRenderer — skeleton, angle panel, phase banner)
  → output video (OpenCVVideoWriter)
  → feedback summary + optional JSON/text session reports
```

Each stage is a pure function or stateful class behind a port. No stage reads from disk inside the frame loop (all config loaded upfront).

---

## Performance Notes

- YOLOv8n-pose: ~30 FPS on CPU (M-series Mac), ~120 FPS on GPU
- Target: process a 10-second lift video in < 30 seconds on CPU (acceptable for async upload)
- If real-time is needed in Phase 2, switch to `yolov8n-pose` with frame skip on CPU or `yolov8n-pose` on CoreML (iOS)
- Batch frames through YOLO where possible: `model.predict(batch_of_frames)` is faster than per-frame calls
