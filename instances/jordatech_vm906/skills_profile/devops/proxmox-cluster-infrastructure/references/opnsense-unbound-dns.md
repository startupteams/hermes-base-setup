# OPNsense DNS bring-up via scripted web/API access (unbound host overrides)

Session-verified recipe (2026-09) for creating DNS records on a MARION-lab OPNsense
firewall when no SSH access or API-key auth is available. All steps use plain Python
stdlib (urllib + http.cookiejar) — no curl CSRF gymnastics required.

## Topology facts (verify per environment, but expect this shape)

- **Web UI / REST API: `http://10.0.10.1`** — plain HTTP, NOT HTTPS (TLS :443 refused).
  The LAN-side DNS address `10.0.20.1` serves :53 only; it is NOT the web UI address.
- SSH :22 closed; basic-auth REST login (`-u root:<UI-password>`) returns **401** —
  OPNsense REST API requires generated API keys (System→Access→API), not the web login.
  The path that works: UI session login + session-authenticated API calls (below).
- Firewall hostnames seen: dashboard title `OPNsense.home.arpa`. Interfaces: `lan`
  (LANJetKVM), `opt1` (2p5GSwitch), `opt2` (ISOLATED30), `wan` (WAN).

## Auth chain (3 traps, in order)

1. **UI login POST** (`/index.php`) needs FOUR things: the hidden randomized-CSRF field
   (field NAME is random per load, e.g. `ktqFJ3L9NBFOo-...` — parse all
   `<input type="hidden">` tags and replay them), `usernamefld`, `passwordfld`, and the
   **submit button field `login=1`**. Omitting `login:1` makes OPNsense silently re-render
   the login page (len ~2.8 KB) — the classic silent-fail symptom.
2. **Success check:** follow-up GET of `/index.php` returns the Dashboard (title
   `Dashboard | Lobby | OPNsense.home.arpa`, len >100 KB). Session cookie auto-persists
   via the cookie jar.
3. **MVC API writes need the X-CSRFToken header.** It is NOT in a meta tag or hidden
   input — it's embedded in the page's JS:
   `xhr.setRequestHeader("X-CSRFToken", "<token>")` in the `$.ajaxSetup` block of any
   `/ui/...` page (fetch `/ui/unbound/general` or `/ui/unbound/overrides` and regex it
   out: `r'setRequestHeader\("X-CSRFToken",\s*"([^"]+)"'`).

## Unbound pages moved to MVC (classic .php pages 404)

`/services_unbound.php` and `/services_unbound_host_overrides.php` are gone; the menu
hrefs are `/ui/unbound/general`, `/ui/unbound/overrides`, etc. The backing REST endpoints
( discoverable via `grep -oE "/api/unbound/[a-z/]*" <overrides page html>` ):

- `GET  /api/unbound/settings/get` — full config model
- `POST /api/unbound/settings/set` — save (see delta rule below)
- `GET  /api/unbound/settings/searchHostOverride` — list host overrides
- `POST /api/unbound/settings/addHostOverride` — body `{"host":{hostname,domain,rrtype:"A",server,description}}` → returns `{"result":"saved","uuid":...}`
- `POST /api/unbound/service/reconfigure` — body `{}` → `{"status":"ok"}`; this ACTIVATES saved changes

All of these work with just the session cookie + `X-CSRFToken` header after UI login.

## Payload shape rules (500 "Unexpected error" avoidance)

- **Post minimal deltas.** `{"unbound":{"general":{"enabled":"1"}}}` saves; posting the
  full round-tripped GET object, partial objects with interface sub-dicts, boolean maps,
  or `active_interface` as arrays all 500 (model applies `set` field-wise; unknown/extra
  shapes are fatal, not ignored).
- Multi-select fields in the GET model look like `{"opt1":{"value":"2p5GSwitch","selected":0},...}`
  or `[{"value":"Level 1","selected":1},...]`. Do NOT try to reproduce that shape in
  writes — empty/omitted multiselects mean "all (recommended)".
- To listen on ALL internal interfaces (default, usually right), just enabling is enough.

## The gotcha that cost hours: unbound installed but DISABLED

Symptoms: port 53 times out from every LAN vantage point; everyone silently falls back to
public resolvers (CT/VM resolv.conf pointing at 1.1.1.1/8.8.8.8); override config exists
but never answers. Diagnosis: `POST /api/core/service/search` → service list shows no
`unbound` running (kea-dhcp, pf, etc. present). Check
`GET /api/unbound/settings/get` → `unbound.general.enabled` was `"0"`. Fix:
`POST /api/unbound/settings/set {"unbound":{"general":{"enabled":"1"}}}` + reconfigure.

## Client-side follow-through

LXCs/VMs that hardcode public resolvers (PVE default template writes
`nameserver 1.1.1.1`) bypass the firewall DNS entirely — override records won't resolve
there. For systemd-resolved guests (Ubuntu):
```
/etc/systemd/resolved.conf.d/firewall.conf:
[Resolve]
DNS=10.0.20.1
Domains=<internal domain>
```
then `systemctl restart systemd-resolved`, verify `getent hosts <name>`.

## Pitfalls

- `nslookup <name> 10.0.20.1` from a CT whose own resolv.conf points at 1.1.1.1 can time
  out if egress/ACLs block UDP :53 cross-vlan — test DNS reachability from multiple
  vantage points (management CT, the target VM, a node) before blaming the override.
- The `.internal` TLD is deliberately not resolvable upstream — only unbound serves it;
  every client that matters must use 10.0.20.1 as its resolver.
- Don't store the firewall password in scripts — read from the profile credential file at
  runtime and regex it out locally (same pattern as `scripts/ssh_run.py`).
