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
- Repo docs: `deploy/README.md` (operator runbook), ADR-0009 + ADR-0010 (both
  Accepted 2026-09-26/27), `docs/HARNESS_CONTROL_MAPPING.md`, `SPRINT.md`
  (current slices), handoffs under `docs/handoffs/`.

## Combined slice 3+4 state (deployed 2026-09-27, v0.6.0 @ 85f3c92)

- **ADR-0009 Accepted** (amended: live evidence + explicit deployment-authority
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
- **CI note:** ACMS repo has NO GitHub Actions workflows / required checks —
  green comes from local pytest only. Run the full suite
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
- **⚠️ OPEN — do not repeat:** a `work_budgets` table was added to migration
  `0006_memory_session_offload.py` LOCALLY after prod already applied 0006.
  That edit is uncommitted and must be REVERTED; budgets belong in a NEW
  `0007_work_budgets` migration. Never edit an already-applied migration in
  place (fresh-install drift). Budget service/API/tests were not written.