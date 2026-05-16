# motion-detective

A gym-ready app where you record a lift, get an annotated video, and receive actionable technique feedback.

Current capability:
- validates an input video
- detects the primary weightlifter each frame (YOLO pose model, HOG + motion fallback)
- renders bounding box, pose skeleton, and joint angle overlays

## Setup

```bash
cd motion-detective
uv sync
```

## CLI

```bash
uv run python main.py --help                          # top-level help
uv run python main.py <command> --help                # per-command help
```

### Commands

| Command | Purpose |
|---|---|
| `analyze <video>` | Run full pipeline (detect, pose, phase, faults, render) |
| `lifts` | List supported lifts in the knowledge base |
| `phases <lift>` | List phases defined for a given lift |
| `rules <lift> <phase>` | Show fault thresholds and feedback cues |
| `validate <video>` | Check the video file is openable and well-formed |

### Examples

```bash
uv run python main.py analyze data/sample_video_side.mp4 --output output/side_annotated.mp4 --lift snatch
uv run python main.py lifts
uv run python main.py phases snatch
uv run python main.py rules snatch first_pull
uv run python main.py validate data/sample_video_side.mp4
```

Optional flags for `analyze`:
- `--yolo-model` — YOLO model path (default: `yolov8n-pose.pt`)
- `--knowledge-base` — fault rules YAML (default: `config/knowledge_base.yml`)
- `--report-json` — JSON report path (default: `<output>_report.json`)
- `--report-summary` — text summary path (default: `<output>_summary.txt`)

`analyze` now exports three artifacts:
- annotated video (`--output`)
- JSON session report (timestamped findings with severity/priority)
- text summary report (human-readable coaching cues)

## How it works

```
src/
  domain/        # pure value objects and angle math — no CV dependencies
  ports/         # abstract interfaces (DetectorPort, PoseEstimatorPort, etc.)
  adapters/      # cv2 / YOLO / file I/O implementations
  use_cases/     # AnalyzeVideo — orchestrates the pipeline
main.py          # CLI entrypoint
```

Pipeline: validate → detect lifter → estimate pose → render overlay → write frame

Current assumptions:
- mostly static camera
- single primary person in frame

## Tests

```bash
uv run pytest -q                        # unit + regression tests (fast, no real video needed)
uv run pytest -q -m integration         # integration tests (require real video files)
```

Current full suite: 341 tests, 95% coverage over `src/`.

Two-tier regression under `tests/regression/`:
- per-rule classify tests for every entry in `config/knowledge_base.yml`
- end-to-end clip tests that render synthetic stick-figure MP4s from YAML fixtures and drive `AnalyzeVideo` with a `FixturePoseEstimator` (no YOLO dependency). These use raw authored poses for strict rule/phase expectations; smoothing is covered separately by CLI and use-case tests.

## Working with AI assistants

See [AGENTS.md](AGENTS.md) for development standards, repo layout, test approach, and known limitations. Claude Code, Cursor, Copilot, etc. should all follow it. `CLAUDE.md` points to the same file.
