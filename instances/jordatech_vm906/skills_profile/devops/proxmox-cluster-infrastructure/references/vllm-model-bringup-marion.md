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

- **UPSTREAM (stock 0.30.0) bans** — all three were V2 blockers, ALL CLEARED 2026-09-24 by the
  todiadiyatmo community overlay (see next section):
  - **PP>1 banned**: `NotImplementedError` — PLE/n-gram embedding needs raw input_ids that
    non-first pipeline ranks never receive. (Overlay fix: #54709 placement-based gate — PP>1
    allowed when every PLE layer lives on pipeline rank 0. PLE at layer 1 → always rank 0.)
  - **TP ceiling 4**: full-attn KV heads=2 replicate to TP4; GDN `linear_num_key_heads=16` fails
    TP6 divisibility. (Overlay + different topology sidesteps: TP2×PP3 uses all 6 GPUs.)
  - **Loader gap**: `RoutedExperts` cannot load unfused per-expert AWQ-gemm checkpoints under TP
    (dim mismatch in `_load_w2`). (Different ARTIFACT sidesteps: AutoRound/INC checkpoint with
    GPTQ-packed per-expert weights → `--quantization inc` → MARLIN WNA16 MoE backend, no patches.)
- **PLE CPU offload works**: `VLLM_PLE_CPU_OFFLOAD=1` + DP1 → ONE pinned-host copy (~51 GB FP8),
  `pinned=True, weight_device=cpu` on the PP0/TP workers only. Host in use 83-85 GiB of 106.
- Benign during 70K profiling: expandable-segments `OOM ... memory mapping failed` WARNINGS that
  retry and recover (recipe-documented). Do NOT abort the boot on these — wait for
  "Application startup complete".

## Two-loader diagnostic pattern (fast triage)

1. Read the OOM numbers: "Tried to allocate X. GPU has Y free" — if Y≈0 with 19.12 GiB already
   PyTorch-allocated during `create_model`, weights simply don't fit per-GPU; compute per-GPU
   weight share from the safetensors index (aggregate `data_offsets` by tensor-prefix) BEFORE
   trying more topologies.
2. If it's a shape/name error in weight loading, print the expert mapping
   (`build_expert_params_mapping(...)` in the live venv) and compare param names vs checkpoint
   tensor names — name-mapping mismatch vs TP-narrow mismatch look similar in tracebacks.

## Community-overlay serving pattern (V3, proven 2026-09-24 — Flash-Next LIVE on 6×3080)

The winning V3 sequence, when stock vLLM hard-bans an architecture:

1. **Zero-prod-impact staging while prod keeps serving:** stop the test VM (GPUs stripped),
   shrink its RAM to 8G (host only has ~12G free beside prod), attach a dedicated artifact disk,
   boot GPU-less, and do ALL slow work (docker pull, image build, 115 GB checkpoint download,
   flat-copy) with zero prod risk. Only the actual test needs the GPU handoff.
2. **GPU handoff sequence with LLM Manager** (the handoff itself): set BOTH
   `desired_power_state='STOPPED'` + `desired_service_state='MAINTENANCE'` on the hosts table →
   `qm stop <prod>` → verify STAYS stopped → restore test VM's hostpci + RAM → `qm start <test>`.
   (See marion-vllm-bench-ops SKILL.md for the dual-trigger recovery pitfall that bit here.)
3. **GPUs missing after boot = kernel/module drift, not a passthrough failure.** `lspci` inside
   the guest showed all 6 GA102s while `nvidia-smi` failed: kernel had auto-updated to 6.8.0-142
   but `linux-modules-nvidia-580-open-*` existed only for -139. Fix WITHOUT reboot:
   `apt-get install linux-modules-nvidia-580-open-$(uname -r) && modprobe nvidia nvidia_modeset nvidia_uvm`.
   (Same VM401 trap; third occurrence. Kernel pinning still not implemented fleet-wide.)
4. **Clone's fstab may remount a model disk at the template's old path after reboot**
   (VM102's clone kept `/dev/sdb → /opt/hf-cache-030 nofail` from VM103's template). The 115 GB
   artifact survived; fix = umount, remount at intended path, sed the fstab line. Audit the fstab
   of any clone that carries a disk.
5. **Mount HF checkpoints FLAT for docker:** snapshot dirs are symlink farms into `../../blobs/`;
   a read-only bind mount of the snapshot breaks them. `cp -rL <snap>/. <flat>/` (231G of 393G used).
6. **nvidia-container-toolkit install from nvidia.github.io fails on 24.04** (unsigned InRelease).
   Install from GitHub release tarball instead: `nvidia-container-toolkit_<v>_deb_amd64.tar.gz` →
   extract → `dpkg -i` the 4 core debs (libnvidia-container1, -tools, toolkit-base, toolkit) →
   `nvidia-ctk runtime configure --runtime=docker` → restart docker (systemctl reset-failed if
   start-limit-hit after churn).
7. **Serve via python -c, not the console script** (see marion-vllm-bench-ops skill for the
   Invalid-repository quirk). Working launcher: `/opt/hf-fork/run_stage.sh` on VM102, with
   MAXLEN/SEQS env knobs.
8. **Proven results (70K ctx, 8K prompts, 256 gen):** C1 37.9 / C2 40.8 / C4 23.9 / C6 23.4 /
   C8 18.9 tok/s per agent (C8 aggregate 150.6). KV pool 665K tokens. ≥20 tok/s/agent met at
   C4-C6. MTP n=2 and FP8 KV are in the image but untested — biggest remaining wins.
   Full detail: `/home/jordatech/flashnext-v3-20260924/HANDOFF-QWEN38-FLASHNEXT-V3-20260924.md`.
   Reusable bench harness (C1-C8, streaming, reasoning-delta aware): `scripts/bench_ladder.py`
   (`python3 bench_ladder.py <port> <max_conc> <prefix>` — writes incremental JSON + VRAM/RAM samples).

## Production restore checklist (proven)

Stop test VM → delete its scsiN → re-add disk to prod VM → start prod → poll guest TCP 22/8000
from the NODE (`/dev/tcp`) → then qga exec for in-guest service checks → `curl :8000/v1/models`
+ one chat completion → LLM Manager `/healthz` from outside. Allow several minutes: 6-GPU vLLM
VMs boot slowly; "no agent" at t+60s is normal, at t+10min with silent serial = wedged.
