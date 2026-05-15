# Motion Detective — Implementation Plan

**Vision**: a gym-ready app where you record a lift, get an annotated video, and receive actionable technique feedback.

**Current date**: 2026-05-15
**Current phase**: Phase 2 complete; ready to start Phase 3 — Gym Usability

---

## Phase 0 — Visual Proof (First Milestone)

Goal: verify with your own eyes that lifter detection and angle overlay work on real video.

### Tasks

| # | Task | Status | Notes |
|---|---|---|---|
| 0.1 | Select 2–3 representative lift videos (side/front) | ✅ Done | `data/sample_video_side.mp4`, `data/sample_video_front.mp4` |
| 0.2 | Run lifter detection pipeline and render bounding-box output | ✅ Done | YOLO+HOG+motion fallback with temporal tracking; bounding box later removed in favour of skeleton |
| 0.3 | Render pose skeleton + joint angle overlays (hip, knee, ankle, torso, elbow) | ✅ Done | `output/side_annotated.mp4`, `output/front_annotated.mp4` |
| 0.4 | Save side-by-side output clips for review | ⬜ Todo | Original vs annotated still pending |
| 0.5 | Write quick findings note: what works / fails | ⬜ Todo | Need `docs/analysis/phase-0-visual-check.md` |

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

| # | Task | Status | Notes |
|---|---|---|---|
| 1.1 | Standardize pipeline stages: validate → detect → pose → angles → render | ✅ Done | Clean Architecture: domain / ports / adapters / use_cases |
| 1.2 | Add confidence gating and fallback logic for low-confidence joints | ⬜ Todo | YOLO confidence threshold exists; per-joint gating not yet |
| 1.3 | Smooth keypoints/angles to reduce jitter (temporal filter) | ✅ Done | `KeypointSmoother` (EMA, alpha configurable via `--smoothing`); also bridges brief occlusions |
| 1.4 | Add lift-segment markers (setup, pull, catch/lockout where possible) | ✅ Done | `PhaseDetector` (idle → setup → first_pull → second_pull → catch → recovery) |
| 1.5 | CLI command for full analysis with reproducible output artifact | ✅ Done | `main.py --lift snatch --knowledge-base config/knowledge_base.yml` |
| 1.6 | Unit tests for angle math + integration tests for video processing path | ✅ Done | 134 tests passing, 92% coverage; integration tests with real sample videos |

### Exit Criteria

- Full analysis succeeds on target sample set without manual tweaking.
- Overlays are stable enough for practical visual review.

---

## Phase 2 — Technique Rules and Feedback

Goal: convert angles and motion into clear coaching cues.

### Tasks

| # | Task | Status | Notes |
|---|---|---|---|
| 2.1 | Define fault rules per lift (e.g., squat: knee cave, forward lean, depth) | ✅ Done | `config/knowledge_base.yml` — snatch + clean & jerk, 6 phases each |
| 2.2 | Implement rule engine using per-frame + per-phase thresholds | ✅ Done | `KnowledgeBase` + `ClassifyFrame` + `AnalyzeLift` |
| 2.3 | Generate human-readable feedback with timestamps and severity | ✅ Done | `AnalyzeVideo` now emits session-level timestamped/severity feedback summary in `analyze` CLI output |
| 2.4 | Export session report (JSON + human summary + annotated video) | ✅ Done | `analyze` now writes annotated video + JSON (`*_report.json`) + summary text (`*_summary.txt`) |
| 2.5 | Add regression tests for each rule using curated clips | ✅ Done | Two-tier suite in `tests/regression/`: per-rule classify regression covers every rule in the KB (incl. unreachable phases); 7 synthetic stick-figure MP4 clips drive `AnalyzeVideo` end-to-end through every reachable phase incl. a clean "perfect rep" negative case |

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

1. Write `docs/analysis/phase-0-visual-check.md` (Phase 0 task 0.5) — pass/fail notes for the two annotated clips.
2. Save side-by-side original vs annotated clips (Phase 0 task 0.4).
3. Phase 1 task 1.2 — per-joint confidence gating (the only remaining Phase 1 gap).
4. Pick first Phase 3 task — likely 3.4 (fast preview mode) before mobile capture.

## Known Limitations (carried forward)

- `PhaseDetector` cannot reach `transition`, `jerk_dip`, or `jerk_catch` phases — the state machine only covers idle → setup → first_pull → second_pull → catch → recovery. Rules for unreachable phases are still pinned by the per-rule classify regression in `tests/regression/test_rule_classify_regression.py` but they will never fire from `AnalyzeVideo`. Extending phase detection is a Phase 3+ task.
