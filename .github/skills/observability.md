---
name: observability
description: Logging standards, health check design, job staleness detection, and what "the system is healthy" means for each component of the planned motion-detective backend. For architect and devops use.
---

# Observability

> **FUTURE — Phase 3+ (not yet built).** The current product is a local CLI; see AGENTS.md for present reality. There are no services, health endpoints, or dashboards today — this applies when the backend exists. (Today's observability is the CLI's console output, the session reports from `--report-json`/`--report-summary`, and the test suite.)

## What "Healthy" Means Per Component

| Component | Healthy when | Unhealthy signal |
|---|---|---|
| **API** | Responds to `/v1/health/ready` in < 500ms | DB unreachable, response > 2s |
| **Worker** | Analysis jobs complete within the latency target (< 60s per 10s video) | Job queue grows, no completions in > 15 min while jobs pending |
| **Analysis quality** | Keypoint confidence above threshold on key joints for most frames | Confidence collapse — model file missing/corrupt, bad uploads |
| **Database** | `pg_isready` passes, query latency < 50ms | Connection refused, slow queries |
| **Storage** | Uploaded and annotated videos readable; disk headroom > 20% | Missing artifacts, disk pressure |

## Logging Standards

Use structured JSON logging in all services. Never use `print()`.

```python
# Standard fields in every log record
{
  "timestamp": "2026-04-07T10:00:00Z",     # ISO 8601 UTC
  "level": "INFO",                          # DEBUG / INFO / WARNING / ERROR / CRITICAL
  "service": "worker",                      # service name
  "module": "use_cases.analyze_video",      # Python module path
  "event": "analysis_complete",             # snake_case event name
  "session_id": "a1b2c3",                   # domain context fields
  "lift": "snatch",
  "frames_processed": 312,
  "findings": 2,
  "duration_ms": 41200
}
```

**Log levels**:
- `DEBUG` — per-frame detail, timing internals (off in production)
- `INFO` — job started/completed, frames processed, findings produced
- `WARNING` — recoverable issues: low keypoint confidence run, no lifter detected in a segment, slow processing
- `ERROR` — failed analysis for a specific session, corrupt upload, DB write failed
- `CRITICAL` — worker crash loop, model file unavailable, DB unreachable

**Never log**: credentials, personal data, video content or frame data — a lift video is personal data (RISK-005); log session IDs, not payloads.

## Job Staleness Detection

Dashboard queries to detect stuck or failed analysis work:

```sql
-- Sessions stuck in processing for more than 10 minutes
SELECT id, created_at, status
FROM analysis_session
WHERE status = 'processing'
  AND created_at < NOW() - INTERVAL '10 minutes'
ORDER BY created_at;

-- Recent analysis failures
SELECT id, started_at, status, error_message
FROM analysis_run
WHERE started_at > NOW() - INTERVAL '24 hours'
  AND status = 'failed'
ORDER BY started_at DESC;
```

## Health Check Endpoints

```
GET /v1/health
→ 200 always (liveness — is the process running?)
→ {"status": "ok"}

GET /v1/health/ready
→ 200 if DB reachable + model file loaded + no stuck jobs
→ 503 if DB unreachable
→ {"status": "ok" | "degraded" | "unavailable", "checks": {...}}
```

Readiness response body:
```json
{
  "status": "degraded",
  "checks": {
    "database": "ok",
    "pose_model": "loaded",
    "stuck_jobs": 1,
    "oldest_pending_job": "2026-04-07T09:48:00Z"
  }
}
```

## `analysis_run` Table

Every analysis job writes an `analysis_run` record:

```sql
CREATE TABLE analysis_run (
    id              BIGSERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL,
    lift            TEXT NOT NULL,            -- 'snatch', 'clean_and_jerk'
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',  -- 'running', 'success', 'failed'
    frames_processed INT,
    findings_count   INT,
    mean_confidence  REAL,                    -- keypoint quality signal
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Alert Rules (System Health)

Configure in the dashboarding tool — these are infra alerts:

| Alert | Query | Threshold |
|---|---|---|
| Stuck analysis jobs | Sessions in `processing` > 10 min | > 0 |
| Failed runs | Failed `analysis_run` rows in last 24h | > 3 |
| Slow analysis | p95 job duration for 10s videos | > 60s |
| API slow | `/v1/health/ready` response time | > 1000ms |
| Confidence collapse | Mean keypoint confidence across recent runs | < 0.5 |
