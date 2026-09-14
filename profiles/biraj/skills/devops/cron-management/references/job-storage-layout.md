# Cron Job Storage Layout

## Profile Directory
Cron data lives per-profile:
```
~/.hermes/profiles/<profile>/cron/
```

## Key Files

| File | Purpose |
|------|---------|
| `jobs.json` | Job definitions (schedule, prompt, model, origin) |
| `executions.db` | SQLite execution history |
| `cleanup.log` | Human-readable run log |
| `ticker_last_success` | Unix timestamp of last successful run |
| `ticker_heartbeat` | Unix timestamp of last ticker check |
| `.jobs.lock` | Lock file for job modifications |
| `.tick.lock` | Lock file for ticker |

## Output Storage
Each job's output goes in:
```
~/.hermes/profiles/<profile>/cron/output/<job_id>/
```
Files: `<date>_<time>.md` — one per execution.

## Inspecting Job State
```bash
# Job definitions
cat ~/.hermes/profiles/biraj/cron/jobs.json

# Latest execution output
ls -t ~/.hermes/profiles/biraj/cron/output/<job_id>/ | head -1 | xargs cat