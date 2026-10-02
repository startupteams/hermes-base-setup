# OPNsense session-auth access recipe (proven 2026-09-10 → 2026-09-29)

OPNsense lives at `http://10.0.10.1` (LAN mgmt IP; the 10.0.20.1 address is
DNS/DHCP on the LAN side). Web UI is HTTP-only, no SSH, no API keys — use a
browser-session login. **Root password = the node root password**
(`~/.miam_root_pass`); confirmed working 2026-09-29 (helper scripts' embedded
regexes read a `opnsense-root/...` line from an OLD profile MEMORY.md that no
longer exists — do not copy those helpers blindly, feed the password from
`~/.miam_root_pass`).

## Login (curl pattern)

```bash
JAR=/tmp/opn_cookies.txt
page=$(curl -s -c $JAR http://10.0.10.1/index.php)
# randomized-named hidden csrf field: name=XYZ value=TOKEN (attr before 'autocomplete')
hidden=$(echo "$page" | grep -oP 'name="\K[^"]+(?=" value="[^"]*" autocomplete)')
data="usernamefld=root&passwordfld=<PW>&login=1&$hidden=<token>"
curl -s -b $JAR -c $JAR --data "$data" http://10.0.10.1/index.php
# verify: GET /index.php -L contains 'logout' or 'Dashboard'
```

## Config.xml download (contains static maps + Kea reservations)

`diag_backup.php` uses the SAME randomized csrf field:

```bash
cfg=$(curl -s -b $JAR http://10.0.10.1/diag_backup.php)
tokname=$(echo "$cfg" | grep -oP 'name="\K[A-Za-z0-9_]{15,40}(?="\s+value="[^"]{10,80}")')
tokval=$(...)  # the 20-22 char value beside it
curl -s -b $JAR --data "$tokname=$tokval&download=Download+configuration" \
  http://10.0.10.1/diag_backup.php > /tmp/opnsense_config.xml
```

Parsing notes (2026-09-29 verified):
- Legacy `<dhcpd><opt1><staticmap>` entries exist for the PDUs (.151-.153).
- **Kea (the active DHCP server) stores reservations under
  `<OPNsense><Kea><...><reservations><reservation uuid=...>` with
  `<ip_address>/<hw_address>/<hostname>` children** — parse BOTH blocks or you
  miss the modern reservations (llm-manager .207, hermes-pilot .187, ct906
  .195, node .41/.42/.43/.44).
- The 10.0.20 DHCP pool is **.190–.250** — static IPs must be outside it
  (Jordan's rule; verified-free candidates then need ARP + PVE-config +
  netplan checks, since "no ping reply ≠ free": offline hosts keep their IP).

## Known-good API endpoints (session-auth, from 2026-09-09/10)

- Kea leases: `/api/kea/leases4/search/` (12+ leases). CSRF may be required on
  POST; the MVC write pattern needs `X-CSRFToken` from page JS and only
  minimal delta payloads save (`{"unbound":{"general":{"enabled":"1"}}}` —
  full-object posts 500).
- Unbound host overrides: created via the session API + reconfigure (see
  `~/llm-manager-work/opnsense_api_dns.py` for the full flow).

## IP-collision vetting checklist (the 2026-09-29 lesson)

When assigning/changing a guest static IP:
1. Kea reservations (config.xml, both legacy + Kea blocks).
2. ARP from ≥2 vantage points (workstation, CT122, VM114) + `ip neigh` MAC vs
   the guest's actual NIC MAC.
3. PVE guest config scan (`/cluster/resources` → per-VM `config` netX +
   `ipconfigX`) for the IP and for the MAC.
4. Guest netplan on the suspect + victim (template clones carry stale static
   IPs — VM108 held `.203` for weeks until it collided with acms-worker-001).
5. `ping -c1` silence is NOT evidence of free. Move the squatter, keep a
   netplan `.bak`, then verify the caller's ARP flips to the real MAC.
