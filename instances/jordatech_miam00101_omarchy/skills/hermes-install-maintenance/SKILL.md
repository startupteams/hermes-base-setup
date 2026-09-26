---
name: hermes-install-maintenance
description: "Use when repairing, updating, or backing up Hermes itself."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, maintenance, backup, update]
    related_skills: [hermes-agent]
---

# Hermes Install Maintenance

## When to Use

Use for any self-hosted Hermes upkeep: update reliability, automated backups, model-default repairs, gateway restarts, and repair-task handoffs. Do NOT use for general "how does feature X work" questions (use `hermes-agent`).

For maintaining a self-hosted Hermes installation: diagnosing update/install topology, building backup automation, and repairing model-default behavior. Load `hermes-agent` skill for general feature questions; this skill is the ops procedure.

## Step 0 — Classify the install BEFORE choosing an update method

```bash
hermes --version          # prints install method + upstream commit
hermes update --plan      # install type, profiles, running services to restart
hermes update --check     # read-only
hermes config get updates.check
```

- **git install**: `~/.hermes/hermes-agent` is a git clone of NousResearch/hermes-agent. Update = fetch/pull + pip reinstall + gateway restart. A running container CANNOT replace its own image for Docker installs — use a host-side wrapper script.
- Gateway runs as `systemd --user` unit `hermes-gateway.service` (Restart=always). Exactly one gateway should be active — verify with `pgrep -af 'gateway run'`.

## Step 1 — Backup FIRST, always

Backup root `~/Work/hermes-backups` (chmod 700). Four classes per snapshot: `brain/` (SOUL.md, memories, sessions), `skills/`, `harness/` (config.yaml, hooks, scripts, cron/jobs.json, systemd units, version info), `private/` (.env, auth.json — LOCAL ONLY, never git), `databases/` (state.db/projects.db/kanban.db via Python `sqlite3.backup()` + `PRAGMA quick_check`). Finish with a SHA-256 manifest and a `BACKUP-COMPLETE` marker written ONLY after validation. See `templates/backup-hermes.sh` for the proven script (flock, retention 3-latest/14-daily/8-weekly/6-monthly gated on newest-complete + >=4 valid).

- Pitfall: sandbox file tools don't reach the host — stage host scripts via a host-exec channel and verify with an immediate host-side `ls`.
- The portable Git sync (hermes-base-setup) is NOT a backup substitute: it deliberately excludes secrets and live DBs.

## Step 2 — Controlled update (git install)

Use a wrapper (`templates/update-hermes.sh`): flock -> mandatory pre-update backup (verify BACKUP-COMPLETE) -> `git pull --ff-only origin main` -> pip reinstall -> `config check` -> `systemctl --user restart hermes-gateway` -> health check -> **automatic rollback to the recorded old rev on failed restart**. Write a receipt to `~/.hermes/logs/local_update_receipts/` (old/new rev+version, backup path, health result).

- **Expect the update to kill your own session**: restarting the gateway terminates every in-flight conversation on it (Telegram/CLI). Schedule long updates, then verify the receipt and gateway health AFTER reconnecting — never assume the update failed because the session dropped; the receipt is the source of truth.

## Step 3 — Model-default diagnosis

Documented semantics: `/model <name>` is session-only; `--global` persists to config.yaml; `/new`/`/reset` clears the session override. Before 'repairing' anything:

1. Read `~/.hermes/config.yaml` `model:` block (`default`, `provider`, `base_url`, `api_mode`) and grep config/.env/auth.json for model aliases — with keys redacted.
2. If the persistent default is already correct but a `/new` still returns the old model, the likely cause is a live session override or a gateway process running old config — a gateway restart resolves it; do not invent YAML keys.
3. Verify local endpoints from the RUNTIME the gateway actually uses: the gateway is a host process, so a host-loopback URL (e.g. a local llama.cpp server on port 8080) is correct for it even though the Docker tool sandbox cannot reach that loopback. Confirm with `/v1/models` from the host.

## Step 4 — Scheduling

systemd user timers (Persistent=true): daily backup 02:30, portable-brain sync 03:00, update 03:15. The updater MUST run backup-hermes.sh first regardless of the daily backup. Keep a separate Hermes-cron sync job from going stale — if a sync has not fired recently, replace it with a timer.

## Step 5 — Delivery conventions for repair work

Jordan's repair tasks run as: detailed Markdown worklog updated during execution + final handoff .md, committed and pushed to the designated repo/branch (checkpoint commits per validated phase, never one giant push), final `git rev-parse HEAD` == `origin/<branch>` verified. Never commit .env, auth.json, live DBs, or raw logs. The user prefers autonomous execution — non-blocking questions only; when a channel keeps failing, write the handoff instead of stalling.
