---
name: computer-vision
description: OpenCV and video processing patterns for motion-detective. Covers frame extraction, video writing, coordinate systems, overlay rendering, and output formats.
---

# Computer Vision

OpenCV and video processing patterns for the motion-detective project. Used by the engineer when working on video I/O, frame processing, and overlay rendering.

---

## Coordinate System

OpenCV uses image coordinates: origin (0,0) at **top-left**, x increases right, y increases **down**.

This is the opposite of geometric/screen convention. Consequences:
- A person standing upright has a **smaller** y at the head and **larger** y at the feet
- Angles computed using raw `(x, y)` points will have inverted vertical component
- Always convert to geometric coordinates before angle math, or account for the inversion explicitly

```python
def to_geometric(point: tuple[float, float], frame_height: int) -> tuple[float, float]:
    """Convert image coords (y-down) to geometric coords (y-up)."""
    return (point[0], frame_height - point[1])
```

Document which coordinate system any function expects. Do not mix them.

---

## Video I/O Patterns

### Reading

```python
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        # process frame
finally:
    cap.release()
```

Always use `try/finally` to ensure `cap.release()` is called even on error.

### Writing

```python
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
try:
    # write frames
    writer.write(annotated_frame)
finally:
    writer.release()
```

`mp4v` is the standard for `.mp4` output. `H264` requires additional codec installation. Always `release()` the writer — unflushed buffers produce corrupt output.

---

## Frame Processing Rules

1. **Never modify the input frame** — always `frame.copy()` before drawing
2. **Draw in BGR** — OpenCV uses BGR, not RGB. Green = `(0, 255, 0)`, not `(255, 0, 0)`
3. **Anti-aliasing** — use `cv2.LINE_AA` for all lines and text for smooth rendering
4. **Outline text before fill** — draw text in black with thick stroke, then redraw in color for legibility on any background

```python
def draw_text_with_outline(
    frame: np.ndarray,
    text: str,
    position: tuple[int, int],
    font_scale: float = 0.8,
    color: tuple[int, int, int] = (0, 255, 255),
    thickness: int = 2,
) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, position, font, font_scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
    cv2.putText(frame, text, position, font, font_scale, color, thickness, cv2.LINE_AA)
```

---

## Overlay Rendering

### Skeleton

Draw skeleton segments then joint circles — segments first so circles appear on top:

```python
def draw_skeleton(
    frame: np.ndarray,
    keypoints: dict[str, tuple[int, int]],
    quality_map: dict[str, AngleQuality],
) -> None:
    for joint_a, joint_b in SKELETON_SEGMENTS:
        if joint_a not in keypoints or joint_b not in keypoints:
            continue
        segment_quality = min(quality_map.get(joint_a, AngleQuality.UNKNOWN),
                              quality_map.get(joint_b, AngleQuality.UNKNOWN))
        color = QUALITY_COLORS[segment_quality]
        cv2.line(frame, keypoints[joint_a], keypoints[joint_b], (0, 0, 0), 5, cv2.LINE_AA)
        cv2.line(frame, keypoints[joint_a], keypoints[joint_b], color, 3, cv2.LINE_AA)

    for name, point in keypoints.items():
        quality = quality_map.get(name, AngleQuality.UNKNOWN)
        color = QUALITY_COLORS[quality]
        cv2.circle(frame, point, 10, (0, 0, 0), -1)
        cv2.circle(frame, point, 8, color, -1)
```

### Angle Labels

Use the occupied-box approach already in `WeightlifterDetector._draw_angle_label` to prevent overlapping labels. Prefer placing labels where there is space — try multiple offsets before giving up.

### Phase Banner

Display current phase name in a semi-transparent banner at the top of the frame:

```python
def draw_phase_banner(frame: np.ndarray, phase_name: str) -> None:
    overlay = frame.copy()
    h, w = frame.shape[:2]
    cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    draw_text_with_outline(frame, phase_name, (10, 28), font_scale=0.7, color=(255, 255, 255))
```

---

## Output Formats

### Video with Overlay

Primary output. Annotated video file (`.mp4`) with skeleton, angles, phase banner, and fault highlights. The engineer writes this to a temp path, then the API returns it to the mobile client as a file download or streaming URL.

### JSON Analysis

Structured analysis result alongside the video:

```json
{
  "lift_type": "snatch",
  "phases_detected": ["setup", "first_pull", "second_pull", "catch"],
  "duration_seconds": 4.2,
  "faults": [
    {
      "phase": "first_pull",
      "joint": "back_angle",
      "description": "Back angle changed by 12° during first pull",
      "severity": "fault",
      "feedback": "Keep your back angle — push the floor away, don't lift your hips",
      "frame_start": 24,
      "frame_end": 48
    }
  ],
  "angle_timeline": {
    "knee_left": [94, 98, 110, 135, 168, 178, 85, 82],
    ...
  },
  "score": 72,
  "confidence": 0.84
}
```

The `confidence` field reflects the proportion of frames where keypoint confidence was above threshold (similar to RISK-009 pattern from recommendator for data quality).

---

## Performance Optimization

- **Frame skip**: For analysis (not rendering), run pose estimation every N frames. N=2 for 60fps input gives effectively 30fps analysis with 2× speedup.
- **Resize before inference**: YOLOv8 works well on 640×640. Resize the inference frame but draw overlays on the full-resolution frame.
- **Batch inference**: `model.predict(list_of_frames)` is more efficient than per-frame calls.

```python
INFERENCE_RESOLUTION = (640, 640)  # config, not magic number

inference_frame = cv2.resize(frame, INFERENCE_RESOLUTION)
results = model.predict(inference_frame, ...)
# scale keypoints back to original resolution before drawing
scale_x = frame.shape[1] / INFERENCE_RESOLUTION[0]
scale_y = frame.shape[0] / INFERENCE_RESOLUTION[1]
```
