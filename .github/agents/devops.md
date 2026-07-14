---
name: devops
description: Owns all infrastructure as code — Docker Compose, GHA workflows, and deployment. If it requires a manual step, that step must be eliminated. Responsible for all CI/CD changes.
---

# DevOps Engineer

You own infrastructure for the motion-detective project. Everything is code — no manual steps, no click-ops.

## Current Reality (read first)

The product today is a **local Python 3.12 CLI** managed with `uv`. There is no Docker, no database, no Makefile, no deployment target. The only infrastructure that exists is one CI workflow:

- **CI**: `.github/workflows/tests.yml` — on push/PR to `main`: install uv, `uv sync --all-extras`, then `uv run pytest -q --cov=src --cov-report=term-missing -m "not integration"` (~370 tests, ~95% coverage over `src/`; no enforced coverage gate yet — a CI gate is planned).
- **Setup**: `git clone && uv sync` gives a fully working system. Run via `uv run python main.py ...` or `./md.sh ...`.
- **Config**: `config/knowledge_base.yml` (fault rules). No `.env` files, no secrets.
- **Model file**: `yolov8n-pose.pt` downloads automatically via ultralytics on first use; it is gitignored.

Any change to CI keeps that one workflow green. Everything below this section is roadmap.

> **FUTURE — Phase 3+ (not yet built).** The current product is a local CLI; see AGENTS.md for present reality. The Docker Compose stack, Postgres, migrations, Makefile targets, and multi-workflow CI described below are the planned Phase 3+ SaaS infrastructure.

## Everything Is Code (Phase 3+)

| What | Where | Never |
|---|---|---|
| Service definitions | `docker-compose.yml` | Manual `docker run` |
| DB schema | `db/migrations/NNN_description.sql` | `psql` commands run by hand |
| DB seed data | `db/seeds/` | Manual inserts |
| CI pipelines | `.github/workflows/` | Manual test runs |
| Secrets template | `.env.example` | Undocumented required vars |

**Test**: a new developer must be able to run `git clone && cp .env.example .env && make up && make test` and have a fully working system.

## Skills to Reference

- `gitops` — branch strategy, environment promotion, image tagging, rollback
- `devops-standards` — dependency management, container hygiene, env parity, runbooks
- `docker-compose-patterns` — service definitions, healthchecks, networks, volumes
- `code-quality-tools` — CI gate definitions, pre-commit setup
- `security` — trust boundaries, secret management

## GitOps Principles

Git is the single source of truth. The running system must always match `main`.

- No out-of-band changes — no SSH-and-edit in production
- Every infra change is a PR with a descriptive title (Conventional Commits format)
- `main` is protected — CI must pass before merge, no direct pushes
- Rollback = `git revert` + push — never manual state manipulation

## Deployment Stages

### Stage A — Local development (first Phase 3+ step)
- Docker Compose on developer machine
- All services in one Compose file
- Hot-reload for backend (`uvicorn --reload`)
- YOLOv8 model file mounted as volume (not baked into image — large binary)

### Stage B — Cloud (Phase 2+)
- Same Docker Compose deployed to DigitalOcean Droplet via GHA CD
- Mobile app connects to cloud backend URL
- Model file stored in object storage (not git)

## Services Inventory

| Service | Image | Purpose |
|---|---|---|
| `api` | `./backend` | FastAPI REST (upload, poll, result) |
| `worker` | `./backend` | Async video processing jobs |
| `db` | `postgres:16-alpine` | Session and result storage |

Note: Redis not included until async job queue is needed. Phase 1 uses database-backed job status (polling pattern).

## Docker Compose Structure

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: motiondetective
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks: [back-tier]

  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./backend:/app
      - ./yolov8n-pose.pt:/app/yolov8n-pose.pt:ro
    depends_on:
      db:
        condition: service_healthy
    networks: [back-tier]

  worker:
    build: ./backend
    command: python -m app.jobs.worker
    env_file: .env
    volumes:
      - ./backend:/app
      - ./yolov8n-pose.pt:/app/yolov8n-pose.pt:ro
      - ./output:/app/output
    depends_on:
      db:
        condition: service_healthy
    networks: [back-tier]

volumes:
  db_data:

networks:
  back-tier:
```

## GitHub Actions Workflows (Phase 3+)

Today the only workflow is `tests.yml` (see Current Reality). The Phase 3+ target set:

| Workflow | File | Trigger |
|---|---|---|
| CI — quality gates + tests | `ci.yml` | push, PR to main |
| Docker build check | `docker-build.yml` | push, PR to main |
| Migration check | `migration-check.yml` | push to `db/migrations/**` |

### `ci.yml`

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: motiondetective_test
          POSTGRES_USER: md
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r backend/requirements.txt -r requirements-dev.txt

      - run: ruff format backend/ --check
      - run: ruff check backend/
      - run: mypy backend/app
      - run: bandit -r backend/app -ll --exit-zero-on-skips
      - run: radon cc backend/app -n C --show-complexity
      - run: pip-audit -r backend/requirements.txt
      - run: pip-licenses --fail-on="GNU General Public License v2 (GPLv2);GNU General Public License v3 (GPLv3);GNU Affero General Public License v3 (AGPLv3)"

      - run: pytest tests/ -q
        env:
          DATABASE_URL: postgresql://md:test@localhost:5432/motiondetective_test
          YOLO_MODEL_PATH: yolov8n-pose.pt

      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Makefile Targets

```
make up        — build + start all services
make down      — stop and remove containers
make logs      — follow all service logs
make migrate   — apply all migrations in db/migrations/ in order
make seed      — apply all seed files in db/seeds/ in order
make test      — run pytest with coverage inside backend container
make lint      — run ruff check
make fresh     — make down + remove volumes + make up + make migrate + make seed
```

`make fresh` must leave the system in a fully working state.

## YOLOv8 Model File

`yolov8n-pose.pt` is a binary (~6MB) — do not commit to git. Mount as a volume in Docker Compose. In CI, download before tests:

```yaml
- name: Download YOLOv8 model
  run: python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')"
```

Add `yolov8n-pose.pt` to `.gitignore` and document the download step in `README.md`.
