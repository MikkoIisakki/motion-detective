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

The production approach (`OverlayRenderer._draw_angle_panel` in src/adapters/overlay_renderer.py) avoids overlapping labels by not placing them at the joints at all: angles render as a fixed panel of rows anchored bottom-left, one row per measured angle (`Knee L: 94 deg`, ...), each colored by that joint's current severity. If you ever move labels onto the skeleton, solve overlap explicitly (occupied-box tracking, multiple candidate offsets).

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

Primary output. Annotated video file (`.mp4`) with skeleton, angle panel, and phase banner, written to `--output` (default `output/annotated.mp4`). In the Phase 3+ SaaS this becomes a download/streaming URL from the API.

### JSON Session Report

Structured analysis result alongside the video — written by `AnalyzeVideo._write_reports` (src/use_cases/analyze_video.py) when `--report-json`/`--report-summary` paths are set. Actual shape:

```json
{
  "generated_at_utc": "2026-07-12T10:15:00+00:00",
  "input_video": "/abs/path/lift.mp4",
  "annotated_video": "/abs/path/annotated.mp4",
  "video": {
    "fps": 30.0,
    "processed_frames": 126,
    "duration_seconds": 4.2
  },
  "summary": [
    "00:00.800-00:01.600 [FAULT/performance] first_pull: Keep hips from rising before the bar passes the knee (24 frames)"
  ],
  "findings": [
    {
      "phase": "first_pull",
      "feedback": "Keep hips from rising before the bar passes the knee",
      "severity": "FAULT",
      "priority": "performance",
      "start_seconds": 0.8,
      "end_seconds": 1.6,
      "start_timestamp": "00:00.800",
      "end_timestamp": "00:01.600",
      "frames": 24
    }
  ]
}
```

An overall per-clip `confidence` field (proportion of frames with keypoint confidence above threshold) is a planned addition for surfacing low-quality detections — not yet implemented.

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
