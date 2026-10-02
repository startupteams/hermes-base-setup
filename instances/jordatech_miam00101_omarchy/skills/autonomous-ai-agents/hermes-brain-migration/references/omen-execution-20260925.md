# Omen (MIAM-00101) execution case file — 2026-09-25

Completion record of the destination side of the VM906 → MIAM-00101 migration.
All facts measured, not assumed.

## Access path (the hard part)

- The Omen is **not a PVE guest** — physical HP Omen desktop, dual-boot
  (Omarchy linux + Windows), on the tailnet as `miam-00101-1-omarchy`
  @ `100.69.169.125` (linux) and `miam-00101` @ `100.125.115.96` (windows).
- Discovery: SSH to miam-00133 → `pct exec 100 -- tailscale status` (CT100
  tailscale-router). `tailscale ping <peer>` works (DERP relay) even when no
  TCP port answers.
- **Signature table for :22 against a tailnet peer:**
  | Result | Meaning |
  |---|---|
  | connection refused | tailscaled forwards, no sshd behind (sshd not running) |
  | TCP connect timeout / hang | tailscaled intercepts :22 (TUN + RunSSH) and fronts Tailscale-SSH |
  | `# Tailscale SSH requires an additional check` + login.tailscale.com/a/<id> URL | Tailscale-SSH check-mode: user must open the URL once |
- Plain `sshd` enabled via `systemctl enable --now sshd` did NOT make port 22
  answer plain SSH — the CT100 tailscaled interception shadows it. LAN side
  dead-ended too (Windows side owned the only LAN MAC, 1c:2a:a3 @ .120).
- **Working recipe:** fresh `tailscale ssh jordatech@100.69.169.125 'echo ok'`
  from CT100 → read the fresh check URL → user opens it in any browser →
  immediately retry with `tailscale ssh jordatech@<ip> 'bash -s' <<EOF ... EOF`.
  Once approved, heredoc-streamed scripts work perfectly (whole import driven
  this way, incl. 1.4k-file rsync + git push).
- `tailscale ssh` CLI does NOT take `-o` flags (it's a thin wrapper, not ssh).
  No sshpass needed: auth is identity-based.

## Import execution timeline (all +05:45, Nepal — mind TZ math on Omen crons)

1. `DRY_RUN=1` pass: 5.2 MB backup + config checksums only. 5 s.
2. Full run **attempt 1**: hit `.gitignore` bug — script was on branch created
   from `main`, whose ignore-everything rules block `instances/`; `git add`
   refused; `set -e` aborted. Fix: branch instance from `origin/jordatech_vm906`.
3. **Attempt 2**: "branch already exists" from the half-created attempt → clean
   slate each rerun (`git branch -D`), then attempt 3 revealed the refspec bug:
   `git fetch origin jordatech_vm906` set only FETCH_HEAD; the clone's stale
   `refs/remotes/origin/jordatech_vm906` (initial-clone vintage, pointing at
   main's tip) was used by `git switch -c ... origin/jordatech_vm906`. The
   "fixed" script reran the OLD code. Fix:
   `git fetch origin '+refs/heads/<b>:refs/remotes/origin/<b>'`.
4. **Attempt 3 (green):** full import in ~50 s wall (skills rsync dominated).
   All gates green (see verification below).

## Import verification results

- Config checksums UNCHANGED (`.env`, `auth.json`, `config.yaml`, `install_id`)
- `state.db` quick_check ok; Omen's 4 pre-existing sessions intact
  (the Desktop gateway was LIVE during import — `.backup()` stayed consistent)
- Skills: additive `--ignore-existing` → 35 categories on the Omen
- Memories: `memories/imported_vm906{,_shared}/` (MEMORY.md, USER.md)
- History: `memories/imported_vm906_history/` — INDEX.md, 186 session MDs,
  `raw/{sessions,messages}.jsonl`
- SOUL: variants in `migration_sources/vm906/`, then semantic merge applied
  (Omen's short direct-style preamble KEPT as the base; inherited
  entrepreneur/infra role + constraints appended; VM906's router-SOUL
  deliberately NOT imported — VM906-specific orchestration role). Backup:
  `SOUL.md.backup-pre-vm906-merge-*`
- Conflict reports: `~/hermes-skill-conflicts-{global,profile}.txt` (252 lines)

## Post-import wiring

- Branch `jordatech_miam00101_omarchy` created from the fixed script, pushed
  (instance.yaml, migration-verification.md with §19 answers, merged SOUL,
  synced skills, IMPORT-COMPLETE.txt). Jordan directive: the Omen USES this
  branch as its home branch.
- Phase R: `~/.hermes/scripts/portable_brain_sync.sh` on the Omen (exports
  SOUL/skills/memories to `instances/jordatech_miam00101_omarchy/`, autostash
  pull --rebase, commit-only-on-change, push) + Hermes cron
  `150481b491a9` (0 * * * *, no-agent, --deliver local).
- Omen Hermes: venv python 3.11.16, model z-ai/glm-5.3-flash via custom
  endpoint; gateway + TUI slash-worker confirmed running after import.

## Small operational notes

- Omen has real `sqlite3` CLI, python 3.14 system / 3.11.16 venv, rsync, gh
  (logged in as jordatech, keyring) — richer tooling than VM906.
- Hermes cron on the Omen: `~/.hermes/hermes-agent/venv/bin/hermes cron create
  --script portable_brain_sync.sh --no-agent --deliver local '0 * * * *'`
  (script path relative to `~/.hermes/scripts/` — no profile dir on a
  default-profile install).
- Writing files remotely: avoid Python `.format()` on scripts containing bash
  `{}` braces (KeyError) — use plain concatenation, or base64 the payload.
- Cleanup: any staged password files on relay nodes (e.g. /tmp/.omenpw on
  miam-00133) must be removed after use.
