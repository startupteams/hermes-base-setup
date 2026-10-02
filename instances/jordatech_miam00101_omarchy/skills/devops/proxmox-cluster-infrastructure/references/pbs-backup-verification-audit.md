# PBS backup coverage verification & safe restore-testing

Cluster-wide backup audit methodology + restore-test safety. Proven 2026-09-26 on MARION-IA-USA
(46 guests, 12 nodes, PBS 4.2.6, datastore on ZFS `bulk/pbs`). Read-only collector:
`scripts/pbs_coverage_audit.py`.

## The two-layer model (why "missing ZFS snapshots" is usually a category error)

- **PBS guest backups** = the cluster's VM/LXC protection layer. Answers "can I restore guest X?"
- **ZFS snapshots on the PBS host** = dataset rollback on THAT host only. They never protected
  remote guests. Before reporting "guest Y has no ZFS snapshot", determine which layer is
  supposed to protect it: PBS group / host dataset / app-level dump.

## Authoritative sources (cross-check, never trust one)

1. `GET /cluster/resources` + per-guest `/config` (onboot, storage, `mp0..N` bind mounts)
2. `GET /cluster/backup` — job scope: `all=1` + `exclude` list (auto-protects NEW guests —
   preferred policy) vs a fixed `vmid` include list (stale risk)
3. PBS token API on :8007, header `PBSAPIToken=<user@pbs!token>:<secret>` (secret lives at
   `/etc/pve/priv/storage/<storage>.pw` on the PVE nodes; fetch via noderun, 0600, never echo):
   - `/admin/datastore/<ds>/snapshots` — **NO `limit` param; a large `?limit=` returns HTTP 400**
   - `/admin/datastore/<ds>/status` (used/avail) and `/admin/datastore/<ds>/gc` (stats; all-zero
     usually means "GC never ran yet", not corruption — check install date vs schedule)
   - `/nodes/<pbs>/tasks?limit=1000` (worker_type: backup/verify/reader/prunejob)
   - `/admin/prune` + `/admin/verify` + `/admin/sync` (last-run-state, schedules)
4. `/cluster/tasks` + `/nodes/<node>/tasks/<upid>/log` for vzdump failures (entries are
   `{"n","t"}`; skip empty `t`)
5. Per-snapshot `verification.state=ok` exists thanks to verify-new + the weekly verify job.

## Coverage rules

- Tier: control-plane node / onboot=1 / infra-name → 0; prod app → 1; stopped dev → 2;
  job-excluded → 3. Unknown guests default to BACK UP until positively classified disposable.
- Recency: Tier 0/1 ≤ 30 h. Excluded-but-Tier-0/1 = WARNING (check whether exclusion is intended).
- Stale PBS groups for destroyed guests (backup-id no longer in cluster resources): flag for
  human deletion; never delete during an audit run.
- Nightly `job errors` on ONE node ≠ total failure — read the task log; usually one guest fails
  while every other guest on that node backs up fine.

## vzdump traps

- **Stopped VM with GPU-passthrough hostpci lines: vzdump AUTO-STARTS kvm to snapshot it** →
  `PCI device '0000:...' already in use by VMID '<other>'` when another VM holds those devices →
  that guest's backup fails every night. Options: (a) accept stale backups while the VM is an
  intentionally powered-off rollback, (b) exclude the guest from the job, (c) strip hostpci lines
  (breaks the rollback purpose). Never improvise destructive fixes on other VMs' passthrough.
- Snapshot mode + dirty-bitmap: "reused 599 GiB (99%)" is dedup working — N recovery points ≠ N
  full physical copies (chunk-level dedup).
- PVE 9 vzdump defaults to NO compression (`.vma` not `.vma.zst`) — see SKILL.md vzdump section.

## ZFS snapshot layer on the PBS host

- If a dataset hosts the PBS datastore (e.g. `bulk/pbs`), EXCLUDE it from recursive auto-snapshots
  (`zfs snapshot -r bulk` covers it): PBS owns retention (prune+GC); a second snapshot layer pins
  pruned chunks and grows daily. Legacy snapshots: report space held, leave deletion to a human.
- Retention-loop pitfall: `zfs destroy -r <snap>` on a parent-pool generation ALSO removes the
  same-named snapshots on child datasets → the next loop name errors ("could not find any
  snapshots to destroy") → with `set -e` the script aborts BEFORE the bulk-side cleanup on every
  run that has a stale pool-level snapshot. Fix: destroy per-name WITHOUT `-r` and tolerate
  already-gone: `zfs destroy "$snap" || echo gone`.
- Snapshot-create loop with exclusions: iterate `zfs list -H -o name -r <pool>` minus the PBS
  dataset and snapshot each dataset individually.

## Safe restore tests (prove recoverability without touching production)

- LXC restore from a PBS volid — use the node shell as root (the PVE API
  `POST /nodes/<n>/lxc` with a PBS `ostemplate` returned 500 in practice):
  `pct restore <newid> <storage>:backup/ct/<src>/<TS> --storage <dst>`.
- **CRITICAL: the restored config carries the ORIGINAL net0 with the production IP.** Before any
  start: `pct set <id> -net0 name=eth0,bridge=vmbr0,type=veth,ip=manual -onboot 0`
  (ip=manual = link up, no IP, no ARP conflict). Then start, `pct exec` to verify key files +
  service active/listening, stop, `pct destroy <id> --purge`.
- VM restore: `qmrestore <volid> <newid> --storage <dst>`. Verify the filesystem WITHOUT booting
  (mandatory when the guest runs automation with production side effects — recovery engines, DBs):
  `modprobe nbd max_part=16` (**max_part=0 hides partitions**), `qemu-nbd --connect=/dev/nbd0
  --read-only /dev/<vg>/vm-<id>-disk-N`, lsblk, `mount -o ro /dev/nbd0p1 /mnt/x`, check
  /etc/hostname + key dirs, umount, `qemu-nbd --disconnect /dev/nbd0`, `qm destroy <id> --purge`.
- Never boot a restored duplicate with its original IP; never boot duplicates of guests whose
  services act on production (LLM Manager recovery engine, ACMS). Boot-test a small
  infrastructure guest (LLDAP-class) instead — network-isolated.

## PBS-side health quick list

- datastore active; prune job schedule + desired keep-* (3/14/8/6/2); verify job + verify-new=true.
- Prune `last-run-state` from `/admin/prune`; GC stats zero = never run (first slot after install)
  — safe, GC only reclaims chunks already pruned; flag the first-run date, not an outage.
- App-aware DB dumps (pg_dumpall etc.) are a DIFFERENT recovery problem from PBS crash-consistent
  snapshots — verify both (dump age ≤30 h, sha256, off-host copy check) before declaring covered.
