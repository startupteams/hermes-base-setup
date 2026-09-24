---
name: degraded-tool-fallbacks
description: "Use when sandboxed tools fail. Run host shell via cron."
version: 1.1.0
---

# Degraded-Tool Fallbacks

When Hermes's sandboxed tools (terminal, execute_code, read_file, write_file, search_files — the Docker-backed set) fail with environment-level errors (e.g. `EnvironmentConnectionError: Docker command is available but 'docker version' failed`), you lose host file/shell access. Do not stop and do not fabricate results — use a working fallback.

## Fallback 1: cron `no_agent` script (verified working, with pitfalls)

The cron scheduler runs `script` payloads **on the host** (via the gateway), not in the Docker sandbox. A one-shot `no_agent: true` job returns the script's stdout verbatim into the chat:

```
cronjob(action='create', no_agent=true, deliver='local',
        schedule='in 1m',
        prompt='<ignored in no_agent mode>',
        script=<script payload>)
```

- Use `schedule='in 1m'` for a near-immediate one-shot; the output re-enters the conversation when the job fires.
- `no_agent: true` is essential: stdout is delivered verbatim and no LLM run is spawned. Without it, an agent run is also scheduled and the job can land in `error` state (and auto-disable), losing the output.
- A job that errored sets `enabled: false` and cannot be re-run with `cronjob(action='run')` (`execution_skipped: Job is paused/disabled`) — create a fresh job instead.
- CORRECTED 2026-09-25 (MIAM-00101, cost a full session): the `script` field executes as **Python** unless it ends in `.sh`/`.bash` (cronjob schema: '.sh/.bash via bash, else Python'). Inline `bash -c '...'` strings are parsed as Python, always error (SyntaxError), and the job auto-disables — one-shots in that state can never re-run. Working shapes: (1) self-contained inline **Python** that subprocess-runs bash; (2) a `.sh` file path relative to `~/.hermes/scripts/` (proven: hourly `portable_brain_sync.sh`).
- CORRECTED: `deliver='local'` saves output WITHOUT posting it — the chat sees nothing. **Omit `deliver`** to post job output to the origin chat.
- CORRECTED: non-zero script exit marks the job `error` and auto-disables it; end scripts with `exit 0` / natural Python completion and record failures inside stdout. There is a **3-minute hard interrupt per run** — long work (compiles, multi-GB downloads) must `nohup ... &` detach and be polled by later jobs.
- Absolute paths: the sandbox's `$HOME` may not match the host user's; write scripts with explicit absolute paths (e.g. `/home/<user>/.hermes/...`).
- Works for both reads (cat/ls/find) and writes (cp/mkdir) — state changes land on the real host.

### Script language is chosen by EXTENSION (critical, learned the hard way)

- A `script` value ending in `.sh` runs as **bash**.
- Anything else (including an inline `bash -c '...'` string) is executed as **Python**. An inline bash string does NOT run as bash — it gets parsed/executed as Python and errors out or misbehaves. Do not use the `script="bash -c '...'"` form despite older examples; see `references/cron-hostexec-failure-modes.md`.
- Preferred pattern: dispatch a tiny inline **Python** job whose first act is to write a proper `stage.sh` into `~/.hermes/scripts/` (chmod +x), then `subprocess.run(['...stage.sh', '<stage>'])` and print the log. All later stages are then fired as tiny jobs calling the same `.sh` runner with different stage names.

### Make every job exit 0, or output is lost

- The scheduler treats a non-zero exit as an error, marks the job `error`, **auto-disables it**, and (for deliver=local) does not deliver partial stdout. Discovery-style scripts end with commands that routinely fail (a missing dir passed to `ls`/`df` exits non-zero) — three separate jobs were lost this way in one session.
- Pattern: the script writes each command's output + rc into a log file, then **always `exit 0`** at the end. Diagnose from the log, not from job status.

### deliver='local' does NOT post to the chat

- `deliver: local` only saves output locally; nothing arrives in the conversation, so a successful run is invisible to you. `deliver` to the active channel (or omit deliver so it posts to the origin chat) when you need to READ the stdout in-session. If a job 'succeeded' but you saw nothing, this is why.

### Other cron semantics

- `cronjob.create` rejects absolute script paths in some contexts: `Script path must be relative to ~/.hermes/scripts/`. In a profile, put a wrapper in that profile's `scripts/` directory and pass only the filename.
- Inline (non-path) script strings run fine; only file-path values are subject to the relative-path rule.

## Fallback 2: computer_use on a host terminal

If a terminal app is open on the user's desktop, computer_use can type commands into it — but only if the window is enumerable. On Hyprland, `list_windows`/`read_window_below` fail when Hyprland's IPC socket isn't reachable from Hermes's session; don't burn turns retrying — go to Fallback 1. Note: computer_use itself is NOT Docker-backed — it still works when the sandbox is down, and `computer_use(action='list_apps')` can enumerate host processes for diagnostics.

## Do NOT capture as rules

The sandbox failure itself is environment state (Docker daemon down), not a durable fact. Never write 'terminal tool is broken' into skills or memory — only the fallback mechanism above. Do capture the FIX for why the daemon is down once diagnosed (e.g. into a setup/troubleshooting skill), never the bare failure.
