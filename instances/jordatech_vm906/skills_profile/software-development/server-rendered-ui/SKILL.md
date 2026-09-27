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

## Evolving a page module across feature slices (learned on ACMS Slice 2, v0.5.0)

When a UI grows by vertical slices (list page in slice 1, detail page in slice
2, ...), each new page module MUST reuse the shared helpers instead of
re-deriving them locally — the duplicated version was a real merge-in bug:

- **Auth/context:** depend on the same `current_user` / role helpers; import
  the shared `_base_context(user)` (or equivalent) so footer/version/brand
  render identically on every page. A page that builds its own context dict
  renders `ACMS v  · build ` with EMPTY version — caught in a test failure's
  diff output.
- **Constants:** import display constants (e.g. the recorded-vs-delivered
  notice) from the module that owns them rather than re-typing a near-variant.
  The near-duplicate string ("Recorded assignments only" vs "Recorded
  assignment only") broke an honesty assertion and fragmented the UX.
- **Honesty/"not yet implemented" lists are living data:** the Home page list
  must be re-audited every time a slice ships a backend capability (a shipped
  primary-assignment feature left "primary assignment" in the not-implemented
  list — a false claim on the dashboard). Add a test-time grep or PR-body
  checklist item: does any page now claim something false about the backend?
- **Cross-linking is part of the slice definition of done:** when a detail
  page lands, add links from the parent list page(s) and from related detail
  pages (both directions), plus tests asserting the `href` appears on each.
- **Router mounting:** add the new module's router inside `install_ui(app)`
  next to the others — a router defined but not mounted produces an app whose
  `/ui/*` route set silently lacks the page (tests will 404).
- **Additive service filters follow the existing pattern:** when a detail page
  needs data filtered by a key the existing list function doesn't support,
  add an OPTIONAL keyword param (e.g. `list_execution_tasks(agent_id=...)`)
  mirroring the sibling function's signature style — additive only, no
  existing caller affected, no schema change.

## LDAP auth recipe (ldap3)

Service bind → user search (escaped filter, `memberOf`, `size_limit=1`) → **rebind as the found user DN with the supplied password** to verify it → map groups. Sync `ldap3` calls MUST run via `anyio.to_thread.run_sync` so the async event loop never blocks. Full flow, failure-classification table, and the fake-ldap3 test harness: see `references/lldap-auth-recipe.md`.

## Testing pitfalls (both cost a debug cycle — read before writing UI tests)

1. **TestClient + Secure cookies:** per-request `cookies=resp.cookies` goes through httpx's cookie jar, which **silently drops Secure cookies against `http://testserver`** → every subsequent page 303s to login. Full details and workarounds: `references/testclient-cookie-pitfalls.md`.
2. **Live smoke test without the password:** register an agent via `/api/v1/agents/register` with the machine token, then **mint the session token directly** (`issue_token(user, role)` from `acms.ui.session_auth` with `ACMS_SESSION_COOKIE_SECURE=false`) and `curl -H "Cookie: acms_session=$TOKEN" /ui/...`. Assert: 303→login when unauthenticated, real values on pages (version, agent names, Alembic revision), logout's `Max-Age=0` cookie, and **zero bearer-token occurrences in any UI response**.
 3. **Template corruption lands differently than Python corruption:** Jinja
    templates have no syntax gate (write-tool lint skips .html), so mid-write
    corruption shows up as broken tables, stray closing tags (`</h2>` inside a
    `<p>`), or truncated cells (`{">`), and is caught ONLY by `git diff`
    review or a render-assertion test. Always review new-template diffs and
    include one full-page-render assertion in the tests (assert a string from
    every major section, which fails loudly on truncation).
 4. **Debug a render failure by diffing the page text, not just the assert:**
    `client.get(...).text` in the pytest failure output IS the rendered page —
    grep it for the neighboring strings to distinguish "string missing because
    feature missing" from "string present but slightly different" (the plural
    'assignments' vs 'assignment' case) before changing test or code.

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
