# Qwen4Exp / Qwen3.8-Flash-Next on Ampere (6×RTX 3080) — full blocker chain, 2026-09-23

Measured evidence for the v2 feasibility gate (steps 1–6 in SKILL.md). Everything below was
reproduced live on VM103 (miam00111), not inferred.

## Verdict
Flash-Next (Qwen4ExpForConditionalGeneration) is NOT deployable on 6×RTX 3080 / 108 GB guest with
vLLM 0.30.0 as of 2026-09-23. Artifact + venv are staged for retry when upstream fixes Qwen4Exp
EP/HC/PLE constraints.

## Artifact selection (verified against live quant registries)
- **leoncca/Qwen3.8-Flash-Next-AWQ-g32** — 143.4 GB total = **91.1 GB GPU-resident** (true AWQ
  W4A16 g32 asymmetric, `quant_method: awq`, gemm) + **52.3 GB PLE** (FP8, Engram CPU-offloaded).
  True AWQ format works on both 0.28 fork (AutoAWQConfig) and 0.30. Staged at
  `/opt/hf-cache-030/hub/models--leoncca--Qwen3.8-Flash-Next-AWQ-g32/snapshots/85fffcf34826dd526a3b5a7abf95baf2345a9cac`.
- Jon-Nielsen FP8PLE (137.1 GB compressed-tensors pack-quantized, targets wtdcode fork) = alt.
- Intel W4A16-AutoRound (181.2 GB; `auto-round` method, needs auto_round pkg — fork has INCConfig
  but risky) and Minachist INT4-Mixed (175.3 GB) — larger, skip.
- TP support note from leoncca README: g32 chosen so expert width 640 divides under TP4 (640/4=160).

## Topology derivation (hard constraints)
- Full attn: 24 heads / 2 KV → TP ∈ {1,2}
- GDN linear attn: 16 key heads / 48 value heads → TP ∈ {1,2,4,8,16,24,48}
- **Common: TP ∈ {1,2}** → only TP2/DP3 is VRAM-feasible on 6×20 GB (TP4 single replica = 91/4 =
  22.75 GB/GPU > 18 GB budget; TP1/DP6 = 91 GB/card).

## Blocker chain (each step reproduced)
1. **Arch adapter:** vLLM 0.28.0 fork registry has no Qwen4Exp (has Qwen3.5/Qwen3Next/Gemma4).
   transformers 5.16.1 supports the config class — irrelevant for serving. vLLM 0.30.0 tag registry
   has `Qwen4ExpForCausalLM/ForConditionalGeneration/MTP` in `vllm/models/qwen4_exp/`.
2. **vLLM 0.30.0 Ampere support:** CUDA_SUPPORTED_ARCHS includes 8.6 (`7.5;8.0;8.6;9.0;9.0a`);
   torch 2.13.0+cu130 sees RTX 3080 (8,6). SM90-only low-latency GEMM plans degrade gracefully
   (`_gemm_plans()` returns {} on non-SM90 → standard `F.linear`).
3. **MoE assert without EP** (`fused_moe/config.py:1350` `assert intermediate_size % tp_size == 0`):
   expert width 640, tp_size seen = 6 (TP2×DP3 combined) → 640 % 6 = 2 → AssertionError. Same assert
   shape as Gemma4's 704 % 6. Fix attempt: `--enable-expert-parallel`.
4. **HC vs seq-parallel MoE with EP:** `vllm/models/qwen4_exp/nvidia/model.py:192` raises
   `NotImplementedError: Qwen4Exp HC does not support sequence-parallel MoE` when
   `use_sequence_parallel_moe` = a2a backend ∈ {allgather_reducescatter, deepep_*, flashinfer_nvlink_one_sided,
   mori_*, nixl_ep} AND EP AND TP>1 AND DP>1. Default backend = allgather_reducescatter → triggered.
   `--all2all-backend naive` would avoid it, but 0.30.0 pip REMOVED naive/pplx (ParallelConfig falls
   back to allgather_reducescatter) even though `cuda_communicator.py:182` still implements it.
   **Local patch applied:** `sed 's/if self.all2all_backend in \["pplx", "naive"\]:/... in ["pplx"]:/'`
   on `vllm/config/parallel.py` (backup `.bak.v5naive`, ast.parse verified). Upstream main still has
   naive in the Literal — a build from main would get this without the patch.
5. **PLE shmem multiplication = the killer.** Dead worker showed `shmem-rss: 19797760 kB`; system
   Shmem peaked at **105,376,372 KB (105 GB)** vs 108 GB guest → `oom-kill:constraint=CONSTRAINT_NONE`
   on VLLM::Worker_DP. `--engram-config '{"dp_shared_memory":true,"cpu_offload":true}'` did NOT
   collapse the copies (6 workers × ~17.5 GB each). `embedding_across_dp:true` then failed
   `AssertionError: 320001536 is not divisible by 6` (PLE numel vs TP×DP embedding-parallel size).
6. Also encountered: systemd strips raw JSON quotes in ExecStart (`Invalid JSON: key must be a
   string`) — single-quote the JSON arg in the unit file; verify actual argv via
   `tr "\0" "\n" < /proc/<pid>/cmdline | grep -A1 engram`.

## What was staged on VM103 (kept for retry)
- `/opt/vllm-venv-030/` — vllm 0.30.0 + torch 2.13.0+cu130 (imports fine, sees all 6 GPUs).
- `/opt/hf-cache-030/` — 250 GB ext4 scsi disk (sdb, UUID fb86116c, fstab nofail), full artifact.
- VM RAM raised 64 → **108 GB** (host has 125 GB total, ~12 GB spare — watch host pressure; PVE
  `PUT /nodes/miam00111/qemu/103/config {memory:110592}` + stop/start; balloon=0;
  `vm.vfs_cache_pressure=200`, dirty_bytes tuned).
- ParallelConfig naive patch (backup `parallel.py.bak.v5naive`).
- Launch command template (in vllm.service, currently reverted to baseline):
  `vllm-venv-030/bin/vllm serve <artifact-path> --served-model-name qwen3.8-flash-next --quantization awq
  --tensor-parallel-size 2 --data-parallel-size 3 --enable-expert-parallel --all2all-backend naive
  --engram-config '{"dp_shared_memory":true,"cpu_offload":true}' --max-model-len 70000 --max-num-seqs 128 ...`
- **Retry conditions:** upstream fixes HC+EP ban, per-worker PLE multiplication, or
  embedding_across_dp divisibility; OR a 192 GB guest; OR drop the PLE requirement entirely.

## Rollback used
`vllm.service` ExecStart replaced with the baseline preset-17 command (cyankiwi/Qwen3.8-27B-AWQ-INT4,
TP2/DP3, HF_HOME=/opt/vllm-cache) → `daemon-reload` → start; ~4 min to /v1/models 200.