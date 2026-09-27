# Hermes harness control research — live test log (2026-09-26/27)

Condensed from the combined slice 3+4 session. Full in-repo doc:
`docs/HARNESS_CONTROL_MAPPING.md` in acms-project-framework. This reference
captures the *method* and the environment quirks so a future bridge/control
session doesn't re-derive them.

## Target + setup recipe (proven)

- Installed Hermes: **0.17.0**, commit `f3d2dfb` (2026-06-30) — always record
  the exact commit; upstream docs describe newer builds.
- Scratch profile recipe: `hermes profile create <name> --clone` (clones the
  ACTIVE profile) → **sanitize .env** (comment out TELEGRAM_*/WHATSAPP_*/etc.
  or the gateway exits with exit 78 "enabled but not paired") → enable
  api-server. Two working paths:
  - `.env`: `API_SERVER_ENABLED=true`, `API_SERVER_PORT=8643`,
    `API_SERVER_KEY=<random>` (openssl rand -hex 16)
  - or config.yaml: `platforms: api_server: {enabled: true, extra: {key: ...}}`
- Launch a test gateway as a transient systemd unit:
  `systemd-run --user --unit=<name> ~/.hermes/hermes-agent/venv/bin/python -m
  hermes_cli.main --profile <name> gateway run` — keeps it outside the
  current gateway's kill scope.
- api-server default port **8642** (env override not always honored via
  systemd-run — check `ss -tlnp | grep 864` and use whatever actually binds).
- Auth: `Authorization: Bearer <key>` on every call.

## Verified capability matrix (Hermes 0.17.0)

| Capability | Mapping | Result |
|---|---|---|
| status | `GET /api/sessions/{id}` + `GET /v1/runs/{run_id}` (status/usage/output) + `GET /api/sessions` | SUPPORTED |
| send_work | `POST /v1/runs` (new) or `/api/sessions/{id}/chat` + `X-Hermes-Session-Id` (existing) | SUPPORTED |
| steer | session chat into a RUNNING run | SUPPORTED (verified mid-run) |
| pause | — | **404 UNSUPPORTED** — never fake with interrupt |
| resume | — | **404 UNSUPPORTED** |
| interrupt | `POST /v1/runs/{id}/stop` → running→stopping→cancelled; session + messages preserved; same-session follow-up works | SUPPORTED |
| cancel | same endpoint; terminal at A2A-task level; Hermes session reusable | SUPPORTED |
| request_handoff | dispatch via send_work with structured instruction | SUPPORTED |
| set_session_title | `PATCH /api/sessions/{id}` `{"title": ...}` (allowed: title, end_reason) | SUPPORTED |
| `new` session | `POST /api/sessions` with explicit id | SUPPORTED |

Key fields: session response has `id, title, model, message_count,
input_tokens, output_tokens, cache_*, api_call_count, last_active` (client-safe
allowlist in `_session_response`). **Context-window max is NOT exposed** —
ACMS records max_source and shows UNKNOWN/INVALID rather than fabricating.

## Research method (transfers to any future harness)

1. Find the installed version + commit FIRST (plan §14: never assume upstream
   docs match the installed build).
2. Read the actual source (`gateway/platforms/api_server.py`,
   `run_agent.py interrupt()`, `cli.py` status/stop handlers) — the mapping
   doc should cite the code path AND the live test.
3. Live-test on a scratch profile, never a production profile.
4. Run each control: dispatch → verify → cleanup. Steering test needs a
   genuinely long-running task (terminal `sleep` loop) or the run completes
   before you can steer.
5. Fill `docs/HARNESS_CONTROL_MAPPING.md` test-log table with results; the
   PR review depends on it.

## ACMS side that consumed this

- `acms/bridge.py` (HermesBridge: fetch_status/send_work/steer/interrupt/
  cancel/set_session_title/request_handoff) — capability list
  `HERMES_SUPPORTED_CAPABILITIES` mirrors the matrix.
- Targets: `ACMS_BRIDGE_TARGETS_JSON` (list of {agent_id, base_url, api_key});
  api_key lives in profile env, never committed (plan §18).
- Telemetry scheduler reconciles a stale agent via
  `get_bridge_for_agent(agent_id).fetch_status()`; failure → UNREACHABLE +
  RECONCILIATION_FAILED event (honest failure, no fabricated recovery).
