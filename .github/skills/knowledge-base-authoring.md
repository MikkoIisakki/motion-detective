---
name: knowledge-base-authoring
description: Schema and semantics of config/knowledge_base.yml — the lift → phase → joint fault rules — plus the checklist for adding or changing a rule. For coach, architect, and engineer use.
---

# Knowledge Base Authoring

`config/knowledge_base.yml` is the product's brain: every fault the system can flag is a rule here. **Thresholds live in this file, never in code.** The coach owns the numbers and cue language; the engineer owns the plumbing.

---

## Schema

```
<lift>:                      # snatch | clean_and_jerk (top-level keys; KnowledgeBase.lifts())
  <phase>:                   # must match a LiftPhase value (src/domain/faults.py)
    <joint>:                 # must match a measured joint name (see below)
      good:    [min, max]    # degrees — correct technique
      warning: [min, max]    # suboptimal, flag to lifter
      fault:   [min, max]    # actionable error, must be corrected
      feedback: "..."        # one actionable sentence, what a coach would say
      priority: safety | performance | efficiency
```

Real example:

```yaml
snatch:
  catch:
    elbow_angle:
      good: [170, 180]
      warning: [160, 170]
      fault: [0, 160]
      feedback: "Lock out the elbows overhead — soft lockout risks shoulder injury"
      priority: safety
```

Parsing: `KnowledgeBase.from_file` → `_parse` (src/domain/knowledge_base.py) builds `rules[lift][phase][joint] -> RuleSpec`. Unknown `priority` strings raise at load time (`FaultPriority(...)`); all five keys are required — a missing one is a `KeyError` at parse, caught immediately by the classify regression.

---

## Classify Semantics — Order Matters

`RuleSpec.classify` delegates to `AngleThreshold.classify` (src/domain/faults.py):

```python
def classify(self, angle: float) -> FaultSeverity:
    if self.good[0] <= angle <= self.good[1]:
        return FaultSeverity.GOOD
    if self.warning[0] <= angle <= self.warning[1]:
        return FaultSeverity.WARNING
    return FaultSeverity.FAULT
```

Consequences to design bands around:

- **good wins over warning** — bands are checked in order, so overlap at edges is harmless but good takes precedence
- **everything else is FAULT** — the `fault` band documents *intent* (and feeds the band-midpoint regression), but any angle outside good and warning is a FAULT even if it's also outside the declared fault band. Don't leave accidental gaps between good and warning
- **bounds are inclusive** on both ends
- Only `WARNING` and `FAULT` results are actionable (`FaultResult.is_actionable`) — `GOOD` never surfaces in the feedback summary

---

## How Rules Map to the Pipeline

**Phases**: `<phase>` keys must be `LiftPhase` values: `setup`, `first_pull`, `transition`, `second_pull`, `catch`, `recovery`, `jerk_dip`, `jerk_catch` (the jerk phases for clean & jerk). All phases in the model are reachable by `PhaseDetector` (src/domain/phase_detector.py) — see its docstring for the wrist-proxy limitations (jerk drive classifies as `jerk_dip`; split vs power jerk are not distinguished).

**Joints**: `<joint>` keys must be names produced by `AnalyzeLift._extract_measurements` (src/use_cases/analyze_lift.py):

| Joint key | Definition (vertex = middle point) | Averaged over |
|---|---|---|
| `knee_angle` | angle(hip, knee, ankle) | left + right |
| `hip_angle` | angle(shoulder, hip, knee) | left + right |
| `elbow_angle` | angle(shoulder, elbow, wrist) | left + right |

A rule for any other joint name will parse fine and then **never fire** — `ClassifyFrame` matches rules to measurements by name and silently skips unmatched rules. Adding a new measurable joint means extending `ANGLE_DEFINITIONS` in src/domain/angle_math.py first (engineer task, TDD).

Per frame: `AnalyzeLift.analyse_frame` gets the phase from `PhaseDetector`, measures the joints, and `ClassifyFrame.execute` looks up `rules_for(lift, phase)` — only the current phase's rules apply.

**Angles are 2D side-view interior angles in degrees** (0–180): straight limb ≈ 180, deep flexion → small values. Thresholds must be authored in those terms.

---

## Checklist: Adding a Rule

1. **Coach specifies** — joint, phase, three bands, feedback cue, priority, and the 2D-detectability caveats (see `weightlifting-biomechanics` and the fault-specification format)
2. **Edit `config/knowledge_base.yml`** — add the entry under the right lift → phase → joint. Keep bands gap-free between good and warning; make `feedback` one actionable sentence; pick `priority` from `safety`/`performance`/`efficiency`
3. **Run the classify regression** — it discovers the rule automatically, no test code needed:
   ```bash
   uv run python -m pytest tests/regression/test_rule_classify_regression.py -q
   ```
   This pins band midpoints, non-empty feedback, and known priority from day one.
4. **Add a clip fixture** — a YAML under `tests/regression/fixtures/` that drives the pipeline into the rule's phase and band, plus expected findings (full walkthrough in the `regression-harness` skill)
5. **Verify via the CLI** — `uv run python main.py rules <lift> <phase>` shows the new rule as the product will use it
6. **No code changes** for a new rule on an existing joint/phase — if you find yourself editing `src/` to add a rule, something is wrong

## Checklist: Changing a Threshold

Same as adding, plus: expect existing clip fixtures to fail if their authored angles now land in different bands — that is the harness doing its job. Re-tune the fixture poses (or the expectations) **only** after the coach confirms the new bands are intended.

---

## Authoring Pitfalls

- **Degenerate bands** (`lo == hi`) are legal but the midpoint tests skip them — avoid unless deliberate
- **Copy-paste between lifts**: snatch and clean & jerk share phase names but *not* thresholds (e.g. `catch.elbow_angle` is good at 170–180 for snatch overhead, 0–45 for the clean rack). Never bulk-copy
- **Feedback drift**: clip fixtures match on `feedback_substring` — rewording a cue can break fixtures; grep `tests/regression/fixtures/` for the old wording when editing feedback
- **Priority is not severity**: `priority` says *why it matters* (safety vs performance vs efficiency) and is displayed in findings; severity comes from the bands and drives summary ordering
