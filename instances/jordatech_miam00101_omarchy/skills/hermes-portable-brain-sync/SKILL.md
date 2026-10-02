---
name: hermes-portable-brain-sync
version: 1.1.0
description: "Sync portable Hermes context between VM906 and MIAM hosts."
tags: [hermes, sync, git]
related_skills: [degraded-tool-fallbacks]
---

# Hermes Portable-Brain Sync (VM906 <-> MIAM-00101)

## When to Use

Any task that moves durable context (skills, memories, handoff docs) between Hermes hosts through `startupteams/hermes-base-setup` instance branches — never by copying runtime state. VM906/STEA-004 is the protected canonical baseline; MIAM-00101 is an independent runtime identity.

## Branch model (always-on rules)

- **`jordatech_vm906` is the MASTER branch.** VM906 is its only writer (`sync_memory.sh` hard-guarded to refuse any other branch). Never commit worker state to `main`.
- **MIAM-00101 is a pull-only follower.** It runs `~/.hermes/scripts/vm906_master_pull.sh` via `hermes-brain-sync.timer` — read the unit's `OnCalendar` live for the real cadence (currently daily 03:00 +0545, not the 3-hourly some handoffs claim): fetch `origin/jordatech_vm906`, additively apply skills (rsync WITHOUT `--delete` — master wins conflicts, MIAM-local skills are never deleted), refresh `memories/imported_vm906/MEMORY.md`. It must not push any branch.
- `jordatech_miam00101_omarchy` is a FROZEN historical archive — no host writes to it. To make a MIAM-local skill or memory change canonical, promote it through VM906 (or a reviewed manual commit) to `jordatech_vm906`; do not resurrect the push-exporter.
- Sync from master is additive: propagate additions/modifications; NEVER propagate deletions to the live host (the host may legitimately keep files the master deleted).
- Every automated sync script must hard-pin its branch with a guard that aborts on mismatch (`current_branch != ALLOWED_BRANCH -> fail`), and push must name the branch explicitly.
- Before pushing to any shared branch: `git fetch`, `git log origin/<branch> -3` for other writers, rebase, then push.

## Instance-dir mapping

Repo layout is `instances/<instance_id>/{brain,memories,skills,metadata}`. Skills on VM906 live under `skills_profile/<category>/<skill>/`, on MIAM under `skills/<category>/<skill>/` — map `skills_profile/*` -> `skills/*` when syncing VM906->MIAM. Live apply on a host is `rsync -a instance/skills/ ~/.hermes/skills/` after a timestamped tar backup of `skills` + `memories`.

## Procedure (source -> target)

1. Verify both host identities live (hostname, user, branch, HEAD) — never trust remembered IPs or branch names.
2. Confirm the source branch is pushed and clean; record the source SHA.
3. In a clean clone, `git diff --name-status origin/<target>..origin/<source>` and classify every path: PORTABLE (skills/references/templates, non-secret markdown), EXCLUDE (conversation_exports/**, sessions, *.db, .curator_backups, .env, auth.json, config.yaml), TARGET_ONLY (preserve target's versions; do not delete).
4. For PORTABLE files that exist on both sides, run a reverse-diff (`comm -13` of sorted lines) to find target-only content; carry it over by appending to the source version — never blind-replace a skill the target has evolved.
5. Run a secret scan over the staged diff (grep for key/token/private-key patterns over added lines only); document every hit as false positive or remediate before push.
6. Commit on the TARGET branch (rebase onto it first — automated writers) and push.
7. Apply on the target host: backup `skills` + `memories` to a timestamped tar, rsync the instance dirs into `~/.hermes/`, then diff-verify 2-3 representative files against the repo copy before reporting success.
8. Confirm the target's Hermes gateway is still healthy after apply.

## Project-context install (agent-context repo)

Portable project summaries live in `startupteams/agent-context:01-projects/` (19 files + `INDEX.md`). Canonical target is `~/.hermes/context/` with a compatibility symlink so Hermes memory discovery finds them:

1. Verify the host and that `~/Work/agent-context` is on `main` and fetched.
2. Run `05-scripts/install_project_context.sh --target ~/.hermes` (DRY-RUN) first, review the file list, then re-run with `--apply`. The installer copies `01-projects/*.md` to `~/.hermes/context/projects/`, installs `PROJECT_INDEX.md` + a `SOURCE.md` stamped with the source git SHA, and backs up any prior context dir to `.backup-<UTC>`.
3. Compat symlink: `mkdir -p ~/.hermes/memories && ln -sfn ~/.hermes/context/projects ~/.hermes/memories/projects`. If `~/.hermes/memories/projects` already exists as a real dir, inspect it before replacing — do not delete useful local content.
4. Verify: index + all project files readable through BOTH paths, symlink resolves, `SOURCE.md` names the source commit.

Claude global context is a separate install from the same repo: back up any existing `~/.claude/CLAUDE.md`, `rules/`, `agents/`, `skills/`, then copy from `02-claude/` per `02-claude/INSTALL.md` — merge, never blind-replace, and never touch auth/config files.

## Timer-run acceptance check (follower sync)

Verify an UNATTENDED scheduled run without triggering it: confirm `systemctl --user status hermes-brain-sync.timer` is enabled and shows the next fire, wait past that time, then inspect `systemctl --user status hermes-brain-sync.service`, `journalctl --user -u hermes-brain-sync.service --since '<window>'`, and the sync log (`~/Work/hermes-base-setup/.git/vm906-master-pull.log`). Confirm: ran OK, fetched from `jordatech_vm906`, refreshed `imported_vm906/MEMORY.md`, skills additive-only, and no MIAM-local secrets/runtime state touched. Byte-compare synced master-managed files against `origin/jordatech_vm906` when practical. Do not mark the task complete if any verification step failed.

Only a run whose invocation follows a timer fire counts for acceptance: read the timer's actual `OnCalendar` from the unit file instead of trusting a handoff's stated cadence, and exclude a manual service run (e.g. from a prior session's verification) even if it exited 0. Stage the post-fire check as a background wait job (sleep past the next fire, then ssh the checks and append to a log) so the wait needs no babysitting.

## Pitfalls

- `git diff --name-status target..source` shows DELETIONS for files that exist only on target — that is the one-way boundary, not a change to apply. Reading the direction wrong inverts the whole sync.
- Set `git config user.name/email` in the fresh clone BEFORE any commit or rebase — a bare clone has no identity, merges fail with 'Committer identity unknown' while the loop keeps printing pre-merge SHAs, and you can believe a merge 'landed' that never happened.
- After pushing anything to a protected `main`, verify with `git fetch && git rev-parse origin/main` — and warn the user when GitHub reports rule-bypass (deploy key admin rights silently defeat required-PR protection).
- MIAM host has no GitHub SSH key and its HTTPS egress hangs: relay through VM906 (which has GitHub HTTPS) — see degraded-tool-fallbacks for the keypair+tar relay pattern.
- SSH access: the sandbox ed25519 key (comment `hermes-sandbox@<host>`) is authorized on VM906 (`jordatech@10.0.20.195`) — ssh there directly, no relay needed. Verify any documented IP against the live host (`ssh <user>@<ip> hostname`) before acting on it — stale IPs in plans/handoffs cost a full wrong-host detour; MagicDNS under the sandbox's `resolv.conf` search domain (e.g. `<hostname>.<tailnet>.ts.net`) resolves host IPs that aren't in any doc.
- Reachability triage: `Permission denied (publickey)` = path works, auth missing — fix auth (give the user the append-to-`~/.ssh/authorized_keys` one-liner with the sandbox PUBLIC key pasted in full; public keys are safe in chat) and keep that IP as the candidate. `Connection timed out` = filtered/unroutable — a different path is needed, more key installs will not help. Do not burn time probing many users/IPs for an auth problem, or port-scanning to find a host when the sandbox key comment already names it.
- When the target IS the sandbox's own docker host: the bridge gateway (172.17.0.1) answers DNS (UDP 53) but the host firewall drops all TCP from docker0, and the host's tailscale IP is unroutable from the bridge — :22 times out even after the key is authorized. Unblock with one reversible host-shell command from the user: `sudo iptables -I INPUT -i docker0 -p tcp --dport 22 -j ACCEPT` (remove afterward with `-D`). Root pubkey login is disabled there — authorize the sandbox key for the Hermes user (`jordatech`) and use `ssh jordatech@172.17.0.1`; `root@` still says `Permission denied (publickey)` after the firewall opens. Check the HTTPS egress proxy early (`curl -m 10 https://api.github.com/zen` — often down after reboot); Git over SSH/LAN port 22 works regardless.
- A relayed copy of `agent-context` on MIAM may be a partial directory with no git metadata (only `01-projects` + handoffs). If `git` commands inside it fail or `02-claude/` is missing, do not install from it: re-relay the full repo (tar from VM906 -> scp via the sandbox -> extract on the target), renaming the partial copy to `*.relay-partial.bak` instead of merging over it.
- After freezing a shared branch, spot-check it for resurrection: `git log origin/<frozen-branch> -3` on the next sync task. A second agent instance on the target host can keep an old push exporter scheduled and keep committing to the frozen branch; that violates single-writer and needs the stale exporter unscheduled, not a branch revert.
Memory syncs through NAMESPACED import dirs (`memories/imported_vm906/`) — overwrite the canonical master version there wholesale, but never touch the instance-local `memories/MEMORY.md`/`USER.md`. The namespace makes a canonical overwrite safe by construction.
- Applying sync content INTO the live `~/.hermes` first, before any exporter runs, used to be load-bearing when MIAM had a push-exporter; that exporter is retired, but the rule still holds for anything that stages repo state before the next timer tick.

## References

- Sync matrix and exclusion list: `agent-context/03-hermes/HERMES_SYNC_POLICY.md` (repo `startupteams/agent-context`).
- Host-exec and file-relay mechanics: see the `degraded-tool-fallbacks` skill.
