---
name: requirements-management
description: Requirements traceability, NFR ownership, change management, and MoSCoW prioritization for the motion-detective project. Owned by the product-manager agent.
---

# Requirements Management

## Requirements Hierarchy

```
Vision
  └── Project Objective
        └── Phase Goal  (see docs/PLAN.md)
              └── Epic  (e.g. "clean & jerk fault coverage")
                    └── User Story  (e.g. "flag soft elbow lockout in the jerk catch")
                          └── Acceptance Criteria  (Given/When/Then)
                                └── Test  (pytest test case / regression fixture)
```

Every item traces up and down. A change at any level must be evaluated for impact on all levels below it.

---

## Functional vs Non-Functional Requirements

### Functional Requirements (FR)
What the system does. Captured as user stories with Given/When/Then AC.
Owner: **product-manager**

### Non-Functional Requirements (NFR)
How well the system does it. Must have explicit acceptance criteria just like FRs.
Owner: **architect** (defines targets) + **product-manager** (validates they are met)

| NFR | Target | Acceptance Criterion | Measured by |
|---|---|---|---|
| Analysis latency | < 60s for a 10s video | `analyze` completes within budget on the dev machine | Timed CLI run |
| Fault recall | > 80% of visible faults flagged | Coach-validated clip set produces expected findings | Regression fixtures + coach review |
| False positive rate | < 15% of flagged faults | Good-form clips produce no findings | `snatch_perfect_rep` style fixtures |
| Test coverage | current: ~95% over `src/`; CI gate planned | Coverage table read on every run; no material drop | `--cov=src --cov-report=term-missing` |
| Onboarding | New dev setup < 15 min | `git clone → uv sync → tests pass` | Manual verification |
| Determinism | Regression clips reproducible | Regenerated MP4s match committed ones | `tests/regression/synthetic_clip.py` |

NFRs must be tested just like FRs. If an NFR cannot be verified automatically, add it to the CI pipeline.

---

## Requirement Traceability Matrix (RTM)

Maintain `docs/requirements/traceability.md`. Format:

```markdown
| ID | User Story | Phase | AC Count | Design Artifact | Test File(s) | Status |
|----|---|---|---|---|---|---|
| US-01 | Analyze a snatch video and get annotated output | 1 | 4 | (pipeline design) | test_analyze_video.py, test_commands.py | Done |
| US-02 | Flag setup faults with coaching cues | 1 | 3 | fault spec (coach) | test_rule_classify_regression.py, snatch_setup_hip_high.yaml | Done |
| US-03 | Compare two lift videos side by side | 1 | 2 | (compare design) | test_compare_videos.py | Done |
| NFR-01 | Analysis < 60s for a 10s video | 1 | 1 | — | timed CLI run | Pending |
```

Update the RTM when:
- A story is added, changed, or completed
- A design artifact is produced
- A test file is created

The RTM is the source of truth for what has been built and what remains.

---

## MoSCoW Prioritization

Use MoSCoW within each phase to decide what ships vs what defers when time pressure occurs:

| Priority | Meaning | Rule |
|---|---|---|
| **Must** | Required for the phase to be considered complete | Cannot defer — blocks next phase |
| **Should** | High value, expected to ship | Defer only under explicit time pressure, log the decision |
| **Could** | Nice to have, adds value | First to defer when scope is tight |
| **Won't** | Deliberately excluded from this phase | Documented so it's not re-debated |

Every story in the backlog has a MoSCoW label. When a Must is threatened, escalate to orchestrator before deferring.

---

## Change Management

### When a requirement changes mid-phase:

1. **Document the change** — what changed, why, who requested it
2. **Impact assessment** — which design artifacts, tests, and implementations are affected?
3. **MoSCoW check** — does this change a Must? If so, what Must is being dropped to make room?
4. **Orchestrator approval** — changes affecting scope, design, or phase completion require orchestrator sign-off
5. **Update RTM** — reflect the change in the traceability matrix

### Change log format (in `docs/requirements/changes.md`):

```markdown
## YYYY-MM-DD — <short description>

**Requested by**: <user/coach/architect>
**Change**: <what changed>
**Reason**: <why>
**Impact**: <which stories, artifacts, tests affected>
**Decision**: Approved / Deferred / Rejected
**Approved by**: orchestrator
```

### What never changes without explicit approval:
- Phase scope (adding stories to a phase already in progress)
- NFR targets (relaxing coverage or latency targets)
- Fault definitions or angle thresholds (coach must approve; see `knowledge-base-authoring`)

---

## Requirements Smells

Flag these to the orchestrator immediately:

| Smell | Example | Problem |
|---|---|---|
| Ambiguous AC | "should be fast" | Not testable — quantify |
| Missing error case | Only happy path AC | Incomplete coverage |
| Implementation in story | "use cv2.inRange to track the bar" | Story dictates how, not what |
| Untraceable story | Story with no test file | Can't verify it was built |
| Orphan test | Test with no linked story | Unknown what requirement it validates |
| Gold plating | Engineer adds unasked features | Scope creep — remove or log as new story |
