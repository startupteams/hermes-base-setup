---
name: cron-management
category: devops
description: Manage, troubleshoot, and investigate Hermes cron jobs — list jobs, diagnose failures, pause/remove broken jobs, and fix common misconfigurations.
---

# Cron Management Skill

## When to Use
- User asks "what cron jobs are running" or similar
- A cron job shows errors or unexpected behavior
- Need to pause, disable, or remove a job
- Investigating why a job isn't running or is failing

## Core Workflow

### 1. List Jobs First
Always start with `cronjob action=list` to see all jobs, their status, schedule, and last run.

```bash
cronjob action=list
```

### 2. Investigate Failures
When a job shows `last_status: "error"`:
- Check `last_error` field for the failure reason
- Common issues:
  - **No model configured** → Set per-job model or global default
  - **Missing script** → Script path in prompt doesn't exist
  - **Missing skill** → Referenced skill not installed
  - **Workdir missing** → Directory doesn't exist

### 3. Examine Job Definition & Logs
Job definitions stored in: `~/.hermes/profiles/<profile>/cron/jobs.json`
Execution logs in: `~/.hermes/profiles/<profile>/cron/output/<job_id>/`

```bash
cat ~/.hermes/profiles/biraj/cron/jobs.json
cat ~/.hermes/profiles/biraj/cron/output/<job_id>/latest.md
```

### 4. Fix or Disable

**Fix common issues:**
```bash
# Set model for a job
cronjob action=update job_id=<id> model=<model-name>

# Update schedule
cronjob action=update job_id=<id> schedule="0 * * * *"

# Attach skills
cronjob action=update job_id=<id> skills='["skill-name"]'
```

**Pause (disable) a job:**
```bash
cronjob action=pause job_id=<id>
```

**Remove a job entirely:**
```bash
cronjob action=remove job_id=<id>
```

## Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| "no model configured" | `job.model=null` and no global default | Set per-job model or `hermes model <name>` |
| "script not found" | Script path in prompt doesn't exist | Create script or update prompt with correct path |
| "skill not found" | Referenced skill missing | Install skill or remove from job |
| "workdir missing" | Directory doesn't exist | Create directory or update workdir |

## Pitfalls

1. **Don't guess job IDs** — always `list` first, then use the exact `job_id` from the result
2. **Script paths in prompts are not validated** — a job can be created with a non-existent script
3. **Jobs without models fail silently** — they show "error" status but no delivery unless you check `last_error`
4. **Profile-specific storage** — cron jobs live per-profile at `~/.hermes/profiles/<profile>/cron/`
5. **Background jobs need `notify_on_complete`** — when creating long-running cron jobs via terminal, always pair with notification

## Verification Steps

After any change:
1. Run `cronjob action=list` again
2. Confirm `enabled: false` for paused jobs
3. Confirm job removed from list for deleted jobs
4. Check `next_run_at` is reasonable for schedule changes

## References

- `references/error-patterns.md` — Detailed error messages and fixes
- `references/job-storage-layout.md` — Where cron data lives on disk