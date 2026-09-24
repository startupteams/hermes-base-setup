# Session log: 2026-09-25 — egress-proxy block + cron Errno 36 regression (VM906)

Task: "Verify that Docker works." Outcome: Docker never reached; every execution channel failed. NOT a validated workflow — this file documents observed failure modes and the identified fixes so a future session recognizes them fast.

## Failure mode A: egress proxy misconfigured (pre-Docker, all Docker-backed tools)
`terminal`, `execute_code`, `read_file`, `write_file`, `search_files` all failed identically, BEFORE any Docker contact:
```
RuntimeError: proxy.enabled is true but iron-proxy is not configured.
Run `hermes egress setup` to mint tokens and write proxy.yaml.
  at tools/environments/docker.py:475 (_egress_proxy_args_for_docker)
```
Fix (host, as user): `hermes egress setup` — or `hermes config set proxy.enabled false` if egress proxying is unwanted. Diagnostic value: this error message itself distinguishes 'Hermes sandbox misconfig' from 'Docker daemon down' — do not conclude the daemon is dead from it.

## Failure mode B: cron no_agent inline script -> Errno 36 filename-too-long
Gateway wrote the script SOURCE as a filename under `~/.hermes/scripts/`:
```
[Errno 36] File name too long: '/home/jordatech/.hermes/scripts/import subprocess\nfor cmd in ...'
```
Hit on: manual `cronjob(action='run')` of an inline script (deleg_06161ba2, 0.22s, 0 API calls) AND two scheduled one-shot fires (03:04:29, 03:08:30). All errored -> auto-disabled. Workaround (identified, NOT yet verified): pre-existing file under `~/.hermes/scripts/` passed as relative filename.

## Failure mode C: browser-harness daemon down (secondary)
`browser_exec` failed: `daemon default didn't come up -- check ~/.config/browser-harness/tmp/bu-default.log`. Uninvestigated; treat as environment state.

## What still worked while sandbox was down
- `cronjob(action='list')` — job state polling (last_run_at/last_status) — reliable.
- `computer_use(action='list_apps'/'wait')` — non-Docker, worked (list output is huge; spillover file warning is expected).
- `session_search`, `web`-independent tools — unaffected (not tested but not Docker-backed).
- Skill/memory tools — unaffected.

## Evidence left on host for follow-up
- `~/.hermes/scripts/qwen_out_discovery.log` — contains real `systemctl status docker` + `docker version` output from 02:35 (job fde69088f87a).
- Cron job outputs for e46a076d17fd, e0f9ab452f0a saved locally (deliver='local').
- Handoff markdown was delivered inline in chat (file write blocked by same Errno 36).

## Lessons encoded elsewhere
- SKILL.md 'Other cron semantics' section now carries the Errno 36 workaround and scheduler-latency note.
- Do NOT treat this session's dead ends as a recommended sequence; the fixes above are single-point diagnoses, not verified end-to-end recoveries.