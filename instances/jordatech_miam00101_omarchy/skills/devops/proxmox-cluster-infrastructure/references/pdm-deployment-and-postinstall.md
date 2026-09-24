# PDM deployment and post-install reference

Session-derived reference for Proxmox VE + Proxmox Datacenter Manager work. Keep credentials out of this file; use only credentials supplied in the current session.

## PVE auth and realm discovery

- Realm discovery endpoint: `GET https://<pve-host>:8006/api2/json/access/domains`.
- LLDAP realm was exposed as `LLDAP-Domain`; login form was `user@LLDAP-Domain`.
- Successful PVE login returns `ticket`, `CSRFPreventionToken`, `cap`, and `username`.
- Use `PVEAuthCookie` for API requests and CSRF header for mutating requests.

## Useful PVE API endpoints used

- `GET /api2/json/version`
- `GET /api2/json/nodes`
- `GET /api2/json/cluster/resources`
- `GET /api2/json/nodes/{node}/status`
- `GET /api2/json/nodes/{node}/lxc`
- `GET /api2/json/nodes/{node}/qemu`
- `GET /api2/json/nodes/{node}/storage`
- `GET /api2/json/nodes/{node}/storage/{storage}/content`
- `POST /api2/json/nodes/{node}/storage/{storage}/upload`
- `POST /api2/json/nodes/{node}/lxc`
- `POST /api2/json/nodes/{node}/lxc/{vmid}/status/stop`
- `DELETE /api2/json/nodes/{node}/lxc/{vmid}?purge=1&destroy-unreferenced-disks=1`
- `GET /api2/json/nodes/{tasknode}/tasks/{urlencoded-upid}/status`
- `GET /api2/json/nodes/{tasknode}/tasks/{urlencoded-upid}/log`

## PDM setup notes

- Community script page: `https://community-scripts.org/scripts/proxmox-datacenter-manager`.
- Raw CT installer observed: `https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/proxmox-datacenter-manager.sh`.
- Raw install script installs:
  - `proxmox-datacenter-manager`
  - `proxmox-datacenter-manager-ui`
  - `proxmox-mail-forward`
  - `proxmox-offline-mirror-helper`
- It uses Debian 13 / trixie and PDM no-subscription repository.
- PDM UI is reachable on `https://<pdm-ip>:8443/`.

## PDM LLDAP verification endpoints

- `GET /api2/json/access/domains`
- `POST /api2/json/access/domains/LLDAP-Domain/sync`
- `GET /api2/json/nodes/{pdm-node}/tasks/{urlencoded-upid}/status`
- `GET /api2/json/nodes/{pdm-node}/tasks/{urlencoded-upid}/log`
- `GET /api2/json/access/users`
- `GET /api2/json/access/acl`
- `GET /api2/json/access/permissions`

If users can authenticate but cannot see dashboard/settings, verify both ACL and resource state. An Administrator ACL at `/` should expose privileges on `/`, `/access`, `/resource`, and `/system`. PDM will still look empty if no remotes/resources are configured.

## Adding PVE cluster to PDM

PDM API tree:

- Root: `/api2/json/` lists `access`, `auto-install`, `ceph`, `config`, `nodes`, `pbs`, `ping`, `pve`, `remotes`, `resources`, `sdn`, `subscriptions`, `version`.
- Remote list/add endpoint: `GET/POST /api2/json/remotes/remote`.
- PVE helper endpoints:
  - `POST /api2/json/pve/probe-tls`
  - `GET /api2/json/pve/realms?hostname=<host>:8006&fingerprint=<fp>`
  - `POST /api2/json/pve/scan`

Observed add flow:

1. Probe TLS for a PVE node and accept/store fingerprint.
2. Scan with `hostname`, `fingerprint`, `authid`, and `token` to discover all cluster nodes and fingerprints.
3. Add JSON to `/remotes/remote`:

```json
{
  "id": "miam-pve",
  "type": "pve",
  "nodes": ["10.0.20.x,fingerprint=AA:BB:..."],
  "authid": "user@realm",
  "token": "<current secret or token>",
  "web-url": "https://<primary-pve-host>:8006/",
  "create-token": "pdm-miam-pve"
}
```

If `create-token` succeeds, PDM stores a generated token and subsequent `GET /remotes/remote` redacts `token` as an empty string.

Verify remote health with:

- `GET /api2/json/remotes/remote/{id}/version`
- `GET /api2/json/resources/status`
- `GET /api2/json/resources/list`

A remote can be healthy while warning about offline nodes in the PVE cluster.

## PDM root password API

- Read root user: `GET /api2/json/access/users/root%40pam`.
- Update password: `PUT /api2/json/access/users/root%40pam` with `password=<new-password>`.
- Verify by authenticating with the new password and confirming the old password fails.

## PDM post-install / subscription popup removal

Community page: `https://community-scripts.org/scripts/post-pdm-install`.
Raw script observed: `https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/tools/pve/post-pdm-install.sh`.

The PDM UI is a Yew/WASM app. The no-subscription popup can be mitigated by appending the community script's runtime close hook to:

```text
/usr/share/javascript/proxmox-datacenter-manager/js/pdm-ui_bundle.js
```

The hook includes marker `PDM_NO_MORE_NAGGING` and looks for dialogs containing `pdm.proxmox.com`, then calls `d.close()` so the dialog's close callback runs instead of breaking refresh flow.

Persistence files:

```text
/usr/local/bin/pdm-remove-nag.sh
/etc/apt/apt.conf.d/no-nag-script
```

Verify after patch:

- `GET https://<pdm-ip>:8443/` returns 200.
- `GET https://<pdm-ip>:8443/js/pdm-ui_bundle.js` returns 200 and contains:
  - `PDM_NO_MORE_NAGGING`
  - `MutationObserver`
  - `pdm.proxmox.com`
  - `d.close()`
- `GET /api2/json/version` still works.
- `GET /api2/json/resources/status` still works.

Tell the user to hard-refresh (`Ctrl+Shift+R`) because browsers may cache the old JS bundle.

## Proxmox xterm.js console pattern

If direct SSH fails but Proxmox console access is allowed:

1. POST `.../termproxy` for a node/CT shell.
2. Open `wss://<pve-host>:8006/api2/json/.../vncwebsocket?port=<port>&vncticket=<encoded-ticket>` with subprotocol `binary` and `PVEAuthCookie`.
3. Send initial auth line: `<termproxy-user>:<termproxy-ticket>\n`.
4. Wait for `OK`, then interact with the shell using termproxy frames: `0:<len>:<data>`.

This is useful for emergency root shell access to an LXC when SSH password login is unavailable, but prefer regular SSH or API actions when possible.

## PDM API login quirks (session-proven 2026-09)

- Login payload on PDM does NOT have a `data.ticket` string: keys are `CSRFPreventionToken` and `ticket-info` (`PDM:<user>:...`). With `curl`, just save the response with `-c cookiejar` — the `__Host-PDMAuthCookie` is set as an HttpOnly cookie and sent automatically on subsequent `-b cookiejar` calls. Hand-extracting the ticket is unnecessary and error-prone (and in Python `data` may arrive as a JSON-encoded string needing `json.loads` twice).
- Working usernames observed: `jordatech@LLDAP-Domain` and `root@pam` (fleet-shared password). `root@LLDAP-Domain` is NOT valid.
- `GET /api2/json/resources/list` returns `{"data":[ {"remote":"<id>", "resources":[ ... ]} ]}` — the guest inventory is nested one level under `resources`, each entry has `node`, `vmid`, `type` (pve-qemu/pve-lxc/pve-node/pve-storage), `status`, `name`. This is the fastest whole-cluster inventory (all 16 nodes, every guest) without SSHing each node.
- Fleet node-name inconsistency matters for grep/parse: nodes with dash `miam-00100…miam-00149`, GPU nodes without `miam00111/miam00112/miam00143/miam00144`.