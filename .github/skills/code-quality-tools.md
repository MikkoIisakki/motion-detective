---
name: code-quality-tools
description: Static analysis, linting, formatting, type checking, and coverage tooling for the motion-detective project — what runs today, what is planned, and the standards to apply either way. For engineer and devops use.
---

# Code Quality Tools

Honest inventory first: **the automated quality gates today are the test suite (with a coverage gate), ruff, and mypy.** Security scanners are planned but not yet configured — do not claim to have run them, and do not invent their output.

---

## Tool Stack

| Tool | Purpose | Status |
|---|---|---|
| `pytest` + `pytest-cov` | Tests + coverage (`--cov=src --cov=main` via `pyproject.toml` addopts) | **Active** — runs locally and in CI (`.github/workflows/tests.yml`) |
| Coverage gate | Fail below threshold | **Active** — `--cov-fail-under=95` in `pyproject.toml` addopts, enforced on every run (local and CI) |
| `ruff` | Linting (`E, F, W, I, UP, B, SIM`; line length 120) | **Active** — `uv run ruff check .`; configured in `pyproject.toml`, enforced by the CI `lint` job |
| `mypy` | Static type checking | **Active** — `uv run mypy src main.py`; configured in `pyproject.toml`, enforced by the CI `lint` job |
| `bandit` | Security scanning | Planned — not yet configured |
| `gitleaks` | Secret scanning | Planned — not yet configured (no secrets exist in this repo today) |

When a "planned" tool is introduced, it must be added to `pyproject.toml` and wired into `.github/workflows/tests.yml` in the same PR — a tool that only runs on one developer's machine is not a gate.

---

## What Runs Today

```bash
# Install (dev extras included)
uv sync --all-extras

# The full quality check
uv run ruff check .
uv run mypy src main.py
uv run python -m pytest -q -m "not integration"
# → 440+ tests, ~3s, coverage table printed via --cov-report=term-missing,
#   fails below 95% total coverage over src/ + main.py
```

CI (`.github/workflows/tests.yml`) runs the same on push/PR to `main`, split into three jobs:

- **lint** — `uv run ruff check .` + `uv run mypy src main.py`
- **test** — `uv run python -m pytest -q -m "not integration"` on a Python 3.12 + 3.13 matrix (coverage gate included via addopts)
- **integration** — `uv run python -m pytest -q --no-cov -m integration` (note: needs the gitignored `data/` sample videos on the runner)

A PR is mergeable only if this workflow is green.

---

## Coverage Standards

- Configured in `pyproject.toml`: `addopts = "--cov=src --cov=main --cov-report=term-missing --cov-fail-under=95"` — every test run prints coverage and fails below 95%
- Coverage measures `src/` and `main.py` — test helpers (e.g. `tests/regression/synthetic_pose.py`) have their own tests instead (`test_synthetic_pose.py`, `test_fixture_pose_estimator.py`)
- `# pragma: no cover` is allowed only on lines that genuinely cannot run without YOLO weights (the `analyze` wiring in `main.py`) or are unreachable guards — never to dodge writing a test
- A 100%-covered line can still be wrong — coverage is a floor, not a goal

---

## Standards Beyond the Tools

`ruff` and `mypy` now run for real, but they don't catch everything. Keep applying these by hand:

### Typing

```python
# Bad — untyped
def classify(measurements):
    ...

# Good — fully typed (real signature, src/use_cases/classify_frame.py)
def execute(
    self,
    lift: str,
    phase: LiftPhase,
    measurements: list[JointMeasurement],
) -> list[FaultResult]:
```

- Every public function is fully annotated (the codebase already is — keep it that way)
- `from __future__ import annotations` at the top of every module (repo convention)
- No `Any` unless interfacing with untyped third-party output (YOLO tensors), and convert to domain types immediately at the adapter boundary

### Complexity

Keep cyclomatic complexity low by structure, not by tooling:

```python
# Real example — src/domain/phase_detector.py keeps a state machine flat:
# one guard clause per phase, early returns, no nesting deeper than two levels
if self._phase == LiftPhase.SETUP:
    if prev and (prev.wrist_y - signal.wrist_y) >= self._rise_threshold:
        return LiftPhase.FIRST_PULL
    return LiftPhase.SETUP
```

If a function needs comments to navigate its branches, extract functions (`_next_phase`, `_detect_yolo`, `_choose_best` are the house style).

### Security hygiene

No web surface, no database, no secrets today — the relevant rules for a local CLI:
- Never `eval`/`exec` on user input
- Validate file paths and user arguments at the CLI boundary (`FileVideoValidator`, `_smoothing_alpha`, `_min_joint_confidence` in `main.py`)
- Keep model downloads pinned via `pyproject.toml` versions (`ultralytics==8.4.21` etc.)

---

## Introducing a Planned Tool (checklist)

1. Add the pinned dev dependency to `pyproject.toml`
2. Add its config (`[tool.ruff]` / `[tool.mypy]`) in `pyproject.toml` — no separate dotfiles unless the tool requires one
3. Run it on the whole repo and fix or explicitly configure away every finding in the same PR — never land a tool that starts red
4. Add a step to `.github/workflows/tests.yml`
5. Update this skill's status table

The actual ruff/mypy config lives in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`): ruff selects `E, F, W, I, UP, B, SIM` at line length 120 (UP042 is deliberately ignored — see the comment there), and mypy runs with `disallow_untyped_defs` plus `ignore_missing_imports` overrides for `cv2`/`ultralytics`/`mediapipe`, which ship no usable stubs.

---

## Pre-commit Hooks

Planned — not yet configured. Mirror the CI gates in `.pre-commit-config.yaml` when it lands. Until then, the pre-push check is:

```bash
uv run ruff check .
uv run mypy src main.py
uv run python -m pytest -q -m "not integration"
```
