# Pre-flight model placement feasibility gate

**Rule: never start a download, never retag an alias, never "extend" a deployment until the
weight-byte math passes.** A model that cannot fit must be rejected with arithmetic, before it costs
hours of download and a production outage.

## 1. Measure the artifact from the Hugging Face API (cheap, no download)

```bash
# total weight bytes per repo (safetensors OR gguf)
curl -s "https://huggingface.co/api/models/<repo>/tree/main?recursive=true" 
```
With Python, sum `f["size"]` falling back to `(f.get("lfs") or {}).get("size")` — sharded repos report
per-shard LFS sizes.

```python
# per-quantization totals for GGUF repos (quant dirs are a path prefix)
agg = collections.defaultdict(int)
for f in tree:
    if f.get("type") != "file" or not f["path"].endswith(".gguf"):
        continue
    key = f["path"].rsplit("/", 1)[0] if "/" in f["path"] else "ROOT"
    agg[key] += f.get("size") or (f.get("lfs") or {}).get("size") or 0
```

Also read `safetensors.parameters` for the dtype breakdown (`BF16`, `F8_E4M3`, `I8`, ...) — that tells
you the released precision and therefore which GPU generation can execute it.

Search for community quants with:
`https://huggingface.co/api/models?search=<ModelName>&limit=40`

## 2. Compare against the real envelope — add every reserve, never just VRAM

```
usable_weights_vram  = Σ gpu_vram × gpu_mem_util        # not 100%
usable_host_ram      = guest RAM reported by `free -g`, minus live services already resident
required             = weight_bytes
                     + KV cache for the target context × concurrency
                     + CUDA graphs / activation / runtime buffers
                     + OS + page cache + file cache
```
Record the *measured* per-node `memory` and `balloon` from the Proxmox VM config, not the plan's
assumption. A 64 GiB guest with a live 18 GB/GPU model resident has almost no offload headroom left.

## 3. Architecture / precision gate (the usual silent killer)

| Released precision | Requires | RTX 3080 (SM86) |
|---|---|---|
| FP8 (`F8_E4M3`) | SM89+ (Ada) / Hopper | ❌ no FP8 tensor path |
| NVFP4 | Blackwell (SM120) | ❌ |
| INT8 / W4A16 (GPTQ/AutoRound, Marlin kernels) | SM75+ **and** an engine that ships the arch's kernels | ⚠️ only if the model arch is supported by the installed engine |
| GGUF (llama.cpp) | CPU or any GPU | ✅ but CPU-only decode is single-digit tok/s on large MoE |
| EXL3 / EXL2 | ExLlamaV3 runtime, newer GPUs | ❌ wrong engine (not vLLM) |

So: *"the official artifact is FP8"* is by itself disqualifying for the 3080 fleet, regardless of size.
A community INT4 quant does **not** rescue it unless the installed engine actually implements that
architecture's kernels.

## 4. Measured results (2026-09-23) — keep as reference points

| Artifact | Weights | Verdict on MARION |
|---|---:|---|
| `deepseek-ai/DeepSeek-V4.1-Flash` (official, FP8+INT8) | 510.3 GB | ❌ > 360 GB VRAM + 186 GB guest RAM; FP8 unsupported on SM86 |
| `lvkaokao/DeepSeek-V4.1-Flash-W4A16-Engram-AutoRound` | 451.7 GB | ❌ smallest vLLM-loadable found; still 92 GB over VRAM with zero KV headroom |
| `nvidia/DeepSeek-V4.1-Flash-NVFP4` | 527.3 GB | ❌ needs SM120 |
| `Mia-AiLab/…-EXL3-2.9bpw` | 210.6 GB | ❌ fits VRAM but is **ExLlamaV3, not vLLM** |
| `antirez/deepseek-v4.1-flash-gguf` (Q2) | 365.7 GB | ❌ llama.cpp only, over VRAM |
| `ggml-org/Qwen3.8-Flash-Next-GGUF` (Q8_0 only) | 163.2 GB | ❌ 2.6× VM149's 62 GB |
| `bartowski/Qwen3.8-Flash-Next-GGUF` IQ1_S (smallest published anywhere) | 70.1 GB | ❌ > 62 GB usable RAM, no KV room |

Envelope used: VM103/109/111 = 18× RTX 3080 20 GB = **360 GB**; each guest 64 GiB (62 usable).
VM401 = 6× **RTX 5060 Ti 16 GB (SM120)**. VM149 = 16 cores, **62 GiB usable, no GPU**.

**Lesson:** for a 180 B+ MoE target on this fleet, no GGUF/INT4 quant of a frontier model fits. State
that as an arithmetic conclusion rather than attempting the download.

## 5. Provider-vs-local detection (do this BEFORE believing "it already works")

A plan that says *"extend the currently working X deployment"* must first prove X is local.

| Signal | Meaning |
|---|---|
| Registration ends in `-api` (e.g. `deepseek-v4.1-flash-api`) | provider-backed model, **not** a local deployment |
| Response `id` shaped `gen-...` | OpenRouter-style provider generated it |
| Response carries `provider: "Together" / "DeepInfra" / "Alibaba"` | cloud upstream; same alias may rotate upstreams |
| Response carries `system_fingerprint: "vllm-*"` | local vLLM |
| Response carries `system_fingerprint: "b1-*"` | local llama.cpp build |

A single alias can report different `provider` values across calls — that means a provider *router*,
not a single backend. Never relabel or repurpose a route based on its name alone.
