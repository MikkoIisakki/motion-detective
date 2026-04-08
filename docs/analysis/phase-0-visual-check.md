# Phase 0 Visual Check — Lifter Detection + Angle Overlay

**Date**:  
**Reviewer**:  
**Goal**: Verify with your own eyes that lifter detection and angle overlays are usable on real gym video.

---

## 1) Test Set

| Video ID | File | View | Conditions | Notes |
|---|---|---|---|---|
| V1 | `data/sample_video_side.mp4` | Side | Clean sample | Baseline for angle plausibility |
| V2 | `data/sample_video_front.mp4` | Front | Clean sample | Baseline for symmetry/left-right stability |
| V3 | `data/<your-gym-video>.mp4` | Side / Front / 45deg | Real gym | Crowded/noisy real-world verification |

---

## 2) Run Metadata

- Model/backend:
- Command used:
- Output file(s):
- Resolution/FPS:
- Any manual tuning:

### Suggested Commands (Run As-Is)

From repo root:

```bash
./myenv/bin/python main.py data/sample_video_side.mp4 \
  --backend yolo \
  --yolo-model yolov8n-pose.pt \
  --output output/phase0_v1_side_overlay.mp4

./myenv/bin/python main.py data/sample_video_front.mp4 \
  --backend yolo \
  --yolo-model yolov8n-pose.pt \
  --output output/phase0_v2_front_overlay.mp4

./myenv/bin/python main.py data/<your-gym-video>.mp4 \
  --backend yolo \
  --yolo-model yolov8n-pose.pt \
  --output output/phase0_v3_gym_overlay.mp4
```

Optional fallback comparison (no keypoints/angles, box tracking only):

```bash
./myenv/bin/python main.py data/sample_video_side.mp4 \
  --backend hog \
  --output output/phase0_v1_side_hog_box.mp4
```

---

## 3) Visual Acceptance Checklist (per video)

### V1

- [ ] Lifter remains detected through the full rep (box stays on subject)
- [ ] Major joints are visible and mostly stable (no frequent swaps/drift)
- [ ] Angles are drawn at correct anatomical joints (hip/knee/ankle/etc.)
- [ ] Angle values look plausible over time (no obvious impossible jumps)
- [ ] Overlay is readable (text size/color/placement works)

**Output file**: `output/phase0_v1_side_overlay.mp4`  
**Result**: Pass / Fail  
**Observed issues**:
- 

### V2

- [ ] Lifter remains detected through the full rep (box stays on subject)
- [ ] Major joints are visible and mostly stable (no frequent swaps/drift)
- [ ] Angles are drawn at correct anatomical joints (hip/knee/ankle/etc.)
- [ ] Angle values look plausible over time (no obvious impossible jumps)
- [ ] Overlay is readable (text size/color/placement works)

**Output file**: `output/phase0_v2_front_overlay.mp4`  
**Result**: Pass / Fail  
**Observed issues**:
- 

### V3

- [ ] Lifter remains detected through the full rep (box stays on subject)
- [ ] Major joints are visible and mostly stable (no frequent swaps/drift)
- [ ] Angles are drawn at correct anatomical joints (hip/knee/ankle/etc.)
- [ ] Angle values look plausible over time (no obvious impossible jumps)
- [ ] Overlay is readable (text size/color/placement works)

**Output file**: `output/phase0_v3_gym_overlay.mp4`  
**Result**: Pass / Fail  
**Observed issues**:
- 

---

## 4) Failure Pattern Log

Track repeated failure types and severity.

| Failure Type | Frequency | Severity (Low/Med/High) | Example Timestamp(s) | Candidate Fix |
|---|---|---|---|---|
| Lost lifter track |  |  |  |  |
| Wrong person selected |  |  |  |  |
| Keypoint jitter |  |  |  |  |
| Keypoint swap |  |  |  |  |
| Angle jump/spike |  |  |  |  |
| Overlay unreadable |  |  |  |  |

---

## 5) Phase 1 Go / No-Go Decision

### Decision

- [ ] **GO** to Phase 1 (pipeline hardening)
- [ ] **NO-GO** (fix blocking issues first)

### Rationale

- 

### Blocking issues (if NO-GO)

1. 
2. 
3. 

---

## 6) Immediate Follow-up Tasks

1. 
2. 
3. 
