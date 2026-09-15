---
name: cron-management
category: devops
description: Manage, troubleshoot, and investigate Hermes cron jobs — list jobs, diagnose failures, pause/remove broken jobs, and fix common misconfigurations. Also manage system-level cron jobs (e.g., /opt/hermes/scripts/sync_memory.sh) that run outside Hermes.
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

## System-Level vs Hermes Cron (learned 2026-09-14)

Hermes `cronjob` (profile-level) ≠ OS `crontab`. System-level jobs live in `crontab -l`, `/etc/crontab`, `/etc/cron.d/` — they do not appear in `cronjob action=list`. Before creating a new Hermes cron for something that "should exist", check system level. This session produced an erroneous Hermes `sync-memory` job (`4215cce15e18`, created, then removed) because the user meant the system-level `sync_memory.sh`.

```
crontab -l | grep <keyword>
ls -la /opt/hermes/scripts/<script>
```

## Script-Existence Trap

Always verify target script exists (`ls <path>`) before declaring a broken job fixable. Session: `cleanup_profile_redundant.py` missing; only `sync_memory.sh` present.

## Verification Before Assumption (user-correction signal)

On pushback ("shouldn't exist", "check again"): re-list; read `jobs.json` `last_error`; confirm filesystem; then confirm disable/remove with fresh list showing `enabled: false` / `state: paused`.

## Script-Existence Trap (session signal)

When a Hermes cron job references a script, always verify the script path exists (`ls <path>`) before attempting to fix. Session: `cleanup_profile_redundant.py` missing; only `sync_memory.sh` present. Create script first, then update prompt/script path.

## System-Level vs Hermes Cron (learned 2026-09-14)

Hermes `cronjob` (profile-level) ≠ OS `crontab`. System-level jobs live in `crontab -l`, `/etc/crontab`, `/etc/cron.d/` — they don't appear in `cronjob action=list`. Before declaring job missing, check system level (session produced erroneous `sync-memory` `4215cce15e18`, then removed). Confirm repo/branch/auth before pulling skills from external source; user corrected assumption (`agentifyme_` vs `hermes-base-setup`; `skills/` folder only, not full profile replacement).

```
crontab -l | grep <keyword>
ls -la /opt/hermes/scripts/<script>
```

## Pitfalls

1. **Don't guess job IDs** — always `list` first, then use the exact `job_id` from the result
2. **Script paths in prompts are not validated** — a job can be created with a non-existent script
3. **Jobs without models fail silently** — they show "error" status but no delivery unless you check `last_error`
4. **Profile-specific storage** — cron jobs live per-profile at `~/.hermes/profiles/<profile>/cron/`
5. **Background jobs need `notify_on_complete`** — when creating long-running cron jobs via terminal, always pair with notification
6. **Distinguish system cron from Hermes cron** — `crontab -l` / `/etc/crontab` / `/etc/cron.d/` scripts don't appear in `cronjob list`. Before declaring a job missing, check system level (learned: `sync_memory.sh` exists in root crontab but not Hermes list — user meant system-level job). Confirm repo/branch/auth before pulling skills from external source; user corrected assumption about which repo (`agentifyme_...` vs `hermes-base-setup`) and which folder (`skills/` only, not full profile replacement).
7. **Check both skills storage layers** — global `/opt/hermes/skills/` (managed by `.curator_state`, `.bundled_manifest`) vs per-profile `~/.hermes/profiles/<p>/skills/`. Updates can land in only one; verify both when user says "skills updated."

## Verification Steps

After any change:
1. Run `cronjob action=list` again
2. Confirm `enabled: false` for paused jobs
3. Confirm job removed from list for deleted jobs
4. Check `next_run_at` is reasonable for schedule changes

## Proxmox Access via LLAP Domain (session 2026-09-14) — username/password (no API keys)

When accessing Proxmox / 10.0.20.135:8006 with only username + password (LLDAP-backed):
- Choose `LLLDAP-Domain` as realm (verify via `GET /api2/json/access/domains`).
- Credentials file: `~/.pve_ldap_bot` (2 lines: username, password; `chmod 600`).
- Use `scripts/pve_api.py` (from this skill) for API calls; send `PVEAuthCookie` + `CSRFPreventionToken`.
- Wrapper script: `/opt/hermes/scripts/proxmox_wrapper.py` delegates to `pve_api.py`; supports start/stop/status/create/configure.
- Safety (from skill body): NEVER restart nodes `miam-00133` / `miam-00135` (critical services / bot VMs). Confirm live PDU labels before cycles on `miam-00147`.
- Skill selection: this is global/infrastructure work → use `devops/proxmox-cluster-infrastructure` + agent's own; profile skills for config only.

## References

- `references/job-storage-layout.md` — Where cron data lives on disk
- `references/job-storage-layout.md` — Where cron data lives on disk
- `references/session-2026-09-14-cron-system-vs-hermes.md` — System vs Hermes cron; verification before pull; user-correction protocol