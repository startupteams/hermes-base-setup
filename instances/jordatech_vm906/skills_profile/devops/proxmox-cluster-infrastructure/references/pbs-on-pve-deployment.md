# Proxmox Backup Server installed ON a PVE host (proven 2026-09-21, MIAM-00147)

Deploying `proxmox-backup-server` directly on a PVE node (Proxmox supports it; they *recommend* a
separate physical PBS, so document the failure-isolation compromise in the handoff). Full session:
`MARION-IA-USA-PBS-RDMA-HANDOFF-20260921.md`.

## Install (non-disruptive)

```bash
. /etc/os-release   # expect trixie on PVE 9
cat > /etc/apt/sources.list.d/pbs.sources <<'EOF'
Types: deb
URIs: http://download.proxmox.com/debian/pbs
Suites: trixie
Components: pbs-no-subscription
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg
EOF
apt-get update -qq
apt-get -s install proxmox-backup-server        # REVIEW: expect ~8 new pkgs, 0 removals, no kernel/proxmox-ve change
apt-get install -y proxmox-backup-server        # 4.2.6-1 at this date
systemctl enable --now proxmox-backup.service proxmox-backup-proxy.service
ss -lntp | grep :8007        # proxy listens here
```
Install the *server* package, NOT the `proxmox-backup` meta-package (which can pull a kernel).

## atime: the make-or-break datastore requirement

PBS garbage collection needs usable **atime**. If the backing filesystem is mounted `noatime`
(common on ZFS pools — check `findmnt /<pool>`), PBS will refuse the datastore. Do **NOT** disable
the safety check. Instead create a **dedicated child dataset** with atime on:

```bash
zfs create -o mountpoint=/bulk/pbs-datastore -o atime=on bulk/pbs
# verify it actually records atime (ZFS atime=on mounts relatime):
touch /bulk/pbs-datastore/.probe; sleep 1; stat -c '%x' /bulk/pbs-datastore/.probe
# read it, then stat again -> atime must advance
```
Do not touch the parent dataset's props, vdevs, ashift, or pool membership.

## Datastore + jobs

```bash
proxmox-backup-manager datastore create marion-pbs /bulk/pbs-datastore \
  --keep-last 3 --keep-daily 14 --keep-weekly 8 --keep-monthly 6 --keep-yearly 2 \
  --gc-schedule "sun 06:30" --prune-schedule "05:30" --verify-new
proxmox-backup-manager verify-job create marion-verify --store marion-pbs \
  --schedule "sun 08:00" --ignore-verified false --outdated-after 30
proxmox-backup-manager garbage-collection status marion-pbs   # runs atime safety check
```

### Pitfalls (all hit this session)
1. **`... | head -5` SIGPIPE-kills the create.** `datastore create` streams progress; piping to
   `head` closes the pipe and kills it mid-init (config gets half-written). Redirect to a FILE,
   never a pipe. If it half-wrote, the config registers but keep-*/prune-schedule are missing.
2. **In PBS 4.x, `keep-*`/`prune-schedule` moved to PRUNE JOBS.** `datastore update --keep-last`
   fails with *"datastore prune settings have been replaced by prune jobs"*. The create-time
   `--keep-*` flags auto-generate a prune job named `default-<store>-<uuid>`. Inspect with
   `proxmox-backup-manager prune list`.
3. **Calendar events are PBS/systemd-style, not cron-ish.** Use `05:30` (daily) and `sun 06:30`,
   NOT `"daily 05:30"` (rejects: `unable to parse calendar event at 'daily'`).
4. `datastore create --help`, `acl update --help`, `user --help` are all cheap — check the exact
   subcommand syntax on the installed version rather than guessing.

## Least-privilege identity + PVE storage integration

```bash
proxmox-backup-manager user create pve-backup@pbs
proxmox-backup-manager user generate-token pve-backup@pbs marion-cluster   # secret shown ONCE
# >>> CRITICAL: PBS tokens are PRIVILEGE-SEPARATED (privsep=1) by default -> the token
#     inherits NOTHING. `user permissions pve-backup@pbs` shows privileges, but the TOKEN
#     shows empty and the API returns "Cannot find datastore". Grant ACLs to the TOKEN id:
proxmox-backup-manager acl update /datastore/<store> DatastoreBackup \
  --auth-id 'pve-backup@pbs!marion-cluster' --propagate 1
proxmox-backup-manager acl update /datastore/<store> DatastoreAudit  \
  --auth-id 'pve-backup@pbs!marion-cluster' --propagate 1
```
- `acl update` takes `--auth-id <userid>`, not a positional user. `--propagate` defaults to true.
- `generate-token` returns JSON with `"value": "<uuid>"`; parse the UUID. Write it to
  `/etc/pve/priv/storage/<store>.pw` (0600) AND keep a root-0600 copy — it is shown once.

Add the storage on a cluster node:
```bash
pvesm add pbs pbs-marion --server <ip> --datastore marion-pbs \
  --username 'pve-backup@pbs!marion-cluster' --password "$SECRET" \
  --fingerprint "$(proxmox-backup-manager cert info | grep -i fingerprint | awk '{print $NF}')" \
  --content backup
```
- **`pvesm add` needs `--password` at creation time** — it does NOT read the `.pw` file first
  (without it: perl warning `uninitialized value $password` + `401 Unauthorized`). Pass it via a
  shell variable so the secret never appears literally in the command/log. `/etc/pve` is a FUSE
  mount; the `.pw` file persists fine once written.
- Wrong datastore API path guesses return "not found"; the real one is
  `/api2/json/admin/datastore`. Test the token live:
  `curl -sk -H "Authorization: PBSAPIToken=<user>@pbs!<tok>:<secret>" https://127.0.0.1:8007/api2/json/admin/datastore`

## Migration of an existing native vzdump job

The "mysterious 03:05 backup with NO-JOBS" was a **pvescheduler** job in `/etc/pve/jobs.cfg`
(`vzdump: <id>`), NOT cron: `/etc/pve/vzdump.cron` and `/etc/cron.d/` carried nothing.
Enumerate with `pvesh get /cluster/backup`. Create the PBS replacement cluster-wide:
```bash
pvesh create /cluster/backup --id marion-pbs-daily-all --schedule "03:05" \
  --storage pbs-marion --mode snapshot --all 1 --exclude "102,107,..." \
  --notes-template '{{guestname}} / {{vmid}} on {{node}}' --enabled 1
pvesh set /cluster/backup/<legacy-id> --enabled 0     # disable duplicate, keep archives
```

## Real restore proof — including a disk-level marker (no guest agent needed)

A storage showing `active` is not proof. Do LXC **and** QEMU backup→destroy→restore→boot→verify.
When the guest has no reachable agent/network (e.g. a cloud image that never DHCP'd), stamp a
unique marker **onto the guest disk from the host** — stronger and independent of guest services:

```bash
qm stop <vmid>
LOOP=$(losetup -Pf --show /dev/pve/vm-<vmid>-disk-0)     # kpartx is often NOT installed; use losetup -P
mount ${LOOP}p1 /mnt/vm                                  # p1 = root on Ubuntu cloud images
echo "MARKER-$(date +%s)-$(head -c6 /dev/urandom|od -An -tx1|tr -d ' \n')" > /mnt/vm/root/MARKER
cat /mnt/vm/etc/machine-id                               # record it too
sync; umount /mnt/vm; losetup -d "$LOOP"; qm start <vmid>
```
After restore to a new VMID, mount the **restored** LV the same way and diff marker + machine-id.
Also grab boot evidence with a console screendump: `echo "screendump /tmp/v.nc.ppm" | qm monitor <vmid>`,
then convert the PPM and read it (guest agent may be absent).
`pvesm list <store>` gives the volid (`<store>:backup/ct/<id>/<ts>` / `.../vm/<id>/<ts>`).