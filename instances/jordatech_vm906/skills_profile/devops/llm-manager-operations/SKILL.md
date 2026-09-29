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
- Endpoints (v1.0.0 + 2026-09-28 additions): `/api/v1/agent-runtimes[/{id}]`,
  `/desired-state`, `/agent-runtimes/{id}/reconcile`, `/reconcile`,
  `/agent-runtimes/{id}/state-sync`, `/api/v1/model-routes[/{route}]`,
  `/api/v1/hosts`, `/api/v1/usage`, `/api/v1/pdu/*` (health, capabilities,
  assets, asset power-state, action-plans=DRY-RUN, jobs, audit; actuation
  env-gated `SERVER_MANAGER_PDU_ACTUATION=1`, `off` refused at SM layer).

## Release transaction to VM114 (proven loop)

1. Local: `bash deploy/build-release.sh . dist` → tar.gz + sha256.
   Build the artifact from the MAIN TIP, not your feature branch: create a
   throwaway `git switch -c tmp-deploy-<sha> origin/main`, build from there,
   then switch back (2026-09-29 pattern; keeps the artifact == merged main).
2. Serve: `python3 -m http.server 8899 --bind 0.0.0.0` from `dist/`
   (Hermes background terminal); kill it after (`pkill -f 'http.server 8899'`).
   **Simpler than http.server: `scp` the tarball+sha directly to
   `vm114:/tmp/`** (VM114 has sshd via the dedicated key) — used successfully
   2026-09-29 for both releases.
3. On VM114: `sha256sum -c <tarball>.sha256` → OK.
4. Run the CURRENT deployment's `deploy-release.sh` (`/opt/llm-manager/current/deploy/deploy-release.sh <tarball>`)
   via `setsid nohup ... > /tmp/deploy-<sha>.log 2>&1 < /dev/null &` (plain
   nohup from a ssh 'bash -c' dies with the session; setsid survives).
5. Poll `tail` of the log via ssh until `==> Release ACCEPTED (<full-sha>)`
   + `healthcheck PASSED`. Note: `pgrep -f deploy-release` matches your OWN
   ssh command line — filter with `pgrep -fl 'deploy-release.sh /tmp'` or
   you'll read a phantom "still running".
6. If `server_manager/` code changed: `systemctl restart server-manager-api`
   (its own systemd unit; NOT restarted by the web-app transaction).
7. Check `deploy/ ops/` diffs before releasing: if the transaction tooling
   itself changed, do a same-tip drill first (tooling-mid-flight is unproven).
8. Verify: `curl -sk https://10.0.20.108/healthz` reports the new git_sha.
   Clean the tarball+sha out of `/tmp` after success.

**Preflight checksum trap (cost a release cycle 2026-09-28):** the `.sha256`
file must sit NEXT TO the tarball AND be named `<tarball>.sha256`. The build
names the sha file after the CONTENT hash, not the tarball — preflight
`sha256sum -c` then fails and the release aborts. Fix before transfer:
`mv <content-hash>.sha256 <tarball>.sha256` (edit the single line to point at
the tarball filename if the manifest lists the content-hash name).

## CI / merge discipline

- 6 required checks on PRs: secret-scan, syntax, tests, deps, config, db
  (+ integration-smoke). Merge only when all pass:
  `gh pr merge N --squash --delete-branch`.
- Main pushes trigger `deploy-staging` → VM120 auto-deploy. Verify staging
  picked up the SHA: `curl -sk https://10.0.20.131/healthz`.
- **Admin-bypass pitfall:** Jordan's token has admin rights; branch protection
  does NOT block `git push origin HEAD` from a local `main`. After a squash
  merge you are left ON main — always `git checkout -b feat/...` BEFORE the
  next commit, or you bypass review (happened twice 2026-09-28; CI covered it,
  but it's against repo policy).

## PVE qga exec pattern (how you touch VM114/VM124)

- Helper: `~/work/pve_api.py` (LLDAP bot account, `~/.pve_ldap_bot`). Node
  locations: **VM114 + VM120 + CT122 on `miam-00135`**; **VM124 on
  `miam00111`**; VM156 on `miam-00133`. Wrong node → 500 "qemu-server/N.conf
  does not exist".
- Two-step: `POST /nodes/{node}/qemu/{vmid}/agent/exec` (returns pid) → sleep
  → `GET .../agent/exec-status?pid=<pid>` (out-data/err-data/exitcode).
- Stage scripts as base64 (≤9KB chunks) written to a temp file, then decoded
  and run. VM114 qga has a known wedge risk on long execs — keep each exec
  minimal, use nohup + log-poll for long operations.

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

## llmmanager ORM migration (TDR-0008) — parity-test patterns

- Slice 1 done (hosts/active_hosts/model_registry reflective models + read
  endpoints). Full 22-table inventory in the 2026-09-28 flight handoff.
  LiteLLM_* tables are NEVER "migrated" (adapter boundary).
- **Slice 4 done (PR #52, 2026-09-29):** read-only reflective models for
  `recovery_events / request_routing_log / electricity_rates / manager_settings`
  (`server_manager/llm_manager/models/orm_slice4.py`), schema mapped from
  prod via `information_schema` (verify live columns before writing a model —
  dates are DATE not String, PKs vary). TDR-0008 now carries a slice log;
  slice 5 = write-path parity behind adapters (row-count + checksum before
  cutover), slice 6 = telemetry family AFTER the gpu_samples retention
  decision (197 MB / 1.59M rows of a 225 MB DB as of 09-29; nothing deleted
  without human approval). Schema-honesty tests pin table names/PKs/column
  sets (`tests/server_manager/test_orm_slice4.py`) and assert the shared
  LlmBase metadata (no-DDL invariant).
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
- Route introspection: `app.routes` shows `_IncludedRouter` wrappers — probe
  with TestClient instead of counting APIRoutes.

## Pointers

- ACMS counterpart skill: `acms-project-operations` (CT122 release.sh, UI).
- PDU: `pdu-manager-vm154`; legacy AgentManager: `agent-manager-vm114`
  (superseded — see parity matrix + TDR-0010 in this repo's docs/).
- OPNsense session-auth + IP-collision vetting recipe (login curl, Kea
  reservation parsing, 5-step IP-vetting checklist): `references/opnsense-access-and-ip-vetting.md`.
- Legacy AgentManager parity matrix: `docs/legacy-agentmanager-parity-matrix.md`;
  TDR-0008 (ORM staging), TDR-0009 (single-replica reconciler), TDR-0010
  (legacy alive pending UI parity) in this repo.
- Session-specific detail (flight 2026-09-28 state, PR list, debugging
  stories, live-proof transcript, open items): `references/flight-2026-09-28-session-notes.md`
