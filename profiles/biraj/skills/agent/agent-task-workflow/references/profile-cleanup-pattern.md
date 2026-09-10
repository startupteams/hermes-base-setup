# Profile Artifact Cleanup Pattern (2026-09-10)

## Trigger
Profile directory (`profiles/biraj`) accumulates redundant artifacts: `models_dev_cache.json`, `provider_models_cache.json`, `cache/`, `bin/`, `logs/`, `gateway.pid`, `gateway.lock`, `auth.lock`, `sessions/`.

## Preservation Rule (hard)
Always preserve `cron/` and `skills/`. Do not delete profile branch contents accidentally.

## Script
/opt/hermes/scripts/cleanup_profile_redundant.py — standalone, accepts profile path argument.

## Verification
- Confirm artifacts removed with `ls` (expect "No such file")
- Confirm preserved dirs exist: `ls profiles/biraj/cron profiles/biraj/skills`
- Log to `profiles/biraj/cron/cleanup.log` (cron redirect `>> ... 2>&1`)

## Cron Schedule
`*/15 * * * * /usr/bin/python3 /opt/hermes/scripts/cleanup_profile_redundant.py /opt/hermes/profiles/biraj >> /opt/hermes/profiles/biraj/cron/cleanup.log 2>&1`

## Pitfalls
- Script uses relative `Path(sys.argv[1])`; prefer absolute paths in cron.
- If nothing to clean, log is empty (exit 0) — not a failure.
- Do not expose credentials or auth.json in logs.
