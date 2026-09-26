# Headless guest provisioning on PVE 9 via API only (2026-09-26, ACMS CT122 deployment)

Deploying a new guest when you have ONLY the PVE API (no SSH to the node, no GUI console).
Full session context: ACMS first live deployment on MIAM-00135.

## The console-automation dead end (do not burn hours here)

Driving an OS installer or cloud-image first boot through the PVE API console DOES NOT WORK
on this stack. All three paths were exhausted in one session:

1. **CT termproxy + vncwebsocket** (`POST /nodes/<n>/lxc/<id>/termproxy` → GET
   `/nodes/<n>/lxc/<id>/vncwebsocket?port=..&vncticket=..` over WSS on :8006 via the API
   host with `Sec-WebSocket-Protocol: binary` + `PVEAuthCookie`): upgrade succeeds and ws
   PING/PONG works, but the stream is permanently SILENT — no login prompt, no boot text,
   no reaction to any frame type (text/binary, with/without the `user\0`+ticket auth
   frames). Fresh Ubuntu CTs have no active getty to attach.
2. **VM vncproxy** (`POST /nodes/<n>/qemu/<id>/vncproxy {websocket:1}`): full RFB handshake
   IS scriptable — server sends `RFB 003.008\n`, security types `[2]` (VNC auth), and the
   one-time password comes back in the vncproxy response (`data.password`, 8 chars).
   Challenge-response = DES-ECB with the password as key, **each key byte bit-reversed**
   (`int(f'{b:08b}'[::-1],2)`), via `cryptography` TripleDES. Auth returns `00000000` = OK,
   ClientInit/ServerInit succeed (framebuffer size + name `VNC Command Terminal`).
   **Then it breaks**: ANY SetEncodings message (raw, or PVE custom -312/-313) makes the
   server close the connection (BrokenPipe). The PVE terminal is a proprietary
   keyboard/resize protocol, not standard RFB — raw clients cannot drive it.
3. **Node termproxy shell**: termproxy returns port 5900 but direct TCP to node:5900 is
   refused (pveproxy only listens 8006); the websocket route is the only path and it is the
   same silent one.

**Conclusion: treat API-only console automation as unavailable. Budget zero time on it in
future sessions; go straight to the working path below.**

## The working path: LXC with credentials at create + SSH

LXC creation accepts everything needed for hands-off access in ONE API call:

```
POST /nodes/<node>/lxc {
  vmid, hostname, ostemplate: local:vztmpl/ubuntu-24.04-standard_...tar.zst,
  cores, memory, swap, rootfs: local-lvm:40,
  net0: name=eth0,bridge=vmbr0,ip=10.0.20.X/24,gw=10.0.20.1,firewall=0,   # static IP at create
  unprivileged: 1, features: nesting=1,keyctl=1,     # keyctl needs root@pam API user
  onboot: 1, startup: order=N, start: 1,
  ssh-public-keys: "<one-line pubkey>"                # ← the unlock
}
```

The Ubuntu template ships sshd RUNNING (unlike the VM cloud image) — after create+start,
`ssh root@<ip>` works immediately with your own key. Get the IP from
`GET /nodes/<node>/lxc/<id>/interfaces` (`[{name, inet, hwaddr}]`).

Gotchas:
- **`start:1` at create means the separate start call 500s with "already running"** — handle it.
- **Stale ARP after destroy/recreate with the same IP**: workstation ARP cache keeps the OLD
  guest's MAC → ping fails/timeout even though the new CT is fine. `ip neigh del <ip> dev eth0`
  and re-probe TCP :22 directly.
- **Host key changed** after destroy/recreate on the same IP: `ssh-keygen -R <ip>` first.
- **VMID freeness must be verified CLUSTER-WIDE at create time** — a full `find_vm()` sweep
  still missed VMID 121 (existed on another node; the sweep raced). The create call itself
  is the authority: a 500 "VM <id> already exists on node X" costs nothing. Pick the next
  free ID and retry; don't over-engineer pre-checks.
- Unprivileged CT + `features: keyctl=1` requires the root@pam API user (fine — the bot
  ticket path already is root@pam).

## Internet exists on nodes (use download-url, don't relay ISOs)

`POST /nodes/<node>/storage/local/download-url` with ONLY `{url, content, filename}` (passing
`null` values for size/checksum → 400 Parameter verification failed) downloads DIRECTLY on the
node — miam-00135 pulled a 3.4 GB Ubuntu ISO in ~2 min. No internet on the workstation is
irrelevant; no cross-node ISO copying needed. Verify completion by polling the task UPID and
listing `/storage/local/content?content=iso`.

## Uploading files (seed ISOs etc.) via API multipart

`POST /api2/json/nodes/<node>/storage/local/upload` with multipart form: field `content=iso`
+ file field `filename`. Build the multipart body manually (uuid boundary, urlencode
disposition) — requests' files= works too. The task lands as `imgcopy` on the API-host node;
poll it there. Uploaded small ISOs appear in `local:iso/<name>`.

## Cloud-init NoCloud seed ISO with pycdlib (when a cloud image is the only option)

```
iso = pycdlib.PyCdlib()
iso.new(interchange_level=3, joliet=True, rock_ridge='1.09', vol_ident='cidata')
# keep tempfiles ALIVE until after iso.write() (pycdlib re-reads them at write time)
fd, tmp = tempfile.mkstemp(); write; iso.add_file(tmp, rr_name='user-data', joliet_path='/user-data')
```
Interchange level 1 rejects names >8 chars ("user-data" fails) — level 3 + Rock Ridge is
required. Volume label MUST be `cidata`. Content: `user-data` (#cloud-config), `meta-data`
(instance-id, local-hostname), `network-config` (v2 ethernets with static addresses).

Even with a correct seed, attaching a cloud image as a VM disk via pure API FAILS: path-based
`scsiN: /var/lib/vz/...` gets auto-remapped to `media=cdrom` when the file sits under a known
storage path, and `/storage/<t>/import` returns 501 on dir/lvmthin (no `import` content type).
A privileged helper CT with `dev0: /dev/pve/vm-<id>-disk-0` + `mp0` for the source dir can
`qemu-img convert` into the LV — but ONLY if you can exec into it (see console dead end).
This is exactly why the LXC+SSH path wins: skip cloud images entirely unless the image is
mandatory.

## DNS reality on MARION (2026-09-26)

There is NO DNS resolution for `home.arpa` names anywhere — unbound on 10.0.20.1 carries no
local overrides, no other service resolves such names, and the established convention is RAW
IP access. A `/etc/hosts` entry on the new guest plus operator workstations is the interim
pattern; an OPNsense unbound override (needs OPNsense API key) is the proper fix. Don't plan
around `*.miam.home.arpa` resolving.

## Post-provision smoke checklist (all API/SSH, no console)

- containers/services: `docker compose ps` over SSH (or qga exec for VMs)
- migrations applied: query `alembic_version` / service version endpoint
- reboot persistence: reboot the CT/VM via API, poll status, verify services auto-return
  (`restart: unless-stopped` + `onboot:1`) and DATA survived (row counts, not just "up")
- PBS coverage: guest is in the all-guests backup job (check `exclude` list), plus one manual
  `POST /nodes/<n>/vzdump {vmid, storage: pbs-marion, mode: snapshot, compress: zstd}` and
  verify the snapshot volid appears in `/storage/pbs-marion/content?content=backup`
