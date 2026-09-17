# Blackwell (SM 12.0) first-boot JIT build — session transcript

Captured from the first bring-up of vLLM 0.28.0 on 6x RTX 5060 Ti (Blackwell, `compute_120f`)
serving a Qwen3 MoE (`qwen3_5_moe`, 256 experts, 8 active/token, 40 layers, AWQ). The
sequence below is the exact debugging path across three failed `vllm serve` attempts until the
box was mid-graph-compile (weights resident, server not yet accepting in the last observed state).

## Environment/stack (the reference match)
- vLLM **0.28.0**, pyTorch **2.13.0+cu130** (CUDA 13.0), transformers 5.16.1,
  flashinfer-python **0.6.16.post3**, NCCL 2.29.7, Python 3.12.3.
- pip's cu130 wheel installed `nvidia/cu13` toolkit at **13.3.73** (a SKEW vs pyTorch's 13.0).
- Model: `QuantTrio/Qwen3.6-35B-A3B-AWQ` (24 GB, 9 safetensors shards).

## Launch attempt #1 — the /opt//llm-cache typo
Pasted the model path twice (`/opt//llm-cache/... /opt/vllm-cache/...`); the stray path was
parsed as an unknown positional arg:
```
vllm: error: unrecognized arguments: /opt/vllm-cache/Qwen3.6-35B-A3B-AWQ
```
Fix: pass the path exactly once. (Trivial, but easy to trip.)

## Attempt #2 — `nvcc` not found
Weight files loaded (all GPUs ~6.7 GB), graph compile started, then:
```
RuntimeError: Worker failed with error 'Could not find nvcc and default cuda_home='/usr/local/cuda' doesn't exist'
```
Fix: set `CUDA_HOME` to the pip-bundled toolkit and put it on `PATH` (see SKILL.md step 1).

## Attempt #3 — `ninja` not found
After nvcc resolved, the ninja build engine itself was missing from PATH in the worker
subprocess env:
```
RuntimeError: Worker failed with error '[Errno 2] No such file or directory: 'ninja''
```
Fix: `apt-get install -y ninja-build` (→ `/usr/bin/ninja` 1.11.1) and ensure `/usr/bin` is on
the PATH exported into the launch script.

## Attempt #4 — cccl CTK compatibility guard (the real blocker on Blackwell)
```
/opt/vllm-venv/.../flashinfer/data/cccl/libcudacxx/include/cuda/std/__cccl/cuda_toolkit.h:41:8:
  error: #error "CUDA compiler and CUDA toolkit headers are incompatible, please check your include paths"
ninja: build stopped: subcommand failed.
```
Root cause: flashinfer JIT-compiles for `arch=compute_120f,code=sm_120f` on Blackwell (the SM
11.0/12.0 prebuilt kernels don't cover it), and the cccl guard compares the toolkit-header
`CUDART_VERSION` against the compiler version → 13.0 vs 13.3 skew trips it.

Attempted `CCCL_DISABLE_CTK_COMPATIBILITY_CHECK=1` in the launch env — **did not propagate**
into the ninja subprocess (still failed). The working fix was to neutralize the `#error` line
in the header directly:
```python
# patch_ctk.py — comment out the guard's error directive; 13.3-built PTX runs on the 13.0 driver
import re
p = "/opt/vllm-venv/lib/python3.12/site-packages/flashinfer/data/cccl/libcudacxx/include/cuda/std/__cccl/cuda_toolkit.h"
s = open(p).read()
s2 = re.sub(r'(?m)^#\s*error .*$', '# // error (CTK compat check disabled for Blackwell JIT build)', s)
open(p, 'w').write(s2)
```
Note on an earlier batch I tried a bash `sed` with a subtly-mismatched pattern and it ran but
did not match — the header manual already shows the `#if !_CCCL_CUDACC_EQUAL(...)` form; the
robust move is the Python regex keyed on `^#\s*error` (a later stray `# error [DISABLED…]"`
leftover then still broke the compile until fully commented — comment the WHOLE error line).

### Verify the fix standalone (NOT via the full server)
```bash
export CUDA_HOME=/opt/vllm-venv/lib/python3.12/site-packages/nvidia/cu13
export PV=/opt/vllm-venv/lib/python3.12/site-packages
"$CUDA_HOME/bin/nvcc" -gencode=arch=compute_120f,code=sm_120f \
  -I"$PV"/flashinfer/data/cccl/cub \
  -I"$PV"/flashinfer/data/cccl/libcudacxx/include \
  -I"$PV"/flashinfer/data/cccl/thrust \
  -isystem "$CUDA_HOME/include" \
  -isystem "$PV"/tvm_ffi/include \
  -isystem "$PV"/flashinfer/data/include \
  -isystem "$PV"/flashinfer/data/csrc \
  --compiler-options=-fPIC --expt-relaxed-constexpr -static-global-template-stub=false \
  -std=c++17 --threads=1 -use_fast_math -Xfatbin=-compress-all \
  -DFLASHINFER_ENABLE_F16 -DFLASHINFER_ENABLE_BF16 -O3 \
  -c "$PV"/flashinfer/data/csrc/sampling.cu -o /tmp/t.o
```
A 2.5 MB `.o` = success. One-file nvcc compile takes ~1 min (don't fire-and-forget; wait).

## After the build clears
- `shm_broadcast.py:801 No available shared memory broadcast block found in 60 seconds` is a
  **benign** message while the 6 DP workers are all busy compiling / quantizing weights — not a
  hang.
- Weights resident on all GPUs + GPUs spinning util = still compiling. First cold launch over 6
  GPUs with a 256-expert MoE + graph compilation takes several minutes before the API accepts.

## Read-through technique
The vLLM engine wraps the real cause: always strip
`RuntimeError: Worker failed with error 'Ninja build failed. Ninja output:…'` down to the
`error:` / `#error` line in the ninja payload — that's the actual root cause, and the worker
`(Worker_DP<n>_TP<n>_EP<n> pid=…)` prefix doubles as the topology confirmation.