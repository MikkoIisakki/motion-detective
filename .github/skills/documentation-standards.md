---
name: documentation-standards
description: Documentation responsibilities per agent role, ADR format, docstring conventions, and living-documentation rules for motion-detective. Used by all agents.
---

# Documentation Standards

## Principle: Documentation as Code

Documentation lives in the repo, versioned alongside the code it describes. A doc that diverges from the code is worse than no doc — it misleads.

**Rules**:
- Every doc change ships in the same PR as the code change it documents
- Docs are reviewed like code — vague or stale docs are rejected in the DoD check
- No external wiki, no Confluence, no Google Docs — everything in `docs/`, `AGENTS.md`, or inline
- **`AGENTS.md` is the source of truth** for AI-assistant conventions; `docs/PLAN.md` is the authoritative status/roadmap doc. If behavior changes, update them first

---

## Documentation by Agent Role

### Coach → `docs/analysis/`
- Fault specification documents (one per fault)
- Phase definition documents
- Threshold rationale notes (why a band is what it is)
- Detection-limitation notes (what a 2D side view can and cannot measure)

### Architect → `decisions/`
- Architecture Decision Records (ADRs) — one file per decision (directory created with the first ADR)
- Diagrams as Mermaid in `docs/architecture/` when design work starts producing them
- NFR matrix when Phase 3+ design begins

### Engineer → inline + `docs/`
- Python docstrings on all public functions and classes
- Module docstrings that explain the *why* of non-obvious designs (see `tests/regression/synthetic_pose.py` for the house standard)
- Keep `AGENTS.md` layout/test sections accurate when structure changes

### DevOps → `.github/workflows/` + `docs/runbooks/`
- Workflow files are self-documenting — clear step names
- Runbooks appear when there is something to operate (Phase 3+)

### Product Manager → `docs/requirements/`
- Requirement traceability matrix (`docs/requirements/traceability.md`)
- Change log (`docs/requirements/changes.md`)
- Phase retrospective notes

Risk register: `docs/risks/risk-register.md` (currently RISK-001 … RISK-007) — see `risk-management` skill.

---

## Architecture Decision Records (ADRs)

ADRs live in `decisions/`. Every significant architecture or technology choice gets one. They are append-only — never edit a past ADR, write a new one that supersedes it.

### File naming
`decisions/NNN-short-title.md` — e.g. `decisions/001-ports-and-adapters-for-cv.md`

### ADR template

```markdown
# ADR-NNN: <Title>

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Superseded by ADR-NNN
**Deciders**: architect, [orchestrator if cross-cutting]

## Context

What is the problem or situation that requires a decision?
What constraints apply (budget, timeline, existing stack, team size)?

## Options Considered

### Option 1: <Name>
- **Pros**: ...
- **Cons**: ...

### Option 2: <Name>
- **Pros**: ...
- **Cons**: ...

## Decision

Chose Option X because [specific reason tied to context and constraints].

## Consequences

**Positive**:
- ...

**Negative / trade-offs**:
- ...

**Revisit when**:
- [concrete trigger, not "if we need to"]
```

### When to write an ADR
- Technology choice (pose model, video backend, future web framework)
- Architectural pattern (e.g. extending `PhaseDetector` vs replacing it, per-lift phase state machines)
- Knowledge-base schema changes with long-term implications
- Any decision that, if changed later, would require significant rework

Do NOT write an ADR for: implementation details, library internals, variable naming.

---

## Python Docstrings

All public functions, classes, and modules must have docstrings. One-liners are fine when the contract is simple; document units, coordinate systems, and `None` semantics — those are where this codebase bites.

```python
# Real example — src/domain/angle_math.py
def joint_angle(a: Keypoint, b: Keypoint, c: Keypoint) -> float:
    """Return the angle ABC in degrees, where B is the vertex joint.

    Returns 0.0 when either vector has zero length (coincident points).
    """
```

```python
# Real example — src/domain/keypoint_smoother.py class docstring
class KeypointSmoother:
    """Exponential moving average over keypoint positions.

    For each keypoint name, smoothed = alpha * new + (1 - alpha) * previous.
    alpha=1.0 disables smoothing; alpha=0.0 freezes at the first value.
    Missing keypoints in a new pose are filled from the last known state
    (handles brief occlusions / detection dropouts).
    """
```

**Module docstring** (for non-obvious modules — real example, `src/domain/joint_gate.py`):
```python
"""Confidence gating for pose keypoints.

Drops keypoints whose detector-reported confidence falls below a threshold.
Dropped keypoints become absent from the returned `Pose`, which lets the
existing `KeypointSmoother` bridge over them from prior frames.
"""
```

**When docstrings are NOT required**:
- Private functions (`_helper()`) — only if the logic is non-obvious
- Test functions — the test name is the documentation
- Simple frozen-dataclass fields — the names carry the meaning

---

## Documenting Conventions That Cross Files

Two conventions in this codebase must be restated wherever they apply, because getting them silently wrong produces plausible-looking garbage:

1. **Image coordinates** — y grows downward; "wrist rising" means `wrist_y` decreasing. State the coordinate system in any function that does geometry (see `PhaseDetector` and `synthetic_pose.py` docstrings).
2. **Angle definitions** — `knee_angle = angle(hip, knee, ankle)`, `hip_angle = angle(shoulder, hip, knee)`, `elbow_angle = angle(shoulder, elbow, wrist)`, averaged over left/right sides (`ANGLE_DEFINITIONS` in `src/domain/angle_math.py`). Any doc or fixture that talks about angles uses these definitions.

---

## API Documentation

> **FUTURE — Phase 3+ (not yet built).** There is no HTTP API today. When the FastAPI backend exists, OpenAPI is generated from code: every router gets `summary=`/`description=`, every response model gets examples, and the generated spec is committed with every API change.

For the current CLI, the "API docs" are `main.py`'s argparse help — keep `help=` strings and the epilog examples accurate:

```bash
uv run python main.py --help
uv run python main.py analyze --help
```

---

## Changelog

There is no `CHANGELOG.md` yet — history is carried by the commit log, which follows the repo style: lowercase prefix (`feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`) + brief one-line subject. Write subjects so a changelog could be generated from them later.

---

## Docs Folder Structure (current)

```
AGENTS.md                 ← source of truth for AI-assistant conventions (CLAUDE.md points here)
docs/
  PLAN.md                 ← phased roadmap; the authoritative status doc
  analysis/               ← coach: fault specs, phase analyses (e.g. phase-0-visual-check.md)
  requirements/           ← product-manager: RTM, change log
  risks/
    risk-register.md      ← RISK-001 … RISK-007
decisions/                ← architect: ADRs (created with the first ADR)
```

---

## Living Documentation Rules

1. **PR that changes behaviour must update the relevant doc in the same commit** — no "I'll update the docs later"
2. **Stale docs are bugs** — if you find a doc that contradicts the code, fix the doc (or the code) immediately
3. **ADRs are append-only** — mark old ones as `Superseded`, write a new one
4. **Fixture YAMLs are docs** — a clip fixture under `tests/regression/fixtures/` documents exactly what a fault looks like; keep the header comments accurate
5. **Test names are docs** — `test_first_pull_hip_angle_below_fault_band_is_flagged` tells you the rule; write test names as specifications
