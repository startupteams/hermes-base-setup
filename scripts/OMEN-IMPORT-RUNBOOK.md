# Omen (MIAM-00101) Import Runbook — VM906 Brain Migration

**Status:** VM906 side complete. Omen side = one script, ready to run.
**Repo:** `startupteams/hermes-base-setup` · Branch with the brain: `jordatech_vm906` (pushed 2026-09-24)

## What already happened (VM906 side — DONE)

| Phase | Result |
|-------|--------|
| A | Backup `~/hermes-migration-backups/20260924-175641/` (manifest 842 files) |
| B | Old git state captured; **real** 5-min sync = cron `hermes-stea-crmmiam02-backup` (whole `~/.hermes`, incl. config.yaml → public-adjacent startupteams repo — hygiene issue now fixed) |
| C–F | Portable export in `/home/jordatech/hermes-portable-export/` (SOULs ×2, 16M global skills, 26M profile skills, MEMORY.md/USER.md, 186-session/20,867-message archive, 3 SQLite snapshots quick_check=ok) |
| G | Hermes v0.17 native `import` = replacement-restore → **rejected**; archive route used |
| H | Conversation export complete; secret-scrubbed at source (GitHub Push Protection caught real Vercel `vck_`/`vcp_` tokens + Google OAuth creds in June-2026 tool outputs — all redacted, push then accepted) |
| J | Branch `jordatech_vm906` pushed: 1,470 files, clean history (rebuilt from main after the flagged commit) |
| K | Old 5-min cron removed; new hourly `portable_brain_sync.sh` cron installed (job `0c9b84306a9f`, no-agent) |

## How to run the Omen side

**Prereq:** Omen online (Tailscale name `miam-00101-1-omarchy`, IP `100.69.169.125` — verified online 18:14 UTC via CT100 tailscale-router) AND either:
- SSH reachable (currently **refused — sshd not running**; enable with `sudo systemctl enable --now sshd`), or
- Jordan / the Omen's own Hermes agent runs it locally on the Omen.

```bash
# On the Omen:
cd ~
git clone https://github.com/startupteams/hermes-base-setup.git hermes-base-setup
cd hermes-base-setup
chmod +x scripts/import-portable-brain.sh
DRY_RUN=1 ./scripts/import-portable-brain.sh   # backup + checksums only, zero writes
./scripts/import-portable-brain.sh             # full import (additive only)
```

The script:
- backs up SOUL/skills/memories/sessions + consistent `state.db` first
- never touches `.env`/`auth.json`/`config.yaml`/`install_id` (checksum-verified before/after — fails loud if changed)
- imports skills additively (`--ignore-existing`; Omen wins conflicts; conflict reports written)
- drops SOUL variants into `~/.hermes/migration_sources/vm906/` (semantic merge = manual agent task, never auto-overwrite)
- namespaces memories under `~/.hermes/memories/imported_vm906*`
- installs the 186-session conversation archive at `~/.hermes/memories/imported_vm906_history/`
- creates + pushes branch `jordatech_miam00101_omarchy` with the Omen's own instance metadata
- dry-run mode supported (`DRY_RUN=1`), idempotent on re-run

## After-import agent tasks (Omen Hermes)

1. **SOUL merge:** read `~/.hermes/SOUL.md` + `~/.hermes/migration_sources/vm906/SOUL-{global,profile}-vm906.md`; propose merge preserving Omen runtime config + useful VM906 identity/ops knowledge; backup SOUL first.
2. **Skill conflicts:** review `~/hermes-skill-conflicts-{global,profile}.txt`; merge useful VM906 customizations only after inspection (plan §16.1).
3. **Verification questions (plan §19):** answer the 7 questions; write answers to `instances/jordatech_miam00101_omarchy/metadata/migration-verification.md`.
4. **Phase R:** give the Omen its own hourly exporter mirroring `portable_brain_sync.sh` (source pattern: `instances/jordatech_vm906` layout + `~/.hermes/scripts/portable_brain_sync.sh` on VM906).

## Rollback

Everything the import writes is additive under `~/.hermes/{skills,memories,migration_sources}` — remove those additions to revert. Full backup of overwritten-able state: `~/hermes-migration-backups/<stamp>/` (incl. consistent `state.db`).

## Success criteria mapping (plan §23)

- [x] VM906 still runs normally (gateway untouched, live session continued)
- [x] Old VM906 data intact (backups + old script preserved)
- [x] `jordatech_vm906` exists, committed, pushed
- [ ] Omen config unchanged — **enforced by script (checksum gate)**, verify at run time
- [ ] Omen retains existing sessions — script never touches `state.db`
- [ ] VM906 skills on Omen — script phase N.1
- [ ] VM906 persona/knowledge on Omen — phases N.2/N.3
- [ ] History searchable archive — phase O
- [ ] `jordatech_miam00101_omarchy` exists — script phase M
- [ ] Both agents export independently — VM906 done; Omen Phase R post-import
- [ ] No SQLite-over-git — enforced (.gitignore blocks `*.db`; sync script never stages them)
- [x] Rollback backups on both machines
- [x] Old whole-`~/.hermes` git sync replaced with portable-brain sync
