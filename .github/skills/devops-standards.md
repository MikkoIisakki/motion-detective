---
name: devops-standards
description: Standard DevOps practices beyond GitOps — dependency management, container hygiene, environment parity, secret rotation, on-call readiness, and operational runbooks.
---

# DevOps Standards

## Dependency Management

### Python
- Pin all dependencies to exact versions in `requirements.txt` (use `pip-compile` from `pip-tools`)
- Separate files: `requirements.txt` (runtime), `requirements-dev.txt` (test/lint only)
- Dependabot enabled for automated PRs on outdated packages (`.github/dependabot.yml`)
- Review Dependabot PRs weekly — don't let them accumulate

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: pip
    directory: /backend
    schedule:
      interval: weekly
    open-pull-requests-limit: 5

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

### Docker base images
- Pin to digest, not just tag: `python:3.12-slim@sha256:abc123...` in production
- Use `docker scout` or `trivy` to scan images for CVEs in CI

```yaml
# CI step: scan image for vulnerabilities
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ghcr.io/${{ github.repository }}/backend:${{ github.sha }}
    severity: CRITICAL,HIGH
    exit-code: 1   # fail CI on critical/high CVEs
```

---

## Container Hygiene

- **Non-root user** in all Dockerfiles — never run as root inside a container
- **Read-only filesystem** where possible — mount only what needs to be writable
- **Minimal base images** — `python:3.12-slim`, not `python:3.12`
- **Multi-stage builds** — dev stage for development, prod stage strips test deps and source tools
- **`.dockerignore`** must exist — exclude `.git`, `tests/`, `.env`, `__pycache__`, `*.pyc`

```dockerfile
FROM python:3.12-slim AS base
RUN groupadd -r app && useradd -r -g app app   # non-root user
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS prod
COPY --chown=app:app . .
USER app                                        # switch to non-root
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Environment Parity

Dev, CI, and production must run the same stack versions. Divergence causes "works on my machine" failures.

| What | Enforced by |
|---|---|
| Python version | `.python-version` file (pyenv) + `setup-python` version in GHA |
| PostgreSQL version | `postgres:16-alpine` pinned in `docker-compose.yml` and CI service |
| Dependency versions | `requirements.txt` pinned with `pip-compile` |
| OS | All environments use Linux containers (no macOS-specific behaviour) |

Local dev uses the same `docker-compose.yml` as CI services. No "I run Postgres locally on macOS" — always Docker.

---

## Secret Rotation

- API keys (Alpha Vantage, FRED, Finnhub) rotated every 90 days
- DB passwords rotated on any suspected exposure
- Rotation procedure:
  1. Generate new secret
  2. Update `.env` locally (test still works)
  3. Update GitHub repository secret
  4. Deploy (CD applies) — verify system still works
  5. Revoke the old secret

Never store rotation history in Git. Use a password manager.

---

## Log Management

All services log to stdout/stderr (Docker captures). No log files written inside containers.

```yaml
# docker-compose.yml logging config
services:
  api:
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
```

For Phase B (Droplet): logs accessible via `docker compose logs -f`. Consider shipping to a log aggregator (e.g. Grafana Loki via Promtail) once debugging reveals the need.

---

## Operational Runbooks

Runbooks live in `docs/runbooks/`. Each covers a failure scenario with step-by-step recovery.

Required runbooks (create at Phase 3):

| Runbook | Scenario |
|---|---|
| `restart-services.md` | Services crashed or unresponsive |
| `failed-migration.md` | Migration applied but schema is wrong |
| `stale-data.md` | Prices not updated — data source issue |
| `restore-db.md` | Database corruption or accidental delete |
| `rotate-secrets.md` | API key or password rotation procedure |

Runbook format:
```markdown
# Runbook: <Scenario>

## Symptoms
- What the user/operator observes

## Diagnosis
- How to confirm this is the problem

## Resolution
- Exact steps to fix (commands, not prose)

## Prevention
- What to add/change to prevent recurrence
```

---

## Backup Strategy

### Phase A (local) — no formal backup needed

### Phase B (Managed PostgreSQL on DigitalOcean)
- DigitalOcean Managed PostgreSQL includes daily automated backups (7-day retention)
- Enable Point-in-Time Recovery (PITR) — DigitalOcean supports this on paid plans
- Test restore at least once after initial setup — an untested backup is not a backup

### Phase C (DOKS)
- Use `pg_dump` scheduled job + upload to DigitalOcean Spaces (S3-compatible)
- Verify restore monthly

---

## Performance Baselines

Establish and track these from Phase 1:

| Metric | Target | Measure with |
|---|---|---|
| API p95 response | < 200ms | Grafana + postgres query timing |
| Daily ingest time | < 30 min | `ingest_run.finished_at - started_at` |
| Score freshness | < 1h after market close | `score_snapshot.as_of_date` vs current time |
| DB query p99 | < 50ms | `pg_stat_statements` extension |
| Container startup | < 30s | `docker compose up` timing |

Enable `pg_stat_statements` in PostgreSQL to track slow queries:
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- Then query:
SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 20;
```

---

## On-Call Readiness (Phase B+)

Even for personal use, define what wakes you up:

| Severity | Examples | Response |
|---|---|---|
| P1 — Data silent | No prices ingested for > 2 days | Fix same day |
| P2 — Degraded | Some tickers missing, scores stale | Fix within 48h |
| P3 — Cosmetic | Grafana panel broken, metric label wrong | Fix next sprint |

Grafana alert rules (provisioned as code) notify via email for P1/P2.
