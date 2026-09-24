---
name: marion-vllm-bench-ops
description: MARION-IA-USA vLLM/llama.cpp hosting & benchmarking ops — pre-flight model feasibility gate, provider-vs-local detection, node-identity fingerprint routing map, MAINTENANCE gate vs recovery engine, duplicate-unit crash loops, Qwen3.8-27B topology on 6-GPU hosts, per-kernel NVIDIA driver risk
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

## ⛔ NEVER upgrade vLLM on VM109 / VM111 — custom fork
Both hosts serve Qwen3.6-35B-A3B at **262144** context using **non-upstream** flags:
`--kv-cache-dtype turboquant_k8v4 --attention-backend TURBOQUANT` (+ `--scheduler-reserve-full-isl
--watermark 0.05 --kv-cache-metrics`). Live fingerprint `vllm-0.28.0-dp6-ep-2bfd2e21`
(VM109 and VM111 share it — identical build). Treat `/opt/vllm-venv` on those hosts as **immutable**:
any "upgrade vLLM" step destroys 262 K capability. Also note their `--max-model-len auto` resolves to
262144 — do not assume 70 K on these hosts, and check the *live* fingerprint rather than a plan's claim.

## Pre-flight model feasibility gate
Before any download / alias retag / "extend the existing deployment": measure the artifact from the HF
API, compare against the **real** envelope (measured guest RAM − live services, VRAM × gpu_mem_util,
minus KV + CUDA graphs + page cache), and check precision-vs-SM support. FP8 needs SM89+ → **the
official DeepSeek-V4.1-Flash artifact can never run on a 3080, at any size**. Reject with arithmetic
*before* spending hours on a download. Full recipe, thresholds and measured 2026-09-23 numbers:
`references/model-placement-feasibility.md`.

## Provider-vs-local detection — verify "it already works" before extending it
A plan saying *"extend the currently working X deployment"* must prove X is local. Signals: name ending
`-api`, response `id` shaped `gen-…`, `provider: Together|DeepInfra|Alibaba` (cloud); `system_fingerprint`
`vllm-*` (local vLLM) or `b1-*` (local llama.cpp). A single alias returning *different* `provider` values
across calls is a provider **router**, not one backend. In MARION, `frontier` and
`deepseek-v4.1-flash-api` are **cloud-only** — there is no local DeepSeek deployment.

## Alias→node routing map via system_fingerprint
vLLM's `system_fingerprint` identifies the *node instance*, so it maps public aliases to hardware:
`fast`→VM401 (`vllm-0.28.0-dp6-ep-5a52ab37`); `qwen3.6-35b-a3b`→VM109 **and** VM111 pool
(`…-dp6-ep-2bfd2e21`, shared); `code` + `qwen3.8-27b`→VM103 (`…-tp2-dp3-263e7d50`);
`startupteams/llamacpp`→VM149 (`b1-311d421`).
**Pitfall:** probing a node directly on `:8000/v1/chat/completions` with an invented model name returns
**HTTP 404** — pass that server's real `--served-model-name`.
Run it all with `scripts/fleet_probe.py` (`--direct` for per-node fingerprints, `--nodes` for ExecStart +
GPU inventory via PVE guest-exec).

## Duplicate systemd units → crash loop (recurring across VMs; check EVERY host)
Symptom: one unit holds `:8000` while a second unit sits in `activating`, retrying
`OSError: [Errno 98] Address already in use` every few seconds. Diagnose with
`systemctl is-enabled` + `is-active` + `systemctl show -p NRestarts --value <unit>` + journal.
Fix = `systemctl stop <the redundant unit>` — serving is unaffected because the other unit owns the port.
**Do not assume a prior "resolved on VM109" note covers the other hosts** — this was found live on
**VM111** on 2026-09-23 (`vllm-qwen.service` active vs `vllm.service` looping) long after the VM109
note. Unit naming is not yet normalised (`vllm-qwen.service` on VM111 vs `vllm.service` elsewhere).

## Hardware envelope + access paths
- VM103/109/111 = 6× RTX 3080 20 GB; **VM401 = 6× RTX 5060 Ti 16 GB (SM120)** — the fleet is **not**
  homogeneous, so never apply one host's fit/kernel math to another.
- VM149 = 16 cores, **62 GiB usable, no GPU** (llama.cpp only; Qwen3-4B at 32 K / 4 slots).
- All five GPU/CPU VMs have 64 GiB guest RAM (62 usable) and `balloon=0`; VM114 = 8 vCPU / 16 GiB.
- **MIAM-00112 (VM401) has a failing DIMM (channel#7) — hardware service required.** Do not make it the
  sole safety anchor for a migration.
- Access: `pve.py` guest-exec from `~/.llm-manager-v011` reaches every guest (PVE API ticket + `pve_root.txt`).
  Prefer it over direct SSH, which is not keyed on the GPU VMs. VM114 accepts `ubuntu@` with passwordless `sudo`.
- LLM Manager is **v0.11.0** (`/healthz` → `version`); app = `/opt/llm-manager/app/main.py` (FastAPI,
  session-cookie auth), DB on CT115. Only `hosting_command_presets` exists — there are **no**
  history/benchmark tables or endpoints, so a "benchmark history" feature is greenfield, not an extension.
  *(Updated 2026-09-23 evening: `deployment_revisions` table + `/api/history/*` endpoints + dashboard
  history card now exist — see self-hosted-llm-gateway skill for the pattern.)*

## Pre-flight feasibility gate v2 — architecture support, not just size math (2026-09-23, Flash-Next chain)

The size-vs-VRAM gate (references/model-placement-feasibility.md) is necessary but NOT sufficient.
Before any download, run these checks IN ORDER on the target venv (each one killed a phase of the
Qwen3.8-Flash-Next attempt — full chain in `references/qwen4exp-flashnext-ampere-blockers.md`):

1. **Arch adapter check:** does the target vLLM build's model registry know the architecture?
   `grep -o '"Qwen4[^"]*"' .../vllm/model_executor/models/registry.py`. transformers having the
   config class is NOT enough (transformers 5.16.1 knew `qwen4_exp`; vLLM 0.28.0 did not; upstream
   0.30.0 added it). Never assume a newer transformers unblocks serving.
2. **TP derivation from ALL head-count dims:** TP must divide num_attention_heads AND num_key_value_heads
   AND every linear-attention head count. Flash-Next (24/2/16/48) → **TP ∈ {1,2} only** — a plan's
   "TP2/PP3" hypothesis can be dead on arrival. Derive, don't copy.
3. **MoE expert-width divisibility:** without EP, fused-MoE treats tp_size = TP×DP; expert
   `moe_intermediate_size % (TP×DP) != 0` = hard assert. With EP the expert dim uses EP instead —
   but see 4.
4. **HC/seq-parallel conflicts:** some archs (Qwen4Exp hyper-connections) raise
   `NotImplementedError` when EP+TP>1+DP>1 enables sequence-parallel MoE. Backends that avoid it
   may be REMOVED from the pip build (`naive` a2a exists in source but 0.30.0's ParallelConfig
   falls back to `allgather_reducescatter`); local sed-patches to vllm config are possible
   (`.bak` + ast.parse check).
5. **CPU-offloaded big tables multiply per worker:** Engram/PLE CPU offload allocates a shard per
   WORKER, not per node — 17.5 GB × 6 workers = 105 GB shmem against a 108 GB guest = global oom-kill
   every boot. `dp_shared_memory: true` did NOT deduplicate; `embedding_across_dp: true` failed a
   divisibility assert (`320001536 % 6 != 0`). Shmem math must count per-worker before committing.
6. **OOM forensics pattern:** `journalctl -k | grep "Out of memory"` shows per-process anon/file/shmem
   RSS — the shmem number is what exposed the PLE multiplication. Sample with a loop script
   (`AnonPages`/`Shmem`/`Cached` every 5s) during load; peak-shmem tells you which mechanism failed.

**GGUF size claims — verify against the actual repo blobs.** A search-result claim ("smallest GGUF
anywhere = 70 GB") was wrong by 10×: unsloth UD quants of Qwen3.8-27B go to 6.2 GB (IQ1_S), UD-Q4_K_M
= 16.5 GB. Always enumerate `api/models/<repo>?blobs=true` per candidate repo before declaring a fit
gate failed. Also: a 27B DENSE model on a 16-core CPU box measured **0.8 tok/s** — smaller quant ≠
viable CPU serving; check the arch (dense vs MoE) before proposing CPU lanes.

**vLLM major-version side-by-side pattern:** never upgrade the production venv (custom forks!).
Build `/opt/vllm-venv-<ver>/`, verify with `pip show` + `import torch; torch.cuda.get_device_capability()`
(SM86 supported in 0.30; SM90-only fast paths fall back gracefully — check `_gemm_plans()` returns {}
→ falls back to F.linear). Stage artifacts on a separately-attached disk (hot-plug scsi + mkfs + fstab
`nofail` works live) sized for the FULL artifact, and raise guest RAM BEFORE the load attempt
(PVE `PUT config {memory: N}` then stop/start — hotplug of memory isn't reliable on existing VMs).

**pve.py guest-exec timing cap:** the helper's internal wait is ~120 s — any longer command (model
loads, pip installs, downloads) must run detached (`setsid nohup ... < /dev/null &` inside a script
FILE) writing to a log, then poll. The qga channel also WEDGES under heavy RAM/page-cache pressure
(repeated `HTTP 500: QEMU guest agent is not running` mid-load) — poll the VM from the node side
(`/qemu/<id>/status/current` uptime/mem) and retry exec with patience instead of concluding the VM died.
