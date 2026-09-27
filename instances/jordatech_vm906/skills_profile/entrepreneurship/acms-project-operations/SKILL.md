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
- Repo docs: `deploy/README.md` (operator runbook), ADR-0009 (safe release
  transaction), `SPRINT.md` (current slices), handoffs under `docs/handoffs/`.