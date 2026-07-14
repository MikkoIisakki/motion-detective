---
name: test-driven-development
description: TDD process, test pyramid, pytest conventions, fakes-over-mocks patterns, and how to write Given/When/Then tests for the motion-detective codebase. For engineer use.
---

# Test-Driven Development

## The TDD Cycle

**Red → Green → Refactor. Always in this order.**

```
1. Read the acceptance criterion (Given/When/Then from product-manager)
2. Write a test that captures the criterion — run it, confirm it FAILS (Red)
3. Write the minimum code to make it pass — run it, confirm it PASSES (Green)
4. Clean up the code without breaking the test (Refactor)
5. Repeat for the next criterion
```

If you write code before a failing test exists, you are not doing TDD. Stop, write the test first.

## Test Pyramid

```
        /\
       /  \   Integration (marked `integration` — real videos, excluded from default run)
      /────\
     / Regr. \  Regression suite — real OpenCV I/O over synthetic MP4s, YOLO faked
    /──────────\
   /   Unit     \  Unit tests — pure domain functions + use cases with fakes, fast
  /______________\
```

- **Unit tests**: majority of tests. Pure domain functions and use cases with fake ports. No YOLO, no video files. Whole suite runs in ~2s.
- **Regression tests**: `tests/regression/` — end-to-end `AnalyzeVideo` runs on deterministic stick-figure clips plus a per-rule classify net (see the `regression-harness` skill).
- **Integration tests**: `@pytest.mark.integration` — need real video files / external I/O; excluded by `-m "not integration"`.

## Pytest Conventions

### File structure (mirrors `src/`)

```
tests/
  domain/
    test_angle_math.py
    test_faults.py
    test_phase_detector.py
    test_keypoint_smoother.py
    test_joint_gate.py
    test_knowledge_base.py
    test_models.py
  adapters/
    test_file_validator.py
    test_opencv_video.py
    test_overlay_renderer.py
    test_yolo_detector.py
    test_yolo_pose_estimator.py
  use_cases/
    test_analyze_lift.py
    test_analyze_video.py
    test_classify_frame.py
    test_compare_videos.py
  cli/
    test_commands.py
  regression/          ← see regression-harness skill
  test_main.py
```

### Test naming
`test_<what>_<condition>_<expected>`:
```python
def test_classify_angle_in_good_band_returns_good(): ...
def test_phase_detector_incomplete_signal_keeps_current_phase(): ...
def test_analyze_rejects_smoothing_above_one(): ...
```

### Given/When/Then in test structure

Map acceptance criteria directly to test structure using comments:

```python
def test_first_pull_hip_angle_below_fault_band_is_flagged():
    # Given: the snatch first_pull hip_angle rule (fault band 0–50°)
    # When: a frame measures hip_angle = 25°
    # Then: the fault is reported with feedback and priority

    kb = KnowledgeBase.from_file("config/knowledge_base.yml")
    classify = ClassifyFrame(kb)

    results = classify.execute(
        "snatch", LiftPhase.FIRST_PULL, [JointMeasurement("hip_angle", 25.0)]
    )

    assert results[0].severity == FaultSeverity.FAULT
    assert results[0].feedback
    assert results[0].priority == FaultPriority.PERFORMANCE
```

## Fakes over Mocks

Use cases depend on ports (`src/ports/`), so tests inject **hand-written fakes that implement the port** — not `unittest.mock` patch chains. Fakes live next to the tests that use them (see `tests/use_cases/test_analyze_video.py`):

```python
class FakeValidator(VideoValidatorPort):
    def __init__(self, should_raise: bool = False):
        self._should_raise = should_raise

    def validate(self, path: str) -> None:
        if self._should_raise:
            raise ValueError(f"Invalid video: {path}")


class FakeWriter(VideoWriterPort):
    def __init__(self):
        self.written_frames: list[np.ndarray] = []
        self.closed = False

    def open(self, path: str, meta: VideoMeta) -> None:
        self.opened_path = path

    def write_frame(self, frame: np.ndarray) -> None:
        self.written_frames.append(frame)
```

Why fakes beat mocks here:
- They are checked by the type system — if a port grows a method, fakes fail loudly
- They hold observable state (`written_frames`) instead of brittle `assert_called_with` chains
- They read like the real thing, so tests document the contract

## Unit Test Patterns

Pure domain functions need no fixtures — just call and assert:

```python
# tests/domain/test_angle_math.py style
from src.domain.angle_math import joint_angle
from src.domain.models import Keypoint

def test_right_angle_is_90_degrees():
    # Given: three keypoints forming an L
    a = Keypoint("hip", 0, 0)
    b = Keypoint("knee", 0, 100)
    c = Keypoint("ankle", 100, 100)
    # When / Then
    assert joint_angle(a, b, c) == pytest.approx(90.0)

def test_coincident_points_return_zero():
    p = Keypoint("hip", 50, 50)
    assert joint_angle(p, p, p) == 0.0
```

## Use-Case Test Pattern

```python
def test_analyze_video_writes_one_frame_per_input_frame():
    # Given: a 3-frame fake video and fakes for every port
    frames = [np.zeros((240, 320, 3), dtype=np.uint8)] * 3
    writer = FakeWriter()
    use_case = AnalyzeVideo(
        validator=FakeValidator(),
        reader=FakeReader(frames),
        writer=writer,
        detector=FakeDetector(),
        pose_estimator=FakePoseEstimator(),
        renderer=FakeRenderer(),
    )
    # When
    use_case.execute("in.mp4", "out.mp4")
    # Then
    assert len(writer.written_frames) == 3
```

## What NOT to Mock

- **Domain logic** — never fake `AngleThreshold.classify` or `PhaseDetector`; test them directly
- **The knowledge base** — load the real `config/knowledge_base.yml` (it is fast and it is the product)
- **OpenCV in the regression suite** — the clip tests intentionally use the real reader/writer on real MP4s

**Fake only at the ports**: YOLO (`FixturePoseEstimator` / `FakePoseEstimator`), video I/O in unit tests, the detector (`_FullFrameDetector` in regression tests).

## Running Tests

```bash
# The standard run (what CI does) — excludes integration tests
uv run python -m pytest -q -m "not integration"

# Everything including integration tests (needs real videos)
uv run python -m pytest -q

# One directory
uv run python -m pytest tests/domain/ -q

# Specific file, verbose
uv run python -m pytest tests/use_cases/test_analyze_video.py -v

# Coverage is on by default (pyproject addopts: --cov=src --cov-report=term-missing).
# Current coverage over src/ is ~95%; there is no enforced gate yet (CI gate planned).
```
