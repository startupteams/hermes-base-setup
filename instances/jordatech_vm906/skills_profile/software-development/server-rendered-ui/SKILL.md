---
name: server-rendered-ui
description: "Add or evolve an authenticated server-rendered internal web UI (LDAP/LLDAP login, role gating, dashboards) on an existing API backend, plus its internal Docker/HTTPS deployment package."
version: 1.0.0
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

1. **TestClient + Secure cookies:** per-request `cookies=resp.cookies` goes through httpx's cookie jar, which **silently drops Secure cookies against `http://testserver`** → every subsequent page 303s to login ("assert 303 == 200" while prod works). Fix: pass the cookie as a plain dict value — `cookies={COOKIE_NAME: token}`. The starlette deprecation warning on per-request cookie jars points at exactly this ambiguity.
2. **`TemplateResponse` must be `return`ed.** A helper that builds but doesn't return it makes the endpoint emit a bare **200 with empty body** (no error anywhere) — an auth denial that silently becomes 200 OK. Annotate helpers `-> Response` and import `Response`.
3. Use `TestClient(app, follow_redirects=False)` so 303 redirects are assertable.
4. Set `session_cookie_secure=False` via the settings object (mutate the cached `get_settings()` instance and restore in teardown) for plain-HTTP test runs.
5. Suites that shell out to tools (e.g. `alembic` in integration tests via `subprocess.run`) need the venv `bin` on PATH — run pytest with the venv activated, not bare `.venv/bin/python -m pytest`.

Full symptom/fix transcripts: `references/testclient-cookie-pitfalls.md`.

## Live smoke test without a real directory

You can exercise authenticated pages end-to-end without LDAP: run `alembic upgrade head`, boot uvicorn, `POST /api/v1/agents/register` with the machine token, then **mint the session token directly** (`issue_token(user, role)` from `acms.ui.session_auth` with `ACMS_SESSION_COOKIE_SECURE=false`) and `curl -H "Cookie: acms_session=$TOKEN" /ui/...`. Assert: 303→login when unauthenticated, real values on pages (version, agent names, Alembic revision), logout's `Max-Age=0` cookie, and **zero bearer-token occurrences in any UI response**.

## Deployment package shape

Standard layout and invariants (no published DB ports; app port compose-internal only; secrets via `--env-file /opt/acms/.env` 0600, never committed; nginx HTTPS + `allow 10.0.10.0/24; allow 10.0.20.0/24; deny all;` + SSE-ready; `update.sh` refuses targets not ancestor-of-`origin/main` and records the previous commit; smoke script with a `check()` helper): see `references/deploy-package-shape.md` and copy `templates/smoke-test.sh`.

## Repo notes

- ACMS (`~/work/acms-project-framework`): PR template + AGENTS.md require requirement-ID tracing, validation table, risks/reviewer focus in every PR body; agents never self-merge; VM creation/deployment is a separate human gate AFTER PR merge.
