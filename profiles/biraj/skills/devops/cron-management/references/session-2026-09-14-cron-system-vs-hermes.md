# Session 2026-09-14 — System vs Hermes Cron + Skill Library Pull

## Trigger
- User asked "what cron jobs" → `profile-redundant-cleanup` broken. Disabled.
- User corrected: sync_memory meant system `crontab`; not Hermes job (removed erroneous `4215cce15e18`).
- Skill pull: user wants `skills/` from `agentifyme_...` branch `jordatech_crmmiam02_906` into `/opt/hermes/profiles/biraj/skills/`; download failed (likely private/auth); need confirm repo/access.

## Key signals embedded in cron-management SKILL.md
- Pitfall #6: distinguish system (`crontab`) vs Hermes (`cronjob list`); verify both.
- Section: System-Level vs Hermes Cron; Script-Existence Trap; Verification Before Assumption.
