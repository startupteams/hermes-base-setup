# Default Model Baseline — Measured Results (v0.11, verified 2026-09-14)

Source of truth for fleet benchmark numbers. Per plan §24: future model upgrades must
benchmark against these numbers, not impressions. Raw artifacts:
- VM401 (MIAM-00112): `/root/v011-bench/*.json`, `/root/bench_serial2.log`
- VM103 (MIAM-00111): `/root/v011-bench/*.json` (+ `eval_coding_qwen38_{c1,tp4}.json`), `/root/bench_00111.log`, `/root/bench_tp4.log`
All legs: `vllm bench serve` via `scripts/bench_serve_wrapper.py`, serial, 256 out-tokens.

## MIAM-00112 / VM401 — Fast Worker Bee (6× RTX 5060 Ti 16GB, MoE Qwen3.6-35B-A3B-AWQ)

Topology: **TP1/DP6/EP6** (one full replica per 16 GB card), `max_model_len 32768`, `max_num_seqs 64` (Mamba-cache bound), `gpu-mem-util 0.92`.

| Leg | total tok/s | mean TTFT | mean ITL | completed |
|---|---|---|---|---|
| C1@4K | 3,607 | 1.53s | 54ms | 32/32 |
| C1@16K | 8,187 | 16.7s | 121ms | 32/32 |
| C4@4K | 5,379 | 5.5s | 63ms | 32/32 |
| C4@16K | 8,328 | 28.2s | 120ms | 32/32 |
| C8@4K | 6,651 | 6.9s | 46ms | 32/32 |
| C8@16K | 8,090 | 29.5s | 129ms | 32/32 |
| C10@4K | 6,530 | 8.2s | 63ms | 40/40 |
| C10@16K | 8,248 | 36.2s | 160ms | 40/40 |
| **C10@25K** | 8,226 | 60.4s | 193ms | 40/40 — **§19.1 gate MET** |
| **Soak C10@8K, 400 prompts** | 7,981 | 179.0s* | 267ms | **400/400, zero failures** |

*Soak TTFT is the 400-deep admission-queue figure (all requests accepted at once); steady-state ITL is the operative number. Output throughput saturates ~125 tok/s per stream at 16K (KV-bound on 16 GB cards, expected). 32K input NOT qualified (max_model_len 32768 < 32K+256) — document as not-selected unless the context is raised.
Preset saved: `FAST-WORKER-PRODUCTION` (scope_key 10.0.20.162).

## MIAM-00111 / VM103 — Coding Worker Bee (6× RTX 3080 20GB, dense Qwen3.8-27B-AWQ-INT4)

Model: `cyankiwi/Qwen3.8-27B-AWQ-INT4` (Apache-2.0, sha 6e134bae811fb5adac50ee042ae5f029ac6779aa), compressed-tensors W4A16 g32, 64L/5120H. `max_num_seqs 128` (163 Mamba blocks at 0.90 util). `max_model_len 32768`.

**Topology comparison (8/8 legs each, C1/C4/C8/C10 × 4K/16K):**

| Leg | TP2/DP3 (3 replicas × 2-GPU shard, all 6 GPUs) | TP4 (1 replica × 4 GPU, 2 idle) |
|---|---|---|
| C1@4K | TTFT 8.6s · ITL 101ms · 2,635 tok/s | TTFT 56.4s · ITL 287ms · 957 tok/s |
| C1@16K | 77.1s · 184ms · 2,599 | 225.7s · 738ms · 1,061 |
| C4@4K | 18.5s · 94ms · 2,862 | 61.0s · 193ms · 1,225 |
| C4@16K | 84.1s · 181ms · 2,896 | 237.6s · 739ms · 1,061 |
| C8@4K | 19.6s · 91ms · 2,922 | 63.1s · 193ms · 1,225 |
| C8@16K | 85.8s · 154ms · 2,955 | 239.5s · 738ms · 1,062 |
| C10@4K | 24.9s · 112ms · **3,106** | 74.7s · 286ms · 1,167 |
| C10@16K | 110.6s · 165ms · 2,723 | 311.2s · 769ms · 1,034 |
| §20.3 coding eval | 6/6 tasks · 10/10 rubric · 313s | 6/6 tasks · 10/10 rubric · 211s |

**Verdict: TP2/DP3 wins at the ~10-concurrent-agent target** — ~2.7× aggregate throughput, ~3× lower TTFT, ~2.5× lower ITL, all 6 GPUs productive (better energy/token). TP4's only edge is single-stream sequential-task wall-time. TP divisibility constraint on this arch: TP ∈ {1,2,4} (24/4/16-head dims; 6∤4). TP6 rejected by vLLM assert; DP6 rejected by OOM (dense model: every DP worker loads FULL weights).
Presets on .161: `ROLLBACK-qwen3.6-35b-a3b-DP6EP6` (untouched per §18.1), `CANDIDATE-qwen3.8-27b-AWQ-DP6` (=TP2/DP3), `CANDIDATE-qwen3.8-27b-AWQ-TP4`.

## Rejected / constrained configurations (avoid re-testing)

- Qwen3.8-27B DP6 on 3080-20G: OOM every GPU (full weights per worker).
- Qwen3.8-27B TP6: vLLM assert (head-count divisibility).
- Qwen3.6-35B-A3B on 5060 Ti 16G: `--max-num-seqs 256` default aborts (Mamba cache ~92 blocks) → 64.
- NVFP4 quants need Blackwell; Ampere fleet takes AWQ/GPTQ INT4 only.

## Eval harness

`templates/eval_coding.py` — 6-task §20.3 set (bug_diagnosis, small_repo_edit, multi_file_refactor, test_writing, infra_troubleshoot, code_review), fixed rubric. Requires content/reasoning merge (reasoning models return `content=None` when thinking eats max_tokens) and max_tokens ≥ 3000.
