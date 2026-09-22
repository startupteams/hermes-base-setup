# RoCE / Ethernet MTU validation on the MIAM ConnectX-5 ring (proven 2026-09-21)

The decision procedure for "should we move the RDMA link to MTU 9000?". Result that session:
**MTU kept at 1500** — jumbo frames are dropped by a device in the path.

## 0. First: identify the LINK LAYER — it gates everything

```bash
# inside the guest:
ibv_devinfo 2>/dev/null | grep -iE 'link_layer|active_mtu|max_mtu|state'
```
- `link_layer: Ethernet` → **RoCE**. The Ethernet netdev MTU governs; 9000 is the candidate.
- `link_layer: InfiniBand` → IPoIB. Do NOT set Ethernet MTU 9000; use IB MTU semantics (~4096).
- `ibv_devinfo` reporting `max_mtu: 4096` is the IB-transport value and is **irrelevant for RoCE** —
  do not let it fool you into thinking 9000 is unsupported or that you should use 4096.

## 1. Bring the ring up (interfaces are DOWN with no persisted config)

MIAM guest CX5 ports (`enp3s0`, `enp4s0*`) come up **DOWN / DISABLED / no IP**; there is **no
netplan/networkd config** referencing them, so links do not survive a reboot. To test you must
configure manually (temp IPs do NOT persist — usually desirable):

```bash
ip link set <iface> mtu 1500 up
ip addr add 10.77.0.1/30 dev <iface>      # use an isolated /30 PER PHYSICAL LINK
```
Use a distinct `/30` per link. Putting several RDMA interfaces on one /24 contaminates discovery
(replies arrive on a different interface and `ping -I` reports false reachability). Discover a link
by configuring one end first, then pinging from the other — an ordering artifact makes the reverse
ping look like 100% loss if the peer IP isn't set yet.

Discovery shortcut for the MIAM ring (guest exec on the owning node):
`qm guest exec <vmid> -- bash -c '<script>'`; device name for `ib_write_bw -d` is `rocep3s0` for
`enp3s0`, `rocep4s0` for `enp4s0*`. Use `-x 3` (RoCEv2 GID index) when multiple devices exist.

## 2. Baseline at MTU 1500

```bash
# server (peer A):
setsid nohup ib_write_bw -d rocep3s0 -i 1 -x 3 -s 1048576 -n 2000 -F > /tmp/bw1500.log 2>&1 < /dev/null &
# client (peer B):
ib_write_bw -d rocep3s0 -i 1 -x 3 -s 1048576 -n 2000 -F <peer-IP>
```
MIAM result: **11,035 MB/s ≈ 88 Gb/s** on a 100 Gb leg (near line rate). "*Background servers inside
guests*": `nohup ... &` alone dies under `qm guest exec` — **`setsid nohup ... < /dev/null &`**.

## 3. The MTU 9000 pilot — validate with a JUMBO PING first

Set 9000 on **both** ends, then the decisive test:
```bash
ping -I <iface> -M do -s 8972 -c 10 <peer-IP>     # 8972 = 9000 - 28 header bytes
```
- **0% loss** → the whole path passes jumbo; proceed to re-benchmark `ib_write_bw` and compare.
- **100% loss while normal `ping` still works at 0%** → a device in the path (switch/segment) does
  NOT pass jumbo. **Immediately set the link back to 1500 and STOP** — do not persist 9000, do not
  chase it. (This was the MIAM outcome.)

All devices on the physical/logical path must agree on MTU — a direct DAC pair can work while a
switched path fails. Never assume; test.

## 4. Rollback + record

```bash
ip addr flush dev <iface>; ip link set <iface> mtu 1500; ip link set <iface> down
```
Record **either** `MTU 9000 KEPT` **or** `MTU 1500 RESTORED` in the handoff, with the measurement.
Keep 9000 only for a real gain (≥5% RDMA or ≥3% app throughput) with zero new errors/AER.

## 5. AER gate — map the root port to its DOWNSTREAM device, not the port number

A corrected-AER storm on root port `0000:00:01.1` does NOT implicate the ConnectX-5. Enumerate the
bridge's children (`/sys/bus/pci/devices/0000:00:01.1/0000:XX:00.Y/`) and `lspci -nn -s XX:00`,
then compare against `qm config` hostpci entries. MIAM: `0000:01:00` = **RTX 3080 (GPU riser)**,
while the CX5's own root ports (`00:03.1/.2/.3`) showed `aer_rootport_total_err_cor = 0` → RDMA work
permitted, GPU riser physical inspection deferred. Check per-port counters:
`cat /sys/bus/pci/devices/0000:00:0X.Y/aer_rootport_total_err_cor`.