# VM906 → MIAM-00101 Hermes Brain Migration — Completion Report (VM906 side)

**Date:** 2026-09-24 · **Executor:** agent_stea004_entrepreneur (Hermes, VM906, self-migration)
**Plan:** `HERMES_MULTI_AGENT_BRAIN_MIGRATION_AND_SYNC_PLAN.md`

## 1. Identifiers

| | |
|---|---|
| Source | VM906 (`hermes-jordan`, LXC 906 on miam-00100) · profile `agent_stea004_entrepreneur` |
| Destination | MIAM-00101 HP Omen / Omarchy · `~/.hermes` (default profile) |
| Repository | `https://github.com/startupteams/hermes-base-setup` |

## 2. Branches created

- **`jordatech_vm906`** — pushed ✔ (`1f57d18`), 1,473 tracked files:
  `instances/jordatech_vm906/{brain,skills,skills_profile,knowledge,conversation_exports,metadata}`
  + `scripts/import-portable-brain.sh` + `scripts/OMEN-IMPORT-RUNBOOK.md` + `.gitignore` update.
- **`jordatech_miam00101_omarchy`** — NOT yet created (needs the Omen; script phase M does it).

## 3. Migrated / excluded (detail)

**Exported to branch:** 2 SOUL variants · 16 MB global skills + 26 MB profile skills
(the live brain) · `MEMORY.md` + `USER.md` durable memories · full conversation archive
(**186 sessions, 20,867 messages**: per-session MD + INDEX.md + JSONL) · migration manifest.
**Deliberately excluded:** `.env`, `auth.json`, `config.yaml`, `install_id`,
`gateway_state.json`, `channel_directory.json`, locks/caches/cron state, `*-wal/*-shm`,
hermes-agent source/venv, and all 3 SQLite DBs (backup artifacts only,
kept in `/home/jordatech/hermes-portable-export/metadata/`, quick_check=ok, 246 MB state).

## 4. Conversation-history method

Hermes v0.17 native `hermes import` = **replacement-restore → rejected** (plan §9 rule).
Used archive route: `export_conversations.py` (re-runnable) → JSONL + per-session MD + index.
Omen gets it at `~/.hermes/memories/imported_vm906_history/` — searchable knowledge,
no DB merge, no session-ID risk.

## 5. Secrets incidents (important)

First push **rejected by GitHub Push Protection** — real secrets my scrubber missed in
June-2026 session tool outputs: **Vercel tokens (`vck_…`, and a second variant `vcp_…`)
+ Google OAuth client IDs + `GOCSPX-…` secret** (pasted configs during Vercel login work,
sessions 2026-06-23 → 07-06). Fix: scrubber patterns extended **at source**, export
re-run, **branch history rebuilt from main** (ancestors are scanned too), re-push accepted.
No secrets reached the remote at any point (all pushes declined before acceptance).
**Lesson recorded in agents.md: regex scans are not a backstop; Push Protection is.**

## 6. Git synchronization change on VM906 (Phase K)

- Discovered the REAL live sync: Hermes cron `hermes-stea-crmmiam02-backup` — every
  5 min, empty commits, pushing the **whole live `~/.hermes`** (incl. `config.yaml`)
  to `startupteams/agentifyme_stea_hermes_memory_and_skills@jordatech_crmmiam02_906`.
  Plan's `hourly_git_sync.sh` was orphaned (expects `crmmiam01_hermes@main`, `HOME=/home/miam`).
- **Removed** the 5-min cron (`37a454b1279d`). **Installed** hourly no-agent cron
  `portable_brain_sync.sh` (job **`0c9b84306a9f`**): refreshes SOUL/skills/memories +
  DB snapshots + conversation archive into `instances/jordatech_vm906/`, autostash-pull
  --rebase, commit only on change, push. Verified live: end-to-end run OK, push OK
  (`3e8be91`). Both old scripts preserved in
  `~/hermes-migration-backups/20260924-175641/scripts/`.

## 7–10. SOUL / checksums / integrity

- Omen SOUL untouched (nothing executed there); both VM906 SOUL variants on the branch
  for the semantic merge. VM906's own SOULs untouched.
- No Omen-side execution yet — checksum gate is built into the import script (fails loud).
- SQLite: online `.backup()` (python3 API; sqlite3 CLI absent, sudo password-gated)
  against the LIVE gateway — `quick_check: ok` on all 3.

## 11. Rollback locations

| Machine | Location |
|---|---|
| VM906 | `/home/jordatech/hermes-migration-backups/20260924-175641/` (manifests, all old sync scripts) |
| VM906 | `/home/jordatech/hermes-portable-export/` (326 MB; DBs + full export) |
| Omen | `~/hermes-migration-backups/<stamp>/` (created by import script before any write) |

Old cron can be restored by re-adding `hermes-stea-crmmiam02-backup` (script intact).

## 12. Unresolved conflicts / blockers

1. **Omen unreachable for Phases L–R:** `miam-00101-1-omarchy` (`100.69.169.125`,
   tailnet, online via DERP) — port 22 **refused** (no sshd). All other access paths
   probed (RustDesk ports, PeerAPI, Windows side offline). Options: enable `sshd` on
   Omen → remote run; or run `import-portable-brain.sh` locally on the Omen.
2. Skill conflicts: unknown until Omen import runs; script writes
   `~/hermes-skill-conflicts-{global,profile}.txt` and imports additively
   (Omen versions win) — semantic merge is a post-import agent task.
3. Empty `knowledge/memories`/`shared` at top level — documented, not an error
   (durable knowledge lives in profile memories + DBs).

## 13. Recommended next steps (shared-brain workflow, plan §21)

1. Enable sshd on Omen (or run script locally) → execute `import-portable-brain.sh`
   (`DRY_RUN=1` first) → creates `jordatech_miam00101_omarchy` branch.
2. Omen Hermes: SOUL semantic merge from `migration_sources/vm906/` (backup first).
3. Review `hermes-skill-conflicts-*.txt`; merge useful VM906 customizations only.
4. Answer plan-§19 questions → `migration-verification.md` on the Omen branch.
5. Phase R: Omen's own hourly exporter (mirror of `portable_brain_sync.sh`).
6. Later: curate `main` as the shared baseline; instance branches feed it via
   review/normalize (never instance-to-instance DB merges).

## Success criteria (plan §23)

VM906-side all ✔ (agent running, data intact, branch live, sync rewired, backups, no
DB-over-git). Omen-side items pending import execution — checklist in
`scripts/OMEN-IMPORT-RUNBOOK.md`.
