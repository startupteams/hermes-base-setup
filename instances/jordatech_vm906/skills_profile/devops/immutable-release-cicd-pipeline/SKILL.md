---
name: immutable-release-cicd-pipeline
description: "Build the Git→CI→artifact→staging→production pipeline for an already-running service: releases/ + current-symlink layout, SHA-identified immutable artifacts, ledger-based forward-only migrations, clean-room bootstrap gate on a staging VM, protected production environment, automatic application rollback. Reference implementation: llm-manager-project-framework (2026-09-27, 11 PRs, staging VM120 proven)."
---

# Immutable-Release CI/CD Pipeline Construction

**Trigger this skill when:** asked to make a running service reproducible/deployable from Git, add CI/CD to a capture-style repo, build a staging environment, or implement "branch → CI → merge → artifact → staging → approval → prod" for VM-hosted services. NOT for container-native apps (use standard image pipelines) — this is for systemd/nginx/venv services deployed onto VMs.

Reference implementation: `startupteams/llm-manager-project-framework` PRs #6–#22 (2026-09-27). The deploy/ directory in that repo is the canonical, battle-tested script set — copy and adapt, don't rewrite. **Proven legs:** staging clean-room bootstrap + full release transaction (migrations + 13/13 healthcheck + ACCEPTED) + real auto-rollback. **Unproven leg:** first real production promotion — the reference prod host still runs the legacy flat layout (`/opt/llm-manager/app` + venv), so the releases/current conversion + protected-environment prod deploy remain the next milestone when using this skill as a template.

## The architecture (plan §2 of the reference plan)

```
/opt/<svc>/
├── releases/<git-sha>/        # immutable trees (app, ops, db, config) — never edited in place
├── current -> releases/<sha>  # activation = symlink swap (mv -T of current.new)
└── shared/{logs,state}        # survives releases; release dirs symlink into it
/etc/<svc>/                    # mutable: secrets/, tls/, generated configs — NEVER inside a release
```

Systemd units point at `/opt/<svc>/current/...` so activation is a symlink swap and rollback is a symlink swap back. `git pull` into production is banned.

## Pipeline stages

1. **PR → CI on GitHub-hosted runners** (never run arbitrary PR code on self-hosted deployment runners).
2. **Immutable artifact on main**: `git archive` of the reviewed SHA (untracked junk can't leak in) + `release_manifest.json` (git_sha, build_time, per-file sha256) + `.sha256` sidecar. Secret-scan gate INSIDE the build (sk- patterns, DSNs-with-password, private keys) — fail the build, not just CI.
3. **Staging CD auto after merge**: self-hosted runner downloads the EXACT CI artifact (workflow_run trigger, checksum-verified, never rebuilt), transfers, runs the release transaction.
4. **Production via workflow_dispatch + protected environment** (required human reviewer). Must deploy the same artifact SHA that passed staging.
5. **Release transaction** (deploy-release.sh): preflight → snapshot → stop interference FIRST (the recovery/supervisor service) → install candidate + venv from pinned freeze → candidate validation (compile/tests BEFORE activation) → ledger migrations → activate (symlink swap) → restart services (recovery-class service LAST) → smoke → **auto-rollback on smoke failure**.

## Active placement as a DB source of truth (§21.7 pattern)

When a service hard-codes "which guest is the active deployment per physical host" as Python constants (VLLM_HOSTS, NODE_MAP), every placement change is a source edit + deploy. Replace the AUTHORITY with a DB table (`active_hosts (physical_host, active_host_ip, updated_at, updated_by)`) + a small module:

- Cached reads (30 s TTL) with **legacy fallback to the constants when the DB is unavailable** — degrade to old behavior, never break (document as TDR).
- One admin endpoint (`POST /api/hosts/active`, Admin-role gated) promotes a guest via DB update only; run the registry/routing reconcile immediately after so `backend_url`s follow.
- Keep the constants as the *inventory* + fallback; consumers sort/label by DB-active. `/api/status` reports `active_source: db|legacy` so the mode is observable.
- Regression tests simulate active = A → B → A purely via DB and assert historical tables (deployment_revisions, ring inventories) stay untouched — switching must never rewrite history.
- Prove it live on staging: promote → read-back → promote-back with zero source edits.

## Migration discipline

- Ledger table `schema_migrations (version, checksum, applied_at, git_sha)`; forward-only runner (`migrate.py apply/status/verify`).
- Files named `NNN_destructive_*.sql` are refused by ordinary runs — require maintenance plan + explicit flag + operator backup.
- Application rollback is only safe across backward-compatible releases; the reference session proved rollback to a release predating an env-var fix fails its own healthcheck — that is correct behavior, document it, don't "fix" it.
- Pre-migration operator backup stays on the host (root-owned 0600); never upload DB dumps to GitHub.
- Baseline migration for a live system is intentionally EMPTY of DDL — it marks the existing schema as 001 so ordering works for both fresh-install and existing paths.

## Clean-room staging gate (the reproducibility proof)

Provision staging ONLY from: GitHub artifact + documented external secrets + documented external endpoints. Procedure:

1. Clone a prod VM for OS parity, then **wipe everything service-specific**: app trees, units, nginx sites, secret VALUES, TLS, generated configs, logs. A clone that still carries prod secrets or configs is not a clean room.
2. Renumber identity BEFORE anything else: netplan IP, hostname, machine-id (`systemd-machine-id-setup`). A cloned VM answering on the prod IP is a live incident.
3. Run `bootstrap-vm.sh <artifact> --staging` (idempotent: apt, Python pin check, venv from freeze, units, nginx + self-signed staging TLS, compat symlinks).
4. Provision staging-local secrets (fresh values, NOT copies of prod) + isolated DB (local PG on the staging VM is cleaner than schema separation).
5. Seed safety: mark hosts/targets UNMANAGED/mock so staging recovery can never act on real infrastructure.
6. Gate: services active, healthz, gated APIs respond (auth gates count as alive), nginx TLS, no restart storm, release manifest observable. Then REBOOT and repeat — persistence counts.
7. Prove switching/rollback scenarios live (symlink swap back/forward, DB-driven promotion).

## Pitfalls (all found live, 2026-09-27)

- **Compat symlinks**: artifact nests source under `service/` and builds `.venv`, but units/code reference flat `app/`, `venv/`. Bootstrap must create `app -> service/app`, `venv -> .venv` etc. per release. Symptom: units exit 203/EXEC while files obviously exist.
- **Env-var overrides for hard-coded constants**: every `PG_HOST`-class constant in app code needs an env override (e.g. `LLM_MANAGER_PG_HOST`) with prod default unchanged, or staging can't point at its own DB. Ship the override via systemd drop-in `Environment=`.
- **Healthcheck timing**: deploy restarts units then healthchecks immediately — a unit in restart backoff (RestartSec=10) reads "not active". Healthcheck needs a bounded wait loop (e.g. 10 × 3s) per unit.
- **Healthcheck route inventory**: a 404 on an optional API route is a release-inventory difference, not a deploy failure — tolerate it. A gated endpoint answering its auth error IS route-alive (the gate working is a PASS).
- **Healthcheck reads current/ after rollback** — a failing candidate's smoke runs the rollback, and the post-rollback healthcheck correctly reports the OLD release manifest. Don't misread that as a bug.
- **CI first-run failures to expect**: starlette SessionMiddleware needs `itsdangerous`, FastAPI forms need `python-multipart`, DB-backed tests need `pgserver` (no-Docker PG); `gitleaks-action@v2` requires an org license — use a pinned gitleaks BINARY instead (`detect --source . --no-git`); runner needs `sudo mkdir` for /etc paths; nginx site goes to sites-available + symlink.
- **QGA file transfer wedges**: large/long guest-exec payloads (multi-KB heredocs, 130KB chunk pushes) wedge the qemu-guest-agent channel — recovery is `qm reset` (services survive; wait for agent ping before next exec). Fallback transfer path: `python3 -m http.server` on the workstation + `curl` from the VM (two-way; remember to kill the server after).
- **Branch protection + self-merge**: `enforce_admins=false` keeps admin merges possible while CI stabilizes; set `required_approving_review_count` per Jordan's instruction at the time (0 during autonomous sprints, tighten later).
- **Protected environment via API** (not in repo settings UI workflow): `PUT /repos/{owner}/{repo}/environments/production` with `{"reviewers":[{"type":"User","id":<user_id>}],"deployment_branch_policy":{"protected_branches":true}}` — reviewer id from `gh api users/<login> --jq .id`. Job-level `environment: production` is what enforces the reviewer gate.
- **workflow_run-triggered CD**: `deploy-staging.yml` on `workflow_run` of the CI workflow (`conclusion == 'success' && head_branch == 'main'`), runner labels `[self-hosted, marion, <svc>-deploy]`; artifact located via `listWorkflowRunArtifacts` on `run.id`.
- **Migration runner must fail loudly when it finds nothing**: a runner computing its input dir as `dirname(__file__) + "/migrations"` while the script itself lives INSIDE that dir double-nests the path (`migrations/migrations`), finds zero files, and `apply`/`verify` exit 0 with "verified 0 applied migrations" — silent success that surfaces later as a confusing downstream deploy failure. Self-referencing dir = `dirname(abspath(__file__))` itself; add a guard: zero input files found ⇒ hard fail (see ops-scripting-pitfalls §9).
- **Cloned-VM netplan MAC-match trap**: the source VM's netplan pins `match: macaddress: <source-MAC>`; the clone has a NEW MAC so netplan errors `Cannot find unique matching interface for eth0` and the NIC stays DOWN — looks like "networking broke" right when you're renumbering. Drop the match block entirely (or substitute the clone's actual MAC from `ip link`) as part of identity renumbering.
- **Post-handoff async triage**: background subagent results land AFTER the handoff message. Budget one triage pass — cross-check subagent findings against what shipped, fix real gaps (the gpu_power_collector missing-active-host bug was found this way → follow-up PR), and APPEND an addendum section to the handoff rather than rewriting it. Also: a fanned-out subagent can complete with status=failed and NO summary — verify its assigned scope yourself before trusting coverage.

- **CD tooling must never default to prod endpoints** (found live 2026-09-27, PR #20): the transaction and preflight scripts shipped `LLM_MANAGER_PG_HOST="${VAR:-<prod-DB-IP>}"` — a staging migration step then pointed at PROD, stopped only by a missing password. Resolution order for any environment target in tooling: explicit env var → the app unit's systemd `Environment=` (`systemctl show <svc> -p Environment --value`) → local/neutral default (`127.0.0.1`). Prod IPs belong in the documented manifest only (informational), never as code defaults. One missing password is all that separates staging from prod otherwise.
- **Mirror the app's credential contract in tooling** (PR #21/#22): the app read its DB password from a secrets file (`PG_PW=` line in `/etc/llm-manager/secrets/pg_app_creds`) while the migration runner only knew env vars → `fe_sendauth: no password supplied` on every plain transaction. Tooling must read the SAME source (explicit env override still wins). Python nuance: `os.environ.get(VAR)` returns `''` (not None) for set-but-empty — the transaction script exports an empty password when the unit env lacks it — so `if pw is None` never falls through to the file; use `pw = os.environ.get(VAR) or None`.
- **Upgrading the deploy tooling itself (chicken-and-egg)**: tooling fixes reach staging only THROUGH the tooling, and the installed transaction script is the old buggy copy that dies on its own bug before the new one activates. When the transaction scripts themselves change, unpack the NEW artifact to a scratch dir and run ITS `deploy-release.sh` against its own tarball — the artifact self-hosts its tooling: `tar -xzf artifact.tgz -C /tmp/tooling && sudo bash /tmp/tooling/<pkgdir>/deploy/deploy-release.sh artifact.tgz`.
- **workflow_run CD runs showing `cancelled` with zero jobs** is usually the guard working, not a failure: PR-branch CI completions also fire `workflow_run`, and the job-level `if head_branch == 'main'` skips them. Read the workflow's `if:` before diagnosing cancelled CD runs; the real signal is a run stuck `pending` with no jobs = self-hosted runner not registered.
- **Merging under agent tool-call timeouts**: `gh pr checks --watch` blocks past 60s tool timeouts — right after `gh pr create`, checks take ~20–40s to even register ("no checks reported on branch" ≠ failure). Pattern: sleep ~25s → snapshot `gh pr checks N | awk '{print $1,$2}'` → bounded re-check loop (sleep 15–30s until `pending`=0) → merge. `gh run view <id> --log-failed` is empty for runs that never got jobs — read its `conclusion`/`jobs` JSON instead.

## GitHub-side configuration (API, not UI)

Branch protection and protected environments have no `gh` subcommands — use `gh api`:

```bash
# Branch protection: contexts must exactly match workflow JOB names; enforce_admins=false
# deliberately during CI stabilization (tighten later)
gh api -X PUT repos/$OWNER_REPO/branches/main/protection --input - <<'EOF'
{"required_status_checks": {"strict": true, "contexts": ["syntax","tests","secret-scan","config","db","integration-smoke"]},
 "enforce_admins": false,
 "required_pull_request_reviews": {"required_approving_review_count": 0, "dismiss_stale_reviews": false},
 "restrictions": null, "allow_force_pushes": false, "allow_deletions": false}
EOF

# Protected 'production' environment with required reviewer (the §12 human-approval gate):
REVIEWER_ID=$(gh api users/<login> --jq .id)
gh api -X PUT repos/$OWNER_REPO/environments/production --input - <<EOF
{"deployment_branch_policy": {"protected_branches": true, "custom_branch_policies": false},
 "reviewers": [{"type": "User", "id": $REVIEWER_ID}]}
EOF
```

- The reviewer gate is enforced by putting `environment: production` at the **JOB level** of the deploy workflow (a workflow-level `environment:` key is invalid YAML for Actions).
- `workflow_run`-triggered staging CD: `on: workflow_run: workflows: ["ci"] types: [completed]` with job-level `if` on `conclusion == 'success' && head_branch == 'main'`; artifact located via `listWorkflowRunArtifacts(run.id)` and downloaded with `downloadArtifact(archive_format: "zip")` — deploy the EXACT artifact, never rebuild.
- Production dispatch validates SHA match: extract `git_sha` from the artifact's `release_manifest.json` inside the tarball and compare against the requested input before transferring anywhere.

## References

- `references/clean-room-gate-runbook.md` — the VM120 staging provisioning runbook (clone → wipe → renumber → bootstrap → secrets → DB → gate → switching proof → rollback proof) with exact commands and the qga-wedge workarounds.
- Reference repo deploy/ scripts: `build-release.sh`, `bootstrap-vm.sh`, `preflight.sh`, `deploy-release.sh`, `healthcheck.sh`, `rollback.sh`, `verify-parity.sh`, `db/migrations/migrate.py` — copy as templates and adapt paths/service names.