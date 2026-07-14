---
name: api-design
description: REST API design conventions, versioning strategy, OpenAPI structure, error response format, and pagination contracts for the planned motion-detective backend. For architect use.
---

# API Design

> **FUTURE — Phase 3+ (not yet built).** The current product is a local CLI; see AGENTS.md for present reality. There is no HTTP API today — these conventions apply when the backend is built.

## Conventions

- **Version prefix**: `/v1/` on all endpoints from day one — never break clients by changing unversioned paths
- **Resource naming**: plural nouns, lowercase, hyphen-separated (`/v1/analysis-sessions`, not `/v1/analysisSessions`)
- **HTTP verbs**: GET (read), POST (create), PUT (full replace), PATCH (partial update), DELETE (deactivate)
- **Response format**: always JSON, always wrapped in a consistent envelope

## Response Envelope

All responses use a consistent structure:

```json
// Success — list
{
  "data": [...],
  "meta": {
    "total": 150,
    "limit": 20,
    "offset": 0
  }
}

// Success — single item
{
  "data": { ... }
}

// Error
{
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session 'a1b2c3' not found",
    "details": {}
  }
}
```

## Pagination

All list endpoints support `limit` and `offset`:

```
GET /v1/sessions?limit=20&offset=0
GET /v1/sessions?limit=10&offset=20&lift=snatch
```

Default `limit`: 20. Max `limit`: 100. Always return `meta.total` so clients can paginate.

## Error Codes

Use machine-readable `code` strings alongside HTTP status codes:

| HTTP Status | Code | When |
|---|---|---|
| 400 | `INVALID_PARAMETER` | Bad query param type or value |
| 400 | `MISSING_PARAMETER` | Required param absent |
| 404 | `SESSION_NOT_FOUND` | Session ID doesn't exist |
| 409 | `ANALYSIS_NOT_READY` | Result requested before processing finished |
| 413 | `VIDEO_TOO_LARGE` | Upload exceeds size limit |
| 422 | `VALIDATION_ERROR` | Request body fails Pydantic validation (e.g. unknown lift type) |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `DATABASE_UNAVAILABLE` | DB connection failed |

## Endpoint Catalogue

The core flow is asynchronous: **upload → poll → result** (video processing is too slow for sync HTTP).

### Sessions (upload / poll / result)
```
POST /v1/sessions                         Upload a video + lift type; returns session ID (202 Accepted)
GET  /v1/sessions                         List sessions (filterable: lift, status; paginated)
GET  /v1/sessions/{id}                    Session detail + processing status (poll target)
GET  /v1/sessions/{id}/result             Analysis result: findings, summary, score
GET  /v1/sessions/{id}/video              Annotated video (download / streaming URL)
DEL  /v1/sessions/{id}                    Delete session + stored video (privacy — RISK-005)
```

### Knowledge Base (read-only mirror of config/knowledge_base.yml)
```
GET  /v1/lifts                            Supported lifts
GET  /v1/lifts/{lift}/phases              Phases for a lift
GET  /v1/lifts/{lift}/phases/{phase}/rules  Fault rules (bands, feedback, priority)
```

### System
```
GET  /v1/health                           Liveness: returns 200 if app is running
GET  /v1/health/ready                     Readiness: returns 200 if DB reachable + model loaded
GET  /v1/analysis-runs                    Recent analysis run history + status
```

## OpenAPI / FastAPI Notes

FastAPI generates OpenAPI automatically. Ensure:
- Every endpoint has a `summary` and `description`
- All Pydantic response models have field descriptions
- Error responses documented via `responses={}` parameter
- Tags group endpoints by resource (`sessions`, `lifts`, `system`)

## Query Parameter Conventions

| Pattern | Example | Notes |
|---|---|---|
| Filter | `?lift=snatch` | Exact match, optional |
| Multi-value filter | `?status=done&status=failed` | FastAPI `List[str]` param |
| Date range | `?from=2026-01-01&to=2026-03-01` | ISO 8601 dates |
| Numeric range | `?min_score=25&max_score=100` | Inclusive bounds |
| Sorting | `?sort=created_at&order=desc` | Default sort documented per endpoint |
| Pagination | `?limit=20&offset=0` | Always supported on list endpoints |
