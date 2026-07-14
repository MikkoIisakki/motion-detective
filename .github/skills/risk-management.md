---
name: risk-management
description: Risk identification, classification, mitigation, and tracking for the motion-detective project. Covers project, technical, domain, and operational risk categories. Used by orchestrator, architect, product-manager, and coach.
---

# Risk Management

## Risk Classification

Every risk is rated on two dimensions:

**Likelihood**: How probable is the risk materializing?
| Rating | Label | Meaning |
|---|---|---|
| 1 | Rare | Unlikely under normal conditions |
| 2 | Unlikely | Could happen, not expected |
| 3 | Possible | Might happen at some point |
| 4 | Likely | Will probably happen |
| 5 | Almost certain | Expected to happen |

**Impact**: What is the effect if it materializes?
| Rating | Label | Meaning |
|---|---|---|
| 1 | Negligible | Minor inconvenience, no data loss |
| 2 | Minor | Small delay, easily recovered |
| 3 | Moderate | Significant effort to recover, some data loss possible |
| 4 | Major | Phase delayed, meaningful data/time loss |
| 5 | Critical | System unusable, or feedback actively misleads the lifter |

**Risk Score** = Likelihood × Impact

| Score | Level | Action |
|---|---|---|
| 1–4 | Low | Monitor |
| 5–9 | Medium | Mitigate |
| 10–16 | High | Mitigate urgently |
| 17–25 | Critical | Stop and address before proceeding |

---

## Risk Register Format

Each risk in `docs/risks/risk-register.md` follows this format:

```markdown
### RISK-NNN: <Title>

| Field | Value |
|---|---|
| Category | Project / Technical / Domain / Operational |
| Likelihood | 1–5 |
| Impact | 1–5 |
| Score | L × I |
| Level | Low / Medium / High / Critical |
| Status | Open / Mitigated / Accepted / Closed |
| Owner | Which agent monitors this |

**Description**: What could go wrong and why.

**Consequences**: What happens if this risk materializes.

**Mitigation**: Concrete steps taken or planned to reduce likelihood or impact.

**Contingency**: What to do if it materializes despite mitigation.

**Review trigger**: Condition that should prompt re-evaluation of this risk.
```

---

## Risk Categories

### Project Risks
Threaten delivery timeline, scope, or quality.

Common risks for this project:
- **Scope creep** — adding features beyond the current phase
- **Over-engineering** — building Phase 3+ SaaS infrastructure before the CLI product is validated
- **Dependency churn** — ultralytics/OpenCV releases changing APIs or model behavior
- **Learning curve** — new technologies slowing delivery (backend stack adopted prematurely)

### Technical Risks
Threaten system correctness, reliability, or performance.

Common risks for this project:
- **Pose estimation quality** — YOLO keypoints noisy or wrong at high bar speed, odd camera angles, or occlusion (RISK-002)
- **Phase misclassification** — phase detector lands in the wrong phase, so the wrong rules fire
- **Silent degradation** — low-confidence keypoints producing plausible but wrong angles without any signal
- **Regression rot** — KB rules or phase logic changing without the regression suite catching it (mitigated by the two-tier suite in `tests/regression/`)

### Domain / Algorithm Risks
Threaten the quality of technique feedback.

Common risks for this project:
- **Threshold validity** — angle bands in `config/knowledge_base.yml` not matching real coaching standards (RISK-004)
- **2D projection error** — side-view angles distorted by camera placement or lifter rotation
- **Bar path proxy error** — wrist midpoint diverging from the actual bar during turnover
- **False positives eroding trust** — flagging good lifts as faults; prefer missing a fault over false alarms
- **Feedback acting as coaching** — treating automated cues as certainty rather than a probabilistic aid

### Operational Risks
Threaten the running system (mostly Phase 3+ once deployed; today the blast radius is local).

Common risks for this project:
- **User video privacy** — lift videos are personal data; storage/retention decisions matter from the first upload feature (RISK-005)
- **Secret exposure** — credentials committed to git once a backend exists
- **Data loss** — single-node storage with no backup
- **Manual infra drift** — someone SSH's and changes something not in git

---

## Failure Mode and Effects Analysis (FMEA)

For critical components, the architect produces an FMEA table:

```markdown
## FMEA: <Component Name>

| Failure Mode | Effect | Likelihood | Severity | Detection | RPN | Mitigation |
|---|---|---|---|---|---|---|
| YOLO finds no person in frame | No pose; frame unanalysed | 3 | 3 | Medium (rendered output shows no skeleton) | 27 | `YoloPoseDetector` HOG + motion fallback; carry last bbox for up to 8 frames |
| Keypoint confidence low at high bar speed | Wrong angles → false faults | 4 | 4 | Low (silent) | 64 | `--min-joint-confidence` gating + `KeypointSmoother`; report confidence per joint (planned) |
| Phase detector stuck in wrong phase | Wrong rule set applied for rest of clip | 2 | 4 | Medium (regression clips) | 24 | Clip fixtures per phase in `tests/regression/fixtures/` |
| Corrupt/unsupported input video | Analysis crashes mid-run | 2 | 2 | High (immediate error) | 4 | `FileVideoValidator` fails fast before processing |
```

**Risk Priority Number (RPN)** = Likelihood × Severity × (6 - Detection rating)
Detection: 1 = immediate, 5 = never detected

---

## Risk Review Process

### Before starting a new phase
1. Review the risk register — re-score open risks
2. Identify new risks introduced by the upcoming phase work
3. Ensure all High/Critical risks have mitigations in place before proceeding

### Before a significant design decision
- Architect includes a risk section in every ADR
- Any new external dependency gets a risk entry

### Before adding a new fault rule (coach)
- Coach documents detection limitations in the fault specification (camera angle, occlusion, 2D projection)
- New KB rules are automatically pinned by the classify regression; a clip fixture covers end-to-end behavior

### Ongoing
- The regression suite (`tests/regression/`) surfaces rule/phase behavior changes on every CI run
- Phase 3+: dashboards/alerts surface operational risks automatically once services exist

---

## Risk Response Strategies

| Strategy | When to use | Example |
|---|---|---|
| **Avoid** | Risk is too high; change the approach | Don't classify faults from occluded joints → gate low-confidence keypoints out entirely |
| **Mitigate** | Reduce likelihood or impact | Smoothing + confidence gating to reduce false faults from keypoint noise |
| **Transfer** | Move risk to a third party | Phase 3+: managed database so backups are the provider's responsibility |
| **Accept** | Risk is low enough; cost of mitigation exceeds benefit | Accept wrist-midpoint bar proxy inaccuracy during turnover for now (documented limitation) |
| **Contingency** | Plan for if it happens | If YOLO detection fails on a clip: HOG fallback → motion detection → report "no lifter detected" rather than guessing |

---

## Risk Escalation

| Level | Action |
|---|---|
| Low | Log in risk register, monitor |
| Medium | Define mitigation steps, assign to relevant agent |
| High | Block current phase task until mitigation is in place; document in ADR |
| Critical | Stop work, escalate to orchestrator, do not proceed until resolved |
