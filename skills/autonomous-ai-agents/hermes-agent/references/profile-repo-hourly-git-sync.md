# Profile Repository Hourly Git Sync

Use this when a Hermes profile/home directory is itself a Git repository that should be backed up to GitHub on a schedule.

## Scenario

Jordan's local Hermes repository is the live `~/.hermes` directory, not a separate working clone:

- Local path: `/home/miam/.hermes`
- Remote: `https://github.com/jordatech/crmmiam01_hermes`
- Branch: `main`
- Purpose: portable backup of Hermes profiles, skills, memories, selected config files, and profile scripts.

## Working pattern

1. Verify the live repo:

```bash
git -C /home/miam/.hermes rev-parse --show-toplevel
git -C /home/miam/.hermes remote get-url origin
git -C /home/miam/.hermes branch --show-current
git -C /home/miam/.hermes status --short
```

2. Keep the sync script inside the repo, e.g. `~/.hermes/scripts/hourly_git_sync.sh`, and whitelist it in `.gitignore` if the repo uses an ignore-everything policy.

3. For Hermes cron script jobs, create a wrapper under the profile scripts directory, e.g.:

```bash
mkdir -p /home/miam/.hermes/profiles/entrepreneur/scripts
cat > /home/miam/.hermes/profiles/entrepreneur/scripts/hourly_crmmiam01_hermes_sync.sh <<'EOF'
#!/usr/bin/env bash
exec /home/miam/.hermes/scripts/hourly_git_sync.sh
EOF
chmod +x /home/miam/.hermes/profiles/entrepreneur/scripts/hourly_crmmiam01_hermes_sync.sh
```

4. Create the cron as a script-only/no-agent job. The `cronjob` tool requires script paths to be relative to the profile scripts directory, not absolute paths:

```json
{
  "action": "create",
  "name": "Hourly crmmiam01_hermes git sync",
  "schedule": "0 * * * *",
  "no_agent": true,
  "script": "hourly_crmmiam01_hermes_sync.sh",
  "workdir": "/home/miam/.hermes",
  "enabled_toolsets": ["terminal"],
  "deliver": "origin"
}
```

## Safe sync script behavior

A robust sync script should:

- export the correct `HOME` for GitHub CLI auth, e.g. `HOME=/home/miam`
- verify the remote is the expected GitHub repository
- verify or check out `main` when the user explicitly wants main
- use a lock file under `.git/` to avoid overlapping runs
- stash local changes before pull, then reapply them
- pull from `origin main`
- add only files permitted by `.gitignore` plus tracked modifications/deletions
- commit only when staged changes exist
- push to `origin main`
- write logs under `.git/` so logs are not committed

## Pitfalls from session

- Do not clone a separate `~/jordatech/crmmiam01_hermes` checkout and wire cron to that if the actual live Hermes app repo is `~/.hermes`; the user wants the live bot memory/skills/config repository synced.
- `cronjob.create` rejects absolute script paths: `Script path must be relative to ~/.hermes/scripts/`. In a profile, put a wrapper in that profile's `scripts/` directory and pass only the filename.
- If another existing cron or process is committing every minute, `git pull --ff-only` can fail due to divergence. Resolve explicitly with rebase/merge as appropriate, then rerun the sync and verify clean status.
- If a failed test run leaves a stash, inspect and drop/apply it intentionally; do not leave confusing sync stashes behind.
