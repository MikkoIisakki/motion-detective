---
name: clean-architecture
description: Clean Architecture principles applied to the motion-detective system. Based on Robert C. Martin's Clean Architecture. Defines dependency rules, layer boundaries, and how domain logic is protected from CV/ML infrastructure concerns. For architect use.
---

# Clean Architecture

Based on Robert C. Martin's *Clean Architecture* and Domain-Driven Design principles. The goal is a system where business rules are independent of frameworks, models, and I/O — the fault-classification engine can be tested without YOLO, OpenCV, or a single video file on disk.

---

## The Dependency Rule

**Source code dependencies must point inward. Inner layers know nothing about outer layers.**

```
┌─────────────────────────────────────────────┐
│  Frameworks & Drivers (outermost)           │
│  main.py wiring, cv2, ultralytics/YOLO      │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Interface Adapters                   │  │
│  │  src/adapters/, src/cli/              │  │
│  │                                       │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  Application / Use Cases        │  │  │
│  │  │  src/use_cases/                 │  │  │
│  │  │  AnalyzeVideo, AnalyzeLift,     │  │  │
│  │  │  ClassifyFrame, CompareVideos   │  │  │
│  │  │                                 │  │  │
│  │  │  ┌───────────────────────────┐  │  │  │
│  │  │  │  Domain / Entities        │  │  │  │
│  │  │  │  src/domain/              │  │  │  │
│  │  │  │  Pose, BBox, RuleSpec,    │  │  │  │
│  │  │  │  angle math, PhaseDetector│  │  │  │
│  │  │  └───────────────────────────┘  │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘

Arrows point inward only. Domain never imports adapters. Use cases never import cv2 or ultralytics.
```

`src/ports/` sits between use cases and adapters: abstract interfaces owned by the inner layers, implemented by the outer ones.

---

## Layers in motion-detective

### Layer 1 — Domain Entities (`src/domain/`)

Pure value objects and math. No CV dependencies, no I/O.

```python
# src/domain/faults.py — domain objects
@dataclass(frozen=True)
class AngleThreshold:
    good: tuple[float, float]
    warning: tuple[float, float]
    fault: tuple[float, float]

    def classify(self, angle: float) -> FaultSeverity:
        if self.good[0] <= angle <= self.good[1]:
            return FaultSeverity.GOOD
        if self.warning[0] <= angle <= self.warning[1]:
            return FaultSeverity.WARNING
        return FaultSeverity.FAULT
```

Modules: `models.py` (`BBox`, `Keypoint`, `Pose`), `angle_math.py` (`joint_angle`), `faults.py` (`LiftPhase`, `FaultSeverity`, `FaultResult`), `knowledge_base.py` (`KnowledgeBase`, `RuleSpec`), `phase_detector.py`, `keypoint_smoother.py`, `joint_gate.py`.

**Allowed imports**: Python stdlib (`math`, `dataclasses`, `enum`) and PyYAML for KB parsing. Never `cv2`, never `ultralytics`, never `numpy` frame buffers.

---

### Layer 2 — Ports (`src/ports/`)

Abstract interfaces (ABCs) that the use cases depend on. Owned by the inside, implemented by the outside.

```python
# src/ports/pose_estimator.py
class PoseEstimatorPort(ABC):
    @abstractmethod
    def estimate(self, frame: np.ndarray, bbox: BBox) -> Pose | None:
        """Estimate pose keypoints for the subject within bbox. Returns None if estimation fails."""
```

Ports: `DetectorPort`, `PoseEstimatorPort`, `VideoReaderPort`, `VideoWriterPort`, `VideoValidatorPort`, `FrameRendererPort`.

---

### Layer 3 — Use Cases (`src/use_cases/`)

Orchestration. Depends on domain types and ports — never on adapter classes.

```python
# src/use_cases/analyze_video.py — constructor takes ports, not implementations
class AnalyzeVideo:
    def __init__(
        self,
        validator: VideoValidatorPort,
        reader: VideoReaderPort,
        writer: VideoWriterPort,
        detector: DetectorPort,
        pose_estimator: PoseEstimatorPort,
        renderer: FrameRendererPort,
        analyzer: AnalyzeLift | None = None,
        ...
    ) -> None: ...
```

**Allowed imports**: `src/domain/`, `src/ports/`, stdlib. **Not allowed**: `cv2`, `ultralytics`, anything from `src/adapters/`.

---

### Layer 4 — Interface Adapters (`src/adapters/`, `src/cli/`)

Implementations of the ports plus the CLI presentation layer.

```python
# src/adapters/yolo_pose_estimator.py — adapter
class YoloPoseEstimator(PoseEstimatorPort):
    def estimate(self, frame: np.ndarray, bbox: BBox) -> Pose | None:
        result = self._yolo.predict(frame, classes=[0], conf=self._yolo_conf, verbose=False)
        ...
        return self._build_pose(kp_array[best_idx], conf_array)  # YOLO tensors → domain Pose
```

Adapters: `yolo_detector.py` (`YoloPoseDetector`), `yolo_pose_estimator.py` (`YoloPoseEstimator`), `opencv_video.py` (reader/writer), `file_validator.py`, `overlay_renderer.py`. `src/cli/commands.py` formats use-case results for the terminal — no business logic.

---

### Layer 5 — Frameworks & Drivers (`main.py`)

Wiring only. Builds the object graph and hands it to the CLI:

```python
# main.py — composition root
use_case = AnalyzeVideo(
    validator=FileVideoValidator(),
    reader=OpenCVVideoReader(),
    writer=OpenCVVideoWriter(),
    detector=YoloPoseDetector(yolo_model=args.yolo_model),
    pose_estimator=YoloPoseEstimator(yolo_model=args.yolo_model),
    renderer=OverlayRenderer(),
    analyzer=AnalyzeLift(kb, PhaseDetector(), args.lift),
)
```

---

## Dependency Inversion in Practice

Because `AnalyzeVideo` depends on ports, tests inject hand-written fakes — no YOLO, no video files, no mocking library:

```python
# tests/use_cases/test_analyze_video.py — fakes over mocks
class FakeReader(VideoReaderPort):
    def __init__(self, frames: list[np.ndarray], meta: VideoMeta | None = None):
        self._frames = frames
        self._meta = meta or VideoMeta(fps=30.0, width=320, height=240, total_frames=len(frames))
        self._index = 0

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        if self._index >= len(self._frames):
            return False, None
        frame = self._frames[self._index]
        self._index += 1
        return True, frame
```

The regression suite goes one step further: real OpenCV reader/writer, but a deterministic `FixturePoseEstimator` (`tests/regression/fixture_pose_estimator.py`) swapped in for YOLO — regressing the rule/phase engine, not the model.

---

## Screaming Architecture

**The top-level structure should scream what the system does, not what framework it uses.**

```
# Bad — screams "it's an OpenCV app"
src/
  cv2_helpers/
  yolo/
  video/

# Good — screams "it analyses lifts" (actual layout)
src/
  domain/          ← lift phases, fault rules, angle math
  ports/           ← what the analysis needs from the outside world
  adapters/        ← how cv2/YOLO satisfy those needs
  use_cases/       ← AnalyzeVideo, AnalyzeLift, ClassifyFrame, CompareVideos
```

Framework names (`cv2`, `ultralytics`) appear only inside `src/adapters/` and `main.py`.

---

## Boundaries and the Anti-Corruption Layer

Where the system touches external ML output (YOLO result tensors), a thin translation layer converts external formats into domain types. The rest of the system never sees ultralytics `Results` objects:

```python
# src/adapters/yolo_pose_estimator.py — anti-corruption layer
_COCO_NAMES: dict[int, str] = {0: "nose", 5: "left_shoulder", 6: "right_shoulder", ...}

@staticmethod
def _build_pose(keypoints_xy: np.ndarray, keypoints_conf: np.ndarray | None = None) -> Pose:
    kps = [
        Keypoint(name, int(keypoints_xy[idx][0]), int(keypoints_xy[idx][1]),
                 confidence=confidence_for(idx))
        for idx, name in _COCO_NAMES.items()
        if idx < len(keypoints_xy) ...
    ]
    return Pose(kps)
```

If ultralytics changes its result format tomorrow, only the adapter changes — `PhaseDetector`, `ClassifyFrame`, and every rule stay untouched.

---

## Architecture Fitness Functions

These tests verify architectural rules are not violated (planned as an explicit test module — today the rule is enforced by review):

```python
# tests/architecture/test_dependency_rules.py — planned
import ast, pathlib

FORBIDDEN_IN_DOMAIN = {"cv2", "ultralytics", "src.adapters", "src.use_cases"}

def test_domain_has_no_cv_imports():
    for path in pathlib.Path("src/domain").glob("*.py"):
        tree = ast.parse(path.read_text())
        imports = {
            node.names[0].name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        }
        assert not (imports & FORBIDDEN_IN_DOMAIN), \
            f"{path.name} imports infrastructure — violates dependency rule"

def test_use_cases_do_not_import_adapters():
    for path in pathlib.Path("src/use_cases").glob("*.py"):
        source = path.read_text()
        assert "from src.adapters" not in source, \
            f"{path.name} imports adapters — depend on ports instead"
```
