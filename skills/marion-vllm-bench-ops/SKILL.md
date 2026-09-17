---
name: marion-vllm-bench-ops
description: MARION-IA-USA vLLM benchmarking/hosting ops lessons — MAINTENANCE gate vs recovery engine, vllm bench serve gotchas, Qwen3.8-27B topology on 6-GPU hosts, per-kernel NVIDIA driver risk
---

# MARION vLLM benchmark & hosting ops (learned 2026-09-13, v0.11 Phase 19/20)

## Recovery engine vs benchmarks — use the MAINTENANCE gate
The LLM Manager recovery engine (60s tick on VM114) restarts a service when its HTTP health probe reports unhealthy. Heavy benchmarks (25K-context prefills) can stall the probe past timeout → false-positive `service_degraded` → bounded service restart **kills the benchmark mid-run**. Evidence: recovery_events ids 16–18 (22:48) killed a 25K leg; after the MAINTENANCE patch, identical load produced `maintenance_skip` (ids 19–24) and the bench survived.

Procedure before any heavy bench:
```sql
UPDATE hosts SET desired_service_state='MAINTENANCE' WHERE guest_ip='<ip>';
```
Afterwards restore:
```sql
UPDATE hosts SET desired_service_state='SERVING' WHERE guest_ip='<ip>';
```
Engine behavior (v011_recovery.py on VM114 `/opt/llm-manager/app/`): `MAINTENANCE` → logs `maintenance_skip`, never restarts; `SERVING` → bounded recovery (2 VM starts / 2 service restarts, cooldown, then FAILED). Backups: `v011_recovery.py.bak.maint`.

**Always run bench legs serially.** Two concurrent bench jobs on one host will saturate it and trigger the false-positive path even with SERVING semantics.

## vllm bench serve gotchas (vLLM 0.28)
- `--tokenizer <real HF repo>` is REQUIRED — the served alias (e.g. `qwen3.6-35b-a3b`) fails HF lookup and all requests fail with 0 completed.
- Endpoint form: `--base-url http://127.0.0.1:8000 --endpoint /v1/chat/completions`. A full URL in `--endpoint` silently completes 0 requests with rc=0.
- Set `HF_HOME=/opt/vllm-cache` (model/tokenizer cache location).
- Request-rate approximates concurrency for async traffic; `--num-prompts max(C*4,32)`; 16K-input legs take ~2–4 min each, 25K ~2.5 min for 40 prompts.

## Host topologies (measured)
- **VM401 (6× RTX 5060 Ti 16G, MIAM-00112), Qwen3.6-35B-A3B AWQ MoE:** TP1/DP6/EP6 works (3B-active MoE fits per-GPU). max_model_len 32768. Production preset `FAST-WORKER-PRODUCTION` in hosting_command_presets (scope_key 10.0.20.162). Full quick matrix C1–C10 × 4K/16K all-pass, ~8.2K tok/s at 16K, soak 400/400 at C10×8K.
- **VM103 (6× RTX 3080 20G, MIAM-00111), Qwen3.8-27B AWQ dense:** DP6 **OOMs** (each DP worker loads full 27B weights). TP6 fails `AssertionError: 16 is not divisible by 6` — attn heads 24, KV heads 4 → TP must divide 4: TP ∈ {1,2,4}. Working: **TP2/DP3 + `--max-num-seqs 128`** (linear-attention/Mamba cache only ~163 blocks at gpu-mem-util 0.90; default max_num_seqs 256 fails CUDA graph capture). TP4 single replica also works; 2 GPUs idle.
- Qwen3.8-27B is a reasoning model: `content` may be None with text in `reasoning_content` — merge both when grading outputs (eval_coding.py does this).

## Benchmark comparison method (quality-per-energy)
1. Coding eval first (`/root/eval_coding.py` on VM103): 6 fixed tasks, rubric substring groups; compare wall-time + output tokens at equal rubric score.
2. Then quick matrix C1/4/8/10 × 4K/16K per topology; compare aggregate tok/s AND per-GPU power draw (`nvidia-smi --query-gpu=power.draw`) — fewer active GPUs at similar quality = better energy/task.

## VM401 NVIDIA per-kernel driver risk
VM401 boots kernel 6.8.0-139 but NVIDIA modules existed only for 138 (no DKMS). GPUs vanish → vLLM dead. Fix: `apt-get install linux-modules-nvidia-580-open-<kernel>-generic`, modprobe nvidia/nvidia_modeset/nvidia_uvm, restart vllm. **Pin kernels on GPU VMs or install matching module packages before any reboot.**

## Provisioning presets (hosting_command_presets on CT115 llmmanager DB)
Columns: scope_type/scope_key/engine/friendly_name/content/**content_hash (NOT NULL, sha256 of content)**/created_by. Existing: `ROLLBACK-qwen3.6-35b-a3b-DP6EP6` + `CANDIDATE-qwen3.8-27b-AWQ-DP6` + `CANDIDATE-qwen3.8-27b-AWQ-TP4` (10.0.20.161), `FAST-WORKER-PRODUCTION` (10.0.20.162). Rollback = load preset + explicit confirmed restart (save ≠ restart, §F3).
