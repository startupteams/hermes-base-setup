# GPU Driver Installer (GDI) — NVIDIA driver-qualification orchestration

Reusable recipe for qualifying NVIDIA GPUs on Proxmox VMs through the **GPU Driver Installer v4.1** controller.
Captured from deploying R580 Open on MIAM-00112 (6x RTX 5060 Ti) using a clean Ubuntu 24.04 VM, replicating the proven MIAM-00111 flow.

## Architecture / layout

- **Controller** is a Flask/gunicorn app living inside a VM (e.g. VM107 `gpu-driver-installer-v4-1`), serving **HTTPS on `:8443`**.
  - App code: `/opt/gdi/app.py` (gunicorn `--bind 0.0.0.0:8443` with TLS cert/key in `/etc/gdi/`).
  - Runtime state (SQLite job DB, SSH key, known_hosts, bundles): `/var/lib/gdi/`.
  - Controller config: `/etc/gdi/controller.json` → `{username, password_hash(scrypt), session_secret, nodes:{MIAM-00xxx: ip}}`.
- **Each Proxmox host** runs a forced-command SSH endpoint `/usr/local/sbin/gdi-node` (root-owned, 0700) plus guest tool `/usr/local/lib/gdi/guest_tool.py`. Node policy: `/etc/gdi-node.json` (0600). State: `/var/lib/gdi-node/`.
- The root `authorized_keys` on each node carries the controller's key as:
  `from="10.0.20.106,10.0.20.107",restrict,command="/usr/local/sbin/gdi-node"  ssh-rsa ...`

## Node policy `/etc/gdi-node.json` (the safety gates live here)

```json
{
  "node": "MIAM-00112",
  "allowed_vmids": [401],
  "backup_storage": "local",
  "external_backup_verified": false,
  "hardware_cleared": false,
  "watchdogs_suspended": false,
  "max_trial_gpus": 1,
  "gpu_family": "RTX5060Ti",
  "local_backup_verified": false,
  "local_backup_override": false
}
```

Gates and their enforceable meaning in `gdi-node`:
- `hardware_cleared` (set true only after verifying IOMMU isolation, PSU/PDU wiring, BMC, storage restore, canary GPU).
- `watchdogs_suspended` (exclusion of external restart watchdogs).
- `backup_storage` independent-of-host: enforces `external_backup_verified==true` **OR** a **request-level `override:true`**. Note `local_backup_override` in the policy is NOT what `backup_storage()` checks — it reads `external_backup_verified` and the request `override` bool only. MIAM-00111's proven sequence = run a real `vzdump <vmid> --storage local --mode snapshot --compress zstd` first, then call checkpoint with `override:true`.
- Opening gates is the operator's *auditable certification*, not a mute override. Per-request `override=true` is fastest but skips the audit trail — prefer opening gates for a disciplined path.

## Driving gdi-node directly (works from a LAN box even if the controller's HTTP path fights you)

`gdi-node`'s `main()` reads the **request JSON from STDIN** (`raw = sys.stdin.buffer.read(16385)`). It also requires the request to carry `node` matching the policy, else "Host identity/policy/request mismatch." So from inside the controller VM:

```bash
echo '<base64 of {"action":"inventory","node":"MIAM-00112"}>' | base64 -d > /tmp/r.json \
  && cat /tmp/r.json | ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
       -o IdentitiesOnly=yes -i /var/lib/gdi/id_ed25519 root@10.0.20.112
```

Read-only actions that should work end-to-end once enrollemnt is correct: `inventory`, `map-environment`, `inspect`, `validate`, `snapshots`, `status`.
A clean `inventory` returning `{"ok":true,"result":{...}}` is the enrollment smoke test — it confirms policy is read (node, allowed_vmids, gates), the VM is visible, and the PCI map is served.

## Controller HTTP API (if preferred; more structured, has audit trail)

- Basic Auth `root:Lempx64S` (or whatever the controller password hash is) on every request.
- `GET /` primes the session and yields `csrf` in the form.
- `POST /submit` needs: `csrf`, `node`, `action`, `profile`, **`verification` = the 3-digit command ID (e.g. `005-CHECKPOINT`)**, `maintenance=yes` (for mutations), `confirmation=<ACTION_UPPERCASE>`, optional `vmid`, `trial_slot`.
- Job page shows state badge + `Job <id>`; the RESULT is the second `<pre>` (after `<h2>Result</h2>`).
- OPERATION_IDS: 001-INVENTORY, 002-MAP-ENVIRONMENT, 003-INSPECT, 004-HOST-BACKUP, 005-CHECKPOINT, 006-START-CPU, 007-PLAN, 008-INSTALL, 009-ARM, 010-VALIDATE, 011-DRIVER-TEST, 012-SNAPSHOTS, 013-SNAPSHOT, 014-TEMPLATE-CREATE, 015-QUARANTINE, 016-PARK, 017-PURGE, 018-ROLLBACK, 019-STATUS.
- Controller serializes operations globally across all nodes (`jobs` table QUEUED/RUNNING check) and refuses while an unresolved node `pending.json` latch exists. Never blindly retry a `UNKNOWN_REQUIRES_REVIEW`; reconcile `pending.json` locally first.

## The disciplined qualification sequence (one GPU at a time)

1. **Enroll host**: node+IP in controller.json; deploy `gdi-node`/`guest_tool.py`; add `from=...` forced-command key to node root authorized_keys; write `/etc/gdi-node.json` policy. Smoke test with read-only `inventory`.
2. **vmfio/passthrough prerequisites**: canary GPU must be bound to `vfio-pci` on the HOST, else checkpoint fails with `"Host PCI function is not safely isolated/bound to vfio-pci: <bdf>"`.
   - `/etc/modprobe.d/vfio.conf`: `options vfio-pci ids=<vid>:<pid>` (get via `lspci -n`) + `softdep nvidia pre: vfio-pci`.
   - `/etc/modprobe.d/blacklist-nouveau.conf`: `blacklist nouveau` / `blacklist nvidiafb`.
   - `modprobe vfio-pci`; the display fn auto-binds. You must ALSO rebind the audio fn (e.g. `echo 0000:22:00.1 > /sys/bus/pci/devices/0000:22:00.1/driver/unbind` then `.../vfio-pci/bind`) — both functions must be vfio.
3. **Attach canary** to the VM config *before* checkpoint: `qm set <vmid> --hostpci0 0000:<bdf>,pcie=1` (pass the whole `bb:ss.f` entry which covers display+audio).
4. **CHECKPOINT** (`confirmation=CHECKPOINT`, `override:true` once a real backup exists): verifies exactly 1 GPU and host vfio binding → graceful shutdown → `qm snapshot` (no RAM) → `vzdump` → `detach()` parks the GPU + `onboot=0` → records `parked_config_hash` → reboots VM **CPU-only**. Result: `CHECKPOINT_COMPLETE_CPU_ONLY_VM_STARTED`.
5. **PLAN** (GPU-detached): apt-update, resolves exact `linux-modules-nvidia-580-open-<kernel>` + `nvidia-headless-no-dkms-580-open` + `nvidia-utils-580`; **rejects** any dkms package or transitional/dummy candidate; refuses if any NVIDIA driver already installed or GPU attached.
6. **INSTALL** (GPU still detached): writes `/etc/modprobe.d/zz-gdi-quarantine.conf` (blacklist nvidia/nvidia_drm/nouveau...), apt-get installs the pinned set, verifies `modinfo -F version nvidia` matches, and refuses an unsigned module if Secure Boot is enabled/signer required. Returns `STAGED_GPU_DETACHED_AND_QUARANTINED`.
7. **ARM** (trial): requires a `last-install.json` (else "Driver changed since staging") → unlinks the quarantine block → attaches trial GPU → boots. Only after reviewing hardware/checkpoint/out-of-band access.
8. **VALIDATE** + **DRIVER-TEST**: `nvidia-smi`, `modinfo version/license`, kernel log scan for `NVRM|Xid|AER|PCIe Bus Error`, then a short torch matmul + finite check. DRIVER-TEST caps at ONE GPU for qualification; a real VLLM burn-in is separate.
9. **TEMPLATE-CREATE**: full clone to a stopped golden template after everything is clean.

## Overcome transport death: the uncertain-operation latch + background-exec pattern

Driving gdi-node through an ephemeral SSH session (e.g. pexpect from a LAN box) is fragile:
if the SSH transport dies **mid-mutation** (checkpoint/plan/install), `main()` has already
written `pending.json` (`state: RUNNING_OR_UNKNOWN`, `agent_pid:<pid>`) and will never unlink
it, so every later mutation fails with *"An uncertain-operation latch exists. Run Status and
reconcile locally before further changes."* This is the one-operation lock doing its job — do
NOT blindly retry.

**Preferred: run gdi-node in a host-side background process so your SSH disconnects can't
kill the op.** Decouple the mutation from the transport:

```bash
# on the host, as root — write result to a file, then poll the file (not the SSH session)
cat > /tmp/gdi_install.sh <<'EOF'
#!/bin/bash
echo '{"node":"MIAM-00112","vmid":401,"action":"install","confirmation":"INSTALL",\
       "profile":"580-open","plan_id":"<id>","override":true}' \
  | timeout 580 /usr/local/sbin/gdi-node > /var/lib/gdi-node/install-result.json 2>&1
echo "EXIT=$?" >> /var/lib/gdi-node/install-result.json
EOF
nohup /tmp/gdi_install.sh >/dev/null 2>&1 &
```
Then poll `install-result.json` (strip the trailing `EXIT=` line before `json.loads`). Long
apt/ninja/nvcc phases (minutes) otherwise keep dying when the pexpect session's 40s expect
window or your transport times out.

**If a stale latch still appears**, reconcile as local admin *after* real investigation —
the guard explicitly allows clearing it once you've confirmed the op didn't partially run:
- `qm status <vmid>` (should be `stopped` if checkpoint died mid-way), `qm listsnapshot`
  (did the `gdi-<ts>` snapshot commit?), `qm config <vmid> | grep hostpci` (was the GPU
  detached?), `ps -p <agent_pid>` (is the worker gone?), and the guest QEMU-agent
  exec-status of any recorded `guest_pid`.
- If no destructive step completed (GPU still attached, no snapshot, worker dead), the latch
  is stale: `cp pending.json pending.stale-<ts>.json && rm pending.json`, then re-run the op.

## `install` requires the `plan_id` from `plan`

`plan` returns `{"id": "b9305a04…"}`. `install` (and `driver-test`) validate it: omitting it
fails with *"Plan ID / profile mismatch. Generate and review a fresh plan."* Pass the plan's
`id` verbatim as the `plan_id` field of the install request. `profile` must also be one of the
allowed set exactly (`580-open`, `580-server-open`, `595-open`, `610-open`, `580-proprietary`);
the proprietary one is refused for Blackwell.

## Pitfalls & notes

- **Checkpoint REQUIRES a GPU attached + vfio-bound first**; it errors otherwise. Don't expect it to work on a bare CPU-only VM.
- On this AMD Threadripper the benign `_OSC: platform does not support [AER LTR DPC]` boot lines are NOT real AER errors — exclude them when grepping for PCIe faults or you'll count 4 phantom errors every boot.
- Known-good package strategy (R580, Ubuntu 24.04 noble): **precompiled kernel module + NO-DKMS headless**; never pin the reference node's `linux-modules-nvidia-XXX-<old-kernel>` — select `-<exact-running-kernel>` for the fresh guest.
- `update-initramfs -u` re-runs wipe the uninstaller evidance; keep the GPU detached until INSTALL is done.
- Cross-host portability: `gdi-node`/`guest_tool.py` are node-agnostic scripts — deploy identical copies to each host, customizing only `/etc/gdi-node.json` (node, allowed_vmids, gpu_family). Transfer binaries by HTTP pull (base64-over-CLI truncates large payloads at shell arg limits).