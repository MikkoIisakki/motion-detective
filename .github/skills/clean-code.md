---
name: clean-code
description: Clean code principles and practices for the motion-detective codebase. Based on Robert C. Martin's Clean Code and related practices. Mandatory for the engineer agent.
---

# Clean Code

Based on Robert C. Martin's *Clean Code*, Martin Fowler's *Refactoring*, and related practitioner standards. These are not suggestions — they are the bar every implementation must meet.

---

## Naming

**Names must reveal intent. If a name requires a comment, rename it.**

```python
# Bad
def ja(a, b, c):
    d = math.hypot(a.x - b.x, a.y - b.y) * math.hypot(c.x - b.x, c.y - b.y)
    ...

# Good — actual signature from src/domain/angle_math.py
def joint_angle(a: Keypoint, b: Keypoint, c: Keypoint) -> float:
    """Return the angle ABC in degrees, where B is the vertex joint."""
```

Rules:
- **Classes**: nouns — `PhaseDetector`, `KeypointSmoother`, `KnowledgeBase`, `YoloPoseEstimator`
- **Functions**: verb phrases — `classify_frame`, `gate_keypoints`, `build_side_pose`, `render_clip`
- **Booleans**: questions — `is_complete`, `is_actionable`, `has_lift`, `has_all`
- **No abbreviations** unless domain-standard (`bbox`, `fps`, `kb` for knowledge base are established here)
- **No single-letter variables** except loop counters and well-known math (`a`, `b`, `c` as angle vertices are fine)
- **No type suffixes** — `keypoint_list` → `keypoints`, `rule_dict` → `rules_by_joint`

---

## Functions

**A function does one thing. If you can extract a meaningful sub-function, it does more than one thing.**

```python
# Bad — detects, estimates, smooths, classifies, and renders in one blob
def process_frame(frame, model, kb, writer):
    result = model.predict(frame)
    ...eighty lines...

# Good — each step is named and independently testable
# (the actual shape of AnalyzeLift.analyse_frame in src/use_cases/analyze_lift.py)
def analyse_frame(self, pose: Pose) -> FrameAnalysis:
    phase = self._phase_detector.update(pose)
    measurements = self._extract_measurements(pose)
    faults = self._classify.execute(self._lift, phase, measurements)
    return FrameAnalysis(phase=phase, measurements=measurements, faults=faults)
```

Rules:
- **Small** — if it doesn't fit on one screen, it probably does too much
- **One level of abstraction per function** — don't mix orchestration with pixel math
- **No side effects** — a function named `joint_angle` must not write files or mutate the pose
- **Maximum 3 parameters** — if you need more, introduce a dataclass (see `PoseSpec` in the regression suite)
- **No boolean flag parameters** — split into two functions instead
- **Command/Query separation** — a function either returns a value OR causes a side effect, not both

---

## Classes

```python
# Single Responsibility — one reason to change (real classes)
class ClassifyFrame:
    """Maps joint measurements to FaultResults using KB rules."""
    # Only classification — no video I/O, no phase logic, no rendering

class KeypointSmoother:
    """Exponential moving average over keypoint positions."""
    # Only smoothing — knows nothing about lifts, faults, or YOLO
```

Rules:
- **Single Responsibility Principle** — one class, one reason to change
- **Small** — if a class needs a table of contents, split it
- **Cohesion** — all methods use most of the instance variables; if not, extract a class
- **No God classes** — a class named `Manager`, `Handler`, or `Processor` is a smell

---

## Comments

**Good code is self-documenting. Comments explain why, not what.**

```python
# Bad — restates the code
# Update the phase
phase = self._phase_detector.update(pose)

# Good — explains why (real comment from src/domain/phase_detector.py)
# Chain transitions until stable so a single fast update can advance
# multiple phases (e.g. first_pull → second_pull → catch).
for _ in range(len(LiftPhase)):
    ...

# Good — documents a non-obvious convention (real, same file)
"""Image coordinates: lower y = higher in the image. Wrist rising means y decreases."""
```

Rules:
- **No commented-out code** — delete it; git history preserves it
- **No redundant comments** — if the code is clear, no comment needed
- **TODO comments** are technical debt — create a story in the backlog instead
- **File-level context** belongs in the module docstring (see `tests/regression/synthetic_pose.py` for a model example)

---

## Error Handling

```python
# Bad — swallows errors silently
try:
    meta = reader.open(path)
except Exception:
    pass

# Bad — silent fallback the caller can't distinguish from success
def load_kb(path):
    if not Path(path).exists():
        return KnowledgeBase({})   # empty KB silently disables all rules

# Good — fail fast with a descriptive error (real code, src/domain/knowledge_base.py)
@classmethod
def from_file(cls, path: str) -> KnowledgeBase:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Knowledge base file not found: {path}")
    return cls.from_yaml(p.read_text())
```

Rules:
- **Never swallow exceptions** — handle explicitly or let them propagate
- **Fail fast** — validate inputs at boundaries (`BBox.__post_init__` raises on negative width/height; CLI arg parsers reject out-of-range `--smoothing`)
- **`None` means "not available", not "error"** — `DetectorPort.detect` returns `None` for "no lifter in frame" (a normal outcome); invalid input raises `ValueError`
- **Release resources in `finally`** — `AnalyzeVideo.execute` closes reader and writer in a `finally` block

---

## Data / State

```python
# Bad — data clump (always passed together → make a class)
def classify(joint, angle, good_lo, good_hi, warn_lo, warn_hi):
    ...

# Good — cohesive frozen dataclass (real, src/domain/knowledge_base.py)
@dataclass(frozen=True)
class RuleSpec:
    good: tuple[float, float]
    warning: tuple[float, float]
    fault: tuple[float, float]
    feedback: str
    priority: FaultPriority
```

Rules:
- **Immutable by default** — `frozen=True` dataclasses (`BBox`, `Keypoint`, `Pose`, `RuleSpec`, `FrameAnalysis`, `VideoMeta` are all frozen)
- **No mutable default arguments** in function signatures — use `field(default_factory=list)`
- **Don't pass primitives when you mean domain objects** — a measured angle travels as `JointMeasurement(joint, angle)`, not a bare float
- **No global mutable state** — the knowledge base is loaded once at startup and read-only after

---

## DRY and YAGNI

- **DRY** (Don't Repeat Yourself) — if you copy-paste logic twice, extract it. Third copy is a rule.
- **YAGNI** (You Aren't Gonna Need It) — don't build for hypothetical future requirements. Implement what the AC requires. (The Phase 3+ SaaS is a roadmap, not a license to add web scaffolding now.)
- **Rule of Three**: tolerate duplication once, refactor on the third occurrence

---

## Boy Scout Rule

**Leave the code cleaner than you found it.**

If you touch a file and see a naming issue, an unnecessary comment, or a function that does two things — fix it in the same PR. Small, continuous improvement prevents rot.
