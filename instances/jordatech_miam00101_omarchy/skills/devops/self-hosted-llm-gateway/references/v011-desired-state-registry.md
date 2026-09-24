# v0.11 Manager — Desired-State, Model Registry, Gated /v1/models, Recovery Engine

Session-proven recipe (2026-09-13) for upgrading the LLM Manager from single-logical-model
round-robin (v0.8.0) to the v0.11 architecture: per-host desired power state, a logical
model registry as the routing source of truth, gated `/v1/models`, generic agent keys,
bounded auto-recovery, and a machine-to-machine agent provisioning API.

## Schema migration (run once via app venv)

```sql
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS desired_power_state TEXT NOT NULL DEFAULT 'RUNNING';
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS management_mode TEXT NOT NULL DEFAULT 'MANAGED';
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS node TEXT;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS vmid INTEGER;
ALTER TABLE deployments ADD COLUMN IF NOT EXISTS desired_service_state TEXT NOT NULL DEFAULT 'SERVING';
CREATE TABLE IF NOT EXISTS model_registry (
    id SERIAL PRIMARY KEY,
    logical_model_name TEXT NOT NULL,
    host_id INT REFERENCES hosts(host_id),
    engine TEXT, backend_url TEXT, context_limit INT,
    capabilities JSONB DEFAULT '{}'::jsonb,
    health TEXT DEFAULT 'unknown', routable BOOLEAN DEFAULT FALSE,
    is_alias BOOLEAN DEFAULT FALSE, alias_target TEXT,
    last_verified TIMESTAMPTZ, updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (logical_model_name, host_id));
CREATE TABLE IF NOT EXISTS recovery_events (id SERIAL PRIMARY KEY, host_id INT, ip TEXT,
    event_type TEXT, detail TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS request_routing_log (id SERIAL PRIMARY KEY, request_id TEXT,
    ts TIMESTAMPTZ DEFAULT now(), model TEXT, api_base TEXT, prompt_tokens INT,
    completion_tokens INT, latency_ms INT, ttft_ms INT, key_alias TEXT, provider_spend NUMERIC);
CREATE TABLE IF NOT EXISTS agent_keys (key_id SERIAL PRIMARY KEY, external_id TEXT UNIQUE,
    project_id TEXT, agent_instance_id TEXT, agent_name TEXT, harness TEXT, alias TEXT UNIQUE,
    raw_key TEXT, created_at TIMESTAMPTZ DEFAULT now(), created_by TEXT, last_used_at TIMESTAMPTZ,
    enabled BOOLEAN DEFAULT TRUE, revoked_at TIMESTAMPTZ, monthly_budget NUMERIC);
```

## nginx exact-match: gated /v1/models vs LiteLLM passthrough

LiteLLM owns `/v1/` but the gated model-discovery endpoint lives in the FastAPI app.
Exact match wins over prefix:

```nginx
location = /v1/models { proxy_pass http://127.0.0.1:8001; proxy_read_timeout 30s; }
location /v1          { proxy_pass http://127.0.0.1:4000; proxy_read_timeout 900s; proxy_buffering off; }
```

Gated endpoint: requires `Authorization: Bearer <valid litellm virtual key>` (validated
via `GET /key/info` against master key; master itself accepted); returns ONLY models with
`model_registry.routable = TRUE` — offline/intentionally-off hosts are OMITTED (OpenAI-
compatible behavior), never listed as unavailable.

## Registry → LiteLLM config regeneration (litellm_sync.py)

- Source of truth = DB (`model_registry` JOIN `hosts`, `routable=TRUE`), NOT hand-edited YAML.
- One `model_name` entry per (routable backend, logical model); per-host `api_key` aliases
  (`local-00111` etc.), `rpm` from engine (30 llamacpp / 300 vllm).
- Role aliases (`fast`/`code`/`frontier`) emitted only when `is_alias AND routable`, mapped
  to the target model's primary backend. `frontier` stays absent until a frontier model qualifies.
- NO cross-model fallbacks in v0.11 (no silent substitution per plan §D); OpenRouter entry kept as its own model_name.
- Write pattern: render → `yaml.safe_load` validate → backup previous config (`.bak.v011.<mtime>`) → atomic `os.replace` → `systemctl restart litellm` → verify `/v1/models` + one completion.
- Remove the old `fallbacks:` block (startupteams/general is retired).

## Generic agent keys (unpin existing keys)

Keys issued before v0.11 carry `models = {startupteams/general}`. Unpin:

```sql
UPDATE "LiteLLM_VerificationToken" SET models = NULL
 WHERE models = ARRAY['startupteams/general']::text[];
```

New issuance omits `models` entirely (LiteLLM default = all hosted models). Keys never
encode an endpoint and never get a default model; missing `model` in a request → explicit 400.

## Desired-state semantics + recovery engine (v011_recovery.py daemon)

- `MANAGED + desired RUNNING + VM unexpectedly stopped` → bounded auto-recovery:
  start VM (≤2 attempts/30min, counted from `recovery_events`), wait for agent/network,
  probe `/v1/models` + 1-token completion, bounded service restart (≤2, cooldown) via the
  guest control agent, then FAILED + out of routing.
- `desired STOPPED_INTENTIONAL` → NEVER power on, NEVER route, NOT counted as an outage;
  logged as `intentional_state_pending` if still running until operator power-off.
- Routability gate (§C2): `desired RUNNING AND vm running AND /v1/models 200 AND health completion ok AND not drained`.
- Ticks every 60 s; every action INSERTs into `recovery_events` + a JSONL file
  (`/var/log/llm-manager/recovery-engine.log`). DB unavailable → no recovery actions (fail-safe).
- First real catch: engine flagged .165 within one tick because the PVE token lacked
  ACL on `/vms/149` (see ACL fix below) — the fix proved the loop end-to-end.

## PVE token ACL: per-VM grants are explicit

The `llm-manager@pve` token had full grants on /vms/103,109,111,401 but NONE on /vms/149
(VM149 added to the fleet later). Symptom: `/nodes/<node>/qemu/149/status/current` →
`Permission check failed (/vms/149, VM.Audit)`. Fix from a root session:

```
PUT /access/acl  {path: /vms/149, users: llm-manager@pve, roles: PVEVMUser}
```

Verify via `GET /access/permissions?userid=llm-manager@pve` (flatten the nested dict).

## M2M agent provisioning API (Phase J foundation)

`POST /api/service/agents/provision` with `{project_id, agent_instance_id, agent_name,
harness, monthly_budget_usd}` + `Authorization: Bearer <service_token>` (secret at
`/etc/llm-manager/secrets/service_token`, 600). Idempotent on `external_id =
project_id/agent_instance_id` — retries return the EXISTING raw key (stored server-side in
`agent_keys.raw_key`), creation returns it once. Also rotate/revoke/status endpoints.
Never expose `agent_keys.raw_key` through the web UI.

## Cost display separation (§H)

Provider spend and direct-compute cost are DIFFERENT metrics: local models show
`provider_spend_usd = 0.0 (actual — local)` while direct compute comes from GPU NVML kWh ×
seasonal rate; OpenRouter rows carry provider-reported spend with local compute `n/a`.
Every energy total includes `telemetry_coverage_pct` (distinct sampled minutes ÷ window
minutes) — partial windows must be labeled partial. Unknown ≠ $0.0000. Integrator gate
tests: 100 W × 1 h = 0.100 kWh; 1000 W × 1 h = 1.000 kWh.

## Session verification evidence (2026-09-13)

- All 5 hosts healthy + routable after migration; VM401 recovered earlier in session (kernel-module fix).
- Gated `/v1/models`: 401 without key, 401 with bogus key.
- Completions through manager verified for vLLM (`startupteams/general`) and llamacpp paths.
- Nonexistent model → explicit 400 "Invalid model name passed in model=...".
- Recovery engine live-flagged the .165 ACL gap and logged `recovery_success` after fix.

## Session-2 acceptance results (2026-09-13 evening) — all §L fleet tests PASS

- **Desired-state E2E (VM111/.164)**: STOPPED_INTENTIONAL → engine logged
  `intentional_state_pending`, made ZERO recovery actions across multiple 60s ticks;
  `/api/hosts/<ip>/power-off` returns 409 unless intentional-off is set first; VM stayed
  stopped. Restore → `outage_detected` → `recovery_vm_start` → `recovery_success` →
  backend 200 → registry `healthy|routable=t` on the next sync. Full FSM proven both ways.
- **Service API idempotency**: provision ×2 with same external_id → second returns
  `status: existing` + same key_id + same raw key. Status listing verified.
- **Recovery engine vs. live load (lesson, not a bug):** two concurrent benchmark jobs
  saturated VM401; the engine's health probe failed → `service_degraded` →
  `recovery_service_restart` → clean vLLM reload. This is CORRECT §K2 behavior — but
  benchmark harnesses must run legs SERIALLY (one bench process at a time) or the
  manager will restart the engine mid-benchmark. If a restart happens mid-run, wait for
  backend 200 (model reload ~2-4 min), `pkill -f bench_`, and re-run the leg.
- **VM111 note:** `systemctl is-active vllm` says `inactive` there while HTTP health is
  200 — that guest uses a different unit name; the manager's health model is HTTP-probe
  based and authoritative. Never use unit-name presence as the health signal.

## Phase 19 benchmarking on MIAM-00112 (VM401, 6×5060 Ti, TP1/DP6/EP6 baseline)

Harness: `/root/bench_00112.py` on VM401 (wraps `vllm bench serve` + NVML snapshots;
results in `/root/v011-bench/<tag>.json` + a manifest JSON per run).

**vllm bench serve gotchas (vLLM 0.28.0):**
- `--model qwen3.6-35b-a3b` (the served alias) makes the client try an HF hub lookup for
  the tokenizer and FAIL all requests with "not a valid model identifier" — pass
  `--tokenizer QuantTrio/Qwen3.6-35B-A3B-AWQ` (the repo id, cached locally) instead.
- `--endpoint` takes the PATH only (`/v1/chat/completions`); put the host in
  `--base-url http://127.0.0.1:8000`. Concatenating a full URL into `--endpoint`
  silently fails every request (all-failed result, exit 0 — check `completed > 0`).
- Export `HF_HOME=/opt/vllm-cache` for the bench client.
- MEASURED BASELINE (2026-09-13/14, 256-out legs, zero failures across every run):
  - **MIAM-00112** (Qwen3.6-35B-A3B, TP1/DP6/EP6, max_model_len 32768): C1@4K 3,607
    tok/s TTFT 1.5s ITL 54ms; C10@4K 6,530 tok/s TTFT 8.2s ITL 63ms; 16K legs saturate
    ~8,200 tok/s (KV-bound on 16 GB cards); **C10@25K 40/40 ✓ 8,226 tok/s TTFT 60.4s
    ITL 193ms → the §19.1 ≥10-agent/≥25K gate is MET**; soak C10×8K 400/400 ✓ (424 s;
    TTFT 179 s is 400-deep queue wait, not per-request latency). 32K input is NOT
    qualifiable at max_model_len 32768 (32,768 in + 256 out > window) — document as
    not-supported at the preset, or raise --max-model-len and requalify.
  - **MIAM-00111** (Qwen3.8-27B-AWQ-INT4 dense, TP2/DP3, max_num_seqs 128): C1@4K
    2,635 tok/s TTFT 8.6s ITL 101ms; C10@4K 3,106 tok/s TTFT 24.9s; 16K legs TTFT
    77–111 s (each 2-GPU replica prefills its own queue).

## Phase 20 topology comparison: quality is topology-INVARIANT — decide on speed/energy

The §20.3 coding eval scored IDENTICALLY under both working topologies (6/6 tasks,
10/10 rubric groups for TP2/DP3 AND TP4×1 — same checkpoint, same rubric).
Methodology consequence: run the quality eval ONCE per checkpoint to confirm
invariance; the topology decision is made on throughput/TTFT/energy, never by re-run
rubric evals expecting different scores. Measured so far (VM103, /root/v011-bench/):
- eval TP2/DP3: 313.4 s, 18,000 out-tokens | eval TP4×1: 211.3 s (32 % faster), only
  4/6 GPUs busy → for LOW-concurrency quality work TP4 wins on latency AND idle-GPU
  energy; for ≥C8 fleet throughput TP2/DP3 wins (3 replicas absorb concurrent legs —
  TP4's 16K legs queue all prefill on one engine and run ~3-5× slower).
- Topology-error ladder actually hit while qualifying (all in one evening): DP6 dense
  → per-worker OOM (every DP worker loads the FULL model); TP6 → `AssertionError:
  16 is not divisible by 6` (linear-attn dim 16); TP2/DP3 default → Mamba-cache abort
  → fixed with `--max-num-seqs 128`. TP4 passes head math (24/4 heads ÷ 4) but see
  the queueing note.
- Presets saved in `hosting_command_presets`: `ROLLBACK-qwen3.6-35b-a3b-DP6EP6`,
  `CANDIDATE-qwen3.8-27b-AWQ-DP6` (actually TP2/DP3), `CANDIDATE-qwen3.8-27b-AWQ-TP4`,
  and VM401's `FAST-WORKER-PRODUCTION`. **Direct-SQL preset INSERTs must populate
  `content_hash` (NOT NULL) — compute sha256(content); only the app path fills it.**

## Deferred / next

- REMAINING for v0.11 closure (2026-09-14 status): pick qwen3.8 production topology
  (TP2/DP3 vs TP4 — data above; energy/1M-token math still to compute from NVML
  samples), C12 leg if stable, restore host `desired_service_state='SERVING'` on
  .161 after benchmarking (left in MAINTENANCE during the topology sweep), registry +
  `litellm_sync.py` re-sync if the served preset changes, Phase 21 frontier
  single-host test (C1/C2 only, NO RDMA), then write
  `MARION-IA-USA-DEFAULT-MODEL-BASELINE-QUALIFICATION.md` (template of required
  sections is in the plan §24; the measured data above feeds it directly).
- Kernel-module-per-kernel trap on GPU VMs (see SKILL.md pitfall) — consider pinning kernels or automating matching module installs before reboot.
