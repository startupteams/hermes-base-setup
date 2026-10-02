---
name: acms-project-framework
description: "ACMS (startupteams/acms-project-framework) — AI workforce control plane on MARION CT122. Governance model (no self-merge, PR gates, REQ traceability), §12 production sync check, repo validation commands, PR conventions, startupteams org quirks (REST PR edit, push protection), vertical-slice feature delivery workflow."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# ACMS Project Framework (startupteams/acms-project-framework)

Class-level workflow for any task touching ACMS: feature slices, deployment
tooling, UI work, requirement updates, or production sync checks.

## Fixed facts

- **Repo:** `startupteams/acms-project-framework` · clone `~/work/acms-project-framework`
- **Venv:** `.venv-acms` (Python 3.12; system python3 is 3.11 but pyproject requires >=3.12)
- **Live:** LXC CT122 "acms" on MIAM-00135 @ `10.0.20.122` (root SSH key works; jordatech user does not)
- **Docs log:** `/home/jordatech/agents.md` — every PR/session appends a dated entry (Surprise Protocol)
- **Plan of record:** `ACMS_FEATURE_DELIVERY_AND_AUTOMATED_ROLLBACK_PLAN_2026-09-26.md` (vertical slices; PR 0 = safe release/rollback)

## Governance model (repo AGENTS.md — binding)

- **Agents never self-merge.** Every change: feature branch → PR → human review → merge.
- **Deployment is separately human-gated** (plan §3). Rollback to the exact previous known-good on failed validation is the ONE pre-authorized autonomous action.
- Trace implementation to `ACMS-REQ-###` IDs; summarize IDs, acceptance criteria, files, assumptions, validation **before editing**.
- Out-of-scope discoveries → `FUTURE_WORK.md` with provenance (Human-Directed / Agent-Discovered / Source-Derived). Next free ID is checked via `grep -oE "^## FW-[0-9]+" FUTURE_WORK.md | sort -V | tail -1`.
- ADRs: agent-originated significant decisions stay **Proposed**; only human-explicit decisions are **Accepted**.
- Meaningful work produces a handoff in `docs/handoffs/YYYY-MM-DD-<topic>.md`: requirements, attempted/changed, believed state, validation results, blockers, next action.
- PR body must list: requirement IDs, acceptance criteria, validation (exact results), risks, ADR/TDR changes, future work, reviewer focus.

## §12 production sync check (run FIRST, before new feature work)

Never infer deployed code from the version string alone:

```bash
# Repository side
git -C ~/work/acms-project-framework fetch origin --prune
git -C ~/work/acms-project-framework rev-parse origin/main
# Production side
ssh root@10.0.20.122 'cd /opt/acms/repo && git rev-parse HEAD && git status --porcelain | head -3'
ssh root@10.0.20.122 'docker exec acms-postgres-1 psql -U acms -d acms -tAc "SELECT version_num FROM alembic_version"'
```

If production != origin/main: the sync deploy goes FIRST (human-authorized), then feature work. If equal: proceed directly. Record the exact live SHA in the PR body and agents.md.

## Validation battery (before every PR)

```bash
cd ~/work/acms-project-framework && source .venv-acms/bin/activate
python -m pytest -q                                   # full suite
bash -n deploy/*.sh                                   # shell syntax
python3 -c "import yaml; yaml.safe_load(open('deploy/compose.yaml'))"
git diff | grep -iE 'sk-[a-zA-Z0-9]|gho_|vck_|vcp_|GOCSPX|BEGIN.*PRIVATE' || echo CLEAN   # secret scan
```

Docker is NOT available on the workstation — deploy scripts validate as
syntax+logic only; live drills happen on CT122 after merge + authorization.

## startupteams org quirks (GitHub)

- **PR body edits must use REST, not `gh pr edit`** — the GraphQL path errors (projects-classic deprecation): `gh api -X PATCH repos/startupteams/<repo>/pulls/<n> -f body=@file.md`
- Issue trackers may be disabled on some repos — re-enable via settings with the jordatech gh token (`repo` scope) if an issue must be filed.
- **Push protection scans ancestor commits.** If a push is rejected for a secret, rebuilding only the tip is not enough — rebuild branch history from main and re-push.

## PR numbering state (check live; snapshot below is stale-by-design)

Always confirm with `gh pr list` before assuming. Historical anchor points:
PR #1–#4 merged (scaffold, async stack, LLDAP fix, work orchestration);
#5–#8 release tooling + fixes; #9 smoke-test fix; #10 Agent Detail (v0.5.0);
#11 combined slice 3+4 (v0.6.0, heartbeat/reconciliation/keys/bridge);
#12 handoff doc. ADR-0009 and ADR-0010 are **Accepted** as of 2026-09-26/27.

## Self-merge override protocol (session-scoped, 2026-09-26)

Jordan granted an explicit session-scoped override ("merge your own features
as you need them merged... This is an override") during the combined slice 3+4
co-work session, then extended it: "work fully autonomously... document any
questions in the handoff." Protocol for overrides:

- Overrides are **session-scoped** — do not carry them into later sessions
  unless restated. Default rule (no self-merge) reasserts next session.
- Log the grant verbatim-date in agents.md the moment it is given.
- Even under override: still run the full validation battery, never merge
  broken/unreviewed-by-CI code, still never touch others' PRs, and still
  deploy only through release.sh with the pre-authorized rollback rule.

## Branch protection + autonomous merge steady state (ACTIVE since 2026-09-29)

The governance model evolved: `main` is now **protected** (PR required; required checks
`syntax`/`tests`/`secret-scan` from `.github/workflows/ci.yml`; force-push and deletion blocked;
`enforce_admins=false` so the human admin keeps emergency direct-push). Per the 2026-09-29
execution plan §15/§16, the authorized workflow is: branch → implement → tests → PR → required
checks green → self-merge (merge commit) → release.sh deploy. Direct main pushes by AI agents are
prohibited. gitleaks runs with the default ruleset; test-fixture secrets go in
`.gitleaksignore` by fingerprint (never a custom `.gitleaks.toml` — a committed config with
unsupported RE2 syntax breaks the scan on every checkout).

## Module inventory — check before reinventing (updated 2026-10-02)

Phase-A-era modules now in the codebase (check before reinventing): `work_creation_guard.py`
(ADR-0011 Executive-only Work Item creation, `ACMS_EXECUTIVE_AGENT_IDS` env, 403 +
`WORK_CREATION_REJECTED` audit), `jira_client.py`/`jira_sync.py` (v1 mock-first Jira contract,
NO create-issue capability, status mutation flag OFF), `session_lifecycle.py` (auto ExecutionSession
around dispatch, idempotent by a2a_task_id, fail-close on bridge error, zombie reconcile),
`bridge_discovery.py` (ARM-authoritative endpoint resolution → manual JSON fallback → fail-closed),
`economics_ingest.py` (GitHub PR facts → pr_outcomes; MERGED never auto-ACCEPTED), `bakeoff.py`
(budget-gated model comparison). Dispatch live-proof recipe: create work item, POST
`/api/v1/dispatch/work/{id}` with instruction + `idempotency_key`, verify `execution_sessions` row
auto-opened, duplicate dispatch returns `duplicate` without a second session.

2026-10-02 additions: `jira_reconcile.py` intake (eligible unlinked issue → exactly-once
Work/assignment/dispatch, durable per-issue outcomes, PRs #75/#76), `mcp_gateway/`
(top-level package — internal MCP gateway, separate systemd service on VM114; NOT mounted
in the ACMS app; see the acms-project-operations skill's `references/mcp-server-building-2026-10.md`
for the build/deploy pattern). Dispatch is Jira-gate-gated (`jira_gate.py` verdicts persist
on work_items; NOT_LINKED blocks dispatch with no bypass env).

## Pitfalls

- **`docker compose up -d acms-app` on CT122 without `ACMS_APP_IMAGE_TAG` recreates the container
  at `acms-app:local`** (compose default) — an ancient image. ALWAYS pass
  `ACMS_APP_IMAGE_TAG=<release-sha>` (and `--env-file /opt/acms/.env -f deploy/compose.yaml`) on any
  manual compose up. Verify identity immediately via `/version` git_sha.
- **Appending to `/opt/acms/.env` without checking for a trailing newline** glues the new var onto
  the previous line (this corrupted `ACMS_BRIDGE_TARGETS_JSON` into invalid JSON and 500'd every
  dispatch). Check/add the newline, then validate any JSON-valued env var parses.
- **Multi-layer nested-quote mangling (hit repeatedly 2026-10-02):** shell one-liners quoted as
  `ssh host "… python3 -c \"…\" …"` lose inner quotes by the third layer (workstation → ssh →
  ssh → python) and produce phantom SyntaxErrors with scrambled strings. For anything with
  nested quoting, base64-stage a script or scp a file, then run it — don't fight the quotes.
  (Recurring class: also bit the 2026-09-29 QGA bootstrap work.)
- **`TelemetryService.record_event` historically dropped `event_type`** (accepted the kwarg, never
  assigned it → PG NotNullViolation → 500, while SQLite tests passed). Fixed 2026-09-29; the class
  lesson stands: SQLite-passing tests do not prove PG behavior — the FK/event bugs (PR #30, PR #39)
  were both live-found on CT122.
- **Don't hardcode `.venv-acms/bin/alembic` in tests/helpers** — CI has alembic on PATH. Resolve
  with `shutil.which("alembic") or str(REPO / ".venv-acms" / "bin" / "alembic")` (the pattern now
  used in all migration/integration test helpers).
- The maintenance-mode nginx conf overlays the tracked `nginx.conf`; any `git checkout` on the VM must restore that file first or checkout is refused. `deploy/common.sh` handles this — keep the pattern if touching release tooling.
- Never run `alembic downgrade` automatically (plan §29); destructive migrations need human approval + restore testing.
- Level-2 DB restore is only authorized inside an open release transaction (`transaction.json`); standalone rollback is app-only by design.
- FastAPI + TestClient infinite-stream hang: an SSE endpoint (`while True` +
  `is_disconnected()`) never returns through TestClient and hangs the whole
  suite. Fix in ENDPOINT code, not the test: accept a bounded `max_events`
  query param; when bounded, exit the generator once the drain target is met
  without awaiting the next keepalive sleep (a sleep-before-check ordering
  still hangs when zero events match). Also gives an operational safety cap.
  ACMS SSE (2026-09-28) uses: semantic allow-list filtering, sequence-ordered
  durable-log source, `Last-Event-ID` exactly-once resume, `X-Accel-Buffering:
  no` for nginx.
- `ALTER TYPE … ADD VALUE IF NOT EXISTS` needs a real migration for any new PG
  enum value (SUPERSEDED runtime state, migration 0003, 2026-09-28) — SQLite
  passes without it, so only the PG integration test catches it. Budget
  gate lessons (PR #28): gate lives in the single authoritative dispatch
  service (`dispatch_service.py`, `POST /api/v1/dispatch/work/{id}`), not UI/
  controller layers; unknown cost is UNKNOWN, never coerced to zero;
  idempotency via `disp-<sha256>` external_task_id; `add_event` takes
  work_key/assignment_key, not item ids.
- **Shared SQLite unit DB persists across tests in one run** — state-sensitive
  suites (economics, attention, dispatch) need the `clean_db` conftest fixture
  (DELETE FROM all tables) or they see prior tests' rows. Migration-test
  ordering: tests sharing `/tmp/acms-integration-pgdata` pollute alembic_version
  — pin exact revisions (`upgrade 0007_work_budgets`, not `head`) and start
  from `downgrade base` when asserting a specific stamp.
- Live CT122 layout facts (repo path, container names, allowlist, DNS reality) → see `references/ct122-live-layout.md` before running anything on the box.

## Related skills

- `implementation-package-execution` — for zip+plan package deliveries (overlaps on STOP gates/handoffs)
- `server-rendered-ui` — the Jinja2 UI conventions ADR-0008 builds on
- `github-pr-workflow` — generic PR lifecycle (protected; org quirks live here, not there)
