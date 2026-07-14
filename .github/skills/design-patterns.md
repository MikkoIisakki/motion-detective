---
name: design-patterns
description: Software design patterns applicable to the motion-detective codebase. When to use each, and how they map to specific modules. For architect and engineer use.
---

# Design Patterns

## Patterns in Use

### Ports and Adapters (Hexagonal)
**Where**: `src/ports/` + `src/adapters/`
**What**: Use cases depend on abstract interfaces; infrastructure implements them. The whole CV/ML stack is swappable.

```python
# src/ports/pose_estimator.py
class PoseEstimatorPort(ABC):
    @abstractmethod
    def estimate(self, frame: np.ndarray, bbox: BBox) -> Pose | None: ...

# Production: YoloPoseEstimator (src/adapters/yolo_pose_estimator.py)
# Tests:      FixturePoseEstimator (tests/regression/fixture_pose_estimator.py)
```

See the `clean-architecture` skill for the full layer rules.

---

### Strategy Pattern
**Where**: everywhere a port has multiple implementations
**What**: A family of interchangeable algorithms behind a common interface — the caller never changes.

```python
# AnalyzeVideo doesn't know which estimator it holds:
AnalyzeVideo(..., pose_estimator=YoloPoseEstimator())        # production
AnalyzeVideo(..., pose_estimator=FixturePoseEstimator(poses))  # regression tests
```

`YoloPoseDetector` also applies strategy internally: YOLO detection when ultralytics is available, HOG fallback otherwise, motion-based detection as last resort.

---

### Command Pattern
**Where**: `src/cli/commands.py`
**What**: Each CLI subcommand is an object (`AnalyzeCommand`, `CompareCommand`, `LiftsCommand`, `PhasesCommand`, `RulesCommand`, `ValidateCommand`) constructed with its dependencies and executed by `main.py`. Adding a subcommand never touches existing ones.

---

### State Pattern (lightweight)
**Where**: `src/domain/phase_detector.py`
**What**: `PhaseDetector` is a state machine over `LiftPhase` — one guard clause per state in `_next_phase`, transitions driven by wrist/hip/shoulder y-signals. Adding a phase means adding a state + transition, not rewriting the loop.

---

### Null-tolerant Domain Objects
**Where**: `Pose.get()`, `DetectorPort.detect`, `PoseEstimatorPort.estimate`
**What**: "Not available" is expressed as `None` at well-defined boundaries and absorbed close to the source — `KeypointSmoother` carries missing keypoints forward from prior frames, `AnalyzeLift._extract_measurements` skips angles whose keypoints are absent. Deeper layers never see partial data without a rule for it.

```python
# src/use_cases/analyze_lift.py
ka, kb, kc = pose.get(a), pose.get(b), pose.get(c)
if ka is None or kb is None or kc is None:
    continue  # angle simply not measured this frame
```

---

### Facade Pattern
**Where**: `src/use_cases/analyze_video.py`
**What**: `AnalyzeVideo.execute(input_path, output_path)` is a single entry point over validate → read → detect → estimate → gate → smooth → analyse → render → write → report. Callers (CLI, regression tests) never orchestrate the pipeline themselves.

---

## Patterns Planned for Phase 3+ (not yet used)

| Pattern | Future home | Note |
|---|---|---|
| **Repository** | `storage/` (sessions, results) | All DB access behind a clean interface once Postgres exists |
| **Observer / Event** | upload → analysis worker trigger | Job status polling first; queue/stream later |
| **Decorator** | retry/timing on external calls | No external APIs today |

Do not introduce these before the infrastructure they serve exists.

---

## SOLID Principles Applied

| Principle | How it applies |
|---|---|
| **Single Responsibility** | Each module owns one concern: `angle_math.py` owns geometry, `knowledge_base.py` owns rule parsing, `overlay_renderer.py` owns drawing |
| **Open/Closed** | Add a fault rule by editing `config/knowledge_base.yml` — never by modifying classifier code |
| **Liskov Substitution** | Every `PoseEstimatorPort`/`DetectorPort` implementation is substitutable — the regression suite depends on it |
| **Interface Segregation** | Ports are small and single-purpose (`VideoReaderPort` ≠ `VideoWriterPort` ≠ `VideoValidatorPort`) — fakes implement only what a test needs |
| **Dependency Inversion** | Use cases depend on `src/ports/` abstractions, never on `cv2` or `ultralytics` directly |

---

## Anti-Patterns to Avoid

| Anti-pattern | Example | Why |
|---|---|---|
| **God module** | `utils.py` with 500 lines | No clear responsibility; becomes a dumping ground |
| **Primitive obsession** | Passing bare `float` angles instead of `JointMeasurement` | Loses type safety and domain meaning |
| **Anemic domain model** | Thresholds as dicts with logic in a service | `AngleThreshold.classify` keeps the rule next to the data |
| **Shotgun surgery** | Adding a lift requiring changes in 8 files | It should be a KB entry + (at most) phase-detector work |
| **Premature abstraction** | Base class for two identical implementations | Wait until the third implementation before abstracting |
