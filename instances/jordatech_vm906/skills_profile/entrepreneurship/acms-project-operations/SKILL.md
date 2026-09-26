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
- Release state lives OUTSIDE git at `/opt/acms/releases/`: `current`,
  `previous`, `history.jsonl`, `releases/<id>.json`, `transaction.json`,
  `backups/<id>.dump`. Never put secrets in release metadata.
- Feature-specific smoke hooks via `ACMS_FEATURE_SMOKE` env (plan §11).

## Live CT122 quirks (validated 2026-09-26)

- Git checkout is at `/opt/acms/repo` (NOT `/opt/acms`); `.env` at
  `/opt/acms/.env` (0600, key names only — never echo values).
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