# ConnectX-5 SR-IOV guest-RDMA runbook (MIAM-IA-USA, 2026-09-13)

Session-proven recipe for exposing RoCE-capable VFs from host-owned CX5-Ex PFs to Proxmox VMs while physical PFs stay on mlx5_core. Reference run: 3-node ring (miam00111/143/144), Dell OEM CX5-Ex fw 16.35.1012 PSID DEL0000000004, PVE 9.2.10 kernel 7.0.14-11-pve.

## Phase 0 — read-only audit

```bash
# firmware + PSID per PF
ethtool -i <pf-iface> | grep -E 'firmware-version'
# SR-IOV capability flags (modern kernels; mlxconfig/mst NOT required)
devlink dev param show pci/<PF> | grep -A2 -E 'enable_sriov|total_vfs'
# classic capability check
cat /sys/bus/pci/devices/<PF>/sriov_totalvfs 2>/dev/null   # absent = firmware-disabled
lspci -vvv -s <PF> | grep -c 'SR-IOV'                      # 0 = capability not exposed
```

Decision gate: `total_vfs` (permanent) > 0 but `enable_sriov`=false → enablement is a reversible NVRAM write, not a flash. If both are absent entirely, stop.

## Phase 1 — enable SR-IOV (per node, then reboot)

```bash
for d in 0000:04:00.0 0000:04:00.1; do
  devlink dev param set pci/$d name enable_sriov value true cmode permanent
  devlink dev param set pci/$d name total_vfs value 8 cmode permanent   # MANDATORY: enable resets total_vfs to 0
done
# reboot node (PVE API: POST /nodes/<node>/status {command:reboot}); then verify:
cat /sys/bus/pci/devices/<PF>/sriov_totalvfs    # 8
ip link set <pf-iface> up                        # ring ports carry no persisted config
```

Reboot effects to expect: ring port links DOWN until `ip link set up` (cosmetic); all temp IPs/MTU lost; stopped VMs with `onboot` do NOT auto-start (start manually — fresh-boot `qm start` is the safe PCI handoff anyway).

## Phase 2 — ephemeral VF + attach

```bash
echo 1 > /sys/bus/pci/devices/<PF>/sriov_numvfs
VF=$(basename $(readlink -f /sys/bus/pci/devices/<PF>/virtfn0))   # 04:00.0 -> 04:00.2 (do NOT guess)
readlink -f /sys/bus/pci/devices/$VF/iommu_group
# health gate: PF still mlx5_core, 100000Mb/s link, no AER/D3cold in journalctl
# attach to a STOPPED VM on a FREE hostpci slot (check qm config first!):
echo mlx5_core > /sys/bus/pci/devices/$VF/driver/unbind
qm set <vmid> -hostpciN $VF,pcie=1
qm start <vmid>
```

Split-driver safety: creating VFs on the mlx5 PF of a card whose sibling PF is already vfio-passthrough validated clean (no D3cold/pin-255). Do not confuse with the dual-function-vfio handoff wedge rule.

## Guest-side bring-up

```bash
apt-get install -y ibverbs-utils rdma-core perftest
ibv_devices                       # device names differ per guest: mlx5_0..N vs rocep<iface>
ip link set <vf-iface> mtu 9000 up; ip addr add <temp-cidr> dev <vf-iface>
# perftest: pin device AND gid index when >1 device exists
ib_write_bw -F --report_gbits -d <dev> -x 3 -s 131072 -n 100 <peer-ip>
# background server inside guest (plain nohup dies under qm guest exec):
setsid nohup timeout 60 ib_write_bw ... > /tmp/s.log 2>&1 < /dev/null &
```

## NCCL over the guest triangle (3 VMs, ring cabling)

- Rendezvous/master must live on the mgmt LAN (`--master_addr 10.0.20.x`), NOT a point-to-point RDMA /30 — other VMs cannot reach a peer's leg subnet, giving errno 101 `Network is unreachable`.
- **RoCE QPs do not survive a routed hop.** NCCL ring pairing across a router (rank pair on non-adjacent /30s routed via the middle VM) fails with `IBV_WC_RETRY_EXC_ERR` (`vendor_err=129`, localGid/remoteGid on different subnets). Every NCCL rank pair needs DIRECT L2 adjacency on some leg — wire the full triangle before testing.
- ufw can be inactive yet rules added harmlessly; check `ss -tln | grep 29500` on the master to confirm the TCPStore is listening before launching workers.
- Working run shape: torchrun `--nnodes=3 --nproc_per_node=6` x3 (node_rank 0/1/2), `NCCL_SOCKET_IFNAME=enp NCCL_IB_DISABLE=0 NCCL_DEBUG=INFO`. Success signature: `NET/IB : Using [0]<vf-dev>:1/RoCE ...; OOB <mgmt-iface>:10.0.20.x<0>` and channel lines `via NET/IB/0` (multi-homed VM uses NET/IB/1 for the second leg). No `NET/Socket` = no fallback.

## 3-node NCCL runbook (VM103/109/111 addresses and roles)

| VM | node | node_rank | VF ifaces | RDMA devs |
|---|---|---|---|---|
| VM103 | miam00111 | 0 | enp3s0 (leg A, 172.31.100.1/30), enp4s0np1 (leg C PF, 172.31.150.1/30) | rocep3s0, rocep4s0 |
| VM109 | miam00143 | 1 | enp3s0 (leg A .100.2), enp4s0 (leg B, 172.31.200.1/30) | mlx5_0, mlx5_1 |
| VM111 | miam00144 | 2 | enp3s0 (leg B .200.2), enp4s0np0 (leg C PF, 172.31.150.2/30) | rocep3s0, rocep4s0 |

Master: 10.0.20.161:29500 (VM103). Launch master first, confirm `ss -tln | grep 29500`, then workers in parallel.

## Performance matrix achieved (100G legs)

| Path | Direction | Gb/s |
|---|---|---|
| VM109 VF-A ↔ 111 host PF | push | 95.65 |
| VM109 VF-B ↔ 144 host PF | push | 96.24 |
| VM109 ↔ VM103 (guest VF ↔ guest VF) | both | 95.9–97.2 |
| VM109 ↔ VM111 (guest VF ↔ guest VF) | both | 96.4–96.5 |
| VM103 ↔ VM111 (guest PF ↔ guest PF, leg C) | both | 95.4–96.6 |

## Cleanup / pause pattern (RDMA "off when idle")

Ephemeral state that does NOT survive host reboot: sriov_numvfs, MTU 9000, link up, temp IPs, guest /30s, static routes. To pause RDMA: stop the inference VMs (VM stopped = VF unassigned = no RDMA). To fully retract: `echo 0 > .../sriov_numvfs` per PF, optionally `devlink ... enable_sriov value false cmode permanent` + reboot.

## Rollback notes

- Pre-change VM configs: `/root/<node>-vm<id>-config-before-sriov-<ts>.txt` on each node.
- VM109 pre-change config: `/root/vm109-config-before-sriov-<ts>.txt` on miam00143.
- Restore a lost hostpci slot from the backup with `qm set <vmid> -hostpciN <orig-bdf>,pcie=1` on a stopped VM.
- Progress log of the reference run: `miam00143:/root/SRIOV-PROGRESS-20260913.md`.
