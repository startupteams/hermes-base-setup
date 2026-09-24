# vLLM model bring-up / rollback on MARION GPU VMs (patterns proven 2026-09-23/24)

Condensed from two live sessions (Gemma4 pool swap; Qwen3.8-Flash-Next V2 attempt on MIAM-00111).
Session detail: `/home/jordatech/flashnext-miam00111-20260924/HANDOFF-QWEN38-FLASHNEXT-MIAM00111-20260924.md`.

## Isolated test-VM pattern (keep production VM untouched)

1. Capture rollback FIRST: `qm config <prod>` via PVE API, guest `vllm.service` text, uname, venv
   versions — into a dated workdir. These ARE the rollback spec.
2. `qm clone <prod> <newid> --name <label>` — LVM-thin full clone (~40s/200G on testthin).
   Clone lands STOPPED, LOCKED (`qm unlock <id>` if a later `qm set` says "VM is locked (clone)").
3. Move the shared model disk ONLY while prod is off: `qm shutdown && qm wait` → `qm set <prod>
   --delete scsiN` → `qm set <new> --scsiN local-lvm:vm-<prod>-disk-N,...` → `qm start <new>`.
   This exact sequence is proven twice; disk ownership is exclusive — never attach to both.
4. `qm set <new> --onboot 0` — test VMs must never autostart.

## PITFALL: cloned GPU-VMs come up networkless — netplan is MAC-locked

Cloud-init netplan files `match: macaddress:` the ORIGINAL VM's MAC. A clone boots with all ifaces
DOWN and no IP (SSH closed, but qga works!). Fix via guest-exec (works without network):

```
# write /etc/netplan/50-flashnext.yaml with match on the NEW VM's MAC (read it from qm config),
# delete the old 50-cloud-init.yaml, chmod 600, netplan apply
```

Then inject your SSH pubkey via the same qga path. Before assuming "guest hung", check: serial
console via `socat - UNIX-CONNECT:/var/run/qemu-server/<id>.serial0` (pty.fork + select pattern)
and whether the netplan MAC matches — networkless and wedged look identical from outside.

## PITFALL: rapid stop/start cycles on GPU nodes can wedge the guest — host reboot is the recovery

On MIAM-00111, repeated `qm stop`/`qm start` cycles around 6-GPU passthrough produced AER
NonFatalErr Timeout storms on riser `0000:61:00` and a boot-hung guest (qemu at ~99% CPU, ~113 GB
RSS, NO serial output, no qga, no TCP). Serial silence + running qemu ≠ slow boot; after ~2 failed
cycles go straight to the node reboot (recovery class authorized by Jordan 2026-09-12; miam00111
is not in the never-reboot list). Do NOT keep cycling a wedged GPU VM.

## vLLM 0.30.0 Qwen4Exp (Flash-Next-class models) — hard constraints, measured

- **PP>1 is banned**: `NotImplementedError` — PLE/n-gram embedding needs raw input_ids that
  non-first pipeline ranks never receive. Any TPxPPy topology for these models is dead in upstream.
- **TP ceiling 4**: full-attn KV heads=2 replicate to TP4; GDN `linear_num_key_heads=16` fails
  TP6 divisibility. Six-GPU plans are unreachable in upstream code.
- **PLE CPU offload works**: `VLLM_PLE_CPU_OFFLOAD=1` (default) + DP1 → ONE pinned-host copy
  (~48 GiB FP8) via UVA lookup. The old DP-replication OOM chain is bypassed by DP1.
- `--cpu-offload-gb N` (UVA weight offload) exists and works on SM86, but only buys ~4 GiB/GPU.
- **Loader gap**: `RoutedExperts` cannot load unfused per-expert AWQ-gemm checkpoints under TP
  (dim mismatch in `_load_w2`); it expects fused `w13_weight`/`w2_weight` params. Dual-format
  artifacts (index = AWQ-gemm experts, sidecar `official-fp8-ple-*` shards ALSO carrying unindexed
  FP8 `weight_scale_inv` expert duplicates) trip `AttributeError` — loader iterates all
  safetensors files, not just index entries.
- On failure, ALWAYS capture the true root-cause line: grep for `NotImplementedError`,
  `AttributeError`, `OutOfMemoryError` OUTSIDE the multiproc-executor wrapper noise
  (`grep -v "944"`), and walk the innermost `File ... line N, in` frames.

## Two-loader diagnostic pattern (fast triage)

1. Read the OOM numbers: "Tried to allocate X. GPU has Y free" — if Y≈0 with 19.12 GiB already
   PyTorch-allocated during `create_model`, weights simply don't fit per-GPU; compute per-GPU
   weight share from the safetensors index (aggregate `data_offsets` by tensor-prefix) BEFORE
   trying more topologies.
2. If it's a shape/name error in weight loading, print the expert mapping
   (`build_expert_params_mapping(...)` in the live venv) and compare param names vs checkpoint
   tensor names — name-mapping mismatch vs TP-narrow mismatch look similar in tracebacks.

## Production restore checklist (proven)

Stop test VM → delete its scsiN → re-add disk to prod VM → start prod → poll guest TCP 22/8000
from the NODE (`/dev/tcp`) → then qga exec for in-guest service checks → `curl :8000/v1/models`
+ one chat completion → LLM Manager `/healthz` from outside. Allow several minutes: 6-GPU vLLM
VMs boot slowly; "no agent" at t+60s is normal, at t+10min with silent serial = wedged.
