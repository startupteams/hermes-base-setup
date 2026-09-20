# 70K Hermes Model Qualification Runbook (MARION)

Session-proven on 2026-09-20 while qualifying Hermes-compatible 70K context aliases through LLM Manager.

## Trigger
Use when raising MARION local vLLM deployments above Hermes' >=64K context floor, or when qualifying `fast` / `code` aliases for long-context Hermes agents.

## Safety sequence
1. Create a timestamped workdir under `~/.llm-manager-v011/70k-migration-<timestamp>/` with `baseline/`, `bench/`, `logs/`, and `scripts/`.
2. Before any restart, capture:
   - manager DB tables: `hosts`, `model_registry`, `hosting_command_presets`, `deployments`, `manager_settings`, `qualification_envelopes`, `benchmark_runs`
   - `/etc/llm-manager/litellm_config.yaml`
   - authenticated manager `/v1/models`
   - direct backend `/v1/models` for each inference VM
   - `systemctl cat` for every relevant unit (`vllm.service`, `vllm-qwen.service`, llama.cpp units)
   - `vllm --version`, PyTorch/CUDA, `nvidia-smi -L`, memory totals, disk/model-cache state
3. Create rollback presets in `hosting_command_presets` from the exact live unit content before changing services.
4. Set `hosts.desired_service_state='MAINTENANCE'` before heavy long-context benchmark/restart windows so recovery does not fight deliberate load.
5. Restore `SERVING` after acceptance.

## Proven 70K configs

### VM401 / 10.0.20.162 / `fast`
- Model: `QuantTrio/Qwen3.6-35B-A3B-AWQ`
- Served model: `qwen3.6-35b-a3b`
- vLLM: `--max-model-len 70000`
- Parallelism: TP1 / DP6 / EP6
- Keep: `--max-num-seqs 64`, prefix caching, chunked prefill, `--enable-auto-tool-choice`, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_xml`
- Acceptance: 5 concurrent 65,536-token requests passed directly and through LLM Manager.

### VM103 / 10.0.20.161 / `code`
- Model: `cyankiwi/Qwen3.8-27B-AWQ-INT4`
- Served model: `qwen3.8-27b`
- vLLM: `--max-model-len 70000`
- Parallelism: TP2 / DP3
- Keep: `--quantization compressed-tensors`, `--max-num-seqs 128`, prefix caching, chunked prefill, `--enable-auto-tool-choice`, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_xml`
- Acceptance: 3 concurrent 65,536-token requests passed directly and through LLM Manager.

## Long-context harness pattern
- Build test prompts with the target model tokenizer; do not estimate by character count.
- Avoid repeated prose that decodes/retokenizes smaller than expected. Use newline-delimited varied strings and binary-search a prefix until `len(tokenizer.encode(prompt)) >= 65536`.
- Use OpenAI-compatible streaming to measure TTFT; capture JSON with direct backend and manager-path results.
- For manager-path tests against the self-signed local TLS endpoint, either ensure the cert is trusted in that runtime or instantiate the HTTP client with explicit `verify=False` for the controlled internal test harness.

## LLM Manager / Hermes metadata gotchas
- Regenerating LiteLLM config is not enough after registry changes: run `/opt/llm-manager/app/litellm_sync.py`, restart LiteLLM, then verify authenticated `/v1/models` and one real completion.
- Hermes uses local profile `custom_providers[].models[].context_length` metadata for initialization. After a backend is raised from 32K to 70K, update the Hermes profile metadata too or Hermes will still abort with `Model <alias> has a context window of 32,768 tokens` even though the server is now 70K.
- Generic LiteLLM virtual keys can fail auth if `models` is `null` in their verification token. Update the key to an explicit list containing the aliases/models being tested.
- `/v1/models` in the manager is registry-driven. Provider-backed models such as `frontier` must be represented in `model_registry` if the manager's model list should show them, even when LiteLLM can route them from YAML.

## DeepSeek V4.1 Flash no-download gate result
- HF metadata for `deepseek-ai/DeepSeek-V4.1-Flash` showed ~510GB total artifacts, including two ~101.5GB safetensor shards.
- Current VM109+VM111 pair has 12x RTX 3080 20GB = 240GB physical VRAM, ~120GB free local disk per VM at the time of qualification, and vLLM 0.28.0.
- This failed the no-download local feasibility gate before any large download. Safe fallback was to expose `deepseek/deepseek-v4.1-flash` via OpenRouter/LiteLLM as `deepseek-v4.1-flash-api` and `frontier`, without representing it as local.

## Final artifact convention
Write at least:
- `70K-MIGRATION-EXECUTION-LOG.md`
- `70K-MODEL-QUALIFICATION.md`
- `70K-ROLLBACK.md`
- benchmark JSON files under `bench/`
- a persistent handoff copy under `~/.llm-manager-v011/`
