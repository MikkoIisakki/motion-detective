# Motion Detective — Implementation Plan

**Vision**: a gym-ready app where you record a lift, get an annotated video, and receive actionable technique feedback.

**Current date**: 2026-04-08  
**Current phase**: Phase 0 — Visual Proof of Core CV Loop

---

## Phase 0 — Visual Proof (First Milestone)

Goal: verify with your own eyes that lifter detection and angle overlay work on real video.

### Tasks

| # | Task | Status | Notes |
|---|---|---|---|
| 0.1 | Select 2–3 representative lift videos (side/front) | ⬜ Todo | Use one clean sample + one noisy gym sample |
| 0.2 | Run lifter detection pipeline and render bounding-box output | ⬜ Todo | Confirm primary lifter stays tracked through full lift |
| 0.3 | Render pose skeleton + joint angle overlays (hip, knee, ankle, torso, elbow) | ⬜ Todo | Frame-by-frame visual sanity check |
| 0.4 | Save side-by-side output clips for review | ⬜ Todo | Original vs annotated |
| 0.5 | Write quick findings note: what works / fails | ⬜ Todo | Detection dropouts, bad keypoints, angle jitter |

### Exit Criteria

- You can visually confirm on at least one full lift that:
1. the lifter is consistently detected
2. key joints are mostly stable
3. angles are drawn in the right anatomical locations
- Failure cases are documented before moving forward.

---

## Phase 1 — Reliable Single-Lift Analysis (MVP Core)

Goal: stable offline analysis for one uploaded video with useful overlay output.

### Tasks

| # | Task | Status |
|---|---|---|
| 1.1 | Standardize pipeline stages: validate → detect → pose → angles → render |
| 1.2 | Add confidence gating and fallback logic for low-confidence joints |
| 1.3 | Smooth keypoints/angles to reduce jitter (temporal filter) |
| 1.4 | Add lift-segment markers (setup, pull, catch/lockout where possible) |
| 1.5 | CLI command for full analysis with reproducible output artifact |
| 1.6 | Unit tests for angle math + integration tests for video processing path |

### Exit Criteria

- Full analysis succeeds on target sample set without manual tweaking.
- Overlays are stable enough for practical visual review.

---

## Phase 2 — Technique Rules and Feedback

Goal: convert angles and motion into clear coaching cues.

### Tasks

| # | Task | Status |
|---|---|---|
| 2.1 | Define fault rules per lift (e.g., squat: knee cave, forward lean, depth) |
| 2.2 | Implement rule engine using per-frame + per-phase thresholds |
| 2.3 | Generate human-readable feedback with timestamps and severity |
| 2.4 | Export session report (JSON + human summary + annotated video) |
| 2.5 | Add regression tests for each rule using curated clips |

### Exit Criteria

- Output includes specific, timestamped technique findings.
- False positives are acceptable for MVP and clearly documented.

---

## Phase 3 — Gym Usability (Record + Analyze Workflow)

Goal: practical end-to-end gym flow from capture to feedback.

### Tasks

| # | Task | Status |
|---|---|---|
| 3.1 | Mobile capture flow (record and upload with minimal taps) |
| 3.2 | Asynchronous processing and job status updates |
| 3.3 | Session history (latest lifts, outputs, notes) |
| 3.4 | Fast preview mode (quick overlay) + full analysis mode |
| 3.5 | UX pass for “in-gym readability” (big cues, short text, quick load) |

### Exit Criteria

- In gym conditions, you can record a lift and review feedback in under ~60 seconds (preview path).

---

## Phase 4 — Accuracy, Scale, and Expansion

Goal: improve robustness and expand capability once core value is proven.

### Tasks

| # | Task | Status |
|---|---|---|
| 4.1 | Benchmark model quality across camera angles, lighting, crowding |
| 4.2 | Add calibration/profile options per user body proportions |
| 4.3 | Extend supported lifts and advanced cues |
| 4.4 | Real-time assist experiments (on-device or low-latency backend) |
| 4.5 | Production hardening: CI/CD, observability, error budgets |

---

## Cross-Phase Guardrails

- Keep Phase 0 and Phase 1 focused on visible correctness before complex scoring.
- Every new rule needs a test clip and expected outcome.
- Prefer deterministic, explainable heuristics first; use ML classifiers later only when baseline is trusted.

---

## Immediate Next Steps (This Week)

1. Run Phase 0 tasks and produce 2–3 annotated clips.
2. Create `docs/analysis/phase-0-visual-check.md` with pass/fail notes.
3. Decide go/no-go for Phase 1 based on visual stability.
