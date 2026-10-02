# Case: VM906 → MIAM-00101 brain migration (2026-09-24)

Full session detail for the proven end-to-end run. Repo: `startupteams/hermes-base-setup`.

## Environment discovered (matters for repeats)

- **The active sync was NOT the plan's named script.** `hourly_git_sync.sh` was orphaned
  (expects `jordatech/crmmiam01_hermes@main`, hardcodes `HOME=/home/miam`). The REAL
  committer (every 5 min, empty commits) was Hermes cron `hermes-stea-crmmiam02-backup`
  (job `37a454b1279d`) running profile script `hermes-stea-crmmiam02-backup.sh`:
  `git pull || ...; git push; git add -A; commit (empty ok); pull --rebase; push` — pushing
  the whole live `~/.hermes` INCLUDING `config.yaml` to
  `startupteams/agentifyme_stea_hermes_memory_and_skills@jordatech_crmmiam02_906`.
- Live `~/.hermes` is a git repo with ignore-everything whitelist (skills/SOUL/config).
- Global skills 16 MB; profile skills 26 MB (the live brain). Top-level
  `~/.hermes/{memories,shared}` effectively empty; durable memory = profile
  `memories/MEMORY.md` + `USER.md` + `memory_store.db`.
- sqlite3 CLI absent, sudo password-gated → python3 `sqlite3` online `.backup()` used
  for all three DBs (state 245 MB / memory_store / verification_evidence);
  `quick_check: ok` each; gateway (PID 285) stayed live throughout.
- state.db schema: `sessions` (186; id TEXT, source, model, system_prompt, title,
  started_at/ended_at REAL, message_count, chat_id...), `messages` (20,867; id INTEGER,
  session_id, role, content, tool_name, tool_calls, timestamp, token_count, active,
  compacted), `messages_fts*`, `state_meta`, `compression_locks`.
  memory_store.db: `facts(fact_id, content, category, tags, trust_score, hrr_vector...)`,
  `memory_banks(bank_id, bank_name,...)`. NOTE: facts has NO bank_id column — don't join on it.
- Native tooling: `hermes sessions export` = safe JSONL. `hermes import <zip>` =
  replacement-restore (rejected). `hermes profile export` = tar.gz of full profile
  (captures config/env — not for sharing). `hermes_state_portability.py` not in v0.17 tree.

## What was produced

- `~/hermes-migration-backups/20260924-175641/` (source-info, 842-file manifest, 3 old
  sync scripts preserved) + `HERMES_MIGRATION_COMPLETION_REPORT.md` (also committed to
  the branch under `instances/jordatech_vm906/metadata/`).
- `/home/jordatech/hermes-portable-export/` (326 MB): brain/, skills/, skills_profile/,
  knowledge/, conversation_exports/ (186 session MDs + INDEX.md + sessions.jsonl +
  messages.jsonl + memory_records.jsonl), metadata/ (3 DB snapshots + manifest), scripts/.
- Branch `jordatech_vm906` (1,473 files; final `853fce8`): seed export + rescrub +
  import script/runbook + completion report. `.gitignore` extended: `!instances/`
  `!instances/**` + explicit `instances/**` blocks for .env/auth.json/config.yaml/
  google_*/*.db/*.key/*.lock/.usage.json.
- Cron rewired: removed `37a454b1279d`; created no-agent job `0c9b84306a9f`
  "VM906 portable-brain sync" `0 * * * *` → profile wrapper
  `portable_brain_sync.sh` → exec `~/.hermes/scripts/portable_brain_sync.sh`
  (SOUL copies, rsync --delete skills with curator exclusions, memory rsync, python DB
  snapshot refresh, re-run export_conversations.py, autostash-pull / commit-only-on-change /
  push; flock; log at `hermes-portable-export/portable-brain-sync.log`).
- agents.md: "2026-09-24 — VM906 → MIAM-00101 Hermes brain migration" entry (Surprise Protocol).

## Secret incident (the big one)

First push of `jordatech_vm906` REJECTED by GitHub Push Protection. Four detectors fired:
Google OAuth Client ID, Google OAuth Client Secret, Vercel API Key, Vercel Personal
Access Token — 22 locations, all in June-2026 session exports (Vercel-login sessions
2026-06-23…07-06 where pasted configs / `export VERCEL_TOKEN=...` landed in tool output:
`messages.jsonl` lines 58/64/900/901/1143/1144 + several `sessions/2026062*.md`).
Second push attempt surfaced MORE (`vcp_4Oik…` — a second token prefix) — iterative
scrubbing is normal. Tokens seen: `vck_5rBj85tg…`, `vcp_4Oik…`.
Resolution: SECRET_SUBS extended at source in `export_conversations.py`
(vck_/vcp_, `*.apps.googleusercontent.com`, GOCSPX-, `"token":"<20+ chars>"`,
VERCEL_TOKEN=), full re-export, **branch deleted and rebuilt from main** (clean single
commit), push accepted. Completion report + final commit pushed after.

## Destination (Omen) discovery — for the pending Phases L–R

- MIAM-00101 is a physical HP Omen, NOT a PVE guest (verified across all 16 nodes,
  44 guests). Dual-boot, both on tailnet:
  - Omarchy (linux): `miam-00101-1-omarchy` @ `100.69.169.125` — Online: true, via DERP
    relay `ord`, created 2026-09-24T16:47Z (same day). Node ID `nYRjAbNG3c11CNTRL`.
  - Windows: `miam-00101` @ `100.125.115.96` — offline since ~15:25Z.
- Access pattern: SSH to PVE node 10.0.20.133 (miam-00133) →
  `pct exec 100 -- tailscale ping miam-00101-1-omarchy` (works, 51–56 ms via DERP).
- Port probes from VM906 (not on tailnet) all time out; from CT100, Tailscale SSH shows
  `dial tcp 100.69.169.125:22: connect: connection refused` = **host reachable, sshd not
  running** (user action: `sudo systemctl enable --now sshd`). RustDesk ports
  (21115–21119) and PeerAPI closed.
- PVE access: creds at
  `~/.hermes/profiles/agent_stea004_entrepreneur/cache/secrets/miam_pve_creds.json`;
  auth requires `root@pam` realm suffix; ticket via `/api2/json/access/ticket`; inventory
  via `/nodes` + `/nodes/<n>/{qemu,lxc}`.
- clarify() to user timed out after 10 min → pivoted to runbook delivery per standing
  "roadblock → pivot" directive.

## Handoff pointers

- **Phases L–R were completed 2026-09-25 — see `references/omen-execution-20260925.md`**
  for the destination-side case file (check-mode access recipe, the two import-script
  bugs + fixes, verification results, Phase R wiring).
- Import script + runbook ON the branch:
  `scripts/import-portable-brain.sh` (DRY_RUN, additive-only, checksum-gated) and
  `scripts/OMEN-IMPORT-RUNBOOK.md`.
- Omen post-import: SOUL semantic merge from `migration_sources/vm906/`, conflict
  review (`hermes-skill-conflicts-{global,profile}.txt`), plan-§19 answers →
  `migration-verification.md`, Phase R hourly exporter, Hermes Desktop start check.
- Next: curate `main` as shared baseline; instance branches feed it via review/normalize.
