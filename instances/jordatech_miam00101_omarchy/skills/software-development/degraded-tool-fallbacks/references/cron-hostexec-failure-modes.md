# Cron host-exec failure modes (observed 2026-09-25, MIAM-00101)

Three one-shot `no_agent: true` discovery jobs (`miam-discovery-phase1`, `list-hermes-profiles`, `qwen-phase1-host-discovery`) all fired and marked `last_status: error`, `enabled: false`, with no output delivered.

## Root causes (compounding)

1. **Inline `bash -c '...'` payloads do not run as bash.** The scheduler selects the executor by script extension; non-`.sh` values (including `bash -c` strings) run as Python. Python parsing a bash script either errors or produces garbage exit codes.
2. **Discovery commands exit non-zero on missing paths.** `ls ~/Work 2>/dev/null`, `df -hT /home`, `crontab -l` etc. all returned rc≠0 on the fresh host, failing the job even when earlier sections produced useful output.
3. **deliver='local' never posts to the chat.** Even had the jobs succeeded, output would not have been visible; the operator only saw 'error' in `cronjob(action='list')`.

## Failure signature in cronjob list

```json
"last_status": "error", "last_fire_error": null, "last_delivery_error": null,
"enabled": false, "state": "completed", "repeat": "1/1"
```

`last_fire_error: null` with status=error means the script itself exited non-zero — check the script, not the gateway.

## Working alternative

Stage-runner pattern:

1. Inline Python bootstrap job: writes `~/.hermes/scripts/qwen_stage.sh` (chmod +x), immediately `subprocess.run([runner, 'discovery'])`, prints the log file contents to stdout, `exit 0` regardless.
2. The `.sh` runner wraps every command as `run(){ echo ...; eval "$1" >> log 2>&1; echo "rc=$?" >> log; }` and ends with `exit 0`.
3. Subsequent stages = fresh one-shot jobs calling the runner with a stage argument.

Reusable runner template: `scripts/stage-runner.sh` in this skill.

## Contrast case (why the file-path form is trusted)

`portable_brain_sync.sh` — a `.sh` file path run hourly — succeeded (`last_status: ok`) across many runs in the same environment, isolating the failure to payload form + exit codes, not the cron host-exec channel itself.
