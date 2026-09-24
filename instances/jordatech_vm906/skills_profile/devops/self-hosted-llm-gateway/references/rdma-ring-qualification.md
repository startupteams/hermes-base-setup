# RDMA / 100 Gb Ring Qualification (MIAM-00111 ↔ 00143 ↔ 00144)

Workstream per LLM Manager plan §19 (RDMA-0 inventory → RDMA-1 link qual → RDMA-2 NCCL
proof → RDMA-3/4 multi-node vLLM). State after the 2026-09-10 session:

## RDMA-0 inventory (all three hosts identical)

| Item | .111 / .143 / .144 |
|---|---|
| NIC | ConnectX-5 Ex (MT28800), dual-port, `15b3:1019` |
| BDFs | 04:00.0 (mlx5_0 → enp4s0f0np0), 04:00.1 (mlx5_1 → enp4s0f1np1) |
| Firmware | 16.35.1012 (DEL0000000004); driver mlx5_core (PVE kernel 7.0.14-11-pve) |
| RDMA | rdma-core present, RoCE (node_guid b8ce:f603:…), mlx5_0/mlx5_1 healthy |
| MTU | 1500 default (raise to 9000 for qualification) |
| IPs | none on CX5 ports (prod mgmt runs on onboard 4-port NICs → vmbr0) |
| PCIe | cap 16 GT/s x16, actual **x8 (downgraded)** — sufficient for 100 Gb, documented |
| GPUs | passthrough to VMs — hosts have NO nvidia-smi; `nvidia-smi topo -m` must be run INSIDE the inference guests (VM103/.161, VM109/.163, VM111/.164) |

## Cold-port gotcha: links report DOWN until administratively raised

All six ports initially showed `state DOWN physical_state DISABLED / Link detected: no`.
After `ip link set <dev> up` on all hosts, 2 of 6 ports negotiated **100 Gb**:
111 `enp4s0f1np1` ↔ 144 `enp4s0f0np0` (ping 172.31.0.1↔.2 at 0.13 ms, MTU 9000 OK).
**Lesson: never conclude "no cabling" from cold ports — bring them up first**, then read
`ethtool <dev> | grep Speed` (100000Mb/s) and `rdma link show` (state ACTIVE).

Link map after bring-up: 111↔144 = 100 Gb; 111 port0 + both 143 ports = 1 Gb partners
(143's CX5 cabling needs a physical check); third ring leg not yet 100 Gb.

Qualification subnet used: `172.31.0.0/24` (temp link-local, no prod conflict).

## Offline package delivery to Proxmox nodes (no working apt)

Nodes have no usable internet (apt hangs) and no iperf3. Working pipeline:
1. Download .deb on the internet-capable Hermes box.
2. Hex-encode; push through the pexpect node runner to node 135 `/tmp` in ≤40 KB hex
   chunks with per-chunk `wc -c` verification (pexpect argv limit ≈ 100 KB —
   `Argument list too long`; raw base64 through the pty corrupted bytes once — always
   md5-verify the reassembled file).
3. Reassemble: `cat chunks | python3 -c "import binascii,sys; open(out,'wb').write(binascii.unhexlify(sys.stdin.read()))"`.
4. `scp -o BatchMode=yes` node→node (node 135 holds BatchMode keys to the ring nodes),
   `dpkg -i`.
iperf3 dependency chain: `iperf3` + `libiperf0` + `libssl1.1` + `libsctp1` (Debian
bullseye builds run fine on PVE 9 hosts). Server: `iperf3 -s -D -p 5201`.

## Open gates

- **RDMA-1 TCP: PASSED 2026-09-10** on the 111↔144 leg — 4-stream iperf3 = **37.0 Gbit/s**
  forward / 39.3 Gbit/s reverse, single-stream 34.1 Gbit/s, 0 retransmits, 0% loss over
  the 9000-MTU pair. **RDMA verbs: PASSED** — `ib_send_bw -c RC -d mlx5_0 -R <peer>`
  (rdma_cm, MTU 4096, Ethernet/RoCE) ran **11,666 MB/s ≈ 93 Gbit/s** between the hosts.
  mid-30s Gbit/s TCP on a single un-tuned NIC is normal; ~93% line rate is not the goal
  for TCP — the verbs number is the headline result. Server side: `ib_send_bw -d mlx5_1 -R`
  (background), client: `ib_send_bw -c RC -d mlx5_0 -R <server-ip>` (flag order matters:
  `-c RC` is the connection type, NOT the address; address goes last, `-R` enables rdma_cm).
- **Verbs userspace stack** (now installed on .111/.144 via the offline pipeline):
  `rdma-core` + `libibverbs1` + `ibverbs-providers` + `libibumad3` + `perftest` (provides
  `ib_send_bw`) + iperf3 chain. Ubuntu noble builds (50.0-2ubuntu0.2) install cleanly on
  PVE 9 (trixie-based) hosts despite the version skew.
- **RDMA-2**: NCCL `NET/IB/GDRDMA` transport proof must come FROM INSIDE the inference
  VMs — requires a guest NIC-exposure design first (PCI passthrough of a dedicated CX5
  port or validated SR-IOV VF; plan §19.2). Host-side RDMA ≠ guest RDMA. This is the
  blocking design decision for RDMA-3/4 — needs the user's sign-off on passthrough vs
  SR-IOV before any guest changes.
- **RDMA-3/4**: multi-node vLLM functional test → >120 GB model qualification →
  production routing gate (§19.8). Multi-node deployment = ONE logical deployment with
  multiple participating hosts.
- **Cleanup pending**: temp qualification IPs 172.31.0.1 (111) / 172.31.0.2 (144) still
  on the CX5 ports; formalize the qualification subnet or remove before production.

## Session 3 (2026-09-11 early AM): RDMA-3 window + 143 card verdict

**RDMA-3 (plan §19.6) — partial:**
- Ray 2.58.0 installed both guests; 2-node cluster over ring UP (12 GPUs visible).
- Multi-node vLLM 0.28 + Qwen3-1.7B served HTTP 200 + real completion (functional proof ✓).
- Strict cross-node TP FAILED: vLLM 0.28 hardcodes `strategy="PACK"` (ray_utils.py:674)
  and only adopts a pre-existing PG when the driver itself runs inside one — env var
  RAY_pgname does NOT work; VLLM_RAY_BUNDLE_INDICES only picks bundles inside an adopted
  PG. Pre-created STRICT_SPREAD PG is ignored (engine makes its own).
- **Completion path:** run the serve inside `ray job submit --address=...` so
  `ray.util.get_current_placement_group()` returns the pre-created STRICT_SPREAD PG.
- Do NOT invent vLLM flags (`--placement-group-preemption-mode`,
  `--ray-workers-use-all-resources` are unrecognized in 0.28).
- Window cost measured: .161 down ~11 min total (restore 180 s via compile cache).

**MIAM-00143 card question resolved — cards identical, DACs remain the fix:**
- All three nodes: MT28800 ConnectX-5 Ex (15b3:1019), firmware 16.35.1012
  (DEL0000000004), mlx5_core 7.0.14-11-pve, kernel 7.0.14-11-pve. Same everything.
- 143 ports DO train (1 Gb, link yes both legs) — the card is healthy; it cannot train
  above 1G only against the OEM 1G-only DACs.
- DAC EEPROM identities: working leg = **QSFP-100G-CU2M** (SN CSC260508200103);
  1G-only parts on 111-f0 + both 143 legs = **QSFP-100G-DAC2M** (SNs 2603050038/40).
- Verdict: **buy 2× QSFP-100G-CU2M; do NOT replace the 143 card.**

**Ops notes:** noderun.py is the proven password-SSH runner (two hand-rolled expect
loops failed with empty payloads before switching). PDU portal 10.0.20.154:5000 creds
staged (~/.pdu_portal, 600).

**VM111 found STOPPED** (prior session died mid-attempt). Recovery sequence, all proven:
1. `qm start` via PVE API (LLDAP bot account, `~/.pve_ldap_bot` 600 file) — agent qga=1 after ~9 s.
2. First vLLM boot hit the CUDA-OOM-orphan pitfall (workers from the earlier hard stop held ~9-10 GiB/GPU). Fix: `systemctl reset-failed vllm-qwen vllm && systemctl restart vllm-qwen` → up ~200 s.
3. **Duplicate unit trap**: a second `vllm.service` (created 02:47 same day) duplicated `vllm-qwen.service`; both enabled, NRestarts=57 crash-loop fighting for port 8000. `systemctl disable --now vllm.service` → canonical unit sole owner, NRestarts 0, port 200, real completion clean. ALWAYS reconcile duplicate vLLM units after guest recovery.

**nvidia-peermem root cause (decisive evidence):** with Secure Boot DISABLED (VM111:
`mokutil --sb-state` = "SecureBoot disabled / Platform is in Setup Mode", lockdown
`[none]`), `modprobe nvidia-peermem` STILL fails EINVAL. The Ubuntu
`linux-modules-nvidia-580-open` `nvidia-peermem.ko` is an **8 KB hollow stub**: only 3
UND imports (`__fentry__`, `__x86_return_thunk`, `param_ops_int`), zero ib_*/nvidia_p2p
references. The running `ib_core` exports **no peer-memory-provider API at all** (787
exports, none containing "peer"; `ib_register_peer_memory_provider` absent from
kallsyms). **Conclusion: peermem is impossible on stock Ubuntu kernels regardless of
Secure Boot** — needs MLNX_OFED-class ib_core or a kernel with the peer-provider API.
GDR-via-peermem on this OS build is a dead end; do not burn more sessions on it.

**DMABUF test result:** `NCCL_DMABUF_ENABLE=1` is accepted (log line confirms) and the
collective passes, but NCCL still reports `GDR 0`; `NCCL_NET_GDR_LEVEL=SYS` does not
change it either. DMABUF GDR does not engage on the virtualized PCIe fabric (q35
passthrough, no PCIe P2P between CX5 and GPUs) — expected for VM passthrough topologies.

**CRITICAL MTU regression lesson:** after guest reboot, VM103's ring port came back at
**MTU 1500** while VM111 was at 9000. Result: verbs QPs CONNECT (GID exchange OK) but
every transfer fails — NCCL shows `IBV_WC_WR_FLUSH_ERR` (receiver) +
`IBV_WC_REM_INV_REQ_ERR` (sender) + "local access violation work queue error", which
masquerades EXACTLY like a GPU-direct failure. Always verify `ip link show <ring> |
grep mtu` on BOTH ends before any RDMA/NCCL debugging. With MTU 9000 both sides:
`ib_send_bw -d mlx5_0 -x 1 -R -m 4096 -s 65536 172.31.0.1` = **11,667 MB/s ≈ 93.3 Gbit/s**,
and 2-node NCCL ALLREDUCE = **PASS** (GDR 0, staged RDMA). Registry evidence key:
`rdma2_reproof_2026_09_10` on MIAM-00111 + MIAM-00144.

- **PVE API access pattern (now primary):** LLDAP bot `~/.pve_ldap_bot` (user/pass lines,
  600); POST `/api2/json/access/ticket` → cookie `PVEAuthCookie` + `CSRFPreventionToken`;
  helper script `~/work/pve_api.py` (login/permissions/nodes/vmconfig/vmstatus/raw).
  Guest exec: POST `/nodes/<node>/qemu/<vmid>/agent/exec` with
  `{"command":["bash","-lc","echo <b64> | base64 -d | bash"]}` — urlencode with
  `doseq=True` (list values are dropped silently otherwise → empty exec). Node short-names
  are inconsistent: `miam00111`, `miam00144`, `miam00112`, `miam00143` (no hyphen) vs
  `miam-00135` etc. — enumerate via `GET /api2/json/nodes`, never guess.

## GDR options summary (from session-2 evidence)

| Option | Status |
|---|---|
| peermem on stock Ubuntu kernel | ❌ impossible (stub module + ib_core lacks peer API) — verified empirically, do NOT retry |
| DMABUF GDR in q35 passthrough VM | ❌ NCCL accepts env but never engages (GDR 0) |
| MLNX_OFED inside guests | ⏳ unexplored; would supply peer-provider ib_core; heavy install + regression risk |
| Bare-metal inference (no VM) | ✅ would enable standard GDR; conflicts with VM fleet architecture |
| Staged RDMA (current) | ✅ qualified: ~93 Gb/s verbs, NCCL ALLREDUCE PASS — adequate for RDMA-3 |

## Session 3 evening (2026-09-11 ~20:30 UTC): post-card-move verification

**Trigger:** Jordan physically moved the 143 CX5 card; asked to verify 100 Gb now
works; authorized node reboots (use `reboot`, never shutdown).

**Verdict: card GOOD, DACs still the blocker — and the cables moved.**
- 143 rebooted cleanly via `reboot` (~6 min return; note: ping from the Hermes box
  is ICMP-filtered — verify liveness via the manager VM or noderun, not local ping).
- **DAC serial-number audit (the decisive technique):** `ethtool -m <port> | grep SN`
  on all four host-side ports → 143-f0=2603050038, 143-f1=2603050040,
  111-f0=2603050040, 144-f1=2603050038. The two OEM 1G-only DACs had been **swapped
  between legs** by the card/cable move. Track cables by EEPROM serial, never by
  physical position — serials are the only way to prove what physically moved.
- Post-reboot dmesg on 143: `port_module ... Cable error, Unknown error` on both
  ports (mlx5 rejects the EEPROM as non-100G-capable). Ports settle at 1 Gb UP after
  a carrier bounce (`ip link down/up`) — first-boot link state can be Unknown/no.
- **Asymmetric L2 anomaly (documented):** ARP broadcasts traverse each leg in exactly
  ONE direction; ICMP fails both directions (ARP resolves via captured broadcasts).
  Signature of mismatched unequalized-copper pairs. Do not chase this as a fabric
  fault before checking whether cables were moved/swapped.
- **144-f1 host port found DRIVERLESS** (vfio unbind leftover from the card-move
  window). Fix: `echo 1 > /sys/bus/pci/rescan` (mlx5_core rebinds, netdev returns).
  May recur after host reboots — check `readlink /sys/bus/pci/devices/0000:04:00.1/driver`.
- /30 test-IP gotcha: 172.31.0.1/30 peer must be .2 (same subnet). A .1↔.11 "ping
  failure" across /30s of different subnets is a self-inflicted routing artifact, not
  a link failure — and local self-pings (rtt 0.017 ms) show up as "received" while
  capturing nothing on the wire; always confirm with tcpdump on BOTH ends before
  declaring L2 broken.
- Buy list refined with serial targets: 2× QSFP-100G-CU2M — one replaces
  SN 2603050038 (111-f0↔143-f0), one replaces SN 2603050040 (143-f1↔144-f1).
  After swap: RDMA-1 both directions per leg (ib_send_bw, MTU 9000 BOTH ends),
  then mark 143 qualified in the ring registry.
- Ring registry (rdma_ring_nodes) updated: 143 unqualified with card-move evidence;
  runtime test IPs flushed from all ring ports; no persisted config changes.

## Session 4 (2026-09-12): post-cable validation PASS + STRICT_SPREAD placement SOLVED

**Trigger:** Jordan installed 2× MCP1600-C002 (Mellanox QSFP28 100G-CR4, 2m) replacing the
OEM 1G-only DACs; authorized autonomous run with restarts (WoL available, not needed).

**Cable map by EEPROM SN (`ethtool -m`):**

| Leg | Ends | PN | SN |
|---|---|---|---|
| A | 111-f0 ↔ 143-f0 (host ports) | MCP1600-C002 | Q260115790049 |
| B | 143-f1 ↔ 144-f1 (host ports) | MCP1600-C002 | Q260306970053 |
| C | 111-f1 ↔ 144-f0 (GUEST ports: VM103 enp3s0np1 ↔ VM111 enp3s0np0) | QSFP-100G-CU2M | CSC260508200103 |

- 143 dmesg clean (`Cable plugged`, no `Cable error`). All six ends 100 Gb after
  `ip link set mtu 9000 up` (cold-port gotcha applies after Jordan's reboot cycle).
- Leg C topology: VM103 holds 111's f1 via hostpci6=0000:04:00.1; VM111 holds 144's f0
  via hostpci6=0000:04:00.0. **144's 04:00.0 bound to vfio-pci while VM111 runs is CORRECT**
  (passthrough active) — do not confuse with the card-move driverless ghost.
- Verbs RC matrix (ib_send_bw, GID idx 1, MTU 4096, 64 KiB): A fwd/rev 11,699.6/11,699.7
  MB/s; B 11,624.2/11,665.5; C guest 11,669.0/11,667.7 — all ≈93 Gb/s = PASS. iperf3 TCP
  sanity 31–36 Gb/s per leg (x8-slot envelope). Error counters clean post-load; no mlx5
  error dmesg.
- Registry: `postcable_2026_09_12` evidence block on all three rows; **MIAM-00143
  qualified=true** (was the last unqualified node).
- ib_send_bw operational traps (bit us twice): the server is SINGLE-connection (a client
  invoked twice — e.g. grep-pipe + tail re-run — consumes it and the second run errors
  "Unexpected CM event"); `ss -ltn | grep 18515` shows NOTHING for the rdma_cm listener —
  use `pgrep -f "ib_send_bw -d"` as the readiness signal; `grep "BW average"` matches only
  the header row — the data row is `65536 1000 <peak> <avg>`, parse that.
- Package delivery upgrade: pexpect-scp from the Hermes box (spawn scp → expect password)
  moves ~1 MB of .debs to password-SSH nodes in seconds — no hex-chunk pipeline needed
  when the Hermes box has direct password SSH (noderun proves it). Verify pushed .debs
  with `file` before dpkg — mirror 404s return 280–300-byte HTML that dpkg rejects as
  "not a Debian format archive" only AFTER the push. Working set for 143: rdma-core,
  libibverbs1, ibverbs-providers, libibumad3, perftest (ubuntu noble 50.0-2ubuntu0.2 +
  perftest 24.01.0-1build2) + iperf3 3.9 bullseye builds (ftp.debian.org) with
  libssl1.1 (focal pool `pool/main/o/openssl/`) + libsctp1 (ubuntu pool, escape `+` in URL).
- Guest ring IP hygiene: a stray `/32` from an earlier `ip addr add` silently breaks ping
  (routing artifact) — `ip addr flush dev <port>` then add ONE `/30`.
- NCCL 2-node torchrun PASSED after exporting `NCCL_IB_GID_INDEX=1` explicitly inside the
  torchrun shell on both nodes (env set only in the parent was not inherited →
  `ibv_modify_qp RTR Invalid argument, local GID index 3`). Evidence: NET/IB RoCE, GDR 0.

**Phase E — strict cross-node TP placement: SOLVED (was open since 09-11).** One-line
env-gated patch to `vllm/v1/executor/ray_utils.py` on BOTH guests:
`strategy="PACK"` → `strategy=os.getenv("VLLM_RAY_PG_STRATEGY", "PACK")` (backup
`ray_utils.py.bak.e2`; unset env = stock behavior). Launch recipe + full 8-step
failure chain in `DISTRIBUTED-VLLM-QUALIFICATION-20260912.md` (2026-09-12 session
work dir). Highlights: ray bundles need CPU inside (`[{"GPU":1,"CPU":2}×N]` — a bare
`{"GPU":1}` PG rejects a `CPU:2` actor: "cannot fit into any bundles"); vLLM workers need
**`NCCL_IB_GID_INDEX=3`** (IPv4 RoCE v2 GID — idx 1 gives `ibv_modify_qp 101 Network
unreachable` in vLLM worker context even though the standalone torchrun test passed with
idx 1) and **`NCCL_SOCKET_IFNAME` unset** (setting it to the LAN iface causes the same
error 101 — it poisons IB GID selection); `GLOO_SOCKET_IFNAME=enp9s18` for the gloo
bootstrap; `VLLM_HOST_IP=<ring ip>`; unset `CUDA_HOME` + `VLLM_USE_FLASHINFER_SAMPLER=0
VLLM_USE_DEEP_GEMM=0` (flashinfer JIT headers mismatch the venv cu13 nvcc) + `pip install
ninja` into the venv (ray workers spawn with a fresh PATH — venv bin must be in PATH).
Proof: TP workers on GPUs of BOTH nodes (17,765 MiB each), /v1/models 200, real
completion, NCCL channels `via NET/IB/0` both directions. ActorHandleNotFoundError in
logs is teardown noise after the real failure — always chase the FIRST error.

**Phase F (3-node): structurally blocked.** 143's two CX5 ports ARE legs A/B
terminations (host-bound). VM109 has NO CX5 passthrough (hostpci0-5 = GPUs only), and
passing either ring port to VM109 would disconnect a leg. Guest-side 3-node RDMA needs a
third CX5 in 143 or an SR-IOV VF design — Jordan's hardware call. Host-side RDMA on all
three nodes is fully qualified. The ray_utils patch is per-venv: apply to VM109's venv
before any future distributed run.

**Production restored:** VM103 (vllm.service) + VM111 (vllm-qwen.service) back to 200 +
real completions after the test window; VM149 untouched. VM401 remained stopped as found
(node miam00112 offline from Jordan's restart cycle). Temp IPs remain on ring ports
(172.31.0.1/.2 host-side + guest /30s, .5/.6) — flush or formalize next window.

## Session 4 (2026-09-12 ~03:45–04:50 UTC): post-cable validation — RING FULLY QUALIFIED + Phase E state

**Phase D verdict: PASS.** Jordan installed 2× MCP1600-C002 (Mellanox QSFP28 100G-CR4, 2m);
both legs negotiated 100 Gb at MTU 9000 immediately, dmesg shows clean `Port module event:
Cable plugged` (the OEM-DAC `Cable error` is gone). Card was never the problem — confirmed.

Cable map by EEPROM serial (a serial appearing on two ports = one physical cable):
- `Q260115790049` (MCP1600-C002): 111 `enp4s0f0np0` ↔ 143 `enp4s0f0np0` — leg A
- `Q260306970053` (MCP1600-C002): 143 `enp4s0f1np1` ↔ 144 `enp4s0f1np1` — leg B
- `CSC260508200103` (QSFP-100G-CU2M): 111-f1 ↔ 144-f0 — leg C

**TOPOLOGY CORRECTION vs earlier notes:** leg C is GUEST↔GUEST. VM103 (miam00111/103,
hostpci6=04:00.1) holds 111's f1 port → guest iface `enp3s0np1`; VM111 (miam00144/111,
hostpci6=04:00.0) holds 144's f0 port → guest iface `enp3s0np0`. Host-side ports for leg C
are vfio-bound while the VMs run (correct, not the driverless ghost). Leg C tests require
in-guest bring-up: `ip link set <iface> mtu 9000 up` + temp IP `/30` (a `/32` add silently
breaks routing — the /30 gotcha again; `ip addr replace X/30` fixes it).

Results (full matrix in `/root`-style report `100G-RDMA-POST-CABLE-VALIDATION-20260912.md`):
- Verbs RC ~93.0–93.6 Gb/s on all 4 host directions + both leg-C guest directions
- iperf3 4-stream 31–36 Gb/s (x8-slot TCP envelope, matches 2026-09-10 baseline)
- Error counters clean post-load on every ring port; links stayed 100 Gb
- NCCL 2-node ALLREDUCE PASS (VM103 rank0 + VM111 rank1): `NET/IB rocep3s0:1/RoCE [RO]`,
  `GDR 0` — first attempt failed `ibv_modify_qp RTR Invalid argument (local GID index 3)`
  because the GID pin wasn't exported inside the torchrun shells
- Registry `rdma_ring_nodes` updated: 143 qualified=True, all three hosts carry a
  `postcable_2026_09_12` evidence block

**Phase E (strict cross-node TP, 111+144) — ~80%, root causes closed:**
- vLLM 0.28.0 confirmed: ray_utils hardcodes PACK; RAY_pgname ignored (re-verified);
  named detached PG (`name=strict-spread-e2`) NOT adopted; `VLLM_USE_RAY_V2_EXECUTOR_
  BACKEND=1` exists (RayExecutorV2, workers=PG-scheduled actors) but EngineCore still
  created its own PG in the tested path.
- Ray-job-driver path FAILS: APIServer multiprocessing-spawns EngineCore → fresh Ray
  session → no current PG (jobs 0a… vs 0b… session mismatch). Also: an actor whose run()
  returns dies before serve finishes; spawn-in-driver needs `if __name__ == "__main__"`.
- **WORKING PATH:** env-gated patch to `vllm/v1/executor/ray_utils.py` on BOTH guests
  (`.bak.e2` backups, ast-checked): `strategy=os.getenv("VLLM_RAY_PG_STRATEGY","PACK")`.
  Launched with `VLLM_RAY_PG_STRATEGY=STRICT_SPREAD` → vLLM's own WARNING
  "tensor_parallel_size=2 is bigger than a reserved number of GPUs (1) in a node" on both
  node IDs = strict spread achieved.
- Remaining blocker: cross-node Gloo bootstrap connects loopback (127.0.1.1 refused).
  Fix staged in `~/work/e_launch2.py`: export `GLOO_SOCKET_IFNAME` + `NCCL_SOCKET_IFNAME`
  = guest LAN iface (`enp9s18`), relaunch, poll :8300, verify placement (nvidia-smi both
  nodes), completion, NCCL evidence, then restore.
- Ray cluster recipe (proven): head VM103 `ray start --head --port=6379
  --node-ip-address=172.31.0.1`; worker VM111 `--address=172.31.0.1:6379
  --node-ip-address=172.31.0.2`. Job logs: `/tmp/ray/session_latest/logs/job-driver-<id>.log`.
- Restore (proven): `ray stop --force; pkill -f 'vllm serve'; systemctl start
  vllm.service` (VM103) / `vllm-qwen.service` (VM111) — call start directly (is-active
  guard no-ops). Production was verified restored once already this session (both :8000
  200 + real completion "OK").
- **Phase F prerequisite:** VM109 has NO CX5 passthrough (no hostpci for 0000:04:00.x) —
  add hostpci + VM restart, apply the same ray_utils patch to VM109's venv.

**Delivery speedup (proven):** root-password SSH works from the Hermes box to nodes →
pexpect scp (`~/work/pexpect_scp.py`, same expect-password loop) replaces the hex-chunk
pipeline for .deb delivery (perftest 24.01 + rdma-core 50.0-2ubuntu0.2 + iperf3 chain →
143). Deb sourcing traps: bullseye iperf3 3.9 runs on PVE 9 but needs `libssl1.1` from
FOCAL pool path `pool/main/o/openssl/` (not `openssl1.1/`) and `libsctp1`; `file`-check
every deb (280–300-byte HTML 404s masquerade as archives); URL `+` may need `%2B`.

**Re-runnable:** `scripts/rdma_qual_matrix.py` (this skill) runs the per-leg verbs matrix
with correct server readiness, single-invocation client, and result parsing.

## Session 5 (2026-09-12 evening): Phase F 3-node attempt — mixed transport + PP-over-Ray lessons

**Hardware reality (Jordan):** one dual-port CX5 per node (111/143/144). Full guest IB mesh
would need all 6 ring ports inside guests — ATTEMPTED AND REJECTED: passing both functions
of a card to vfio wedges it at D3cold (`invalid PCI interrupt pin 255`); only host reboot
recovers (see proxmox skill CX5 pitfall). Production topology restored: VM103=111-f1,
VM111=144-f0, VM109=no CX5.

**Workable 3-node design (mixed transport):** Ray + Gloo bootstrap over mgmt LAN
(10.0.20.161 head :6379; workers join by LAN IP), NCCL `NET/IB` on the 103↔111 leg,
`NET/Socket` for 109 pairs. Plan §F1 explicitly allows this — first test is orchestration,
not max bandwidth. Ray envs must be exported INSIDE each raylet start shell per node
(`NCCL_IB_GID_INDEX=3 NCCL_DEBUG=INFO`, `NCCL_SOCKET_IFNAME`/`GLOO_SOCKET_IFNAME` per
guest: `enp9s18` on VM103/VM111, `enp8s18` on VM109 — ifaces differ per guest, never
export one guest's iface from the driver).

**TP=3 on Qwen3-1.7B fails structurally** — "Total number of attention heads (16) must be
divisible by tensor parallel size (3)". **PP=3 works structurally** (28 layers ÷ 3), but
vLLM 0.28 PP-over-Ray hits a startup deadlock: NCCL connects ("Connected all trees") yet
one worker sleeps while others spin 100% CPU; V1 AND V0 engines both hang at
`shm_broadcast.py:801 "No available shared memory broadcast block"`. Root causes found
and fixed along the way (keep these for the next attempt):
- flashinfer JIT in Ray workers needs `CUDA_HOME=/opt/vllm-venv/lib/python3.12/site-
  packages/nvidia/cu13` + that bin on PATH **baked into the raylet env** (verify inside a
  worker via a `ray.remote` env check — the venv python cannot import nvidia.cuda_runtime
  at launch time on all guests, so hardcode the cu13 path).
- ray_utils STRICT_SPREAD patch must exist on ALL nodes (copied to VM109, verified by
  md5 `93ebf2…`; VM109 backup `.bak.f3`). Guest-side md5 comparison is the safe copy
  check — controller-side fetch_text display truncation caused a false ABORT.
- ray 2.58.0 pip-installed into VM109's venv (pypi reachable from guests).
- Remaining open question: whether the spin/sleep hang is fixable via `NCCL_COMM_ID`
  pinned to head (untested) or whether 0.28 PP-over-Ray is simply broken — next window
  should also try TP=2×PP mismatch configs or wait for a vLLM upgrade. Spin/sleep
  diagnosis: `ps aux | grep RayWorkerProc` CPU% per node + NCCL channel lines in
  `/tmp/ray/session_latest/logs/worker-*.out` ("Connected all trees" = transport fine,
  the hang is elsewhere).
- vLLM serve log ERROR lines propagate from workers via `multiproc_executor.py:1047`
  tracebacks — always pull the worker `.err` file from `/tmp/ray/session_latest/logs/`
  on the node hosting the failing rank for the real traceback (serve-log tail is often
  stale/repeated from the previous attempt).
