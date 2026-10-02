---
name: llm-manager-operations
description: "Operate LLM Manager + Server Manager (VM114 prod 10.0.20.108, VM120 staging .131): SM API auth, release transactions via qga artifact self-hosting, ARM reconciler semantics, ORM parity patterns, CI/merge discipline."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [llm-manager, server-manager, ARM, releases, postgres]
---

# LLM Manager + Server Manager Operations

Repo: `~/work/llm-manager-project-framework` (jordatech). Test venv `.venv-sm`
(Python 3.11; `pgserver` embedded PG for DB tests). Prod **VM114**
(10.0.20.108), staging **VM120** (10.0.20.131, both on node `miam-00135`).
CD: LXC-130 self-hosted runner (staging auto-deploys on main push; prod is a
manual release transaction). Do not edit prod files in place.

## Server Manager API (:8300) — auth pattern

- Scoped bearer identities from `/etc/llm-manager/secrets/service_tokens`
  (0600, outside Git). **File format trap:** lines are `service=token:scopes`.
  `cut -d= -f2` yields `token:scopes` — you MUST split off everything from the
  first colon or every call 401s. Token staged locally at
  `~/.sm_service_token_acms` (0600, never echo).
- Scopes: read = runtime:read, job:read, route:read, usage:read, health:read;
  write = runtime:write, runtime:destroy, job:submit. 401 first, then 403.
  Empty scope string or `ALL` in the file = full scope set (require_identity
  in `server_manager/common/auth/service_tokens.py`; constant-time lookup).
- **The MCP gateway (VM114:8202) is a downstream consumer of this API** — it
  authenticates to :8300 with the svc-acms identity for its llm.*/runtime.*
  domains. SM stays the domain authority; do not add gateway-specific routes
  here, and remember `agent-runtimes` GET needs `runtime:read`.
- Endpoints (v1.0.0 + 2026-09-28 additions): `/api/v1/agent-runtimes[/{id}]`,
  `/desired-state`, `/agent-runtimes/{id}/reconcile`, `/reconcile`,
  `/agent-runtimes/{id}/state-sync`, `/api/v1/model-routes[/{route}]`,
  `/api/v1/hosts`, `/api/v1/usage`, `/api/v1/pdu/*` (health, capabilities,
  assets, asset power-state, action-plans=DRY-RUN, jobs, audit; actuation
  env-gated `SERVER_MANAGER_PDU_ACTUATION=1`, `off` refused at SM layer).
  New 2026-10-01 (PR #74, prod fce5ba7): **`GET /api/v1/facility/power`**
  (scope `usage:read`) — per-channel (PDU MIAM-00151/152/153 + mini split) +
  TOTAL MARION_IA_USA energy/cost for ACMS ingest; stale → NULL + STALE +
  timestamp (never 0), total withheld with `incomplete_reason` when any
  channel stale; rate from `electricity_rates` components else plan v0.2.1.
  Self-contained SQL over `get_session_factory("llm")` — deliberately does
  NOT import the web app's `power_view` (layout boundary). ACMS's
  `FacilityPowerClient` consumes this with the SAME svc-acms token.
- **LLM-Manager web `/api/fleet` is LDAP-session-auth (humans only)** —
  machine consumers (gateway, ACMS) must use the SM :8300 machine API instead.
  `/api/hosts/state` is the one unauthenticated web read (verified 200).

## VM114 release transaction (proven loop)

1. Local: `bash deploy/build-release.sh . dist` → tar.gz + sha256.
   Build the artifact from the MAIN TIP, not your feature branch: create a
   throwaway `git switch -c tmp-deploy-<sha> origin/main`, build from there,
   then switch back (2026-09-29 pattern; keeps the artifact == merged main).
2. Serve: `python3 -m http.server 8899 --bind 0.0.0.0` from `dist/`
   (Hermes background terminal); kill it after (`pkill -f 'http.server 8899'`).
   **Simpler than http.server: `scp` the tarball+sha directly to
   `vm114:/tmp/`** (VM114 has sshd via the dedicated key) — used successfully
   2026-09-29 for both releases.
3. On VM114: `sha256sum -c <tarball>.sha256` → OK. **The `.sha256` file must
   be named `<tarball>.sha256` and sit next to it** — the build names the sha
   after the CONTENT hash; rewrite the single line first
   (`python -c` writing `<content-hash>  <tarball-name>`) or preflight aborts.
   Also: **build-release.sh names tarballs with the SHORT (12-char) sha**
   (`llm-manager-8b05afb5c586.tar.gz`) while GitHub artifact uploads use the
   full `github.sha` — never match an artifact by full sha.
4. Run the CURRENT deployment's `deploy-release.sh` (`/opt/llm-manager/current/deploy/deploy-release.sh <tarball>`)
   via `setsid nohup ... > /tmp/deploy-<sha>.log 2>&1 < /dev/null &` (plain
   nohup from a ssh 'bash -c' dies with the session; setsid survives).
   **EXCEPTION — tooling-changing merges:** when the artifact CHANGES
   deploy-release.sh itself, invoke the ARTIFACT'S OWN script
   (`/opt/llm-manager/releases/<new-sha>/deploy/deploy-release.sh`) — the
   current/deploy path is the OLD tooling until the new release activates, so
   a new gate would silently not run (hit live 2026-09-29: the Phase-E dep
   probe never executed because the old script was invoked; fixed by a
   same-tip drill through the artifact's script). Phase E of the transaction
   also now RUNS a dependency-import verification (window-4 PR #67): the
   release venv must import sqlalchemy/alembic/psycopg2/httpx/uvicorn/fastapi
   before cutover — missing dep = die = pre-activation abort + auto-rollback
   (closes the window-3 sqlalchemy-gap class; tests/test_release_dep_gate.py).
5. Poll `tail` of the log via ssh until `==> Release ACCEPTED (<full-sha>)`
   + `healthcheck PASSED`. Note: `pgrep -f deploy-release` matches your OWN
   ssh command line — filter with `pgrep -fl 'deploy-release.sh /tmp'` or
   you'll read a phantom "still running".
6. If `server_manager/` code changed: `systemctl restart server-manager-api`
   (its own systemd unit; NOT restarted by the web-app transaction).
   **Re-hit live 2026-10-01 (PR #74):** deploy-release.sh restarted
   web/collector/emporia/recovery but NOT server-manager-api → the new SM
   route 404'd via openapi until the manual restart. Make
   `systemctl restart server-manager-api && curl -s :8300/openapi.json |
   python3 -c "…"` the mandatory post-release verification whenever the diff
   touches `server_manager/`.
7. Check `deploy/ ops/` diffs before releasing: if the transaction tooling
   itself changed, do a same-tip drill first (tooling-mid-flight is unproven).
8. Verify: `curl -sk https://10.0.20.108/healthz` reports the new git_sha.
   Clean the tarball+sha out of `/tmp` after success.
9. **Env persistence across releases:** systemd DROP-INS survive releases —
   env set via drop-in files (e.g.
   `/etc/systemd/system/llm-manager-web.service.d/orm-cutover.conf`) is NOT
   lost when a new release ships; plain env vars passed at restart time ARE.
   There is no `/opt/llm-manager/.env` (staging toggle learned this: `touch ""
`).

## Staging VM120 (10.0.20.131) — access reality

- NO direct SSH shell for the agent (no root ssh from workstation or VM114; the
  CT130 self-hosted runner's `llm-manager-deploy@10.0.20.131` key is the ONLY
  ssh path, and that user's sudo is wrapper-only: bootstrap/deploy/healthcheck
  wrappers — arbitrary sudo asks for a password). **This is INTENTIONAL
  least-privilege design, not a missing key (diagnosed 2026-09-29, window-4
  plan §F1) — do not "fix" it by widening sudo.**
- **qga IS available on VM120** (node miam-00135, `qm guest exec 120` — exit 0
  verified). Window-3's "no shell access" finding was SSH-only; bounded
  read-only verification (ORM shadow parity, DB counts, settings) works via
  node-side qga exec with base64-staged scripts. CT130 lives on miam-00133;
  its `llm-runner` user holds the llm-manager deploy key (`su - llm-runner`).
- Staging auto-deploys on main push via `deploy-staging.yml`. Verify with
  `curl -sk https://10.0.20.131/healthz` — the git_sha must match main tip.
- One-shot env toggles go through the `staging-orm-cutover-toggle.yml`
  workflow (workflow_dispatch, value=1/0) — it writes systemd drop-ins,
  daemon-reloads, restarts, and verifies via `systemctl show`.
- ORM shadow parity PROVEN on staging (window-4 Phase F3): slice-5
  `orm_hosts_inventory()` == legacy psycopg2 host count; slice-6 gpu_orm
  imports clean; retention settings 90/730 present; gpu tables empty on
  staging by design (no GPU collectors target staging).
- When VM120 access blocks a staging-first validation, prod validation via
  VM114 root + systemd drop-ins is the accepted fallback (documented
  deviation; prod cutover flag is instantly reversible by removing drop-ins).

## CI / merge discipline

- 6 required checks on PRs: secret-scan, syntax, tests, deps, config, db
  (+ integration-smoke; `artifact` shows "skipping" on non-main-branch runs —
  normal). Merge only when all pass:
  `gh pr merge N --squash --delete-branch`.
- Main pushes trigger `deploy-staging` → VM120 auto-deploy. Verify staging
  picked up the SHA: `curl -sk https://10.0.20.131/healthz`.
- **Admin-bypass pitfall:** Jordan's token has admin rights; branch protection
  does NOT block `git push origin HEAD` from a local `main`. After a squash
  merge you are left ON main — always `git checkout -b feat/...` BEFORE the
  next commit, or you bypass review (happened twice 2026-09-28; CI covered it,
  but it's against repo policy). **Confirmed still live 2026-09-29 (2 more
  violations): the merge command itself leaves the local checkout ON main —
  make `git branch --show-current` the mandatory first command after ANY
  merge-with-delete.**
- **CD artifact chain (3 bugs found + fixed 2026-09-29, PRs #61-#64):**
  deploy-staging "succeeded" while deploying a 2-day-old artifact. (1) Self-
  hosted runners REUSE RUNNER_TEMP — stale `llm-manager-*.tar.gz` survive jobs
  and `find | head -1` picks them: always rm stale tarballs + select by EXACT
  name (short-sha form — see the release-transaction section). (2) Do NOT `rm
  artifact.zip` in the unpack step — the download step writes it fresh; rm-ing
  it after download kills unzip ("cannot find or open artifact.zip"). (3)
  `dist/` was TRACKED in the repo (no .gitignore entry) — the CI artifact zip
  contained multiple committed stale tarballs; fixed by git-rm + gitignore +
  a CI step asserting exactly ONE tarball pair before upload.
  Verify staging health: `curl -sk https://10.0.20.131/healthz` must report
  the current main git_sha — a "successful" deploy-staging run proves nothing
  on its own.

## PVE qga exec pattern (how you touch VM114/VM124)

- Helper: `~/work/pve_api.py` (LLDAP bot account, `~/.pve_ldap_bot`). Node
  locations: **VM114 + VM120 + CT122 on `miam-00135`**; **VM124 on
  `miam00111`**; VM156 on `miam-00133`. Wrong node → 500 "qemu-server/N.conf
  does not exist".
- Two-step: `POST /nodes/{node}/qemu/{vmid}/agent/exec` (returns pid) → sleep
  → `GET .../agent/exec-status?pid=<pid>` (out-data/err-data/exitcode).
- Stage scripts as base64 (≤9KB chunks) written to a temp file, then decoded
  and run. VM114 qga has a wedge risk on long execs — keep each exec
  minimal, use nohup + log-poll for long operations.
- **VM114 has root SSH too** (`ssh vm114` alias via `~/.ssh/config.d/`, dedicated
  key) — simpler than qga for file staging (`scp` tarballs/probes to /tmp) and
  log polling. Deploy-flow exceptions where qga/node-SSH is still required:
  see `vm114-qga-ssh-recovery` skill.

## ARM reconciler semantics (services/reconciliation.py)

- desired RUNNING: observe → start owned VM once (ownership-verified, bounded
  retries w/ capped backoff, `recovery_count`) → RUNNING; PVE truth corrects
  stale DB actuals.
- desired STOPPED: graceful shutdown once → **bounded convergence wait**
  (`ARM_RECONCILE_SHUTDOWN_WAIT_S`, default 30s/3s polls). Live lesson: PVE
  state flips LAG the API ack — an immediate status read still says `running`
  after an accepted shutdown. Never record nonconvergence without the wait.
- DESIRED_DESTROYED is API-only; the reconciler NEVER destroys. PVE
  unreachable → record `last_error`, no state flip on unknown ground truth.
- Single-replica discipline (TDR-0009): one uvicorn worker; no leader election
  yet. state-sync health vocabulary: PENDING|SYNCING|VERIFIED|STALE|FAILED.
- Stale failed-provisioning rows: disposition is **SUPERSEDED** (never delete).
  Admin endpoint marks each failed attempt row SUPERSEDED and links it to the
  live runtime (5 ERROR rows → live VM124 runtime 56c1b849, 2026-09-28, PR
  #50). Needs a PG enum migration for the new actual-state value; verify via
  DB audit-event count, and `expire_all()` after API calls in tests (session
  caches the pre-update row) — a 404-before-422 test ordering trap means the
  bad-target test needs an existing row to hit 422.
- **Recovery policy (PR #51, 2026-09-29, human direction):** default
  `max_recovery_attempts` is now **5** (env `ARM_RECONCILE_MAX_ATTEMPTS`
  overrides; prod has NO env override → 5 active). Backoff 10/20/40/60s capped
  (attempts vary). Every attempt audits `failure_class` /
  `recovery_method` / `attempt` in the RuntimeEvent detail (durable audit log
  IS the recovery-method history — no second mutable table). Exhaustion
  audits `strategy_next: human_attention`. Ladder: recheck/observe → VM start
  ×5 → Human Attention. Service/harness restarts belong to LLM Manager
  serving / ACMS bridge, NOT ARM; PDU hard-cycle is NEVER automatic. Tests:
  `tests/server_manager/test_recovery_policy.py` (shared fakes imported from
  test_reconciliation — import `make_runtime` too or NameError).

## LLM Manager web UI (window-5 additions — /admin/fleet, /admin/agents)

- **Fleet one-card bug (fixed 2026-09-30, PR #69, prod 439cf8d):** `_physical_host_for_ip()` led with
  `ip.startswith("10.0.20.16")` which matched EVERY guest .161-.168 → all hosts collapsed onto
  MIAM-00111 → `_active_hosts()` promoted only VM102 → the dashboard rendered ONE card while 5 served.
  Second stacked bug: the demotion loop checked `if phys not in promoted` and silently DROPPED a rollback
  VM sharing the active one's physical host (docstring claimed "demoted to the END"). Fix: exact-IP checks
  first; demote-but-never-drop via an active_ips set. Lesson: **IP→group mappers must lead with exact
  matches, every "demote" path must append, and a test must count distinct groups over the real
  inventory** (`tests/test_fleet_visibility.py`). Verify such bugs by importing the DEPLOYED module on prod
  and calling the function — code reading kept saying "fine".
- **Model Fleet page (PR #70, prod 81ca2b3):** `GET /api/fleet` + `/admin/fleet` — inventory-driven (hosts
  table ∪ legacy VLLM_HOSTS; nothing hard-coded in the UI), operator states SERVING / ONLINE_IDLE /
  STOPPED_EXPECTED / UNREACHABLE / MISCONFIGURED / STALE (routable model last_verified > 48h; aliases
  don't mask staleness). Powered-off/unreachable hosts stay visible; "VM powered on" and "model healthy"
  are separate facts; drill-down per host; PDU hard-power never on this page.
- **Agent Runtimes UI (PR #71, prod d021f70):** `/admin/agents` list + `/admin/agents/{id}` detail +
  `/admin/agents/new` wizard in the operator shell (LDAP session). The web app proxies the SM/ARM API
  (:8300) server-side via the `svc-server-manager` identity from the same 0600 service_tokens file (same
  VM; token never echoed). Wizard = 6 steps → the EXISTING ARM provisioning path (authority fixed
  server-side `sprint_execution_context`); external/customer baseline shown as NOT authorized; budget
  fields point at ACMS (never faked); destroy NOT exposed. Failure classes render actionable errors
  (503 no-token / 599 network / upstream status) — never raw 500s.
- **New-app dependency rule:** anything imported at module level of the web app must be in
  **[project].dependencies** (base), not only `[project.optional-dependencies].dev` — the Dockerfile
  installs `pip install .` (base only). Hit live: `httpx` was dev-only, so `jira_client` (imported by
  window-5 gate code) would 500 in prod; PR moved httpx to base deps. Audit imports-vs-deps before
  releasing any new integration module.

- Slice 1 done (hosts/active_hosts/model_registry reflective models + read
  endpoints). Full 22-table inventory in the 2026-09-28 flight handoff.
  LiteLLM_* tables are NEVER "migrated" (adapter boundary).
- **Slice 5+6 done + CUTOVER LIVE (PRs #60/#66, 2026-09-29):** the v011 legacy
  app routes hosts/model_registry/recovery_events + gpu_samples family writes
  through sync SQLAlchemy Core adapters behind `ORM_WRITE_CUTOVER=1`
  (systemd drop-ins on web+recovery+collector; default OFF = legacy psycopg2;
  rollback = remove drop-ins + daemon-reload + restart).
  - `service/app/orm_write_adapter.py` — sync Core over the SAME schema (no
    DDL, column whitelist, v011 credential contract: LLM_MANAGER_PG_HOST env
    fallback + PG_PW_FILE `PG_PW=` line; prod DB is CT115 @ 10.0.20.116, NOT
    127.0.0.1). v011_core desired-state/power-off/sync_registry/routable_models
    + v011_recovery audit()/recent_count() call it.
  - `service/app/gpu_orm.py` — BULK insert (one multi-row INSERT per collector
    cycle, never row-at-a-time), hourly_rollup_window (identical upsert SQL
    incl. power_sum_wh/last_ts + DO UPDATE refresh), bounded prune on
    `sample_id` PK (gpu_samples has NO `id` column), parity checksums.
  - **Legacy-parity finding:** `model_registry` UNIQUE(logical_model_name,
    host_id) does NOT dedupe NULL host_ids (PG treats NULLs as distinct) —
    alias inserts need the legacy delete-then-insert order or they duplicate.
  - **cmd_rollup window MUST be hour-aligned at the START edge** (W2's
    backfill-chunk lesson applies to every rolling window): `now-3h` mid-hour
    truncated the oldest bucket and later runs never re-covered it → permanent
    deficit (verify FAIL 104 mismatches, rollup 134 vs raw 142). Fix + live
    repair (re-aggregate 24h → 576 buckets) → VERIFY PASSED 0 failures.
  - `sqlalchemy` was in the requirements freeze but NOT in the prod venv —
    pip-installed 2.0.54 into `/opt/llm-manager/venv` (venv is NOT rebuilt by
    the release transaction; freeze drift is now known debt).
  - **The systemd unit's WorkingDirectory (/opt/llm-manager/app) is a STALE
    static dir; the RUNNING process cwd is
    `/opt/llm-manager/releases/<sha>/service/app`.** Scripts probing deployed
    code must `sys.path.insert(0, "/opt/llm-manager/current/app")` — and
    `current/app` is a symlink into the active release.
  - ORM is NOT imported by the FastAPI app for these domains yet — the flag
    gates the legacy call sites themselves; parity tests live in
    tests/test_orm_slice5_cutover.py + tests/test_gpu_orm_slice6.py (pgserver;
    set PG_HOST=<socket dir>, PG_USER=postgres, PG_PW="" empty-string VALID —
    `if pw is None` not `if not pw`, or empty trust passwords break).
- Slice 4 done (PR #52): read-only reflective models for
  `recovery_events / request_routing_log / electricity_rates / manager_settings`
  (`server_manager/llm_manager/models/orm_slice4.py`), schema mapped from
  prod via `information_schema` (verify live columns before writing a model —
  dates are DATE not String, PKs vary). TDR-0008 carries a slice log.
  Schema-honesty tests pin table names/PKs/column sets
  (`tests/server_manager/test_orm_slice4.py`) and assert the shared
  LlmBase metadata (no-DDL invariant).
- LiteLLM-owned writes are NEVER absorbed (SpendLogs lives in the separate
  `litellm` database — `SELECT ... FROM "LiteLLM_SpendLogs"` needs
  `-d litellm`, not `-d llmmanager`). **Query recipe (window-4 economics):**
  token/cost columns are `prompt_tokens` / `completion_tokens` / `spend` /
  `model` / `api_key` (NOT tokens_input/output); `startTime` is
  case-sensitive and needs full qualification in WHERE:
  `WHERE "LiteLLM_SpendLogs"."startTime" > now() - interval '7 days'`.
  Credentials via the pg_app_creds file contract (`PGPW=$(sed -n "s/^PG_PW=//p"
  /etc/llm-manager/secrets/pg_app_creds)`); spend-by-api_key rollup identifies
  which consumer (worker key vs master key) spent. 30-day baseline captured
  2026-09-29: $0.62 total, 99.98% deepseek-v4.1-flash — economics comparison
  verdict lives in the ACMS economics API, not SpendLogs alone.
- Parity tests (tests/server_manager/test_orm_parity.py, pgserver embedded):
  - `schema.sql` carries pg_dump ≥17 `\restrict`/`\unrestrict` meta lines —
    strip lines starting with backslash before `cur.execute(schema)`.
  - `OWNER TO llmmanager` → create the role first (DO $$ block).
  - pg_dump leaves `search_path=''` on the session → later unqualified DDL
    fails "no schema has been selected" → `SET search_path = public` (the
    set_config(..., true) form did NOT stick).
  - `active_hosts` is created by `service/app/active_deployments.DDL` at
    service startup, not by schema.sql — apply that DDL in fixtures.
  - **SQLAlchemy unix-socket URLs:** a socket dir in the netloc
    (`...@/path:5432/db`) is parsed as the DB path → engine host=None →
    silently targets `/var/run/postgresql`. `_make_url` now emits socket dirs
    as `?host=...` — keep it that way.
- Settings/test-env hygiene: `SERVER_MANAGER_LLM_PG_*` env, then clear
  `session._engines`, `session._sessions`, `get_settings.cache_clear()`;
  token-file env must be saved/restored across tests (mtime-keyed cache).
- FastAPI gotcha: an auth dependency's inner function MUST annotate its param
  `request: Request` — an unannotated `request` becomes a required QUERY param
  and every call 422s with `loc: ["query","request"]`.
- **Stubbing `get_session_factory` in route tests:** routes do
  `Session = get_session_factory("llm")` then `with Session() as session:` —
  the monkeypatched factory must return a CALLABLE that returns the fake
  session (`monkeypatch.setattr(fp, "get_session_factory", lambda *a, **k: (lambda: _FakeSession()))`),
  not a session instance (`TypeError: '_FakeSession' object is not callable`).
  Fake sessions need `__enter__`/`__exit__` and per-call scripted `execute()`
  results (see tests/server_manager/test_facility_power_route.py — 4 tests:
  401 no-token / 403 wrong-scope / 200 payload / collector-missing).
- **Jira REST v3 comment bodies are ADF documents, not strings** (contract
  applies anywhere Jira is written): plain-string bodies 400 with "Comment
  body is not valid!". ACMS `jira_client._markdown_to_adf` converts
  markdown → `{"type":"doc","version":1,"content":[…]}`; any NEW Jira-writing
  code must go through it.
- Route introspection: `app.routes` shows `_IncludedRouter` wrappers — probe
  with TestClient instead of counting APIRoutes.

## Pointers

- ACMS counterpart skill: `acms-project-operations` (CT122 release.sh, UI).
- PDU: `pdu-manager-vm154`; legacy AgentManager: `agent-manager-vm114`
  (superseded — see parity matrix + TDR-0010 in this repo's docs/).
- OPNsense session-auth + IP-collision vetting recipe (login curl, Kea
  reservation parsing, 5-step IP-vetting checklist): `references/opnsense-access-and-ip-vetting.md`.
- Legacy AgentManager parity matrix: `docs/legacy-agentmanager-parity-matrix.md`;
  TDR-0008 (ORM staging), TDR-0009 (single-replica reconciler), TDR-0010 (legacy alive pending UI parity) in this repo.
- Session-specific detail (flight 2026-09-28 state, PR list, debugging
  stories, live-proof transcript, open items): `references/flight-2026-09-28-session-notes.md`
- **ADR-0012 completion callback live notes** (contract, dispatch changes,
  reconciler sweep, live proof, probe recipes, test patterns):
  `references/adr0012-completion-callback-2026-09-29.md`
- **CD artifact chain repair** (RUNNER_TEMP staleness, rm-order, tracked dist/,
  short-sha naming, staging access reality, debug technique):
  `references/cd-artifact-chain-repair-2026-09-29.md`
- **Provisioning hygiene gate** (HYGIENE_GATE wiring, checks, failure
  semantics, test patterns): `references/provisioning-hygiene-gate-2026-09-29.md`
  stories, live-proof transcript, open items): `references/flight-2026-09-28-session-notes.md`
- **Facility-power SM route (2026-10-01, PR #74):** route SQL semantics,
  stale-withholding contract, ACMS-ingest pairing, test patterns for stubbing
  `get_session_factory`: `references/sm-facility-power-route-2026-10-01.md`
