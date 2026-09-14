# ZFS pool buildout on a PVE node — session detail (MIAM-00147, 2026-09-11)

Concrete recipes, exact commands, and evidence paths from a successful bulk+fast build.
The SKILL.md carries the class-level pattern; this file carries the reproducible detail.

## Pre-flight evidence chain (per handover order)

1. Final SMART dump per persistent serial: `smartctl -x /dev/disk/by-id/ata-..._<serial>` into
   `/root/<node>-zfs-phase1/smart-final-<stamp>/`, plus an awk-extracted SUMMARY.txt
   (`Reallocated_Sector_Ct`, `Current_Pending_Sector`, `Offline_Uncorrectable`, `UDMA_CRC_Error_Count`
   for HDDs; `Reallocated_Sector_Ct`, `Grown_Bad_Blocks`, `Reported_Uncorrect` for SSDs).
   Note: `smartctl -l selftestlog` is INVALID on smartmontools 7.5 — use `-l selftest`.
2. Fresh vzdump of the production CT + off-host copy + `sha256sum -c` on the remote node.
   Dumpdir chmod 755 chain (see SKILL.md vzdump pitfalls).
3. Restart-migrate the CT: POST `/nodes/<src>/lxc/<id>/migrate` `{"target": ..., "restart": 1}`;
   live (`online: 1`) returns "lxc live migration is currently not implemented".
4. Cold/warm/cold qualification via PDU outlet cycling (host outlet + enclosure outlet),
   running `/root/<node>-zfs-phase1/qualification.sh` after each boot; grep
   `SERIAL_CHECK_EXIT|MISSING|MISMATCH|ARC_MAX|no pools` as the rollup.

## Pre-erase recheck script (inline, passed 2026-09-11)

```bash
set -eu
[[ "$(hostname -s)" == miam-00147 ]] || { echo STOP wrong host; exit 1; }
# per serial: [[ -b $disk ]] + lsblk SERIAL round-trip + exact byte size check
# findmnt -rn -o SOURCE,TARGET | grep -E '^/dev/sd[a-h]'  (NOT plain `mount | grep sd`)
for d in sda sdb sdc sdd sde sdf sdg sdh; do
  if ls /sys/block/$d/*/holders/* >/dev/null 2>&1; then echo "STOP holders on $d"; exit 1; fi
done
zpool import          # must say: no pools available to import
blkid <each disk>     # signature inventory before erasing
```

## Erase recipe

```bash
sgdisk --zap-all $disk
wipefs -a $disk $disk-part1 $disk-part2 2>/dev/null || true
dd if=/dev/zero of=$disk bs=1M count=8 conv=fsync status=none   # optional; fsync may fail on USB bridge — verify with blkid, not dd's exit code
```

USB-bridge write-failure signature (SSD 21193G800468): ALL writes fail (dd 512B..64MB,
direct+buffered) with `I/O error ... Aborted Command`, link drops to UDMA/33, reads fine,
SMART counters unchanged (realloc/grown stable at 29), zero CRC errors, empty error log.
Conclusion: broken write path → exclude from pool; rebuild fast as 3-way mirror to keep
2-disk fault tolerance; record `ssd-<serial>-FAIL-<date>.txt` on the node.

## Pool creation (exact working commands)

```bash
zpool create -o ashift=12 \
  -O compression=lz4 -O dedup=off -O sync=standard -O atime=off \
  -m /bulk bulk raidz1 \
  /dev/disk/by-id/ata-WDC_WUH721818ALE6L4_3GKY0D6E \
  /dev/disk/by-id/ata-WDC_WUH721818ALE6L4_3GKW0L7E \
  /dev/disk/by-id/ata-WDC_WUH721818ALE6L4_3GKXHT2E \
  /dev/disk/by-id/ata-WDC_WUH721818ALE6L4_3GKXES0E

zpool create -o ashift=12 -o autotrim=on \
  -O compression=lz4 -O dedup=off -O sync=standard -O atime=off \
  -m /fast fast mirror \
  /dev/disk/by-id/ata-WDC_WDS400T1R0A-68A4W0_21193G800448 \
  /dev/disk/by-id/ata-WDC_WDS400T1R0A-68A4W0_21193G800296 \
  /dev/disk/by-id/ata-WDC_WDS400T1R0A-68A4W0_21193G800178
```

- `zpool create -n` dry-run output must be inspected first; check topology + member order.
- `autotrim=on` MUST be `-o` (pool prop); as `-O` it errors "not a valid filesystem property".
- ARC cap persistence: `/etc/modprobe.d/zfs.conf` `options zfs zfs_arc_max=1636827136`; verify after
  each boot via `cat /sys/module/zfs/parameters/zfs_arc_max`.

## Datasets + registration

- bulk children: model-weights, model-archive, llm-benchmarks, llm-metrics-exports,
  postgres-backups, pve-backups, gdrive-archive, infra-backups, diagnostics.
- fast children: models-hot, benchmarks-hot, metrics-hot, scratch, lxc.
- `zfs set atime=off bulk/model-weights bulk/model-archive`.
- storage.cfg append (verified active via `pvesm status`):

```
dir: bulk-backups
	path /bulk/pve-backups
	content backup
	nodes miam-00147
	prune-backups keep-daily=7,keep-weekly=4,keep-monthly=6

zfspool: zfs-fast
	pool fast/lxc
	content rootdir
	nodes miam-00147
```

## CT118 file server (unprivileged, miam-00147)

- Pre-existed (CT118, stopped, nesting=1, 2c/2G/512M swap/16G) — never duplicate-create.
- net0 via API: `PUT /nodes/<node>/lxc/118/config` `net0: name=eth0,bridge=vmbr0,gw=10.0.20.1,hwaddr=BC:24:11:B2:7C:9E,ip=10.0.20.156/24,type=veth`
  (IP pre-cleared: silent on ping/ARP from two nodes, absent from corosync + /etc/pve + DHCP pool .190-.250).
- Bind mounts (applied via `pct set -mp<N>`, require CT restart to take effect):

```
mp0: /fast/models-hot,mp=/srv/models,ro=1
mp1: /bulk/model-weights,mp=/srv/models-canonical,ro=1
mp2: /fast/scratch,mp=/srv/scratch
mp3: /bulk/pve-backups,mp=/srv/pve-backups,ro=1
```

- Ganesha config gotchas: per-export `FSAL { Name = VFS; }` REQUIRED (top-level FSAL block =
  restart failure); `NFS_CORE_PARAM { NFS_Protocols = 3,4; }`; `Pseudo = /<name>`; CLIENT blocks
  `Clients = 10.0.20.0/24`. Working template at /tmp/ganesha-setup.sh pattern (heredoc into
  /etc/ganesha/ganesha.conf, `systemctl restart nfs-ganesha`, `systemctl is-active`).
- Verify what actually loaded:
  `dbus-send --system --print-reply --dest=org.ganesha.nfsd /org/ganesha/nfsd/ExportMgr org.ganesha.nfsd.exportmgr.ShowExports`
  (only `uint16 0 "/"` = exports didn't load). Mount test from client: `mount -t nfs4 10.0.20.156:/models /mnt/x`.
- `showmount -e` (RPC v3) returns "RPC: Program not registered" against Ganesha v4 — not an error signal.

## Evidence file locations on the node

- `/root/miam00147-zfs-phase1/` — smart-final-<ts>/, qual-{cold1,warm2,cold3}-<ts>.txt,
  erase-<ts>.txt, pool-create-<ts>.log, datasets-<ts>.log, storage.cfg.pre-zfs-<date>,
  ssd-0468-FAIL-20260911.txt
- Off-host: MIAM-00119 `/root/miam00147-zfs-backups-20260911/` (vzdump + SHA256SUMS, verified OK)
- Post-boot task evidence: PVE task log for the restart-migration UPID on miam-00147.