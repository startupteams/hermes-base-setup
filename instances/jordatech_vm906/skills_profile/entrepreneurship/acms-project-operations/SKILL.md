---
name: acms-project-operations
description: "Operate the ACMS control plane (startupteams/acms-project-framework): branch/PR/no-self-merge discipline, safe release + rollback tooling, live CT122 quirks, Docker/Compose pitfalls."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [ACMS, deployment, rollback, docker-compose, jordan-workflow]
---

# ACMS Project Operations

ACMS (AgentifyMe Cloud Management System) is Jordan's internal AI-workforce
control plane at `startupteams/acms-project-framework`, live on Proxmox CT122
(10.0.20.122, MIAM-00135). Local clone: `~/work/acms-project-framework`
(venv `.venv-acms`, Python 3.12). This skill is the durable operating
procedure; the chronological findings log lives in `/home/jordatech/agents.md`
and current state in memory.

## Authority model (never violate)

- Feature work: branch → PR → **human review only**. Agents do NOT self-merge.
- Deployment is human-gated, BUT once a release is authorized, rollback to the
  previous known-good on failed validation is pre-authorized — do not stop and
  ask mid-rollback.
- Never hotpatch production code (fix `main` via a corrective PR later).
- Never run `alembic downgrade` automatically; destructive migrations need
  explicit human approval.

## Jordan collaboration rules (embedded from corrections)

- Questions before NEW plans, then **full autonomy** — roadblock → pivot,
  never stop.
- **Never re-gate mid-execution.** If a plan is already approved (his authored
  plan doc, his "continue work"), do not send a clarify/decision prompt; the
  2026-09-26 session's clarify timed out and he replied "What are you waiting
  on me for?" → proceed, document decisions as you go, report at the end.
- Deliverable pattern: single `.md` handoff in the work folder + chat summary;
  every PR/deployment gets a handoff doc listing requirements, validation,
  backup paths, previous known-good, and next step.

## Interrupted-session handoff format (Jordan-requested 2026-10-01)

When a session ends mid-execution or amid confusion, the handoff `.md` must
have this shape (executed example:
`~/acms-a2a-20261001/HANDOFF-20261001-ACMS-A2A-PRODUCTION-PATH.md`):

1. **§0 verified-vs-unverified, READ FIRST** — every directive asserted
   mid-session WITHOUT a visible user message goes into an explicit
   "confirm with Jordan before building on it" list, with any conflict against
   the plan doc called out. Tool-verified facts are listed separately from
   in-window assertions.
2. **Three explicit state sections:** DONE (each claim tied to its tool
   output/evidence), STARTED BUT NOT COMPLETED (exact remaining steps per
   item, enough for the next session to execute), NOT DONE AT ALL (untouched
   plan sections).
3. Then: live-state inventory, health-check commands, incidents & security
   notes, per-service rollback, ordered next-session runbook whose FIRST step
   is the human confirmations from §0.
4. Deliver the handoff to Jordan's Telegram (see `messaging/telegram-send-file`).

**Compaction-window discipline (hit live 2026-10-01):** in multi-window
sessions, assistant prose — INCLUDING self-assessments like "this session
drifted off-plan" — is NOT ground truth; only tool output is. Before acting on
or repeating such a claim, `session_search` for the underlying records; if
they don't exist, the assertion itself is the confusion artifact (the final
pre-handoff message of 2026-10-01 fabricated record names and falsely declared
the whole environment unverified). Conversely, directives that DID arrive but
were dropped from the visible transcript are marked unverified, not discarded.

## Release tooling (deploy/ in the repo)

- `deploy/release.sh [<approved-main-sha>]` — full safe transaction: preflight
  → maintenance window (nginx 503 page + app stop) → verified `pg_dump -Fc`
  (magic `PGDMP` + size floor + `pg_restore --list` + SHA-256) → SHA-tagged
  image `acms-app:<short-sha>` → `alembic upgrade head` → two-stage validation
  (`--stage app` direct under maintenance, `--stage full` via HTTPS proxy) →
  accept or **auto-rollback** via `rollback.sh --in-flight`.
- `deploy/rollback.sh` — standalone = Level 1 (app-only, never touches DB,
  never downgrades); `--in-flight` = Level 2 (checksum-guarded app+DB restore,
  live DB kept as `acms_old` forensics). DB restore is REFUSED outside an open
  transaction.
- `deploy/validate-release.sh --stage app|full --strict-build
  --expected-rev <rev> [--feature-smoke <cmd>]`.
- `deploy/smoke-test.sh [base-url]` — standalone operator smoke (not a
  release gate): backend probes run IN-CONTAINER via `compose exec -T acms-app
  python` + urllib with exact status asserts (health 200, version 200, unauth
  agents 401, Work UI 303 via proxy) and exits 1 on any failure. Do NOT
  reintroduce host-side `127.0.0.1:8000` probes — the app publishes no host
  ports (nginx is the sole ingress by design). Live-proven 12/12 exit 0 after
  the 137a008 deploy. **Also: never ship a check-script that counts failures
  but always exits 0 — smoke-test.sh had exactly that bug (FAILURES counted,
  no exit 1); scripts that gate anything must propagate failure to the exit
  code, and `exit 0` printed after a pipeline (`cmd | tail`) is `tail`'s
  status, not the script's — use `${PIPESTATUS[0]}`.**
- **Pipeline status (2026-09-26): fully routine.** Drill 3 = "Release ACCEPTED"
  end-to-end (preflight → verified backup → maintenance → build → migrate →
  ready 2s → 6/6 + 12/12 validation, exit 0); routine deploys #137a008 and
  #9545123 (v0.5.0) each ACCEPTED with zero intervention, smoke 12/12.
  **Standing deploy cadence: user message "PR N merged" → fetch new main tip →
  `bash deploy/release.sh <tip-sha>` on CT122 → report ACCEPTED + smoke.** No
  manual hop unless the on-box tree is somehow behind the transaction baseline
  (bootstrap-hop rule applies only to first-ever tooling install).
- **Slice-2 view delivered (9545123, v0.5.0):** Agent Detail page at
  `/ui/agents/{agent_id}` — read-only; identity + capability manifest
  (declared vs not-declared flags rendered honestly), assignment/execution-
  task/handoff history, background-routine inventory (REQ-014) with explicit
  "ACMS does not schedule" note, recorded-only delivery notice (shared
  `DELIVERY_STATE` constant from work_routes), and an explicit
  heartbeat-pending note (slice 3) — never fabricate liveness. Reuse
  `_base_context` + shared constants in new UI routes (a locally re-declared
  delivery string diverged from the Work UI wording and a version-empty footer
  appeared; single source of truth fixes both). Home "not yet implemented"
  list must track what the backend actually maintains.
- **Tooling-self-replacement caveat:** when a target tip CHANGES
  `deploy/release.sh` (or rollback/validate scripts), the running transaction
  checks out the new tree mid-flight while bash still reads the old script
  from disk — unproven territory. The 137a008 deploy was safe only because
  release.sh itself was byte-identical in the target. After a tooling-changing
  merge, run a same-tip drill first (re-release the accepted SHA through the
  new script) before the next real feature deploy — the drill pattern from
  2026-09-26 (drills 1–3).
- Release state lives OUTSIDE git at `/opt/acms/releases/`: `current`,
  `previous`, `history.jsonl`, `releases/<id>.json`, `transaction.json`,
  `backups/<id>.dump`. Never put secrets in release metadata.
- Feature-specific smoke hooks via `ACMS_FEATURE_SMOKE` env (plan §11).

## Live CT122 quirks (validated 2026-09-26)

- Git checkout is at `/opt/acms/repo` (NOT `/opt/acms`); `.env` at
  `/opt/acms/.env` (0600, key names only — never echo values).
- **Compose v2 container names are `acms-<service>-1`** — bare
  `docker exec acms-app` FAILS ("No such container"). Always
  `docker compose -f deploy/compose.yaml --env-file /opt/acms/.env exec -T
  <service>` (service-name agnostic). If a manual hop stage dies on a bare
  name AFTER copying the maintenance conf, the host
  `deploy/reverse-proxy/nginx.conf` is already switched —
  `git checkout -- deploy/reverse-proxy/nginx.conf` BEFORE retrying, or the
  retry double-applies maintenance content.
- No `pg_dump`/`psql` on the CT host — run inside the postgres container:
  `docker compose -f deploy/compose.yaml --env-file /opt/acms/.env exec -T
  postgres pg_dump -U acms -Fc acms`.
- No `curl` in the app image — probe with `docker exec acms-acms-app-1
  python -c "import urllib.request; ..."` on 127.0.0.1:8000.
- nginx allowlists 10.0.10.0/24 + 10.0.20.0/24 — validate via the VM's own IP
  `https://10.0.20.122` with `curl -k` (self-signed; MARION has NO home.arpa
  DNS — raw IPs everywhere).
- `/version` returns `{version, git_sha, git_sha_short, build_time}` — the
  git_sha identity check catches wrong-image states instantly. Run it after
  ANY container recreation.
- LLDAP 10.0.20.101:3890, base dc=example,dc=com; groups acms-admin/16
  (jordatech), acms-workers/17, acms-observers/18.

## Docker/Compose pitfalls (from the live drill — see references file)

- **Single-file bind mounts pin the inode**: swapping the file on disk is
  invisible to the container; HUP reload then serves stale config forever.
  nginx now uses a directory mount (`./reverse-proxy:/etc/nginx/conf.d`) and
  the maintenance template is named `*.conf.template` so the include glob
  never loads it. Never re-introduce a single-file conf mount.
- **`docker compose up -d <svc>` recreates depends_on services too** and can
  bring the app back with the default image (`acms-app:local`). Pin
  `ACMS_APP_IMAGE_TAG=<tag>` on EVERY compose up in tooling.
- **Never command-substitute `compose build`** — its stdout is the build log
  and pollutes captured variables (`invalid tag`). Send build output to
  `>&2`; compute the tag, never capture it.
- **pipefail + `grep -c` false positive**: `grep -c` exits 1 when the count
  is 0; capture the count into a variable with `|| true`, compare numerically.
- Recovery from stuck maintenance mode: `up -d --force-recreate
  reverse-proxy`, then re-pin the app image, then verify via `/version`.

## Bootstrap hop (chicken-and-egg first deploy)

The first deployment of the release tooling cannot use the tooling. Manual
hop with identical guarantees: verified backup → stop app → checkout target
SHA → build SHA-tagged image → migrate → start → validate → write release
metadata (mark `mode=manual-bootstrap`). Proven 2026-09-26 (~2 min window).

## Verification hygiene (file-tool corruption lesson)

Ground truth for any file change is `git diff` / `py_compile` / `bash -n` —
never the tool result echo. Echoes can mislead in BOTH directions (phantom
errors and phantom success; this session had mid-write corruption injecting
garbage text). For large/critical writes: verify immediately after writing,
and if corrupted, repair via a python rewrite with assertion pre-checks on
known anchor lines, then re-verify with git diff.

## PR-discipline trap (hit TWICE on 2026-09-29 — mandatory habit)

`gh pr merge --squash --delete-branch` checks the LOCAL checkout out onto
`main` when it deletes the branch. A following `git push -q` (or any commit +
push) then goes DIRECT to main — Jordan's token has admin rights, so branch
protection silently bypasses (remote prints "Bypassed rule violations" but the
push lands). Happened twice in one window (c2d68d7, 8575982; content was
green, the process was violated). **Habit: after every merge-with-delete-branch,
run `git branch --show-current` BEFORE any commit; if on main, `git switch -c
<branch> origin/main` first.** Never `git push` bare from a merge aftermath.

**PERMANENT FIXES now installed on the agent workstation (window-4, plan §D;
still keep the habit — the guard is local to this machine):**
- `~/.config/git/hooks/pre-push` via global `core.hooksPath` — REFUSES
  pushes to `main|master|production` before the network is touched
  (behavior-tested in a scratch repo). Emergency override:
  `ACMS_ALLOW_PROTECTED_PUSH=1 git push …` (audited in shell history).
  Server-side `gh pr merge` is a GitHub API operation — unaffected.
- `~/bin/gh-merge <PR#>` — wraps merge-with-delete-branch, then runs the
  mandatory branch check and auto-detaches to `origin/main` when the merge
  landed the checkout on main. PATH via `~/.bashrc`.
- Durable identity fix (least-privilege AI GitHub identity) = staged spike +
  HUMAN-SETUP file in the flight-work dir; needs Jordan's web-UI action.

## ADR-0012 completion callback (PRs #45/#46, 2026-09-29, live)

- `POST /api/v1/callbacks/execution-completion` — dedicated scoped token
  `ACMS_CALLBACK_TOKEN` (never the admin token; unset ⇒ 503 fail-closed).
  CT122 env has CALLBACK_TOKEN (hex) + `ACMS_CALLBACK_BASE_URL=https://10.0.20.122`
  in /opt/acms/.env; compose passthroughs merged (PR #47, which also added
  ACMS_JIRA_* + ACMS_GITHUB_ECONOMICS_TOKEN passthroughs).
- Identity binding: task must belong to the claimed agent (mismatch → 403 +
  durable EXECUTION_CALLBACK_REJECTED audit; unknown task → 404 + audit).
  Duplicate/late → idempotent `already_terminal`. Success → no Attention item.
- **dispatch_service now PRE-creates the execution task before the bridge
  call**; the task id travels in the instruction (COMPLETION PROTOCOL block,
  gated on ACMS_CALLBACK_BASE_URL); `external_task_id` = the REAL A2A run id.
  The dispatch idempotency ledger MOVED to the EXECUTION_DISPATCHED event
  metadata (dedupe_key → task_id) — code querying `external_task_id ==
  "disp-<key>"` is stale.
- **Runtime-driven watcher is now the PRIMARY path (window-4, PR #49, prod
  3679067):** `acms/run_watcher.py` schedules a bounded in-process watcher at
  dispatch (RunWatchRegistry, idempotent per task_id) that observes the bridge
  run and delivers the EXACT authenticated callback on terminal state — model
  compliance NOT required. Retries 0/10/30/60s on transient failure; permanent
  rejections (403/404/503) stop immediately; watch lifetime bounded (2h
  default, RUN_WATCH_EXPIRED audit); reconcile remains fallback. Settings:
  ACMS_CALLBACK_WATCH_ENABLED (default true), ACMS_CALLBACK_SELF_URL (default
  in-container loopback :8000 — nginx 403s compose-network sources),
  ACMS_CALLBACK_WATCH_POLL_SECONDS/MAX_SECONDS. **CRITICAL pitfall: the
  watcher is an asyncio task in the APP process — dispatch MUST go through
  the API route (`POST /api/v1/dispatch/work/{id}`). Dispatching from a
  one-shot script process schedules the watcher into a process that exits →
  nothing watches (hit live: first proof attempt silently fell back to
  reconcile).**
- **Live callback-before-reconcile proof (ACMS-WORK-000007, 2026-09-29):**
  API-route dispatch → worker explicitly instructed NOT to call back →
  EXECUTION_COMPLETED "Completion callback: task … → SUCCEEDED" delivered by
  the watcher (+50s) with EXECUTION_RECONCILED ABSENT (300s reconcile window
  not elapsed) → task SUCCEEDED + session CLOSED, zero manual close. Tests:
  tests/test_run_watcher.py (7). Hermes api-server still has no
  run-completion webhook — the ACMS-side watcher is what closes that gap.
- **Window-3 proof pattern (superseded as the completion authority, kept for
  reconcile-fallback behavior):** dispatch → session auto-open → Hermes run
  completes (LiteLLM SpendLogs row = cost-of-record) → worker GLM IGNORED the
  in-instruction completion protocol → the telemetry-scheduler reconcile sweep
  closed the task from bridge run status + the orphaned OPEN session (both
  orderings: task-then-session and session-already-orphaned) → zero manual
  close.
- Live endpoint probes from the CT HOST work via curl; from INSIDE the app
  container nginx 403s (container-network source not allowlisted) — same
  rule as all CT122 API probing.

## Phase B data layer (2026-10-01, prod 11a39de, alembic 0014→0016)

- **Human UIDs:** `ACMS-WORK-######-YYYYMMDD_HHMMSS` / `ACMS-ARTIFACT-######-…`
  (`acms/uid_keys.py`). Work UIDs share the REQ-052 `work_key` counter (short
  key + long UID = same row number — telemetry session-alignment untouched);
  artifacts have their own `artifact_uid` counter. Allocation = durable
  `acms_key_counters` atomic `UPDATE…RETURNING` (never COUNT(*), proven
  collision-free at 20 parallel on PG). Migration 0014 backfill semantics:
  work rows WITH a `work_key` KEEP that number; keyless rows continue after
  the max; artifacts numbered 1..N oldest-first; counters seeded past max so
  post-migration allocation never collides.
- **Canonical work handoff (§9):** `acms/canonical_handoff.py` — exactly ONE
  `work_handoff` artifact per terminal Work Item; an agent-provided handoff
  becomes the body (NEVER overwritten — §47 stop condition), else a fallback
  synthesized from durable data (scope/sessions/model/tokens/artifacts/Jira).
  Hooked into BOTH completion authorities (ADR-0012 callback AND the
  reconciler sweep); idempotent; swallow-and-audit (generation must never
  break completion).
- **Route-mount map — check `/openapi.json` FIRST on any 404** (re-earned
  twice 2026-10-01): `a2a_api` AND `search_api` routers mount at ROOT —
  `/artifacts[/{id}][/content]`, `/projects`, `/products`, `/repositories`,
  `/repository-metrics/refresh`, `/products/{id}/slop[-history]`,
  `/model-policy/...`, `/inbox/...`, `/execution/...`, `/power/summary`,
  `/usage/summary`, `/search`. There is NO `/api/v1/artifacts`. `work_api` =
  `/api/v1/work/...`; agents = `/api/v1/agents...`.
- **Jira REST v3 comments REQUIRE ADF document bodies** — a plain string
  400s with "Comment body is not valid!" (hit live posting the STNA-87
  correction note). `JiraClient._markdown_to_adf` converts headings / bullets
  / fenced code / paragraphs; ALL lifecycle comments ride it. Never POST
  `{"body": "<string>"}` to `/rest/api/3/issue/*/comment`.
- **STNA-86 template fidelity:** `acms/jira_template.py` — fetch the live
  template issue, extract its sections, fail the candidate when required
  sections are absent; documented REQUIRED_SECTION_FLOOR applies when the
  source fetch fails. Future authorized AI-created tickets must CLONE STNA-86
  and pass this validator (STNA-87 was the loose clone; its correction note
  = Jira comment 10893, links the canonical artifact by UID).
- **Slop/repositories (§15/§16):** `acms/slop_metrics.py` — `repositories`
  (unique owner+repo), product/project link tables (unique pairs),
  `repository_metric_snapshot` timeseries. LOC/ADR collected via the **GitHub
  API (trees + contents)** — the app container has NO git binary, so a
  git-clone collector cannot run in prod. True Slop = LOC / human-written
  ADRs; Precision = LOC / total ADRs; human-ADR v1 = acceptance marker in the
  ADR body (approved-by/accepted-by/human-decision); counts stored separately
  for later refinement; unique-source dedupe in product summaries (a repo
  linked to N projects under one product counts ONCE). Collector file cap
  400 (the first real repo measured 221 eligible files and hit the original
  60). API failures → error snapshot, never a crash.
- **Facility power (§17):** ACMS ingests `GET /api/v1/facility/power` from
  Server Manager (:8300, svc-acms token, scope `usage:read`) via
  `acms/power_ingest.py` → `power_cost_snapshot` (migration 0016). NEVER put
  Emporia credentials or the llmmanager DSN into ACMS — LLM Manager stays the
  collector/provider. Stale → NULL + STALE + timestamp (never 0); TOTAL
  MARION_IA_USA withheld with `incomplete_reason` when any channel is stale.
  `/power/summary?refresh=1` ingests now; `/usage/summary?hours=` rolls up
  `cost_attribution` (cloud = ACTUAL, local = ESTIMATE-labeled, never
  fabricated, never exceeds measured energy).
- **Test-infra traps (new, hit live):**
  - Tests calling ROUTE HANDLERS directly must NOT combine the
    `get_session()` async-generator with an explicit `db.close()` — the
    generator's context-manager close + the explicit close double-close
    mid-transaction → `IllegalStateChangeError` + phantom pending INSERTs (a
    bare `ProductRecord()` insert surfaces at generator cleanup and looks
    like unrelated corruption). Own the session directly:
    `from acms.db import SessionLocal; db = SessionLocal()`.
  - New models modules MUST be imported in `tests/conftest.py` (schema is
    created at session start, BEFORE the test imports the module — symptom:
    "no such table: repositories") AND in the parity test's `_collect()`.
  - Enum seed values are lowercase (`trust_class="internal"`) — the Pydantic
    response model rejects `"INTERNAL"`.
  - **Cross-venv PATH pollution:** after sourcing the LLM Manager `.venv-sm`,
    its `alembic` shadows the ACMS one and the PG-parity chain tests fail
    spuriously. Rerun clean:
    `env -i HOME=$HOME PATH=/usr/bin:/bin:/usr/local/bin ACMS_ADMIN_TOKEN=test-token .venv-acms/bin/python -m pytest -q`.
- Detailed session specifics (PR list, live §36–§40 proofs, release chain):
  `references/phase-b-data-layer-2026-10-01.md`.

## Pointers

- `references/live-drill-2026-09-26.md` — bug-by-bug drill breakdown, exact
  commands, recovery timeline.
- `references/hermes-harness-live-tests-2026-09.md` — Hermes 0.17.0 live
  control-mapping results (pause/resume unsupported, steer/interrupt verified),
  scratch-profile setup recipe, bridge-to-ACMS wiring.
- `references/hermes-worker-bringup.md` — the full worker-runtime bring-up recipe
  (VM clone → Hermes venv install via qga → LLM gateway wiring incl. context caps →
  api-server platform config shape → systemd unit → verification + traps) as
  executed on acms-worker-001.
- `references/worker-fleet-provisioning-2026-10-01.md` — MULTI-worker fleet
  provisioning from template 121 (clone → offline cross-node storage-migrate →
  re-identify → pip bootstrap → ACMS register + bridge targets), incl. the
  template's baked-in static netplan (.203 IP collision ×4) + NO-Hermes-runtime
  facts, task-polling correctness, naming convention
  `acms-hermes-worker-uid-###`, and the no-rename-endpoint registration trap.
- `references/ip-collision-10-0-20-203-case-2026-09-29.md` — the template-clone
  impostor-IP case (symptoms, ARP diagnosis, VM108 renumber, generalization).
- Repo docs: `deploy/README.md` (operator runbook), ADR-0009 + ADR-0010 (both
  Accepted 2026-09-26/27), `docs/HARNESS_CONTROL_MAPPING.md`, `SPRINT.md`
  (current slices), handoffs under `docs/handoffs/`.
- `references/window5-jira-gate-fleet-ui-2026-09-30.md` — window-5 session
  detail: fleet one-card root-cause chain, Jira kickoff-gate live facts,
  Settings-fixture anti-pattern, bootstrap honesty contract, live-UI probe
  recipes, open items.
- `references/hermes-019-worker-api-surface-2026-10-01.md` — the VERIFIED
  Hermes 0.19.0 worker api-server surface: /v1/capabilities, run lifecycle
  (run_id = A2A ACK; statuses TTL'd), run-events SSE payload shapes,
  /health/detailed + /api/sessions fields (heartbeat sources), and the
  model_routes caveat (unmatched request-model aliases are silently ignored —
  worker config owns the mapping).

## Test-suite hygiene (conftest patterns — keep using these)

- **Migration-vs-model drift is invisible to SQLite unit tests** — create_all
  builds from MODELS, so a migration that creates a differently-named column
  (0008 created `commit_shas`, model/ingest expected `commit_shas_json`;
  every economics write 500'd on prod) passes the whole suite.
  `tests/test_migration_model_parity.py` (window-4, PR #50) upgrades a real
  PG (pgserver) through the FULL chain and diffs EVERY ORM-mapped table's
  column set against the migrated schema. **When adding a new models module,
  add its import to that test's `_collect()`** or the new tables escape the
  parity check. Run `tests/test_economics_migration.py`-style pinned-revision
  chain tests for every migration regardless.

- **SQLite batch-mode migration pitfalls (0012 class, hit live 2026-10-01):**
  (a) `batch.add_column` with an inline `ForeignKey(...)` fails on SQLite with
  `ValueError: Constraint must have a name` — add the column PLAIN, then add
  the named FK via `op.create_foreign_key("fk_...", ...)` gated on
  `op.get_bind().dialect.name != "sqlite"` (SQLite FK enforcement rides the
  ORM layer / next full head). (b) A column added with `index=True` inside a
  batch creates `ix_<table>_<col>` — the DOWNGRADE must `op.drop_index` it
  BEFORE the batch column drops: batch recreates ALL reflected indexes and a
  dropped-column reference aborts with `no such column: ...`. (c) SQLite has
  no `ALTER DROP CONSTRAINT` — gate downgrade FK drops on dialect too.
  Verify with a full `upgrade head` + `downgrade base` cycle on SQLite BEFORE
  releasing; the release transaction otherwise aborts mid-flight (this cost 5
  auto-rollback release attempts on 2026-10-01 before the chain ran clean).

- **The shared SQLite unit DB persists rows across tests in one pytest run** —
  any suite asserting event/row COUNTS must use the `clean_db` fixture
  (conftest DELETEs all tables, FK-off during wipe). Symptom when missing:
  count assertions see prior tests' rows (`assert 2 == 1`-style failures that
  pass under `-x` in isolation but fail in full runs).
- `get_settings()` is lru_cached — env-var fixtures must
  `get_settings.cache_clear()` on entry AND exit (see
  test_work_creation_guard.py pattern).
- Endpoint tests: sync `TestClient(app)` + async dependency override
  (`app.dependency_overrides[get_session] = async gen`), NOT
  httpx.ASGITransport with a sync client (fails:
  "ASGITransport object has no attribute handle_request").
- Reconciler/scheduler tests monkeypatch `acms.bridge.get_bridge_for_agent`
  (the attribute resolved at call time), not the scheduler module.
- asyncio_mode=auto (pyproject) — plain `async def test_` works; `db` fixture
  pattern: `async for session in get_session(): yield session`.

- **Settings-attribute-mutation anti-pattern (hit repeatedly 2026-09-30, silently no-ops):** mutating a
  cached Settings instance's attributes then `get_settings.cache_clear()` DISCARDS the mutation (cache_clear
  rebuilds from env). Fixtures must set **env vars** (`monkeypatch.setenv("ACMS_JIRA_AI_ACCOUNT_ID", …)`) and
  `cache_clear()` on entry AND exit — see test_jira_gate.py `gate_env`. Also: patching a module-level
  `from .x import Y` binding (e.g. `acms.jira_api.JiraClient`) requires patching BOTH the source module and
  each importing module, or call sites resolve the original.

- **Async expire-on-commit lazy-load crash (prod-verified 2026-10-01, 4 release
  auto-rollbacks):** any code that loads ORM rows, then `commit()`s inside a
  per-row loop (via a service call like `ingest_heartbeat`), and afterwards
  touches ANY attribute of the pre-loaded rows fires a SYNC lazy load in async
  context → `telemetry scheduler tick failed` traceback EVERY tick. The
  release transaction's `app_log_error_scan` (grep `Traceback` in last 100
  compose-log lines) then fails validation and auto-rollback fires. Fix =
  snapshot plain values (ids/trust_class) BEFORE any commit, end the read
  transaction, then one fresh session per unit of work. Corollary: new
  background loops must be smoke-tested against a REAL PG (or by running the
  built image against the migrated DB) before release — the SQLite unit suite
  can't see this class. Debugging recipe when release validation fails on
  `app logs clean` and docker logs rotated with the rolled-back container:
  `docker compose stop acms-app` + `ACMS_APP_IMAGE_TAG=<new> compose up -d
  acms-app` against the CURRENT (migrated) DB, `sleep 8`, then
  `docker logs acms-acms-app-1 | grep -A20 Traceback` — reproduces the exact
  prod traceback safely (DB stays migrated; restore app after).

- **Jira kickoff gate (window-5, LIVE — never bypass):** `dispatch_service` gates EVERY dispatch path on
  Jira eligibility BEFORE budget checks (`acms/jira_gate.py`). Verdicts persist on work_items: ELIGIBLE /
  NOT_LINKED / NOT_READY / ASSIGNEE_MISMATCH / LOCAL_HOLD / JIRA_UNKNOWN. Match the dedicated AI account by
  immutable **accountId** (`ACMS_JIRA_AI_ACCOUNT_ID` = 712020:520fb263-ef0f-425c-a0be-14e9d258917e — the
  integration's own service account IS startupteamscompany@gmail.com); never display name or email
  visibility. Live Jira re-read before decisions; read failure → UNKNOWN → fail-closed for NEW dispatch.
  Drafts save unlinked but stay visibly non-executable. Persistent PAUSE/STOP holds
  (`work_runtime_holds`, migration 0010) survive restarts AND polls; only an explicit operator clear
  removes them; fan-out via Server Manager desired-state (requested ≠ acknowledged tracked honestly).
- **One reconciliation service (window-5, LIVE):** ALL triggers (manual Check-Jira-now POST
  `/api/v1/jira/reconcile`, UI `/ui/jira/check-now`, durable in-process scheduler ≤24h UTC w/ catch-up +
  overdue events) converge on `jira_reconcile.start_reconciliation_run` — durable lease coalesces duplicate
  clicks into one run; paginated candidate scan PLUS direct re-fetch of every linked issue by immutable id
  (withdrawal detection); run ledger counts requested-vs-acknowledged. §13.2 mapping lives in
  `jira_reconcile.py` (In Progress WITHOUT proven ready generation → Attention, never infer authorization;
  stopped generations never restart on re-polled identical snapshots).
- **Fine-grained PATs CANNOT create GitHub repositories** (HTTP 403 orgs/{org}/repos — platform limitation,
  not a scope gap). The product-bootstrap repo adapter (`acms/repo_adapter.py`) fails with
  `repo-create-forbidden` + exact human-gate guidance and stays resumable (reuse-if-exists; idempotent
  per-file docs push). Human creates the private repo in the web UI, then the SAME request completes.
- **Custom session-cookie auth (ACMS UI):** HMAC token = base64url(JSON {"u","r","exp"}) + "." +
  b64url(hmac-sha256(secret)); cookie `acms_session`; role lowercase `administrator`. In-container live-UI
  probes mint a token in-process from `ACMS_SESSION_SECRET` (never printed) — used for route/200 checks
  without LDAP creds. Docker `docker cp` moves files INTO the acms-app container (compose exec can't see CT
  /tmp).
- **Window-5 UI/data surfaces:** `/ui/work/board` (5 columns; cards = actionable facts only), work-detail
  PR panel over economics pr_outcomes (MERGED renders "merged ≠ accepted"), `/ui/products` +
  `/ui/products/new` idea-review screen (draft/unvalidated stays draft; assumptions never become accepted
  requirements), `/ui/projects/{id}` tabs, `/ui/usage` (cost-per-accepted NULL when zero, never fabricated;
  work/agent/model/date filters), `execution_sessions.model_id` captured at open from
  ACMS_WORKER_MODEL_PROFILE. Jinja gotcha: `col.items` on a dict resolves to the dict's `.items()` METHOD —
  name board columns `cards` to avoid `len()` type errors.

When a plan authorizes an integration but the credential requires web-UI
creation (Atlassian API tokens, GitHub fine-grained PATs — NO REST create
path exists for either):
1. Search session archives (session_search across queries) + Honcho memory
   for the credential BEFORE declaring it missing — but NEVER reuse unrelated
   credentials found in context (wrong-boundary facts stay facts).
2. Do NOT ask the human to re-paste passwords into chat (plan §1.2 pattern).
3. Write an exact `HUMAN-SETUP-*.md` (step-by-step UI path + two install
   options: human does it via ssh, or pastes into chat for staging into
   /opt/acms/.env without echoing) + merge the compose passthrough so
   activation = human adds env vars + container recreate.
4. Continue all other work — never block the sprint on the credential.
5. **ACTIVATION TRAP (hit live 2026-09-29):** a container ALREADY RUNNING
   when the human installs the token keeps its OLD (empty) env — compose
   `environment:` passthroughs resolve at container CREATE time, not start.
   Symptom: host-side `.env` line non-empty, in-container value empty
   string. Fix: recreate with the PINNED current image tag —
   `ACMS_APP_IMAGE_TAG=<current-sha> docker compose ... up -d --force-recreate acms-app`
   — then re-verify in-container non-emptiness. Also check env hygiene
   WITHOUT printing values (CR endings, quotes, trailing whitespace all
   break compose interpolation): awk length + pattern checks on the .env
   file only.
6. Safe live-verification recipe (Jira/any bearer API): run the probe
   script INSIDE the acms-app container via base64-staged stdin
   (`echo <b64> | base64 -d | docker compose exec -T acms-app python3 -`),
   reading the token from `os.environ` — the secret never appears in any
   command line, log, or handoff. Report only: status codes, counts,
   identity booleans (email matches expected), lengths.
## Combined slice 3+4 state (deployed 2026-09-27, v0.6.0 @ 85f3c92)
  policy); **ADR-0010 Accepted** — heartbeat 60s / STALE 300s / reconcile
  3600s / fleet 86400s / alignment grace 120s / context warnings 70-85-95,
  all config-backed via `ACMS_*` settings (settings.py gained the fields).
- Human-readable keys `ACMS-WORK-000001` / `ACMS-ASG-000001` via the
  `acms_key_counters` transactional counter table — never row counts, never
  reused; allocated in `create_work_item` / `assign_primary`.
- State dimensions stay separate (plan §5): connectivity is ACMS-derived
  (UNKNOWN/HEALTHY/STALE/UNREACHABLE from contact recency), `agent_running`
  is harness-reported tri-state — the UI shows both as independent facts.
- Heartbeat = complete snapshot (`acms-heartbeat-v1`), unknown fields rejected
  by the Pydantic model; semantic events only on material change (never
  per-heartbeat spam); event sequences allocated via the same counter table.
- Time-dependent tests: inject `now_fn` into TelemetryScheduler; watch for
  tz-naive vs tz-aware datetimes when mixing `datetime.now(timezone.utc)` with
  DB-loaded values (replace(tzinfo=utc) guard in the stale delta).
- **Next steps logged in agents.md:** wire `ACMS_BRIDGE_TARGETS_JSON` into
  CT122 env + dispatch/control buttons in the UI; slices 5–9 per master plan.

## Recovery guardrails (PRs #30–#32, 2026-09-29, prod 6f772aa)

- **PR #30 live bug (budget events FK):** `budget_service` wrote
  `agent_id=""` on BUDGET_SET/OVERRIDE/THRESHOLD_CROSSED →
  `agent_events_agent_id_fkey` violation on prod PG; SQLite unit tests DON'T
  enforce FKs so the whole suite passed while prod 500'd. Work-scoped events
  now leave `agent_id` NULL. **Lesson: SQLite-with-FKs-off is a silent prod
  gap class — when a unit DB is SQLite, grep for sentinel `""` foreign-key
  values before trusting green tests.** Candidate FUTURE_WORK: FK pragma in
  the unit engine.
- **C4 (PR #32):** `AGENT_RUNNING_WITHOUT_ASSIGNMENT` = informational, emitted
  ONCE per state entry (scheduler in-memory dedupe dict, reset on state exit),
  never per tick; severity `info`; NO auto-remediation (human direction:
  never auto-stop). Attention/SSE allowlists both new event types.
- **C5:** `acms/reassignment_guard.py` — max 3 Executive reassignments per
  work item, counted from durable `REASSIGNMENT_RECORDED` audit events (no
  second mutable counter table); identical retry (`changed_dimension=none`)
  → `REASSIGNMENT_REFUSED` (does NOT consume budget — the refusal must not
  use the same event type or the count is poisoned); 4th real attempt →
  `REASSIGNMENT_LIMIT_REACHED` (Attention high) and auto-reassignment stops.
  Every attempt must declare changed_dimension. The subjective "<60%
  instruction match" rule is deliberately NOT automated.
- **Real dispatch PROVEN 2026-09-29** (ACMS-WORK-000002 → VM124, budget-gated,
  echo verified via bridge messages API, $0 local, 12,385/84 tokens in
  LiteLLM SpendLogs; retry=duplicate; attention 0; SSE dispatched). Loop:
  create work → assign worker → `PUT /api/v1/budgets/work/{id}` →
  `POST /api/v1/dispatch/work/{id}` → verify via bridge →
  `POST /api/v1/work/tasks/{id}/finish?new_status=SUCCEEDED` (only
  SUCCEEDED/FAILED/CANCELLED accepted) → close assignment → PATCH item to
  completed. Bridge targets are IP-pinned in `ACMS_BRIDGE_TARGETS_JSON`
  (`/opt/acms/.env`, compose passthrough exists); DNS indirection = future work.
  **IP-collision trap:** see
  `references/ip-collision-10-0-20-203-case-2026-09-29.md` — a template-clone
  impostor (VM108) squatted on the worker's `.203` and bridge traffic hit the
  wrong guest while every app-level check passed; diagnose at the ARP/MAC
  layer before touching config.
- **ACMS recovery policy counterpart:** ARM reconciler now max 5 attempts
  (env `ARM_RECONCILE_MAX_ATTEMPTS`, prod unset → 5 active) with
  failure_class/recovery_method/attempt audited per attempt and
  `strategy_next: human_attention` at exhaustion — see the LLM Manager skill.

## Agent-state ownership + architecture recs (PRs #33–#34, 2026-09-29, in prod 6f772aa)

- **Work lifecycle default (PR #31, ADR-0011 Proposed — awaiting Jordan's
  acceptance):** Work Item = ONE measurable goal; a goal may span multiple
  execution sessions (crash/context-rotation/retry does NOT spawn a new Work
  Item); the NEXT measurable goal = the next CHILD Work Item linked to the
  same Feature/Program parent (smallest-safe parent/child representation;
  Executive Agent may propose the next child only within the approved parent
  scope, provenance recorded — no silent scope expansion). Review findings
  classify BLOCKING / REQUIRED / OPTIONAL; OPTIONAL findings never block
  completion and review never creates new product scope.
- **Ownership contract (human direction, durable):** Server Manager/ARM owns
  agent state-sync health (`last_state_commit_sha`/`state_sync_health`); ACMS
  may consume a summarized health signal only. Do NOT build ACMS-side
  git/cloud-backup sync state or UI implying ACMS authorship — that duplicates
  ARM authority. Existing ACMS copies stay read-only until a
  compatibility/migration path is proven (never delete data first).
- **Architecture recommendations awaiting Jordan's sign-off** (docs under
  `docs/architecture/` in the ACMS repo, PR #34): Jira = **Option D** (Jira
  parents authoritative for human planning; ACMS AI micro-work beneath;
  one-way summary/progress sync upward; never mutate Jira without explicit
  authorization); Speed-to-Lead = separate product repo + **dedicated External
  Agent Gateway** (a service boundary, not a bare firewall) +
  `agentifyme-external-agent-base` PROPOSED but NOT created (repo creation
  needs Jordan's OK); tenant-isolation threat/test plan drafted (no prod
  pentest); design memory = Git/Markdown canonical, vector index only as a
  rebuildable retrieval layer (never canonical storage); portal discovery
  found the REAL prototype repo `startupteams/agentifyme-speed-to-lead`
  (prototype + P0 15/15 + UX docs; High Point demo pending Utkarsh) — no UI
  redesign until Jordan reviews the discovery doc.

## JINT-001 — Server Manager integration (live 2026-09-27, prod e1cd84ed, alembic 0005)

- `acms/server_manager_client.py` (urllib, contract pinned Server Manager API 1.0.0) + `/api/v1/server-manager` routes: POST /agents (persistent identity reservation + `provisioning_requests` row with authority provenance per REV4 §14: human_in_acms | human_in_server_manager | pre-authorized_sprint_execution_context), POST /requests/{id}/provision (calls SM; ownership refusals → 403, SM errors → 502), GET /requests/{id} (correlates live job/runtime state). Migrations `0004_provisioning_requests`, `0005_prov_attempt`.
- **State honesty (live-found bug):** the provision route MUST reflect the returned SM job state — SM job FAILED → request FAILED with the error, DONE → LIVE + runtime_id correlation via `list_runtimes`, else PROVISIONING. Unconditionally writing PROVISIONING stuck a failed request permanently (blocking both retry and truth). ACMS prod now runs this fix.
- **Retry semantics (live-found):** same request_id replays the original (failed) SM job forever; deriving `|retry:N` by counting markers recomputes N=1 forever. Real fix = monotonic `attempt` column (migration 0005, default 1, increment per retry → `request_id|retry:N`).
- **create_runtime timeout:** provisioning is synchronous server-side (clone+boot = minutes); the 30 s client default timed out while the job completed — ACMS then recorded FAILED for a LIVE runtime. `create_runtime` now uses timeout=600; other calls stay at the default.
- **Honest-state correctness chained into worker bootstrap:** the request that hit the timeout recorded FAILED while VM 124 was actually LIVE — corrected manually via SQL (state='LIVE', runtime_id, job_id). When reconciling such rows, pull truth from the SM side (`GET /api/v1/agent-runtimes?acms_agent_id=`), never assume.
- **Pitfalls found live:**
  - **compose `environment:` enumerates explicitly** — new ACMS_* settings NEVER reach the container from `--env-file` alone; add passthrough lines to `deploy/compose.yaml` (live symptom: "Server Manager integration not configured" 503 despite env in /opt/acms/.env). Applied to `ACMS_SERVER_MANAGER_*` AND `ACMS_BRIDGE_TARGETS_JSON` — grep compose when adding any setting.
  - **`env_prefix="ACMS_"`** — Settings fields map to `ACMS_<FIELD>` env vars; naming them `SERVER_MANAGER_*` (no prefix) silently leaves settings empty. Check the prefix before writing env lines.
  - **CT122 nginx 403s 127.0.0.1-originated API calls from inside the CT** (allowlist covers the CT IP, not loopback) — call ACMS APIs via `https://10.0.20.122`, not `https://127.0.0.1`.
  - **ACMS repo has GitHub issues DISABLED** — reference `ACMS-REQ-###` in commit messages instead of creating issues (issue creation fails with "has disabled issues").
  - **Bridge chat shape:** `/api/sessions/{sid}/chat` expects `{"message": str}`; the `{"messages": [...]}` array shape 400s with `missing_message` (steer + send_work session-bound path both fixed, PRs #20/#21).

## ACMS agent registration + fleet wiring (live facts 2026-10-01)

- **Register agents:** `POST /api/v1/agents/register` — `/api/v1/agents` (no
  /register) is GET-only and 405s on POST. Body: `{external_registration_id
  ("arm-<name>"), display_name, trust_class: "internal", harness: "hermes",
  bridge_version, protocol_version: "1"}` → 201 + agent_id. Bearer =
  ACMS_ADMIN_TOKEN from /opt/acms/.env. **There is NO display-name PATCH
  endpoint** (`PATCH /api/v1/agents/{id}` → 404, hit live) — set the FINAL
  name at registration time; renames need re-registration or a new endpoint.
  Jordan naming convention (2026-10-01): `acms-hermes-worker-uid-###` (harness
  in the middle; the UID is THE durable identifier).
- **Bridge endpoint resolution** (`acms/bridge_discovery.py`): SM
  `/api/v1/agent-runtimes` (bearer ACMS_SERVER_MANAGER_TOKEN) is tried FIRST
  and is authoritative for identity/state (runtime_id ↔ acms_agent_id,
  node/vmid, state_sync_health), but its `bridge_base_url` was NULL in prod —
  URL+key come from the manual fallback `ACMS_BRIDGE_TARGETS_JSON`
  (agent_id-keyed list in /opt/acms/.env). New workers = append a target entry
  + **container recreate** (compose env resolves at create time; restart is
  not enough). Dispatch sends the resolved `model` on `/v1/runs` (new-run
  path); the worker honors it only for aliases in its own profile config —
  unmatched aliases are silently ignored (worker config owns the mapping).
- **Switching a worker's effective model live (proven on VM124):** edit the
  worker profile config (append the alias to custom_providers[0].models + set
  `model.default`), keep a dated `.bak`, `systemctl restart hermes-bridge`,
  then verify `/health` (`{"status":"ok"}`) + `/health/detailed` readiness —
  the model config check runs at startup. Flash-Next resolves LIVE through
  LLM Manager (`/v1/chat/completions` → real local vLLM fingerprint).

## Worker runtime facts (acms-worker-001, provisioned via the full chain 2026-09-27)

- VM 124 on miam00111 @ 10.0.20.203 (DHCP), runtime_id 56c1b849-5407-452b-b326-b6e3ff7000e1, ACMS agent 22ac1b19-b7c9-4fd8-bf70-0b8e654ee026, cloned from template VM 121 (VM103-lineage Ubuntu 24.04 + legacy st-agentd; hostname carries `miam00111-vllm-vm103` lineage — cosmetic).
- §8 ownership marker lives in the VM's PVE `description` field (full JSON: server_runtime_id / acms_agent_id / request_id / created_by_agent_runtime_manager=true / template_source) — written at provision time by ARM; the destroy path refuses without it.
- Worker Hermes: venv `/opt/hermes-venv` (hermes-agent via pip; aiohttp REQUIRED for the api-server platform), profile `acms-worker-001`, bridge = `hermes-bridge.service` running `hermes gateway run --profile acms-worker-001 --replace` (gateway run takes NO --host/--port — they go in the profile config under `platforms.api_server.extra.{host,port,key}`; top-level host/port keys are IGNORED, defaults to loopback:8642). `API_SERVER_KEY` also required as env (both extra.key and the env var).
- Worker LLM path: profile provider `llm-manager` → `http://10.0.20.108:8080/v1` (nginx plain-LAN surface on VM114 — self-signed TLS on :443 breaks OpenAI clients; bearer key is the auth layer on the private network). LiteLLM virtual key `agent_key_acms_worker_001` (0600 on VM114). Profile model caps: `model.context_length: 70000`, `max_tokens: 8192`, `tools.tool_search.enabled: "on"` (same playbook as the 2026-09-20 qwen3.8 70K incident — otherwise Hermes requests context-minus-prompt output tokens and litellm 400s ContextWindowExceeded).
- nginx backups must NEVER live in `sites-enabled/` (duplicate default_server breaks reload) — `/etc/nginx/backups/`. The VM114 sites-enabled file has DIVERGED from sites-available (enabled = live v2 TLS config).
- Worker bootstrap runs via node qga (`qm guest exec 124 -- bash -c ...`): stage scripts as base64 files, run under nohup for long installs (qga channel wedges on long execs).

## Worker Hermes state sync (installed 2026-09-28, REV4 §10A)

- Branch `agent/22ac1b19` on startupteams/hermes-base-setup (child of
  feat/rev4-hermes-state-backup `df75cc8` + hygiene commit: the rev4 branch
  whitelist `!profiles/**` WOULD have committed the worker's `config.yaml`
  which carries the bridge API key — profiles/.gitignore now excludes
  config.yaml/.env/db/bin/cache/locks per profile. Never trust the rev4
  whitelist alone for worker profiles).
- Deploy key (repo-scoped, read-write, id 164639272) + mirror repo at
  `/home/hermes/hermes-state-backup`; script `/usr/local/bin/hermes-state-sync`
  (root-owned, runs as hermes); systemd `hermes-state-sync.timer` (hourly,
  Persistent, RandomizedDelaySec=300).
- Sync behavior: mirror sessions/memories/skills/state (+small workspace);
  **`request_dump_*` files are explicitly deleted from the mirror** — they
  contain masked bearer keys (`sk-...QPjA` form) + full prompts, and the
  mask slips past the secret regex. Fail-closed scan patterns include
  `LLM_MANAGER_AGENT_KEY=`/`API_SERVER_KEY=`; probe file → exit 1, nothing
  committed (verified live).
- Post-sync verification is MANDATORY: grep the pushed blobs for auth values
  (the scan runs pre-commit, but the leak found here was only caught by
  re-reading the pushed files). Also fetch `git pull --rebase` (not
  `--rebase=local`, unsupported on this git), and set repo-local git identity
  or commits fail "Author identity unknown".
- ARM records `last_state_commit_sha`/`state_sync_health` via
  `POST :8300/api/v1/agent-runtimes/{id}/state-sync` (health vocab: PENDING |
  SYNCING | VERIFIED | STALE | FAILED).

## ACMS release via SSH (simpler than qga — CT122 has sshd)

- `ssh root@10.0.20.122` works (unlike VM114/VM124 which are qga-only).
  Loop: `cd /opt/acms/repo && git fetch origin main` →
  `nohup bash deploy/release.sh <main-tip-sha> > /tmp/release-<sha>.log 2>&1 &`
  → poll `tail` until `Release ACCEPTED: <id> (acms-app:<sha>, alembic <rev>)`
  → `bash deploy/smoke-test.sh https://10.0.20.122` (exit 0) →
  `curl -sk https://10.0.20.122/version` shows the new sha.
- Keep prod == origin/main: after EVERY docs-only merge, run the release too
  (cheap, keeps /version identity checks meaningful).
- **CI note (updated 2026-09-30):** ACMS main now HAS branch protection with 3 required checks (syntax / tests / secret-scan) — PRs sit `mergeStateStatus: BLOCKED` until green, `CLEAN` when mergeable (poll `gh pr view N --json mergeStateStatus -q .mergeStateStatus`; `gh-merge` refuses BLOCKED). Still run the full suite
  (`.venv-acms/bin/python -m pytest tests/ -q --ignore=tests/test_postgres_integration.py`)
  before merging. The pgserver integration test fails on this workstation even
  on clean main (env gap, not a regression).
- conftest must register EVERY models module (work/telemetry/SM/memory) or
  create_all misses tables in unit tests — missing-table errors
  (`acms_key_counters`, `context_packages`) are both this bug.
- ACMS has no PDU credentials; power flows LLM Manager → Server Manager → PDU
  (`/api/v1/pdu/*` on VM114:8300; dry-run plans; actuation env-gated).

## Runtime lifecycle API + Memory/Session Offload (both live 2026-09-28)

- Runtime (Phase 3): `GET /api/v1/fleet/agents/{id}/runtime` +
  Administrator `POST .../runtime/{start|stop|restart|reconcile}` — mirrors
  ARM desired/actual/recovery state, executes desired-state + reconcile NOW
  via Server Manager. Destroy not exposed. Stop with an ACTIVE assignment
  emits `RUNTIME_STOPPED_WITH_ACTIVE_WORK`; work state preserved. UI posts are
  Administrator-only (303 back to agent page; observer 403). Distinct from A2A
  interrupt/cancel/steer.
- Memory offload (Phase 8, migration 0006): `/api/v1/memory/*` —
  execution_sessions / context_packages / session_checkpoints. Rotation
  advisory bands at 50/70/85% context (MONITOR/CHECKPOINT_RECOMMENDED/
  ROTATE_RECOMMENDED); invalid context telemetry → UNKNOWN, never fabricated;
  rotation endpoint closes session 1 and builds a COMPACT reconstructed
  package (work facts + live assignment + latest checkpoint refs — never
  transcripts); completeness validator checks 10 required fields. The
  multi-session proof ran LIVE on prod: session 1 closed → session 2 open →
  work still active.
- **⚠️ RESOLVED (2026-09-28):** the 0006 `work_budgets` in-place edit was REVERTED; budgets shipped properly as `0007_work_budgets` (PR #25, v0.9.0). Prod alembic is now **0008** (v0.11.0, `a67bef9`): economics tables (`pr_outcomes`/`requirement_links`/`cost_attribution`) + attention feed (`GET /api/v1/attention`, derived from audit log). PG lesson learned live: **boolean server_default must be `sa.false()`** — `sa.text("0")` passes SQLite but DatatypeMismatchErrors on PostgreSQL (only the PG migration test catches it; keep `tests/test_budget_migration.py`-style chain tests for every migration).