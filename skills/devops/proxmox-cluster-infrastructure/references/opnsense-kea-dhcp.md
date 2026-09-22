# OPNsense Kea DHCP management via scripted MVC API (leases + static reservations)

Session-verified recipe (2026-09-10) for reading DHCP state and managing static
reservations on the MARION-lab OPNsense firewall. Extends `opnsense-unbound-dns.md` —
read that first for the auth chain (UI session login with hidden-CSRF replay +
`login=1`, then X-CSRFToken regexed from any `/ui/...` page's `$.ajaxSetup` JS).

## Access facts

- **UI credential: username `root` + the Proxmox node root password** (the same
  `~/.miam_root_pass` used for the nodes) — verified working 2026-09-10. LDAP password
  and username `admin` both fail.
- **Vantage point matters**: DHCP-pool guests (e.g. CT906 @ 10.0.20.19x) CANNOT reach
  `10.0.10.1:80` (timeout). A cluster node CAN (routes via `default via 10.0.20.1`).
  Run the session script on a Proxmox node, not from pool-range guests. Ports: 80 open,
  22 closed.
- One CSRF token from any /ui page authorizes all MVC API calls in the session.

## Kea endpoint map (discover module endpoints from the /ui page JS)

OPNsense MVC modules expose grid endpoints as `/api/<module>/<verb>_<grid_id>/`
(composed in page JS as `search: '/api/kea/dhcpv4/search_' + grid_id` etc.). To find
them: fetch the module's /ui page and regex `/api/<module>/[a-zA-Z0-9/_-]+` out of the
source. Verified endpoints:

- **Active leases**: `GET /api/kea/leases4/search/` →
  `{"total":N,"rows":[{"address","hwaddr","hostname","state"}]}`
- **Static reservations** (grid id `reservation`):
  - list: `GET /api/kea/dhcpv4/search_reservation/` → rows: `uuid, subnet (uuid),
    %subnet, ip_address, hw_address, hostname, description`
  - add: `POST /api/kea/dhcpv4/add_reservation/` body
    `{"reservation": {"subnet": "<subnet-uuid>", "ip_address": "10.0.20.x",
    "hw_address": "bc:24:11:xx", "hostname": "name", "description": "..."}}`
    → `{"result":"saved","uuid":...}`. Subnet uuid comes from an existing row.
  - CSV export: `GET /api/kea/dhcpv4/download_reservations` (semicolon-CSV, NOT JSON)
  - CSV import: `POST /api/kea/dhcpv4/upload_reservations` (multipart — returned
    `{"status":"failed"}` on first attempt; prefer the JSON add endpoint)
  - apply: `POST /api/kea/service/reconfigure` `{}` — **may return `{"status":"failed"}`
    even when the reservation persisted**; verify via `search_reservation/` and
    `/api/kea/service/status` (`"running"`) instead of trusting the reconfigure result.
- General model: `GET /api/kea/dhcpv4/get` → `{"dhcpv4": {"general", "lexpire", "ha"}}`
  (subnet/reservation detail is NOT here — use the grid endpoints).

## Static-IP assignment procedure (used for the Hermes pilot CT)

1. Enumerate claimed addresses IN THIS ORDER:
   a. `/etc/pve/corosync.conf` `ring0_addr` on any node — the DEFINITIVE bare-metal
      node map (includes powered-off nodes; a ping sweep missed offline MIAM-00110 @
      10.0.20.110 until Jordan corrected: "10.0.20.110 is definitely used").
   b. Kea leases (pool .190–.250) + Kea reservations (statics: .151-.153 PDUs, .207
      llm-manager, .187 hermes-pilot).
   c. Live ARP (`ip neigh` — only entries WITH an lladdr are claimants; a `FAILED`
      entry with no MAC is your own probe's negative cache, not a conflict) + ping/arping.
2. Pick the lowest free address OUTSIDE the DHCP pool; set the guest static (netplan for
   Ubuntu CTs; keep nameservers = 10.0.20.1).
3. **Add a Kea reservation for the guest MAC in the same pass** so DHCP can never lease
   the address to anyone else (`add_reservation` + verify + service check).
4. Re-verify the workload E2E from the new IP before reporting done (e.g. chat
   completion through the gateway).

Guest MAC for an LXC: `pct exec <ctid> -- ip link show eth0` (or read from the Kea
lease it currently holds).
