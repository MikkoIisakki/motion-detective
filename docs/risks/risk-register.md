# Risk Register

Last reviewed: 2026-07-14
Current phase: Phases 1–2 complete; Phase 3 (Gym Usability) next — see `docs/PLAN.md`

Score = Likelihood (1–5) × Impact (1–5). High ≥ 10, Critical ≥ 17.

---

## RISK-001: Video upload latency exceeds user tolerance

| Field | Value |
|---|---|
| Category | Technical |
| Likelihood | 3 |
| Impact | 3 |
| Score | 9 |
| Level | Medium |
| Status | Open |
| Owner | architect, engineer |

**Description**: A 10-second lift video at 1080p/30fps is ~100MB. Upload over mobile network + 30–60s processing time may feel too slow for a training environment.

**Consequences**: Poor UX. Users abandon after one or two tries. App does not get used.

**Mitigation**:
- Async design (upload → poll) sets correct expectations — show progress, not a spinner
- Compress video before upload (lower bitrate, 720p sufficient for pose estimation)
- YOLOv8n is fast — target < 30s processing for 10s video on CPU
- Progress updates via polling endpoint every 3s

**Contingency**: If processing is too slow, add GPU inference (DigitalOcean GPU Droplet) or reduce to keyframe-only analysis.

**Review trigger**: After first end-to-end test with real phone video.

---

## RISK-002: Pose estimation accuracy on Olympic lifts

| Field | Value |
|---|---|
| Category | Domain / Technical |
| Likelihood | 4 |
| Impact | 4 |
| Score | 16 |
| Level | High |
| Status | Open — first two mitigations shipped (confidence gating via `--min-joint-confidence`, EMA smoothing via `--smoothing`); accuracy still unvalidated on real extreme positions |
| Owner | coach, engineer |

**Description**: YOLOv8 COCO pose model was trained on general human poses, not Olympic weightlifting. Extreme positions (full squat, overhead lockout, very fast second pull) may produce low-confidence or incorrect keypoints.

**Consequences**: False fault detection or missed faults. Feedback is wrong. User mistrusts the app.

**Mitigation**:
- Confidence threshold filtering: skip angle computation when keypoint confidence < 0.5
- Temporal smoothing: average over 5-frame windows to reduce noise
- `confidence` field in analysis result reflects proportion of high-quality frames
- Coach validates fault thresholds against real video before publishing
- Coach documents which faults are NOT reliably detectable from 2D video

**Contingency**: Fine-tune YOLOv8 on weightlifting-specific pose dataset (Roboflow has some). Or use a larger model (yolov8m-pose) for better accuracy at cost of speed.

**Review trigger**: After testing with real snatch and C&J videos. If false positive rate > 20%, model fine-tuning is needed.

---

## RISK-003: Backend API unavailable during training session

| Field | Value |
|---|---|
| Category | Operational |
| Likelihood | 2 |
| Impact | 3 |
| Score | 6 |
| Level | Medium |
| Status | Open (Phase A: accepted) |
| Owner | devops |

**Description**: In Phase 1 (local), the backend runs on a developer machine. In Phase 2 (cloud), a Droplet outage would block all analysis.

**Consequences**: App unusable during training. Lifter cannot get feedback.

**Mitigation (Phase A)**: Accepted — local dev, single user.

**Mitigation (Phase B)**: DigitalOcean Managed PostgreSQL, auto-restart on worker crash, health check endpoint for app to show "service unavailable" gracefully.

**Contingency**: On-device inference (CoreML YOLOv8 export for iOS) as fallback — reduced accuracy but works offline.

**Review trigger**: Phase 2 cloud deployment.

---

## RISK-004: False fault detection causes incorrect coaching feedback

| Field | Value |
|---|---|
| Category | Domain |
| Likelihood | 3 |
| Impact | 4 |
| Score | 12 |
| Level | High |
| Status | Open — threshold *drift* is now pinned by the two-tier rule-regression suite (every KB rule + end-to-end synthetic clips) and the 95% coverage CI gate; threshold *correctness* against real lifts remains unvalidated |
| Owner | coach, engineer |

**Description**: Fault thresholds are set by the coach based on biomechanics knowledge, but not validated against a labelled dataset of lifts. The system may flag good technique as a fault or miss real faults.

**Consequences**: Lifter receives wrong coaching cues. May attempt to fix something that isn't broken, disrupting technique. Worse: may ignore real faults flagged as false alarms.

**Mitigation**:
- Coach prioritizes recall over precision — missing a fault is less harmful than a false positive
- `confidence` field in output signals when keypoint data is unreliable
- Safety faults (soft lockout, rounded back) are flagged conservatively — only when angle is clearly outside range
- Initial thresholds validated by the coach against real video before v1 release

**Contingency**: If false positive rate is unacceptable, widen fault thresholds or add a "confidence threshold" gate — only flag faults observed in > 50% of phase frames.

**Review trigger**: After first 10 real lift analysis sessions. Compare flagged faults to coach manual review.

---

## RISK-005: User video privacy

| Field | Value |
|---|---|
| Category | Operational / Legal |
| Likelihood | 2 |
| Impact | 4 |
| Score | 8 |
| Level | Medium |
| Status | Open |
| Owner | architect, devops |

**Description**: The app processes and stores video of a specific person. This is personal data under GDPR. If the backend is cloud-hosted, video is transmitted and stored externally.

**Consequences**: GDPR violation if video is retained without consent or beyond necessity.

**Mitigation**:
- Phase 1 (local): video never leaves the developer's machine — no GDPR risk
- Phase 2+ (cloud): auto-delete raw video after processing completes (keep only the annotated result)
- Annotated video and JSON result are retained only for the session duration (user-configurable)
- No raw video stored beyond processing

**Contingency**: If GDPR compliance is complex for SaaS, process video entirely on-device (CoreML) — no upload, no GDPR risk.

**Review trigger**: Phase 2 cloud deployment. Legal review before storing any user video in the cloud.

---

## RISK-006: Bar path not detectable from COCO keypoints

| Field | Value |
|---|---|
| Category | Technical |
| Likelihood | 5 |
| Impact | 2 |
| Score | 10 |
| Level | High |
| Status | Accepted |
| Owner | coach, engineer |

**Description**: YOLOv8 COCO pose does not include the barbell as a keypoint. Bar path tracking is a wrist-midpoint approximation only. This is inaccurate during the turnover/rack phase when wrists diverge from the bar.

**Consequences**: Bar path analysis is approximate. Some coaching insights (bar path deviation, hip contact proximity) are less precise.

**Mitigation**:
- Accepted for Phase 1 — wrist midpoint is sufficient for most pull phases
- `pose-estimation` skill documents Options 2 (color tracking) and 3 (barbell detector) for Phase 2
- Coach's fault specifications note which faults use wrist proxy vs actual bar

**Contingency**: Phase 2: implement color-based bar tracking or fine-tuned barbell detector.

**Review trigger**: After testing bar path feedback accuracy on real videos.

---

## RISK-007: Scope creep beyond Phase 1

| Field | Value |
|---|---|
| Category | Project |
| Likelihood | 3 |
| Impact | 3 |
| Score | 9 |
| Level | Medium |
| Status | Open — re-scored 2026-07-14: Phases 1–2 shipped without scope creep; note the phase-gate table in `.github/agents/orchestrator.md` had been commented out and was restored 2026-07-14 (see RISK-008) |
| Owner | orchestrator, product-manager |

**Description**: Temptation to add real-time analysis, cycling geometry, social features, or subscription model before Phase 1 is solid.

**Consequences**: Phase 1 never ships. Core analysis pipeline is shaky. Future phases are built on untested ground.

**Mitigation**:
- Phase gates enforced by orchestrator — no Phase 2 work until Phase 1 DoD is fully met
- Product-manager backlog is MoSCoW-prioritised; future-phase items labelled `Won't (this phase)`

**Contingency**: If scope creep is detected, orchestrator returns the task to product-manager to defer the out-of-scope portion.

**Review trigger**: Any task description that references features not in the Phase 1 plan.

---

## RISK-008: Knowledge base and process docs drift from what the pipeline actually does

| Field | Value |
|---|---|
| Category | Process |
| Likelihood | 4 |
| Impact | 2 |
| Score | 8 |
| Level | Medium |
| Status | Realized and resolved (2026-07-14) |
| Owner | orchestrator, engineer |

**Description**: Realized risk, logged retroactively. The knowledge base shipped rules for phases (`transition`, `jerk_dip`, `jerk_catch`) the phase detector could never reach, so those rules silently never fired; meanwhile process docs claimed phase-gate enforcement while the orchestrator's phase-gate table was commented out, and this register went unreviewed across two phase boundaries.

**Consequences**: Rules that appear covered but never execute end-to-end; process controls that exist on paper only.

**Resolution (2026-07-14 hardening pass)**: phase detection extended through `transition` and the jerk phases (plus multi-rep re-entry), knowledge-base validation added at load, the per-rule classify regression pins every KB rule including previously unreachable phases, and the orchestrator phase gates were restored to match `docs/PLAN.md`.

**Review trigger**: Any new KB phase or rule — confirm the phase detector can reach it end-to-end (the clip regression suite is the check).

---

*Add new risks as they are identified. Re-score existing risks at each phase boundary.*
