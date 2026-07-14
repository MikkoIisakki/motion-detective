# Agent / AI instructions for motion-detective

This file is the source of truth for AI assistants (Claude Code, Cursor, Cody, Copilot Workspace, etc.) working in this repo. `CLAUDE.md` points here.

## Project goal

A gym-ready app where you record a lift, get an annotated video, and receive actionable technique feedback. See [docs/PLAN.md](docs/PLAN.md) for the phased roadmap and current state.

## Development standards (non-negotiable)

- **TDD**: red → green → refactor. Failing test first, then minimum implementation, then refactor as the third step of the cycle (not a separate cleanup pass). Tests are part of the deliverable — don't skip them to move faster.
- **Clean Architecture**: layers are domain (pure value objects + math, no CV deps), ports (abstract interfaces), adapters (cv2/YOLO/file I/O), use cases (orchestration). Dependencies point inward — domain has no knowledge of frameworks. CV/ML details (YOLO, OpenCV) live behind ports so core logic is testable without them.
- **Clean Code**: meaningful names, small focused functions, no dead code, comments only where the *why* isn't obvious. No duplication.
- Don't add features, error handling, or abstractions beyond what the task requires.

## Repository layout

```
src/
  domain/        # value objects, angle math, knowledge-base parsing — no CV deps
  ports/         # abstract interfaces (DetectorPort, PoseEstimatorPort, ...)
  adapters/      # cv2 / YOLO / file I/O implementations
  use_cases/     # AnalyzeVideo, AnalyzeLift, ClassifyFrame
main.py          # CLI entrypoint
config/
  knowledge_base.yml   # per-lift, per-phase fault rules (good/warning/fault bands)
tests/
  domain/ adapters/ use_cases/ cli/
  regression/    # rule-regression suite — see below
docs/PLAN.md     # phased roadmap; the authoritative status doc
```

## Test approach

Run with `uv run python -m pytest -q -m "not integration"` (523 tests, ~3s; plus 10 `integration`-marked tests that need the gitignored `data/` sample videos — run those with `-m integration`; the real-footage phase-detection test additionally needs the YOLO weights and skips otherwise). Coverage is gated: the run fails below 95% over `src/` + `main.py` (`--cov-fail-under=95` in `pyproject.toml`).

Quality gates (all enforced by CI in `.github/workflows/tests.yml`; the test job runs on a Python 3.12 + 3.13 matrix):

```bash
uv run ruff check .                                # lint (config in pyproject.toml)
uv run mypy src main.py                            # type check (config in pyproject.toml)
uv run python -m pytest -q -m "not integration"    # tests + 95% coverage gate
```

The **regression suite** under `tests/regression/` is two-tiered:

1. **Per-rule classify regression** ([test_rule_classify_regression.py](tests/regression/test_rule_classify_regression.py)) parametrizes over every rule in `config/knowledge_base.yml` and asserts good/warning/fault classification + non-empty feedback + known priority. This is the comprehensive coverage net — including phases the phase detector can't currently reach.
2. **End-to-end clip regression** ([test_rule_regression.py](tests/regression/test_rule_regression.py)) loads YAML fixtures under [tests/regression/fixtures/](tests/regression/fixtures/), renders them to stick-figure MP4s in [tests/regression/clips/](tests/regression/clips/), and runs `AnalyzeVideo` end-to-end via real OpenCV I/O with a `FixturePoseEstimator` injected in place of YOLO. It intentionally uses raw authored poses so rule/phase expectations strict-match; smoothing behavior is covered by CLI parser tests and `AnalyzeVideo` use-case tests.

Supporting modules:
- [synthetic_pose.py](tests/regression/synthetic_pose.py) — `build_side_pose(PoseSpec)` turns joint angles into a 2-D side-view pose. Two arm modes: natural and anchored-wrist (isoceles-triangle elbow placement) for clips that need to pin `wrist_y` for phase detection without distorting the elbow rule.
- [synthetic_clip.py](tests/regression/synthetic_clip.py) — renders a pose sequence to MP4.
- [fixture_pose_estimator.py](tests/regression/fixture_pose_estimator.py) — deterministic `PoseEstimatorPort` stand-in for YOLO.
- [clip_fixture.py](tests/regression/clip_fixture.py) — YAML loader.

**Adding a new rule** → add it to `knowledge_base.yml`; the classify regression picks it up automatically. **Adding a clip** → drop a YAML in `tests/regression/fixtures/`; the test parametrize will discover it. MP4s auto-regenerate when missing.

## Known limitations

- `PhaseDetector` uses the wrist midpoint as the only bar proxy: the jerk drive cannot be told apart from the jerk dip (both keep the bar racked, so drive frames classify as `jerk_dip` until the bar is overhead), and a split jerk is indistinguishable from a power jerk (both land in `jerk_catch`). The full ladder (`setup → first_pull → transition → second_pull → catch → recovery`, plus `jerk_dip → jerk_catch → recovery` for clean & jerk, plus multi-rep re-entry into `setup`) is otherwise reachable end-to-end.

## Working preferences

- Delegate substantial multi-step refactors / surveys to subagents (Claude Code: `general-purpose` or `Explore`) rather than doing them inline.
- Don't commit unless explicitly asked. Commit messages follow the existing repo style: lowercase prefix (`feat:`, `test:`, `refactor:`, `docs:`, `chore:`) + brief one-line subject + optional body.
