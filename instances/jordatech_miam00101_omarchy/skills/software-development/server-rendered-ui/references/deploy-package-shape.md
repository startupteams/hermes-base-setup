# Deployment Package Shape (single-VM, Docker Compose + nginx)

Session-proven invariants from ACMS PR #2 (`deploy/` in `startupteams/acms-project-framework`). Compose file itself is `deploy/compose.yaml`; run with `docker compose -f deploy/compose.yaml --env-file /opt/acms/.env`.

## Compose invariants

- Three services: `postgres` (16) + `acms-app` (built from repo Dockerfile) + `reverse-proxy` (nginx alpine).
- **Postgres has NO published ports** — reachable only inside the compose network. App port also unpublished: the proxy is the single entrypoint.
- Postgres healthcheck `pg_isready -U acms -d acms`; app `depends_on: postgres: condition: service_healthy`.
- DB URL assembled in compose from env: `postgresql://acms:${ACMS_POSTGRES_PASSWORD}@postgres:5432/acms` — app never hard-codes host assumptions (DB movable later via `ACMS_DATABASE_URL`).
- Required env vars use `${VAR:?set VAR in /opt/acms/.env}` so a missing secret fails compose startup loudly.
- Secrets live only in `/opt/acms/.env` (0600, never committed — example file with placeholders ships in-repo).
- Proxy mounts nginx conf ro + operator TLS dir (`/opt/acms/tls` → `/etc/nginx/tls:ro`).

## nginx (reverse-proxy/nginx.conf)

- Port 80: `return 301 https://$host$request_uri;` — no auth content on plaintext.
- Port 443 ssl + http2; `server_name` = internal DNS name; TLS1.2/1.3.
- Source allowlist before proxying:
  ```
  allow 10.0.10.0/24;
  allow 10.0.20.0/24;
  deny  all;
  ```
- Forwarded headers: `Host`, `X-Forwarded-For`, `X-Forwarded-Proto https`, `X-Real-IP`.
- SSE-ready: `proxy_http_version 1.1`, `proxy_set_header Connection ""`, `proxy_buffering off`, `proxy_read_timeout 3600s`.
- `client_max_body_size 1m` for JSON-only APIs.

## Dockerfile

python:3.12-slim → `pip install .` (package ships templates/static via package-data) → non-root user (`useradd --system --uid 10001 acms`) → `HEALTHCHECK` curl-equivalent via stdlib urllib on `/health` → `CMD uvicorn acms.main:app --host 0.0.0.0 --port 8000`.

## Migrations

Deploy flow runs `docker compose run --rm acms-app alembic upgrade head` between DB health and app start — never `create_all`; the app never owns schema. Never run destructive `alembic downgrade` in rollback without human direction.

## update.sh invariants (safe update flow)

1. Record current commit (`git rev-parse HEAD`).
2. `git fetch origin main`; resolve target to concrete SHA.
3. **Refuse if target is not an ancestor of origin/main** (`git merge-base --is-ancestor`).
4. `git checkout --detach $SHA` → build → migrate → `up -d acms-app` → health loop.
5. On health failure: print the previous commit + point to manual rollback; exit 1.
6. Print both commits at the end. No auto-CD.

## smoke-test.sh pattern

`check "name" cmd` helper that counts failures; sections: backend-direct (`/health`, `/version`, unauth API 401) and via-proxy (HTTPS login page, HTTP→301, UI 303 for unauth, registry API not exposed through proxy). Exit non-zero on any failure. Validated copy in `templates/smoke-test.sh`.

## Operator runbook (deploy/README.md) required sections

Status/logs/restart-app/restart-proxy/DB-health/current-commit/current-Alembic-revision (psql `SELECT version_num FROM alembic_version`) as copy-paste wrapper commands; first-deploy steps (checkout approved SHA → `.env` → TLS files → `deploy.sh`); update flow; rollback procedure; backup/restore notes (PBS job, named volume location, restore + smoke verification).

## Known gaps to flag in PR/handoff (honesty items)

- `docker compose config` unvalidated if Docker isn't on the workstation — validate at deploy time.
- TLS cert path must exist (internal CA); no plaintext fallback for login pages ever.
- Real group DNs / bind credentials are operator-supplied at deploy time.
