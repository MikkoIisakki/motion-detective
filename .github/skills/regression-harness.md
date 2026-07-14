---
name: regression-harness
description: How the two-tier rule-regression suite under tests/regression/ works — synthetic poses, rendered clip fixtures, the FixturePoseEstimator, and the per-rule classify net — plus the walkthrough for adding a new fault clip fixture. For engineer and coach use.
---

# Regression Harness

The regression suite pins the behavior of the rule + phase engine so knowledge-base or detector changes can't silently change findings. It is two-tiered:

1. **Per-rule classify regression** — every rule in `config/knowledge_base.yml`, tested at band midpoints. Comprehensive, cheap, automatic.
2. **End-to-end clip regression** — curated synthetic MP4s run through the real `AnalyzeVideo` pipeline, asserting the exact findings (and *only* those findings) appear.

Run it:

```bash
uv run python -m pytest tests/regression/ -q
```

---

## The Modules

### `synthetic_pose.py` — PoseSpec → deterministic keypoints

`build_side_pose(PoseSpec)` turns joint angles into a 2D side-view `Pose` whose measured angles match the spec to within pixel-quantisation tolerance (~2°). Image coordinates, lifter faces +x, angles follow the production `joint_angle` definitions.

```python
@dataclass(frozen=True)
class PoseSpec:
    knee_angle: float
    hip_angle: float
    elbow_angle: float
    anchor_x: int = 320
    anchor_y: int = 400          # ankle position
    wrist_y_offset: float | None = None
```

Two arm modes:
- **Natural** (default): forearm rotates off a hanging upper arm so `elbow_angle` is exact.
- **Anchored wrist** (`wrist_y_offset` set): wrist pinned at `anchor_y + wrist_y_offset`, elbow solved via an isoceles triangle so the requested `elbow_angle` still holds. Use this to **drive the phase detector** (which watches `wrist_y`) without distorting the elbow rule. `wrist_y_offset: 0` puts the wrist at ankle level → detector enters SETUP; increasingly negative offsets raise the wrist → FIRST_PULL → SECOND_PULL → CATCH.

### `synthetic_clip.py` — poses → MP4

`render_clip(poses, path, fps=, width=, height=)` draws each pose as a stick figure (same segment list as the production renderer, plus head circle) and writes an `mp4v` MP4. Deterministic by construction — a regenerated clip can be diffed against the committed one.

### `clip_fixture.py` + `fixtures/*.yaml` — clip metadata, frame groups, expectations

`load_fixture(path)` parses a YAML into a `ClipFixture(name, lift, fps, width, height, poses, expected)`. Each `frames` entry is one `PoseSpec` (field-for-field kwargs) repeated `count` times; `expected` is a list of `ExpectedFinding(phase, severity, priority, feedback_substring)`.

### `fixture_pose_estimator.py` — YOLO bypass

`FixturePoseEstimator(poses)` implements `PoseEstimatorPort` and returns the authored pose for each successive frame (repeating the last one after the sequence ends). The tests regress the rule/phase engine, **not** the model — YOLO/HOG never run.

### `test_rule_regression.py` — end-to-end clip tests

For each YAML under `fixtures/` (auto-discovered via glob, parametrized by stem):
1. Renders the clip to `clips/<name>.mp4` **if missing** (MP4s are committed so contributors can inspect them; delete one to regenerate)
2. Runs `AnalyzeVideo` with the real `FileVideoValidator`, `OpenCVVideoReader/Writer`, `OverlayRenderer`, a `_FullFrameDetector`, and the `FixturePoseEstimator`
3. Asserts every expected finding matches a summary line (severity + priority + phase + feedback substring)
4. **Negative assertion**: asserts no *unmatched* findings appear — a fixture with an empty `expected` list must produce exactly `"No actionable faults detected."`

Clips intentionally use raw authored poses (no smoothing configured) so rule/phase expectations strict-match; smoothing behavior is covered by CLI parser and `AnalyzeVideo` use-case tests.

### `test_rule_classify_regression.py` — every-rule net

Parametrizes over **every** `lift::phase::joint` rule in `config/knowledge_base.yml` and asserts:
- good-band midpoint → `GOOD`, warning midpoint → `WARNING`, fault midpoint → `FAULT` (degenerate `lo == hi` bands are skipped)
- feedback is non-empty; priority is a known `FaultPriority`

This is the coverage net for the whole KB — every phase, every joint, independent of clip authoring. **A new KB rule is covered automatically**, with zero test code.

---

## Worked Example: Adding a New Fault Clip Fixture

Goal: pin "hips shoot up early in the clean first pull" (`clean_and_jerk.first_pull.hip_angle`, fault band 0–50°).

**1. Pick the rule and target band** — read it from the KB:

```bash
uv run python main.py rules clean_and_jerk first_pull
```

**2. Author the fixture** — `tests/regression/fixtures/cnj_first_pull_hips_shooting.yaml`:

```yaml
# Clean first pull with hips shooting up — hip angle collapses below 50 deg.
# Targets clean_and_jerk.first_pull.hip_angle FAULT band (0 - 50 deg).
clip:
  name: cnj_first_pull_hips_shooting     # must match the filename stem
  lift: clean_and_jerk
  fps: 30
  width: 640
  height: 480

frames:
  # Hold a clean SETUP first so the detector starts in the right phase.
  - count: 10
    pose:
      knee_angle: 90        # setup good band
      hip_angle: 55         # setup good band
      elbow_angle: 180
      wrist_y_offset: 0     # wrist at ankle level -> SETUP
  # Then rise into FIRST_PULL with the faulty hip angle.
  - count: 20
    pose:
      knee_angle: 120       # first_pull good band — isolate ONE fault
      hip_angle: 30         # first_pull hip FAULT band
      elbow_angle: 180
      wrist_y_offset: -40   # wrist rising -> FIRST_PULL (still below knee height)

expected:
  - phase: first_pull
    severity: FAULT
    priority: performance
    feedback_substring: "hips from shooting up"
```

Authoring rules of thumb:
- **Isolate one fault per fixture** — keep every other joint in its good band for the phase you land in, or the negative assertion will fail on surprise findings
- **Drive phases with `wrist_y_offset`**, not by hoping: `0` → SETUP; a rise ≥ 5px/frame leaves SETUP; above knee height → TRANSITION; within 50px of shoulder height → SECOND_PULL; above shoulder → CATCH (see `PhaseDetector._next_phase` for the exact ladder, incl. the clean & jerk `jerk_dip`/`jerk_catch` conditions)
- **`feedback_substring`** must be a stable substring of the KB rule's `feedback` string
- **Severity/priority are matched as text** in the summary line: `FAULT`/`WARNING` and `safety`/`performance`/`efficiency`

**3. Run the suite** — the parametrize discovers the YAML and renders the MP4 automatically:

```bash
uv run python -m pytest tests/regression/test_rule_regression.py -q
```

**4. On failure, read the assertion output** — it prints the full feedback summary. Typical causes: pose lands in a different phase than expected (check `wrist_y_offset` progression), or another joint strayed out of its good band (adjust it, or add it to `expected` if it's genuinely part of the scenario).

**5. Inspect the clip** — open `tests/regression/clips/cnj_first_pull_hips_shooting.mp4` and sanity-check the stick figure. Commit the YAML **and** the MP4.

---

## Invariants to Preserve

- Fixture discovery is by glob — no test-code registration; never hardcode fixture lists
- Clips are cached and committed; missing MP4s regenerate, stale ones don't — delete the MP4 after editing its YAML
- `FixturePoseEstimator` and `_FullFrameDetector` keep YOLO/HOG out of the loop; don't "improve" the suite by wiring real models in
- The negative assertion is the point — resist loosening it to make a noisy fixture pass
