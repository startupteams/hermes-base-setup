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
- **MIAM-00101 is a pull-only follower.** It runs `~/.hermes/scripts/vm906_master_pull.sh` (via the 3-hourly `hermes-brain-sync.timer`): fetch `origin/jordatech_vm906`, additively apply skills (rsync WITHOUT `--delete` — master wins conflicts, MIAM-local skills are never deleted), refresh `memories/imported_vm906/MEMORY.md`. It must not push any branch.
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

## Pitfalls

- `git diff --name-status target..source` shows DELETIONS for files that exist only on target — that is the one-way boundary, not a change to apply. Reading the direction wrong inverts the whole sync.
- Set `git config user.name/email` in the fresh clone BEFORE any commit or rebase — a bare clone has no identity, merges fail with 'Committer identity unknown' while the loop keeps printing pre-merge SHAs, and you can believe a merge 'landed' that never happened.
- After pushing anything to a protected `main`, verify with `git fetch && git rev-parse origin/main` — and warn the user when GitHub reports rule-bypass (deploy key admin rights silently defeat required-PR protection).
- MIAM host has no GitHub SSH key and its HTTPS egress hangs: relay through VM906 (which has GitHub HTTPS) — see degraded-tool-fallbacks for the keypair+tar relay pattern.
Memory syncs through NAMESPACED import dirs (`memories/imported_vm906/`) — overwrite the canonical master version there wholesale, but never touch the instance-local `memories/MEMORY.md`/`USER.md`. The namespace makes a canonical overwrite safe by construction.
- Applying sync content INTO the live `~/.hermes` first, before any exporter runs, used to be load-bearing when MIAM had a push-exporter; that exporter is retired, but the rule still holds for anything that stages repo state before the next timer tick.

## References

- Sync matrix and exclusion list: `agent-context/03-hermes/HERMES_SYNC_POLICY.md` (repo `startupteams/agent-context`).
- Host-exec and file-relay mechanics (the sandbox cannot reach the hosts directly): see the `degraded-tool-fallbacks` skill.
