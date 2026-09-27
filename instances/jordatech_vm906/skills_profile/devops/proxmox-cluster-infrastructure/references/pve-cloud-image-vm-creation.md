# Creating a VM from a cloud image on PVE 9.2 — API + node-SSH recipe

Proven 2026-09-27 (pdu-manager-staging VM156 on miam-00133). Use when provisioning a
staging/production VM from a vendor cloud image (Debian genericcloud, Ubuntu noble, etc.)
with no human at a console. Complements `headless-guest-provisioning-api-only.md` (which
covers why console automation and the storage import API are dead ends).

## Image acquisition — `download-url` quirks (PVE 9.2)

- Endpoint: `POST /nodes/<node>/storage/<store>/download-url`, body
  `{content: "iso", filename: <name>, url: <url>, checksum: <sha256-hex>, "checksum-algorithm": "sha256"}`.
- **`checksum: "auto"` FAILS** — PVE passes the literal string to the downloader
  (`checksum mismatch: got '<real>' != expect 'auto'`). Fetch the real checksum from the
  vendor's SHA256SUMS file first, or do a no-checksum download + verify manually.
- **`.qcow2` extension REJECTED** ("wrong file extension") — rename to `.img`.
- The task UPID completes in ~1-3 min for a 3 GB image (node has internet).
- Result lands in the `iso` content dir (`/var/lib/vz/template/iso/`) — even though it's a
  disk image, not an ISO. That's fine; the next step imports it properly.

## Disk import — the API path is DEAD; use node SSH

- `POST /nodes/<node>/storage/local-lvm/content` does NOT support `import-from` on PVE 9.2
  (400: "property is not defined in schema" / demands `size`+`filename` like a plain upload).
  `move-disk` is 501-not-implemented. See `headless-guest-provisioning-api-only.md` for why
  console automation also fails.
- **Working path: node SSH + `qm importdisk`.** From the Hermes box: paramiko with
  `~/.miam_root_pass` (plain-password auth works; `ssh -o BatchMode=yes` does NOT — no agent
  key is authorized on the nodes). Sequence:

```python
# 1. create empty VM shell via API (vmid, name, cores, memory, net0, scsihw, agent, serial0, vga, boot, onboot, tags, description)
# 2. via node SSH:
qm importdisk <vmid> /var/lib/vz/template/iso/<image>.img local-lvm --format raw
qm set <vmid> --scsi0 local-lvm:vm-<vmid>-disk-0,discard=on,ssd=1
qm resize <vmid> scsi0 <target-size>G     # cloud images ship ~3G; resize to parity with prod
qm set <vmid> --ide2 local-lvm:cloudinit  # creates vm-<vmid>-cloudinit LV
# write pubkey to a node temp file, then:
qm set <vmid> --ciuser <user> --sshkeys /tmp/keys --ipconfig0 ip=<ip>/24,gw=<gw> --nameserver <dns>
qm start <vmid>
```

## Cloud-init credential gotcha (genericcloud images)

- **`--sshkeys` alone was NOT sufficient on Debian 12 genericcloud** — ssh-key auth kept
  failing after boot (AuthenticationException from paramiko; the key fingerprint matched).
  Fix: also set `qm set <vmid> --cipassword '<password>'`, then `qm stop` + `qm start`
  (regenerates the cloud-init ISO) — after that BOTH password and key auth work.
- Don't burn >2 min on key-only debugging: add cipassword + reboot, then verify.
- Verify readiness: TCP :22 probe loop, then paramiko connect, then `cloud-init status` = done.

## Sizing/VMID/IP conventions used

- VMID: enumerate `/cluster/resources` for ALL guests cluster-wide (VMIDs are global);
  next free after the prod guest (154 → staging 156; 155 left as buffer).
- IP: static, low band, outside Jordan's `.190-.250` pool; check the corosync map +
  ping sweep per `references/network-ip-collision-audit.md`.
- Tags: `staging;<product>`; description marks it STAGING / not-production.
- `onboot=0` for staging (starts on demand); production VMs onboot=1.

## Staging bootstrap for an app (PDU Manager example)

1. Build release artifact on the workstation: `./deploy/build-release.sh <sha>` → `.tar.gz` + `.sha256`.
2. paramiko/SFTP upload artifact + checksum + deploy tree to the staging VM.
3. `sudo PDU_STAGING=1 bash deploy/install.sh <artifact>` — mock PDU backend, throwaway secrets, TLS self-signed, nginx + nftables.
4. Exercise action paths against the MOCK backend only; run `deploy/healthcheck.sh ... full`.
5. Rollback drill: deploy an intentionally-broken artifact, watch auto-rollback fire, verify health restored.