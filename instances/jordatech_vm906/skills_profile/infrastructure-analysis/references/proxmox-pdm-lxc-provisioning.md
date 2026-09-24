# Proxmox Datacenter Manager LXC Provisioning Notes

Use this reference when asked to deploy Proxmox Datacenter Manager (PDM) inside a Proxmox cluster where GUI/API credentials are available but SSH/root shell may not be.

## Class of workflow

- Target: install PDM as an LXC on a specified Proxmox node.
- Access pattern: authenticate to the Proxmox VE API, discover node/storage/network state, create or update an LXC, then verify PDM's HTTPS/API endpoint.
- Security boundary: do not store passwords, tickets, CSRF tokens, or LDAP bind secrets in the skill. Use only credentials explicitly provided in the current session, redact them from logs, and avoid persisting them in support files.

## Useful PVE API sequence

1. Authenticate:
   - `POST /api2/json/access/ticket`
   - Include realm in username, e.g. `<user>@LLDAP-Domain` if `/access/domains` reports that exact realm.
2. Discover cluster and target node:
   - `GET /nodes`
   - `GET /cluster/resources`
   - `GET /nodes/<node>/status`
   - `GET /nodes/<node>/lxc`
   - `GET /nodes/<node>/qemu`
   - `GET /nodes/<node>/storage`
3. Inspect existing container network patterns:
   - `GET /nodes/<node>/lxc/<vmid>/config`
   - Look for bridge, gateway, CIDR, tags, and reserved IP conventions.
4. Upload custom templates if needed:
   - `POST /nodes/<node>/storage/<storage>/upload` with `content=vztmpl` and multipart file.
   - The upload task can run on a different node than the target; parse the UPID node segment and poll that node's task endpoint.
5. Create LXC:
   - `POST /nodes/<node>/lxc`
   - Typical params: `vmid`, `ostemplate`, `hostname`, `storage`, `rootfs`, `memory`, `swap`, `cores`, `unprivileged`, `features=nesting=1`, `net0`, `password`, `onboot`, `start`, `tags`, `description`.
6. Task polling:
   - UPIDs are node-scoped. Extract the node from `UPID:<node>:...` and poll `/nodes/<upid-node>/tasks/<urlencoded-upid>/status`.
   - Retrieve `/log` on failures.

## PDM community-script install mechanics

The community script wrapper currently delegates to:

- `ct/proxmox-datacenter-manager.sh`
- `install/proxmox-datacenter-manager-install.sh`

Core defaults observed:

- App: `Proxmox-Datacenter-Manager`
- CPU: `2`
- RAM: `2048`
- Disk: `10`
- OS: Debian `13`
- Unprivileged LXC: enabled
- Access URL pattern: `https://<container-ip>:8443`

The install payload adds the Proxmox PDM no-subscription repo, pins unneeded kernel/firmware packages away, and installs:

```bash
proxmox-datacenter-manager \
proxmox-datacenter-manager-ui \
proxmox-mail-forward \
proxmox-offline-mirror-helper
```

## API-only provisioning workaround

When SSH to the node is unavailable but PVE API permissions allow VM/LXC administration:

1. Download the base Debian LXC template locally.
2. Build a derived template that includes a first-boot systemd unit.
3. First-boot unit installs/configures PDM inside the container.
4. Upload the derived template to `local:vztmpl/...` via the Proxmox API.
5. Create and start the container from that template.
6. Poll TCP `8443`, then verify `GET https://<ip>:8443/` returns the PDM UI title.

This keeps host-level changes within supported Proxmox API operations and avoids needing root SSH to the node.

## LLDAP/PDM verification pattern

- PDM unauthenticated endpoints may expose `/access/domains`, but `/version` requires auth.
- PDM login response may put the actual cookie in `Set-Cookie` rather than a `ticket` JSON field; keep a `requests.Session()` so cookies persist.
- After configuring an LDAP realm, trigger sync with `POST /api2/json/access/domains/<realm>/sync` as `root@pam` or an authorized PDM admin.
- Confirm:
  - `/access/domains` includes the realm.
  - `/access/acl` contains expected user-to-role mappings.
  - `/access/domains/<realm>/sync` task exits `OK`.
  - A representative LDAP user can authenticate to PDM and call `/version`.

## Pitfalls

- **Realm strings are exact.** `@ldap` can fail while `@LLDAP-Domain` succeeds.
- **Do not infer SSH from GUI/API success.** Proxmox UI/API admin access does not imply SSH login works for the same account.
- **Feature flags are restricted.** Non-root Proxmox API users may be allowed `features=nesting=1` but blocked from `keyctl=1`; create with nesting only unless root explicitly authorizes extra flags.
- **DELETE params belong in the query string.** Some Proxmox API endpoints reject JSON/form bodies for DELETE with `Unexpected content`; pass `purge=1` and `destroy-unreferenced-disks=1` as query params.
- **UPID task node can differ from requested target.** Poll the node embedded in the UPID, not always the target node.
- **Avoid persisting secrets in templates.** If a first-boot script must use a temporary secret from the current task, scrub the generated artifact after the session or rebuild from secret-free templates for long-term reuse.
