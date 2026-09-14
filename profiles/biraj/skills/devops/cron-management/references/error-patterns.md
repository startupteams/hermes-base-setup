# Cron Error Patterns & Fixes

## Error Messages

### "no model configured"
**Full message:** "Cron job 'X' has no model configured (job.model=None, HERMES_MODEL='', config.yaml model.default missing or empty)."
**Cause:** Job created without a model and no global default set.
**Fix:**
```bash
# Per-job model
cronjob action=update job_id=<id> model=openrouter/free
# Or set global default
hermes model openrouter/free
```

### "script not found"
**Cause:** Script path referenced in prompt doesn't exist on disk.
**Fix:** Create the script or update the job prompt with the correct path.

### "skill not found"
**Cause:** Job references a skill that isn't installed.
**Fix:** Install the skill or remove it from the job's skills list.

### "workdir missing"
**Cause:** Working directory doesn't exist.
**Fix:** Create directory or update workdir.

## Last-Status Values

| Value | Meaning | Action |
|-------|---------|--------|
| `error` | Last run failed | Check `last_error` |
| `running` | Currently executing | Wait or check process |
| `completed` | Last run succeeded | No action needed |

## Delivery Error Patterns

- `last_delivery_error` is set when the job runs but can't deliver the result (e.g., Telegram chat not found).
- Check origin platform/chat_id in jobs.json if delivery keeps failing.