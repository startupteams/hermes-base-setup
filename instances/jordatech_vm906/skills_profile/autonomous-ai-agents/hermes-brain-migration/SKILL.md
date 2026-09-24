---
name: hermes-brain-migration
description: "Migrate/sync portable brain state between Hermes instances (skills, SOUL, memories, conversation history) via Git — additive-only, never touching runtime config or live DBs."
version: 1.1.0
author: agent_stea004_entrepreneur
license: MIT
metadata:
  hermes:
    tags: [hermes, migration, profiles, git, multi-agent, backup, secrets]
    related_skills: [hermes-agent, github-repo-management]
---

# Hermes Brain Migration

Move/sync the durable "brain" of one Hermes agent instance (VM/desktop/profile) to another via a Git repository, without overwriting the destination's working configuration, credentials, or live databases. Proven end-to-end VM906 → MIAM-00101 (2026-09-24).

## WHEN TO USE

- "Migrate my Hermes agent / brain / skills / memory to the new machine"
- "Share knowledge between two Hermes instances" (multi-agent sync model)
- Replacing a whole-directory git sync of a live `~/.hermes` with a portable export
- Any plan that says "do not overwrite config/credentials/state.db on the destination"

## CORE MODEL (non-negotiable)

| Synced via Git | Stays local (NEVER copy) |
|---|---|
| SOUL.md variants, skills, MEMORY.md/USER.md, shared knowledge | `.env`, `auth.json`, `config.yaml`, `install_id`, gateway/cron state, caches |
| Conversation exports (MD/JSONL + INDEX) | live `state.db` / any SQLite + `-wal`/`-shm` |
| Manifests, instance.yaml, migration metadata | SSH keys, tokens, request dumps |

**Additive-only on the destination:** skills import with `rsync --ignore-existing` (destination wins conflicts; write a conflict report for later semantic merge). SOUL is never overwritten — source variants land in `~/.hermes/migration_sources/<instance>/`. Memories land in namespaced dirs (`memories/imported_<instance>/`). Verify config integrity with sha256 checksums before/after; fail loud on any change.

## WORKFLOW (source side)

1. **Backup first:** `~/hermes-migration-backups/<stamp>/` with source-info, file manifest, and copies of any script you will modify.
2. **Discover the REAL sync before touching it.** Check `hermes cron list` (no-agent jobs with scripts) — the plan's named script is often NOT the active committer. Inspect `git -C ~/.hermes remote -v; git log --oneline -5` for a high-frequency commit loop. Preserve every old script before rewiring.
3. **Export portable state** outside the live dir: SOUL copies, `rsync -a --exclude='.usage.json' --exclude='.curator_state' --exclude='.curator_ledger.jsonl'` for BOTH global and profile skills (profile skills are usually the live brain), profile `memories/` (MEMORY.md/USER.md are the real durable memories — top-level `~/.hermes/memories` is often empty; don't conclude "no memory" from that).
4. **SQLite snapshots via Python online backup** (sqlite3 CLI often absent; sudo may be password-gated):
   ```python
   s = sqlite3.connect(src); d = sqlite3.connect(dst)
   with d: s.backup(d)   # WAL-safe with a live gateway
   # validate: PRAGMA quick_check == 'ok'
   ```
   DBs are backup/import-source artifacts — keep OUT of git (`.gitignore` blocks `*.db`).
5. **Conversation history:** `hermes import` (v0.17) is **replacement-restore semantics — NEVER use it to merge into a live agent**. Use `hermes sessions export` (safe JSONL) or the DB-archive exporter (see `scripts/export_conversations.py` under this skill): per-session Markdown + INDEX.md + JSONL, secret-scrubbed at source.
6. **Repo:** clone into a separate path (never turn live `~/.hermes` into the repo), create an instance branch, copy portable content under `instances/<id>/`, extend `.gitignore` to whitelist `instances/` while explicitly blocking `instances/**/.env|auth.json|*.db|*.key|...`, commit, push.
7. **Rewire the old sync** to a portable exporter that: refreshes SOUL/skills/memories + DB snapshots + conversation archive, then `git pull --rebase --autostash`, commit only on change, push. For Hermes cron: script must live in the **profile** `scripts/` dir and the cron `script` field takes a **relative filename** (`no_agent: true`).

## WORKFLOW (destination side)

Run `DRY_RUN=1` first (backup + checksums only), then full: backup → clone/fetch source branch into a temp worktree → additive skills import (`--ignore-existing` + `diff -qr` conflict reports) → SOUL comparison copies → namespaced memories → conversation archive into `memories/imported_<instance>_history/` → create destination instance branch + push → checksum re-verify → `PRAGMA quick_check` on destination `state.db`. See `templates/import-portable-brain.sh`.

**Two script bugs that cost three run attempts (fix present in the template, re-verify if hand-rolling):**
1. **Branch the destination instance from the SOURCE branch, not `main`.** `main`'s `.gitignore` usually still blocks `instances/`, so `git add instances/<id>` fails with "paths are ignored". Branch from `origin/<source-branch>` where the whitelist exists.
2. **`git fetch origin <branch>` does NOT update `refs/remotes/origin/<branch>`** — it only sets `FETCH_HEAD`. A following `git switch -c <new> origin/<branch>` silently lands on a STALE ref (initial-clone vintage) and the "fixed" script reruns the old bug. Use the refspec form: `git fetch origin '+refs/heads/<branch>:refs/remotes/origin/<branch>'` before branching from it.

## PITFALLS

- **GitHub Push Protection is the backstop, not regex scrubbing.** Real secrets (Vercel `vck_`/`vcp_` tokens, Google OAuth client IDs + `GOCSPX-` secrets) hid inside old session tool output. If a push is rejected: scrub at SOURCE, then **rebuild the branch history from main** — ancestor commits are scanned too, incremental fix-commits still push the dirty tree. Never allowlist-and-force.
- `git reset --hard main` / `git switch` **reverts your `.gitignore` whitelist edits** on a shared branch — re-apply the ignore rules after any hard reset.
- Ignore-everything `.gitignore` (`*` + `!dir/` `!dir/**`) needs BOTH the dir and `**` lines; verify with `git check-ignore -v <probe-file>` before committing.
- Pull with `--rebase --autostash` in automated sync scripts, or unstaged changes block the pull.
- SQLite `.backup()` (Python API) is the only safe copy against a WAL-active gateway; file-copying the .db is not.
- Destination machine not a PVE guest? Check the tailnet (`tailscale status` from the router CT, e.g. miam-00133 CT100) — desktops often live there, not in the cluster. "connection refused" on :22 = host reachable, sshd not running (user action needed); timeout = filtered.
- **Tailscale SSH check-mode (the Omen path, proven 2026-09-25):** even after the user runs `systemctl enable --now sshd`, plain SSH to the peer's tailnet IP can HANG/TIMEOUT (not refuse) because the relay CT's tailscaled (TUN mode + RunSSH=true) intercepts :22 and fronts it with Tailscale-SSH. `tailscale ssh user@<peer-ip>` then prints a one-time browser approval URL (`https://login.tailscale.com/a/...`). Working access recipe: miam-00133 → `pct exec 100 -- tailscale ssh jordatech@100.69.169.125 'bash -s' <<'EOF' ... EOF` — but only AFTER the user approves the URL once (new URL per attempt; fresh one from a fresh attempt, hand it to the user, then retry). Funnel all Omen work through a single relay runner (`scripts/omen_run.py` under this skill) that streams scripts over `tailscale ssh` — heredoc-over-ssh works fine once approved. Password-auth attempts (SSH_ASKPASS) and LAN IP discovery both dead-end here: the Omen had no reachable LAN IP (Windows dual-boot side owned the only LAN MAC), so the tailnet relay is the ONLY path.
- PVE API auth needs realm suffix (`root@pam`), creds files often store bare `root`.

## SUPPORT FILES

- `references/vm906-omen-migration-20260924.md` — full case file: branches, cron job IDs, secret incident, Omen access discovery
- `references/omen-execution-20260925.md` — Omen-side completion case file: check-mode access, refspec-fetch bug, import verification results
- `references/secret-scrub-and-push-protection.md` — scrub patterns + unblock playbook
- `references/hermes-portability-tooling.md` — sessions/import semantics, state.db schema notes
- `scripts/export_conversations.py` — re-runnable conversation-archive exporter from DB snapshots
- `scripts/omen_run.py` — tailscale-ssh relay runner for driving the Omen (MIAM-00101) over the CT100 bridge
- `templates/import-portable-brain.sh` — destination-side additive importer (DRY_RUN support)
- `templates/portable-brain-sync.sh` — hourly portable exporter for cron rewiring
