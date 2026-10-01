# Hermes 0.19.0 worker api-server surface — verified live 2026-10-01

Probed against acms-worker-001 (VM124 @ 10.0.20.203:8402, hermes-agent 0.19.0
in `/opt/hermes-venv`, gateway = `hermes-bridge.service` running
`hermes gateway run --profile acms-worker-001 --replace`). Everything below
was verified with real HTTP calls from the ACMS container; the worker needed
ZERO changes for the A2A production path.

## Machine-readable capability list
`GET /v1/capabilities` → auth, `runtime.mode=server_agent`, feature flags
(run_events_sse, run_stop, tool_progress_events, session_chat_streaming,
session_fork, skills_api, …), and an `endpoints` map with exact paths/methods.
Probe this FIRST instead of guessing routes.

## Run lifecycle (the A2A ACK)
- `POST /v1/runs` body `{input:[{role,content}], metadata, title, model?}` →
  **202 `{run_id, status:"started"}`** — the run_id IS the worker ACK
  (ADR-0013 contract).
- `GET /v1/runs/{run_id}` → `{status: running|completed|failed|cancelled,
  output, usage{input_tokens,output_tokens,total_tokens}, last_event,
  session_id, created_at, updated_at}`. **Run statuses are TTL'd** — old run
  ids 404 after a while; don't treat a 404 as "never ran".
- `POST /v1/runs/{run_id}/stop` = interrupt/cancel (one endpoint).
- **Model-field caveat:** the request `model` only takes effect through
  `platforms.api_server.extra.model_routes` (alias → `{model, provider?,
  api_key?, base_url?}`) in the worker profile config. An UNMATCHED alias is
  silently ignored → the agent runs the profile config default. Verified live:
  `model=qwen3.8-flash-next` without a model_routes entry ran `fast`
  (= qwen3.6). Worker-side fix = add model_routes entries; ACMS-side =
  still send the effective model in the request body
  (`bridge.send_work(model=...)`) so the intent is auditable.

## Run events SSE — `GET /v1/runs/{run_id}/events`
text/event-stream, `data: {json}` lines, ~30s `: keepalive` comments, stream
closes after the terminal event. Verified payload shapes:
- `run.completed` `{output, usage{input_tokens,output_tokens,total_tokens}}`
- `run.failed` `{error (redacted)}`, `run.cancelled`
- `tool.started` `{tool, preview}`, `tool.completed` `{tool, duration, error}`
- `message.delta` `{delta}`, `reasoning.available` `{text}`
Subscribe right after POST (handler waits up to 1s for stream registration).
`reasoning.available` carries hidden model reasoning — ACMS drops it
(STEA-004 plan §14: never expose non-user-visible reasoning).

## Session chat stream — `POST /api/sessions/{id}/chat/stream`
SSE events: run.started, message.started, assistant.delta, tool.progress,
tool.started/completed/failed, assistant.completed, run.completed, error,
done. Response header `X-Hermes-Session-Id` echoes the session id.

## Health / status (heartbeat sources)
- `GET /health/detailed` → `{status, readiness.checks{state_db, config,
  model, disk{used_percent,free_bytes}, gateway{state,connected_platforms},
  background_queues{active_api_runs,process_completions,
  active_delegations}}, active_agents, gateway_busy, gateway_drainable,
  platforms.api_server{state}, version, updated_at}`.
  `active_agents > 0 or gateway_busy` ⇒ worker is executing.
- `GET /api/sessions` rows carry: id, model, title, started_at/ended_at,
  message_count, tool_call_count, input_tokens, output_tokens,
  cache_read_tokens, cache_write_tokens, reasoning_tokens,
  estimated_cost_usd, actual_cost_usd, api_call_count, last_active, preview —
  one call yields session identity + token usage + cost for the heartbeat
  payload (what `telemetry_scheduler._fetch_worker_status` consumes).
- `GET /api/sessions/{id}/messages` → role, content, reasoning, token_count,
  timestamp (transcript excerpts for Context Markdown).

## Route truth for model-policy chains (ACMS side)
Server Manager (VM114 :8300) `GET /api/v1/model-routes` (svc-token auth —
`svc-server-manager` from service_tokens; split `token:scopes` on the FIRST
colon) returns every logical route with `{engine, backend_url, health,
routable, is_alias, alias_target, context_limit}`. Healthy locals =
`routable && !is_alias && health=="healthy" && engine != openrouter`.
This is what `acms/model_policy.py::fetch_healthy_local_models()` consumes —
LLM Manager owns route truth; ACMS never maintains its own health copy.