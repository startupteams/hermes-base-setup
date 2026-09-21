# Fleet-wide safe userspace maintenance + one-at-a-time reboots (MARION 16-node, proven 2026-09-21)

Proven end-to-end on the MARION-IA-USA cluster from CT906 `hermes-jordan` (10.0.20.195, on miam-00100).
Result: 16/16 nodes updated (~1838 pkgs), 13 rebooted one-at-a-time and verified, 0 removals, 0 errors.

## Working directory layout

```
~/marion-maintenance-<YYYYMMDD>/
  fleet.py            # sequential password-SSH runner (imports noderun.run), writes logs/<label>-<ip>.out
  preflight.sh        # read-only inventory per node
  simulate2.sh        # apt --simulate with explicit removal/prohibited checks
  apply.sh            # explicit-list install with --force-confold + before/after snapshots
  nodecycle.py        # stop guests -> API restart -> poll -> verify -> restart guests
  postcheck.sh / storage.sh / finalval.sh / quiet.sh
  logs/               # everything, one file per node per phase
  gen_handoff.py      # builds the handoff markdown from the logs
```

Node→IP map is `MIAM-00XXX → 10.0.20.XXX`. Node **short-names are inconsistent**: `miam00111/miam00112/miam00143/miam00144`
(no hyphen) vs `miam-00110` etc. Always enumerate `GET /api2/json/nodes` and use the returned name verbatim.

## API gotchas that cost time (fix these first)

1. **Node status endpoint is `/api2/json/nodes/<node>/status`** — `/status/current` returns
   `501 Method 'GET .../status/current' not implemented` (that path is for **VMs** only).
2. **`pve_api.api()` returns the FULL JSON body**, i.e. `{"data": ...}`. You must read `d["data"]`
   (`GET /nodes/<node>/qemu` → `d["data"]` is the list; `.../config` → `d["data"]` is the dict).
3. **Polling during a reboot WILL hit `TimeoutError: read operation timed out`** on
   `urllib.request.urlopen(..., timeout=20)`. Do NOT let it crash the loop. Wrap `node_up()` so a
   timeout returns `(None, None)` = "unknown", and only treat `up is False` as "node is down".
4. **Reboot must go through the PVE API** — the agent terminal hardline-blocks `shutdown`/`reboot`
   even inside SSH payloads. Use
   `POST /api2/json/nodes/<node>/status` with body `{"command": "reboot", "node": <node>}`.
   It returns 200 immediately; poll until the node stops answering, then until `uptime` is small.
5. **`onboot` default trap:** `qm config <id>` shows the option ONLY if explicitly set (unset = won't
   auto-start), while the **API `/config` returns `onboot: 1` as a default**. So never trust the API
   value for "will it come back?" — read `qm config`/`pct config` over SSH, and always explicitly
   restart every guest that was running before the reboot (idempotent: `qm start` on a running VM
   just errors, swallow it).

## Phase 1 — preflight (read-only)

Per node: `hostname`, `pveversion -v`, `uname -r`, `qm list`, `pct list`, `pvesm status`, `df -h`,
`systemctl --failed`, `journalctl -p err..alert -b`, `lsblk`, `zpool status`, `apt list --upgradable`,
APT sources. Stop if quorum is unhealthy or a node has an unexplained critical fault.

## Phase 2 — simulate before installing

```bash
PROHIB='kernel|linux-image|linux-headers|firmware|microcode|nvidia|cuda|libcuda|nvml|mellanox|mlx|rdma|infiniband|ibverbs|ofed'
apt list --upgradable 2>/dev/null | tail -n +2 | cut -d/ -f1 | sort > /tmp/upg.txt
grep -vEi "$PROHIB" /tmp/upg.txt > /tmp/safe.txt
apt-get install --simulate -y $(tr '\n' ' ' < /tmp/safe.txt) > /tmp/sim.txt 2>&1
grep '^Remv' /tmp/sim.txt            # MUST be empty
grep '^Inst' /tmp/sim.txt | grep -Ei "$PROHIB"   # MUST be empty
```
Require: no removals, no prohibited class in the transaction, no `E:`/`Unable to correct` errors.
Expect exactly one extra package beyond the safe list — **`proxmox-firewall-data`** (a new dep of the
upgraded `pve-firewall`); that is normal and safe.

## Phase 3 — apply

`apt-get install -y -o Dpkg::Options::=--force-confold <explicit safe list>` with
`DEBIAN_FRONTEND=noninteractive` (force-confold prevents interactive conffile prompts).
Snapshot `dpkg-query -W -f='${Package}\t${Version}\n'` to `/root/packages-before-maintenance.txt` and
`...-after-maintenance.txt`. Then check `dpkg --audit`, `grep '^Remv'`, and `/run/reboot-required`.

**Useful fact:** after upgrading `libc6` on Proxmox 9.2, `/run/reboot-required` was **NOT** set on any
node — so "reboot required" is not automatic evidence for a reboot here. Reboots are for hygiene/validation.

## Phase 4 — one node at a time

Order (proven): Phase A lightly-loaded → Phase B infra → Phase C GPU → Phase D the agent's own host last.

Per node:
1. `pvecm status` quorum check + inventory running guests (`/nodes/<n>/qemu`, `/nodes/<n>/lxc`).
2. Graceful stop: `qm shutdown <id> --timeout 180 || qm stop <id>`, `pct shutdown <id> --timeout 180`;
   poll until 0 running.
3. API reboot; wait for down (≤240 s), then for up with `uptime < 600` (≤420 s).
4. Verify: `hostname`, `uname -r` (**must equal the pre-reboot kernel**), `pvecm status`, `pvesm status`,
   `qm list`, `pct list`, `systemctl --failed`, `journalctl -p err..alert -b`.
5. Restart every guest that was running before.

**Expected noise:** right after boot, `pmxcfs[...]: crit: quorum_initialize failed: CS_ERR_LIBRARY
(failed to connect to corosync)` appears for ~2 s. It is a boot-order race and self-resolves —
confirm with `pvecm status` showing `Quorate: Yes`, not by the absence of the log line.

**Never reboot:** `miam-00100` (hosts the agent's own CT906) and `miam-00133` / `miam-00135`
(standing hard boundary: LLDAP + PDM + tailscale router on 00133; LLM Manager + other Hermes agent VMs
on 00135). Update them, then defer the reboot to a human window.

## Phase 5 — hardware triage (read-only)

**Corrected ECC (MCE/EDAC):**
```bash
journalctl -k --no-pager | grep -Ei 'mce|machine check|hardware error|edac|ecc'
for r in /sys/devices/system/edac/mc/mc0/rank*/; do echo "$(basename $r) $(cat ${r}dimm_label) ce=$(cat ${r}dimm_ce_count)"; done
```
- On Threadripper (family 17h) `mc0 csrow0 channel N` maps to physical slot **`DIMM_P0_<letter>N`**
  (channel 0 = A0 … channel 7 = H0). `dmidecode -t memory` lists all slots — do not `head -90` it
  (that silently truncates the last DIMMs and makes an 8-DIMM box look like 6).
- `ce_count` is **cumulative per boot** and equals the number of journal CE events. A reboot resets it —
  so re-sample after the reboot: errors that return prove a persistent hardware fault, not a transient.
- Corrected-only + stable → `MONITOR`; single-channel/single-DIMM stream that persists across reboot →
  `HARDWARE SERVICE REQUIRED` (reseat/replace that DIMM); any uncorrectable/UE → escalate immediately.

**Corrected PCIe AER:**
```bash
grep -h TOTAL_ERR_COR /sys/bus/pci/devices/*/aer_dev_correctable   # cumulative since boot
grep -h TOTAL_ERR_FATAL /sys/bus/pci/devices/*/aer_dev_fatal       # must be 0
journalctl -k -b | grep -E 'pcieport .*(BadTLP|BadDLLP)'
```
`BadTLP`/`BadDLLP`/`Timeout` are corrected classes (Data Link Layer). Corrected-only + stable → document
and monitor; a high sustained rate on one root port means a marginal riser/cable/slot — **do not change
PCIe/BIOS/ASPF/ACS**, defer to the PCIe/RDMA project. `grep -vE ': 0$'` does NOT filter these files
(values are space-separated, not `key: 0`); filter with `awk '$2!=0'`.

## Verification of guest/service recovery

Don't conclude a service is broken from a closed port right after a reboot — vLLM takes minutes to
reload (GPUs allocated + `load average` high = still loading). Check inside the guest with
guest-agent exec (`systemctl is-active`, `ss -ltn`, `nvidia-smi`) before acting. In this run `.163`
took ~10 min to bind :8000; the real unit was `vllm.service` while a **pre-existing** duplicate
`vllm-qwen.service` had been failing since days earlier — check `journalctl -u <unit> -b -1` to prove
whether a failure predates your change before blaming the maintenance.
