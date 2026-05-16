# Phase 0 Visual Check — Lifter Detection + Angle Overlay

**Date**: 2026-05-16 (run metadata captured); visual review TBD  
**Reviewer**: _to be filled in after watching the comparison clips_  
**Goal**: Verify with your own eyes that lifter detection and angle overlays are usable on real gym video.

---

## 1) Test Set

| Video ID | File | View | Conditions | Notes |
|---|---|---|---|---|
| V1 | `data/sample_video_side.mp4` | Side | Clean sample | Baseline for angle plausibility |
| V2 | `data/sample_video_front.mp4` | Front | Clean sample | Baseline for symmetry/left-right stability |
| V3 | _(not captured yet)_ | Side / Front / 45° | Real gym | Optional real-world verification once a gym clip is recorded |

---

## 2) Run Metadata

- **Pose backend**: YOLO `yolov8n-pose.pt` (default).
- **Defaults applied**: `--smoothing 0.5`, `--min-joint-confidence 0.0` (gating disabled), `--lift snatch`.
- **No manual tuning** — both runs use stock defaults.

| Video | Output | Frames | FPS | Duration | Actionable faults |
|---|---|---:|---:|---:|---:|
| V1 (side) | `output/side_annotated.mp4` + `_report.json` + `_summary.txt` | 859 | 29.97 | 28.66 s | 0 |
| V2 (front) | `output/front_annotated.mp4` + `_report.json` + `_summary.txt` | 190 | 30.00 | 6.33 s | 0 |

Reports regenerated 2026-05-16 from `main` at commit `4037a90`.

### Suggested Commands (Run As-Is)

From repo root, dependencies managed via `uv`. The `md.sh` wrapper is a thin shortcut for `uv run python main.py`.

```bash
./md.sh analyze data/sample_video_side.mp4 \
  --lift snatch \
  --output output/side_annotated.mp4

./md.sh analyze data/sample_video_front.mp4 \
  --lift snatch \
  --output output/front_annotated.mp4

./md.sh analyze data/<your-gym-video>.mp4 \
  --lift snatch \
  --output output/gym_annotated.mp4
```

`analyze` writes three artifacts per run alongside `--output`:
- the annotated MP4
- `<output>_report.json` — machine-readable session report
- `<output>_summary.txt` — human-readable feedback summary

Useful flags (see `./md.sh analyze --help`):
- `--smoothing` — temporal keypoint EMA in [0, 1]; `1.0` disables (default `0.5`).
- `--min-joint-confidence` — drop per-joint detections below this threshold in [0, 1]; `0.0` disables (default `0.0`).
- `--yolo-model` — alternate pose model (default `yolov8n-pose.pt`).

### Side-by-side comparison

To produce an original-vs-annotated comparison clip for visual review:

```bash
./md.sh compare data/sample_video_side.mp4 output/side_annotated.mp4 \
  --output output/side_compare.mp4

./md.sh compare data/sample_video_front.mp4 output/front_annotated.mp4 \
  --output output/front_compare.mp4
```

---

## 3) Visual Acceptance Checklist (per video)

### V1 — side view

- [ ] Lifter remains detected through the full rep (box stays on subject)
- [ ] Major joints are visible and mostly stable (no frequent swaps/drift)
- [ ] Angles are drawn at correct anatomical joints (hip/knee/ankle/etc.)
- [ ] Angle values look plausible over time (no obvious impossible jumps)
- [ ] Overlay is readable (text size/color/placement works)

**Annotated**: `output/side_annotated.mp4`  
**Side-by-side comparison**: `output/side_compare.mp4`  
**Pipeline outcome (mechanical)**: 859 frames processed, 0 actionable faults from rule engine.  
**Result**: _Pass / Fail — fill in after watching_  
**Observed issues**:
- 

### V2 — front view

- [ ] Lifter remains detected through the full rep (box stays on subject)
- [ ] Major joints are visible and mostly stable (no frequent swaps/drift)
- [ ] Angles are drawn at correct anatomical joints (hip/knee/ankle/etc.)
- [ ] Angle values look plausible over time (no obvious impossible jumps)
- [ ] Overlay is readable (text size/color/placement works)

**Annotated**: `output/front_annotated.mp4`  
**Side-by-side comparison**: `output/front_compare.mp4`  
**Pipeline outcome (mechanical)**: 190 frames processed, 0 actionable faults from rule engine.  
**Result**: _Pass / Fail — fill in after watching_  
**Observed issues**:
- 

### V3 — real gym (not yet captured)

_Skip until a representative gym video is recorded._

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

Phase 1 is already complete (see `docs/PLAN.md`). This decision is retroactive
documentation — the go/no-go below should reflect whether the visual review
*would have* gated Phase 1, given what you see in the comparison clips.

### Decision

- [ ] **GO** — overlays usable; Phase 1 work was justified.
- [ ] **NO-GO retroactively** — visible defects that should have been fixed before Phase 1; log them under "blocking issues" for follow-up.

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
