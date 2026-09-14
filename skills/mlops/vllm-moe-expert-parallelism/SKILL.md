---
name: vllm-moe-expert-parallelism
description: "Serve vLLM mixture-of-experts (MoE) models across multiple GPUs: expert-parallel topology sizing (TP/DP/EP), launch flags, Blackwell/SM-arch first-run JIT build failures, and multi-GPU fabric verification for hosts without NVLink."
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [vllm, torch]
platforms: [linux]
metadata:
  hermes:
    tags: [vLLM, MoE, Expert Parallelism, Mixture-of-Experts, Multi-GPU, Blackwell, JIT Build, NCCL, Tensor Parallelism]

---

# vLLM MoE / Expert Parallelism + Multi-GPU bring-up

Use when serving a mixture-of-experts (MoE) model with vLLM across several GPUs — sizing the
TP/DP/EP topology to fit VRAM, passing the flags, and debugging the first-run JIT build that
new GPU architectures (e.g. Blackwell SM 12.0) trigger. Complements the general
`serving-llms-vllm` skill (when that one is available/protected, keep the reusable MoE +
JIT-build detail here).

## MoE model-parallel topology sizing

For MoE models vLLM combines three parallel axes; the sizing identity is:

```
EP_SIZE = TP_SIZE × DP_SIZE          # only when --enable-expert-parallel is set
```

So `--tensor-parallel-size 2 --data-parallel-size 3 --enable-expert-parallel` on 6 GPUs =
**TP2 / DP3 / EP6**: expert weights sharded across all 6 expert-parallel ranks; attention
weights sharded only within each 2-GPU TP group. This fits a large MoE on low-VRAM cards
(e.g. 16 GB/GPU) where the reference build used TP1/DP6/EP6 on 20 GB cards. Escalation when
VRAM is still tight: TP2/DP3 → TP3/DP2 → TP6/DP1.

Relevant launch flags (vLLM 0.28.x / V1 engine):
- `--enable-expert-parallel` + `--expert-placement-strategy linear|round_robin`
  (start `linear`; change only one variable at a time).
- `--tensor-parallel-size N --data-parallel-size M` (their product = EP size when EP on).
- `--api-server-count` defaults to `data_parallel_size` (one OpenAI API server per DP group).
- Optional turboquant KV-compression flags if the build supports them
  (`--kv-cache-dtype turboquant_k8v4 --attention-backend TURBOQUANT`).

**Verify the topology, don't assume it.** Engine logs name workers `Worker_DP<n>_TP<n>_EP<n>`
(e.g. `Worker_DP2_TP1_EP5`) and report `world_size=6` + `api_server_count=3`.

## Multi-GPU fabric: verify before you trust TP/EP scaling

On a host with **no NVLink** (every GPU on its own PCIe host bridge → `PHB` in
`nvidia-smi topo -m`):
- `torch.cuda.can_device_access_peer(i, j)` is **False everywhere** (no P2P/GPUDirect).
- NCCL all-reduce aggregate saturates ~6–7 GB/s (vs tens of GB/s with NVLink).
Cross-GPU traffic for TP/EP comms traverses host memory — a hard ceiling on expert-sharding.
Measure it (NCCL allreduce 1–128 MB) before scaling; it's a platform-architecture limit, not
necessarily a hardware fault. Record it for any pre-vs-post/motherboard comparison.
- Idle GPUs park the PCIe link at Gen1/low power (ASPM). Don't read a link fault into
  `pcie.link.gen.current == 1` at idle — check `gen.max` / `lspci ... LnkSta2 Target Link Speed`
  and confirm it rails up under real load.

## First-run JIT build on a NEW SM architecture (e.g. Blackwell SM 12.0)

On an architecture the prebuilt kernels don't cover, vLLM JIT-compiles device kernels
(flashinfer / cutlass) at first `vllm serve`, invoking `nvcc` + `ninja` through ninja. Pitfalls
in the order you hit them:

1. **Missing nvcc and/or ninja.** pyTorch may be built for one CUDA (e.g. `2.13.0+cu130`,
   CUDA 13.0) while vLLM's pip deps pulled a newer `nvidia/cu13` toolkit (13.3.73) with no
   system `/usr/local/cuda`. Point the compiler at the pip-bundled toolkit and put nvcc+ninja
   on PATH:
   ```bash
   export CUDA_HOME=/opt/vllm-venv/lib/python3.12/site-packages/nvidia/cu13
   export PATH="/opt/vllm-venv/bin:$CUDA_HOME/bin:/usr/bin:$PATH"
   export LD_LIBRARY_PATH="$CUDA_HOME/lib:$LD_LIBRARY_PATH"
   ```
   Failures present as `RuntimeError: Worker failed ... 'nvcc' not found` / `'ninja' not found`.

2. **Toolkit/compiler incompatibility guard.** flashinfer's ccl bundle carries a preprocessor
   guard (`.../cccl/libcudacxx/include/cuda/std/__cccl/cuda_toolkit.h`) that raises
   `#error "CUDA compiler and CUDA toolkit headers are incompatible..."` when bundled headers
   and nvcc skew (CUDA 13.0 vs 13.3). The env var `CCCL_DISABLE_CTK_COMPATIBILITY_CHECK=1` does
   NOT reliably propagate into the ninja subprocess. Reliable fix — comment out the guard (it's
   a conservative heuristic; 13.3-built PTX runs fine against a 13.0 driver):
   - Replace the `# error ...` line with a comment (regex `(?m)^#\s*error .*$` → comment).
   - Verify with a one-file standalone compile before relaunching:
     `nvcc -gencode=arch=compute_120f,code=sm_120f -c <flashinfer-side>/csrc/sampling.cu -o /tmp/t.o`

3. **First graph build is slow.** After the kernel build clears, vLLM compiles CUDA graphs;
   `shm_broadcast "No available shared memory broadcast block found in 60 seconds"` is a
   **normal** mid-compile message. Weights resident + GPUs spinning util = still compiling.
   Give it several minutes before concluding it's stuck.

4. **Linker can't find `-lcudart`.** Even with nvcc/ninja on PATH and the CTK guard gone, the
   build compiles objects then dies at link with `ld: cannot find -lcudart: No such file or
   directory`. Root cause: the pip `nvidia/cu13` package installs its `.so` runtime libraries
   in `.../nvidia/cu13/lib`, but flashinfer's ninja link command hardcodes the classic CUDA
   layout and passes `-L.../cu13/lib64 -L.../cu13/lib64/stubs -lcudart -lcuda`. The pip package
   also ships only the **versioned** `libcudart.so.13` (no unversioned `libcudart.so`), so the
   linker finds neither. Fix (venv-local, reversible):
   ```bash
   export C=/opt/vllm-venv/lib/python3.12/site-packages/nvidia/cu13
   ln -sfn lib "$C/lib64"                      # flashinfer searches lib64/
   ln -sf libcudart.so.13 "$C/lib/libcudart.so"  # unversioned symlink for -lcudart
   ```
   Pull the exact link line from the log (`grep -E '\-lcudart|collect2' vllm_server.log`) to
   confirm which `-L` dirs it searches before guessing. A standalone single-file **compile**
   (`nvcc ... -c csrc/sampling.cu`) proves the front-end is fine but does NOT exercise the
   link step — so a clean standalone compile does not guarantee the ninja link will succeed.
   Clearing the flashinfer build cache (`rm -rf ~/.cache/flashinfer/<ver>`) between attempts
   forces a from-scratch retry; otherwise a stale partial ninja state silently no-ops.

- Read *through* `RuntimeError: Worker failed with error 'Ninja build failed. Ninja output:…'`
  wrappers to the real `#error`/`error:` line — that's the actual root cause.

## References
- `references/first-boot-jit-build.md` — full transcript of the Blackwell bring-up and the
  ccl guard patch.