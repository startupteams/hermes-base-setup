# Spend & facility analytics — data shapes and endpoint pattern (v0.6.0–v0.7.1)

## Source tables (litellm DB on CT115 @ 10.0.20.116; manager reads it READ-ONLY)
- `LiteLLM_SpendLogs` columns in use: `model`, `model_group`, `api_key`, `spend`
  (provider-reported USD; **$0.00 for local models — no price map yet**),
  `prompt_tokens`, `completion_tokens`, `startTime` (timestamp WITHOUT tz, UTC),
  `request_duration_ms`, `status`. Filter `(total_tokens>0 OR spend>0)` to drop
  empty health-check rows (they appear with blank model/api_key).
- `api_key` values: raw token hash for virtual keys, `litellm_proxy_master_key`
  for master-key traffic. Alias resolution: `LiteLLM_VerificationToken(token,
  key_alias, key_name)` — display alias or key_name, fallback to first 8 chars.
- Model values observed: `openai/qwen3.6-35b-a3b` (local), `openrouter/z-ai/glm-5.3-flash`
  (fallback), `startupteams/general` (logical name on some rows). Group per-row by
  `model or model_group or '(unknown)'`.
- Virtual-key spend/token totals also live on the token row itself (`spend`,
  `model_spend` columns) but request-level SpendLogs is the richer source.

## Manager endpoints (all session-auth; roles Admin/Security-Admin for mutations)
- `GET /api/spend/analytics?hours=N` (default 168) or `?from_=ISO&to=ISO` →
  usage box (today / this_week / this_month / all_time; today = midnight UTC,
  month = 1st), `models[]` with min/max/avg/total spend + tokens + avg duration,
  `keys[]` alias-resolved totals, `days[]` daily totals, `window_energy`
  (GPU kWh × effective seasonal rate, $/1M tokens).
- Energy attribution: `SUM(gpu_watts_avg)/60.0/1000.0` kWh over the window from
  `host_power_rollup_1m` (app DB) × componentized `effective_rate()` — never
  hardcode the tariff (plan §16).
- `GET /api/facility?minutes=N` — Emporia facility view (v0.6.0); reads
  `facility_power_samples` + `emporia_channel_map`, roles compute|cooling|other.
  Returns a friendly note when the collector isn't deployed (tables absent).
- `GET /api/rdma/ring` + `POST /api/rdma/ring` (v0.7.0) — ring node registry
  (`rdma_ring_nodes`, auto-created + seeded 111/143/144). POST updates
  qualification/evidence (Admin+).
- `GET/POST /api/rdma/deployments` — multi-node vLLM configs
  (`multi_node_deployments`); POST renders the Ray head/worker + `vllm serve`
  + NCCL launch script. **§19.8 hard gate**: state stays `planned`,
  `routable: false`, gate_errors listed, until every participating host has
  `qualified=true` — the endpoint never touches the gateway or hosts.
- v0.7.1: `/api/cost` embeds `facility` split (via `_facility_split()`) when the
  Emporia collector writes `facility_power_samples`; dashboard renders
  compute/cooling/other rows automatically when the key appears.

## Dashboard JS conventions
- Range selector (24h/7d/30d/custom) posts `hours=` or `from_=&to=` (note the
  trailing underscore — FastAPI quirk).
- Usage row mirrors OpenRouter: Total reqs, Today, This Week, This Month ($ +
  tokens). Models table columns: Model | Min | Max | Avg | Totals | Reqs | tokens.
- Daily bars: inline-block divs scaled to max daily tokens; label `$X · N tok`.

## Pitfalls
- Keep SQL literals ASCII (SQL_ASCII cluster on CT115).
- Patch deployments follow SKILL.md §Manager web-app additive patching (dry-run,
  sudo for backups, TestClient before restart).
- The app venv has psycopg2 but plain python3 on VM114 does not — always
  `/opt/llm-manager/venv/bin/python` (as root for secret access).