---
name: server-rendered-ui
description: "Add or evolve an authenticated server-rendered internal web UI (LDAP/LLDAP login, role gating, dashboards) on an existing API backend, plus its internal Docker/HTTPS deployment package."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [FastAPI, Web-UI, Auth, LLDAP, Deployment, Testing]
    related_skills: [github-pr-workflow, writing-plans]
---

# Server-Rendered Internal Web UI

Class of task: an internal control surface (login, role-gated read pages, dashboards) added on top of an existing API backend, when a full SPA is not yet justified. Proven on ACMS PR #2 (LLDAP login + Administrator/Worker/Observer roles + Jinja2 dashboards + Compose/nginx deployment package); patterns generalize beyond FastAPI.

## When to use

- Internal UI needed quickly; no Node build pipeline wanted. Frame the choice in a **Proposed ADR** ("intentionally replaceable by React/Next.js later").
- Human auth against an existing directory (LLDAP/LDAP); machine/API auth stays on the bearer token and must NEVER reach browser JS or templates.
- Deployment: single VM, Docker Compose, internal-only HTTPS behind a reverse proxy with source-network allowlist.

## Architecture pattern (FastAPI)

- UI lives **inside the app**: `acms/ui/{routes.py, session_auth.py, ldap_auth.py, roles.py, templates/, static/}`, attached via `install_ui(app)` (router `prefix="/ui"`, `include_in_schema=False`, plus a `StaticFiles` mount).
- Pages: `/ui/login`, `/ui/`, `/ui/agents`, `/ui/system`, `/ui/logout`. Show **only real backend data** — fields the backend doesn't maintain yet (assignment, status, cost, last contact) are labeled "Not yet implemented", never fabricated. This honesty is an acceptance-criteria matter, not style.
- Fail-closed config (env-prefixed settings): missing/placeholder `SESSION_SECRET` → login page and POST both return **503 "disabled"** instead of operating insecurely; placeholder sentinels to treat as unset: `""`, `change-me`, `replace-with-a-random-secret`.
- Sessions: `base64url(payload).base64url(HMAC-SHA256(secret, payload))` JSON `{u, r, exp}`; `hmac.compare_digest` for verification; cookie `HttpOnly` + `SameSite=Lax` always, `Secure` from config (default on).
- Roles: map directory group DNs → roles via configurable env vars; normalize case/whitespace; multi-group membership → highest-privilege wins (deterministic); unmapped authenticated user → denied (403, generic message — no user enumeration); LDAP down → 503.
- Pages gate with a dependency that raises `HTTPException(303, headers={"Location": "/ui/login"})` on missing/invalid cookie.

## LDAP auth recipe (ldap3)

Service bind → user search (escaped filter, `memberOf`, `size_limit=1`) → **rebind as the found user DN with the supplied password** to verify it → map groups. Sync `ldap3` calls MUST run via `anyio.to_thread.run_sync` so the async event loop never blocks. Full flow, failure-classification table, and the fake-ldap3 test harness: see `references/lldap-auth-recipe.md`.

## Testing pitfalls (both cost a debug cycle — read before writing UI tests)

1. **TestClient + Secure cookies:** per-request `cookies=resp.cookies` goes through httpx's cookie jar, which **silently drops Secure cookies against `http://testserver`** → every subsequent page 303s to login. Full details and workarounds: `references/testclient-cookie-pitfalls.md`.
2. **Live smoke test without the password:** register an agent via `/api/v1/agents/register` with the machine token, then **mint the session token directly** (`issue_token(user, role)` from `acms.ui.session_auth` with `ACMS_SESSION_COOKIE_SECURE=false`) and `curl -H "Cookie: acms_session=$TOKEN" /ui/...`. Assert: 303→login when unauthenticated, real values on pages (version, agent names, Alembic revision), logout's `Max-Age=0` cookie, and **zero bearer-token occurrences in any UI response**.

## Deployment package shape

Standard layout and invariants (no published DB ports; app port compose-internal only; secrets via `--env-file /opt/acms/.env` 0600, never committed; nginx HTTPS + `allow 10.0.10.0/24; allow 10.0.20.0/24; deny all;` + SSE-ready; `update.sh` refuses targets not ancestor-of-`origin/main` and records the previous commit; smoke script with a `check()` helper): see `references/deploy-package-shape.md` and copy `templates/smoke-test.sh`.

### Secret hygiene in written artifacts (HARD RULE, user-mandated 2026-09-25)

Deployment plans, PR bodies, handoff docs, runbooks, memory entries, and any other artifact written for this class of task must **never contain** passwords, bearer/API tokens, private keys, LDAP bind secrets, or session secrets — not even "temporary" ones. Reference secrets by **name and location only** (e.g. `SESSION_SECRET` lives in `/opt/acms/.env`, 0600) or by placeholder (`<from .env>`). Same rule applies to terminal output pasted into documents: redact before writing. The fail-closed design means every secret needed at runtime is already in the env-file — a plan that needs an inline secret to be executable is a plan with a design smell.

## Post-merge production sync (proven 2026-09-26, ACMS CT122)

After the human merges the PR, sync prod to the merged commit — a checkout alone does NOT update the running service:

1. On the prod box: `git checkout -- <locally-modified files>` first (hotfixes scp'd during the original deploy block `git pull`); verify merged main actually contains those hotfixes before discarding.
2. `git pull --ff-only origin main` to the merge commit.
3. **Rebuild the app image and recreate the container** (`docker compose -f deploy/compose.yaml --env-file /opt/acms/.env build <app> && ... up -d <app>`). A `git checkout` changes nothing in the running container.
4. Verify from INSIDE the container (`docker exec <app> python -c "import <pkg>; print(__version__)"` + `/health`) — the app port is compose-internal by design, so curl from the CT host fails with connection-refused and that is NOT an outage.
5. **Compose file shadowing pitfall:** a root-level dev `compose.yaml` (postgres-only) shadows `deploy/compose.yaml` — `docker compose ... <service>` from the repo root says `no such service: <app>`. Always pass `-f deploy/compose.yaml` explicitly (the deploy runbook scripts already do).

## Repo notes

- ACMS (`~/work/acms-project-framework`): PR template + AGENTS.md require requirement-ID tracing, validation table, risks/reviewer focus in every PR body; agents never self-merge; VM creation/deployment is a separate human gate AFTER PR merge.
- **Open-PR loop closure:** an "PR open, awaiting human review" session ends with (a) a dated handoff doc committed in the repo — `docs/handoffs/YYYY-MM-DD-PR-<topic>.md`: branch, PR link, what changed, validation table, open questions, recommended next action — and (b) persistent memory updated via `replace` on the existing repo-state entry (merged vs open PRs, deployed commit, live-deployment identity). Keep memory entries short and high-signal so the next session resumes without re-deriving state.
- **Plan-doc convention:** when the user asks for a deployment plan (e.g. `docs/ACMS_FIRST_LIVE_VM_AND_WEB_UI_DEPLOYMENT_PLAN_2026-09-25.md`), structure it as staged, individually-verifiable steps with a rollback note per stage and end the doc with the recommended next PR. Apply the secret-hygiene hard rule above to every stage.
