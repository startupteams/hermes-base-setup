# PVE Guest/VM Remote Operations (headless, no web console)

Session-proven recipes for driving PVE VMs/MIAM nodes when the only access is a LAN
Hermes host + password SSH, and there is no DHCP and no outbound internet on the
Proxmox hosts themselves.

## SSH without sshpass (pexpect) — password AND ed25519 key

`sshpass` may not be installed and `sudo` may need a password you don't have. Use a
user-level venv + pexpect instead:

```bash
python3 -m venv ~/ssh-venv
~/ssh-venv/bin/pip install pexpect
```

Helper pattern (host + password, and a sibling key-based one for VMs):

```python
import pexpect
child = pexpect.spawn('/usr/bin/ssh', ['-o','StrictHostKeyChecking=no',
    '-o','UserKnownHostsFile=/dev/null','-l',user,host,cmd], encoding='utf-8', timeout=t)
idx = child.expect([r'[Pp]assword'], timeout=40)      # handle 'yes/no' first if it appears
child.sendline(password)
child.expect(pexpect.EOF, timeout=timeout)            # then drain; collect child.before
```

Key-based variant drops the password step entirely (reliable once a key is injected).

### PITFALL: pexpect pattern-false-positive "AUTH REJECTED"
Do NOT treat a `[Pp]assword` match AFTER you've already sent the password as an auth
rejection. `qm config` output contains a literal `cipassword: *******` line, and a
scripted VM login loop prints `Password:`. Both will false-match the password pattern and
make the helper wrongly report auth failure while the command actually succeeded.
Only treat it as a real failure if you see `Permission denied`. Fix: after sending the
password, expect only `[EOF, TIMEOUT]` and check `'Permission denied' in first`.

### PITFALL: pexpect child.before empty/truncated on long batched output
A single `expect(EOF)` followed by one `child.before` read can return EMPTY (pattern
matched at buffer start) or silently lose most output — this cost a whole session of
"empty result" debugging before the cause was found. Drain pattern (proven):
loop `expect([r'[Pp]assword:', pexpect.EOF, pexpect.TIMEOUT])` until EOF, appending
`child.before` to a list on EVERY iteration, then `"".join(pieces)`. Keep the password
pattern inside the loop so late prompts still match. Ready-made implementation:
`scripts/ssh_run.py` in the parent skill.

### PITFALL: host SSH rate-limits rapid reconnects
Repeated quick SSH connections get intermittent "auth rejected". Pace calls (cooldown
between attempts) and batch as many `qm`/remote commands into ONE ssh call as possible
(single base64'd script executed once) instead of many tiny calls.

## Transferring a large binary to an offline Proxmox host

- Proxmox hosts in this fleet have NO outbound internet (gateway reachable, external
  HTTP/HTTPS fail) even though VMs routed through the same vmbr0 DO. Do not assume a
  host can reach an ISO/CDN.
- Path: download the image on the LAN Hermes host (which has internet), serve it with
  `python3 -m http.server 8088`, then `curl` it inside the Proxmox host over the LAN.
- pexpect-scp with `encoding='utf-8'` CORRUPTS binary files (leaves a tiny wrong file).
  Either run scp in binary mode (no encoding) or, more reliably, use the HTTP pull path.
- Use a generous timeout on the SSH helper (large files take minutes); set the pexpect
  timeout high enough that the transfer is NOT torn down mid-flight.

### PITFALL: injecting a script INTO a guest via a long base64 arg breaks the shell
`qm guest exec <vmid> -- bash -lc "echo <LONG_BASE64> | base64 -d > /tmp/x.py"` is fragile
for any payload > a few chars: the long token gets captured as another positional arg (the
sh -c/payload and even the SSH helper's timeout slot swap places → `ValueError: invalid
literal for int()`), and embedded heredocs/nested quotes (`<<PY`, `\"` escapes) throw
`unexpected EOF` / `syntax error` under the double-wrapped `bash -lc`. Don't fight it —
two-step it:
1. Land the base64 on the **HOST** disk first, over host SSH, writing to /tmp (avoid the
   shell-arg path entirely if it still mis-splits, e.g. `cp /dev/stdin /tmp/f.b64 <<< "$B64"`).
2. Then run a **short** `qm guest exec <vmid> -- bash -lc "base64 -d /tmp/f.b64 > /tmp/x.py"`.
For files that don't already exist in the guest, this host-land-then-decode detour is far
more reliable than inlining the payload through the `qm guest exec` argument string.

## Reading a VM console without the GUI or guest agent

When a VM has no qemu-guest-agent yet and/or no SSH, attach to its serial console
directly from the PVE host:

- The serial socket is `/var/run/qemu-server/<vmid>.serial0`.
- Use `socat - UNIX-CONNECT:/var/run/qemu-server/<vmid>.serial0` under a `pty.fork()`
  (stdlib — no pexpect needed on the PVE host) to log in interactively and run commands
  even before the guest network/agent are up.

This is the only way to see cloud-init progress / login-screen state on a headless VM.

## cloud-init on the Ubuntu noble image applies network ONLY on first boot

This is the biggest trap when reproducively building VMs.
- `qm set <vmid> --ipconfig0 ... --ciuser ... --cipassword ... --sshkeys ...` only take
  effect on the FIRST power-on that runs cloud-init.
- If you boot the VM once, then go back and add the IP/creds and `qm reboot`, the noble
  image does NOT re-read them — you get a VM with neither a usable IP nor (potentially)
  the password applied, because cloud-init already ran its first-boot phase without them.
- Correct recipe: bake ALL cloud-init config BEFORE `qm start`. Scaffold with
  `qm create` -> `qm importdisk` -> `qm set --scsi0 ... --efidisk0 ... --ide2 ...cloudinit`
  -> set `ipconfig0/ciuser/cipassword/sshkeys/boot` -> then start. Recreate (stop, purge,
  rebuild) rather than trying to patch a partially-booted instance.
- If `--cicustom` ran a `package_update` phase that leaves a stale concrete
  `apt-get` holding `/var/lib/apt/lists/lock` in the guest, the guest agent install will
  block with "Unable to lock directory". Wait for cloud-init to release, then run install.

### Finding a VM's unknown DHCP address from the PVE host

The bridge knows it. Take the MAC from `qm config <vmid>` (`net0: virtio=BC:24:...`):

    ip neigh show | grep -i <mac>      # lladdr <mac> -> 10.0.20.207
    bridge fdb show | grep -i <mac>

Combine with a parallel /24 ping sweep for the live-host list:

    rm -f /tmp/ipsweep; touch /tmp/ipsweep
    for i in $(seq 2 254); do ( ping -c1 -W1 10.0.20.$i >/dev/null 2>&1 && echo $i >>/tmp/ipsweep ) & done; wait

**IP-assignment audit (Jordan-mandated before ANY static assignment):** (1) grep
`ipconfig|net0` across `/etc/pve/qemu-server/` + `/etc/pve/lxc/` (cluster-shared) and
repeat per remote node via SSH; (2) ARP/FDB tables; (3) the ping sweep; (4) PDM
`resources/list` for cluster-wide guest inventory. Absence from ALL four is the "unused"
signal; any contradiction aborts — never assign on a single-probe pass.

### qm guest exec output + installing services into a guest with no SSH

`qm guest exec` returns JSON (`out-data` carries escaped newlines); parse with
`python3 -c "import sys,json; print(json.load(sys.stdin).get('out-data',''))"`.
Heredocs DO work inside the guest command when spawned via SSH argv list:
`qm guest exec <vmid> -- bash -lc 'cat > /etc/systemd/system/svc.service <<EOF ... EOF; systemctl daemon-reload && systemctl enable --now svc'`.
When a service is down and undocumented, mine `/root/.bash_history` and `/home/*/.bash_history`
for the battle-tested command line (env exports + full flag set) and promote it to a systemd
unit (`Restart=on-failure`, `TimeoutStartSec` sized for model load) — session-proven reviving
vLLM on VM103 from its history instead of guessing flags.

### PVE API /agent/exec specifics (python urllib client, session-proven 2026-09-13)

When driving the PVE API directly from Python (urllib + ticket auth), four contract
details cost a debugging cycle each — encode them once:

- **GET parameters go in the QUERYSTRING, never a form body.** A POST-style body on a
  GET request is silently ignored, so `exec-status?pid=` polls never resolve (the poll
  loop just times out). Only non-GET methods take urlencoded bodies.
- **Array params repeat the plain key**: `command=bash&command=-lc&command=<cmd>` —
  NOT `command[]=` (JSON-string form). Sending the whole argv as a JSON string fails
  parameter verification.
- **`timeout` is NOT an accepted `/agent/exec` parameter** — including it 400s with
  `property is not defined in schema`. Launch returns a PID; poll
  `GET .../agent/exec-status?pid=<pid>` (2s interval) until `exited: true`.
- **`/agent/exec` returns `{"data": {"pid": N}}` (a dict)** — unwrapping `data` as the
  pid itself puts a dict repr in the status URL and dies with
  `InvalidURL: URL can't contain control characters`. Take `data['pid']`.
- **LXC exec is NOT implemented on this PVE build** (`POST /nodes/<n>/lxc/<id>/exec`
  → 501 not implemented). For containers, install a client (e.g. postgresql-client)
  on a reachable VM and work remotely, or use node-side `pct exec` over SSH.
- Exec responses can be large; when pulling files out of a guest, `base64 -w0` the
  file inside the guest and decode locally (keep chunk sizes under arg limits).

### Re-run WITHOUT recreating: bump the cloud-init instance-id (session-proven 2026-09)
When a first boot half-applied (VM up, hostname set, but sshd/packages never installed),
you do NOT need to destroy/rebuild the disk:
1. Fix the user snippet (`/var/lib/vz/snippets/<name>.yaml`) — add users/ssh_authorized_keys/packages.
2. Bump `instance-id` in the meta snippet (e.g. `llm-manager-114-bootstrap-v2` → `-v3`).
   This alone forces cloud-init per-instance modules to re-run.
3. `qm set <vmid> --ipconfig0 ip=<static>/24,gw=<gw>` (only if the IP must change).
4. `qm stop <vmid> && qm start <vmid>` — the start regenerates the cloud-init ISO.
5. Poll readiness: loop `timeout 2 bash -c 'echo > /dev/tcp/<ip>/22'` AND
   `qm agent <vmid> ping`; both YES = ready (can be <60s with cached packages).
6. Verify inside: `cloud-init status --long` (expect `status: done`, `errors: []`),
   `systemctl is-active ssh qemu-guest-agent nginx`, `ip -br a` shows the static IP.

Real case: a VM whose user snippet had `disable_root: true` + `ssh_pwauth: false` but
a valid `ubuntu` user with an RSA key baked in — the keypair lived on the Proxmox node
(`root@miam-00135`), so node-side `ssh ubuntu@<ip>` works even before agent-based
access; re-bootstrap added a second (Hermes container) key for direct management.

## Static IPs: verify DHCP before asserting (corrected 2026-09)
The earlier claim "vmbr0 has NO DHCP" is outdated for this fleet: a DHCP server IS
present on the vmbr0 /24 (a cloud-init `ip=dhcp` VM leased 10.0.20.207; Hermes LXCs
all run `ip=dhcp`). Infrastructure roles should still get STATIC IPs via cloud-init
so identities never drift. Before assigning any address, prove it unused:
`qm list`/`pct list` per node, `pvesh get /cluster/nextid`,
`grep -rE '10\.0\.20\.[0-9]+' /etc/pve/qemu-server/ /etc/pve/lxc/`, `ip neigh show`,
and a parallel /24 ping sweep. A failed probe alone does NOT prove unused. Map a
running guest's IP read-only via `qm guest cmd <vmid> network-get-interfaces`.

### Deploying scripts INTO a guest: node-side scp hop (session-proven 2026-09)

When the Hermes container holds the only working guest key but the guest only accepts
keys held on the Proxmox node, deploy in one SSH call to the node:

```
ssh root@<node> "bash -c 'echo <B64> | base64 -d > /tmp/deploy.sh &&
  scp -o StrictHostKeyChecking=no /tmp/deploy.sh ubuntu@<guest-ip>:/tmp/deploy.sh &&
  ssh -o StrictHostKeyChecking=no ubuntu@<guest-ip> \"sudo bash /tmp/deploy.sh\"'"
```

The guest user (cloud-init `ubuntu` + NOPASSWD sudo) runs the script as root. `scp`
node→guest works because the node holds the baked-in key. Avoid `pct push` for QEMU VMs
(it is LXC-only; "can only push files to a running CT" also fires if run on the wrong node).