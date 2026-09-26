# CT122 (ACMS production) live layout — verified 2026-09-26

Facts verified via SSH during PR #5 work. Re-verify if session is much later.

## Paths & containers

| What | Value |
|---|---|
| Git checkout | `/opt/acms/repo` (NOT `/opt/acms` — that holds .env + tls only) |
| Secrets | `/opt/acms/.env` (0600 root; key names: ACMS_ADMIN_TOKEN, ACMS_POSTGRES_PASSWORD, ACMS_SESSION_SECRET, ACMS_LDAP_URL/BIND_DN/BIND_PASSWORD/USER_BASE/USER_FILTER, ACMS_LDAP_GROUP_ADMIN/WORKER/OBSERVER) |
| TLS | `/opt/acms/tls/acms.crt` + `acms.key` (self-signed; no internal CA on MARION) |
| Compose project | `acms` (containers: `acms-acms-app-1`, `acms-postgres-1`, `acms-reverse-proxy-1`) |
| DB volume | `acms-pgdata` |
| Release state | `/opt/acms/releases/` (created by release.sh; root-only) |

## Container realities (shapes all validation tooling)

- **No curl in the app image** (python:3.12-slim) — health/GET checks must use `python -c "import urllib.request; ..."` via `docker compose exec -T acms-app`.
- **No pg_dump on the CT host** — backups run inside the postgres container: `docker compose exec -T postgres pg_dump -U acms -Fc acms > file.dump`.
- **Nginx allowlist = 10.0.10.0/24 + 10.0.20.0/24 only** — localhost curls get 403; validate via the VM's own IP (10.0.20.122) or an allowlisted source.
- **Self-signed TLS** — every HTTPS check needs `-k`.
- **MARION has NO home.arpa DNS** — `acms.miam.home.arpa` does not resolve; raw IPs are the convention (OPNsense override is a Jordan follow-up).
- Disk: 40G, ~2.6G used — space is not a constraint at current scale.

## Auth model (live-verified)

- LLDAP @ 10.0.20.101:3890, base `dc=example,dc=com` (NOT home.arpa).
- Groups: acms-admin (gid 16, jordatech), acms-workers (17), acms-observers (18).
- LLDAP writes go through HTTP API :17170 GraphQL only (plain LDAP modify → namingViolation). Recipe in /home/jordatech/agents.md 2026-09-26 entry.

## Release tooling map (PR #5)

- `deploy/release.sh` — 4-phase transaction (preflight → backup+maintenance → deploy → two-stage validate); auto-rollback on failure
- `deploy/rollback.sh` — Level 1 app-only standalone / Level 2 in-flight guarded DB restore (forensics copy `acms_old`)
- `deploy/validate-release.sh` — `--stage app|full`, `--strict-build`, `--expected-rev`, `--feature-smoke`
- `deploy/common.sh` — shared helpers; state in `/opt/acms/releases/`
- `/version` returns `{version, git_sha, git_sha_short, build_time, reported_at}` (baked via Docker build args ACMS_BUILD_GIT_SHA / ACMS_BUILD_TIME)

## Session tooling lesson (2026-09-26)

The file-write channel corrupted content mid-write 5+ times this session
(phantom text injected into tool results and files). Ground truth = git diff
+ python verification, never the tool echo. See the `file-write-verification`
skill for the full pattern.