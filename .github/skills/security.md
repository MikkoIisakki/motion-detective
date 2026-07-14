---
name: security
description: Trust boundaries, secret management, API key handling, and auth patterns for the motion-detective system across its deployment phases. For architect and devops use.
---

# Security

> **FUTURE — Phase 3+ (not yet built).** The current product is a local CLI; see AGENTS.md for present reality. Today there are no secrets, no network surface, and no user data leaving the machine — these patterns apply when the backend exists.

## Trust Boundaries

```
[ Public Internet ]
      |
   [ Caddy ]  ← TLS termination, only entry point
      |
  ┌───┴────────────┐
  │  front-tier    │
  │  API :8000     │
  │  Grafana :3000 │
  └───┬────────────┘
      |
  ┌───┴────────────────────────────┐
  │  back-tier (internal only)     │
  │  Worker, Scheduler, PostgreSQL │
  └────────────────────────────────┘
```

**Rules**:
- PostgreSQL is never exposed outside `back-tier` — no port binding to host
- Worker and Scheduler have no public interface
- Grafana is accessible via Caddy only — not directly on :3000 in production
- Uploaded videos are stored on the back tier; the API serves them only to their owner

## Secret Management

### Phase A & B (local + single Droplet)
- All secrets in `.env` file, never committed to git
- `.env.example` committed with placeholder values
- `.gitignore` must include `.env`
- Secrets referenced via environment variables only — no hardcoding

### Required secrets
```bash
# .env.example
DB_PASSWORD=change_me
GRAFANA_PASSWORD=change_me

# Phase B — DigitalOcean
DROPLET_SSH_KEY=           # stored in GitHub Secrets for CD workflow
DROPLET_HOST=              # stored in GitHub Secrets
```

### Phase C (DOKS — future)
Migrate to Kubernetes Secrets + External Secrets Operator (syncs from a secrets manager). Never use `kubectl create secret` with inline values in CI logs.

## Config and Credential Handling

- Config read from environment via a `pydantic-settings` class — never `os.environ.get()` scattered through code
- Credentials never logged, even at DEBUG level
- Credentials never passed between services — each service reads its own env

```python
# Correct pattern — central config
class Settings(BaseSettings):
    db_url: str
    video_storage_path: str
    yolo_model_path: str

    model_config = SettingsConfigDict(env_file=".env")
```

## Authentication (Phase A & B — Personal Use)

No user auth needed for personal-use local deployment. Grafana protected by admin password.

For multi-user SaaS, design auth before implementing:
- Use an established solution: Auth0, Supabase Auth, or FastAPI + JWT + refresh tokens
- Never roll a custom auth implementation
- Design: users table, session management, row-level security in PostgreSQL per user

## Data Sensitivity

| Data | Sensitivity | Handling |
|---|---|---|
| **User lift videos** | High — personal data (RISK-005) | Owner-only access, explicit retention policy, deletable via API |
| Analysis results / findings | Medium | Owned by user, row-level access control |
| Knowledge-base rules | Low | Public product content |
| Credentials | High | `.env` only, never logged |
| Grafana dashboards | Low | Admin password protected |

## GitHub Actions Security

- API keys and SSH credentials stored as **GitHub repository secrets** — never in workflow YAML files
- Use `secrets.CONTEXT_NAME` syntax, never echo secrets in run steps
- Pin action versions to a commit SHA (e.g. `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af68`) in production workflows — prevents supply chain attacks on tags

## Caddy Security Headers

Configure in `Caddyfile` for production:
```caddyfile
api.yourdomain.com {
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
    reverse_proxy api:8000
}
```
