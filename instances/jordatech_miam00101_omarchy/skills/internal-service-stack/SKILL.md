---
name: internal-service-stack
description: "Use when deploying internal service portal stacks on MARION."
---

# Internal Service Stack (MARION)

Build one internal portal + monitoring + registry stack on a dedicated PVE VM. Reference
implementation lives on VM119 (`miam-service-dashboard`, 10.0.20.172); handoff doc also on
that VM at `/opt/miam-dashboard/`. Workflow rules first, pitfalls attached to their step.

## Network mode decisions (do these FIRST, they're the expensive ones)

- **Caddy MUST run with `network_mode: host`.** Docker's userland-proxy SNATs every
  inbound connection to a bridge gateway address, so a bridge-mode Caddy's `remote_ip`
  matcher never sees real client IPs — everyone gets 403 (or everyone passes).
- **Homarr must NOT run host-networked**: its internal Next.js server binds `*:3001` and
  collides with Uptime Kuma's 3001. Keep Homarr on the compose bridge with
  `ports: ["127.0.0.1:7575:7575"]` (loopback-only publish is fine because Caddy makes the
  upstream call itself; ACL matching happens on connections to Caddy, not upstreams).
- Uptime Kuma v2 can run host-networked on 3001.
- **nftables `flush ruleset` wipes Docker's iptables chains** — a subsequent compose
  up fails with `Failed to Setup IP tables ... No chain/target/match by that name`.
  Fix with ordering units: `nftables.service` `Before=docker.service`, and
  `docker.service` `After=nftables.service` (+ `ExecStartPost=/bin/sleep 2`), then
  `systemctl restart nftables && systemctl restart docker` and only then `compose up`.
- Enforce subnet ACL with a Caddy `remote_ip` matcher per site (10.0.10.0/24,
  10.0.20.0/24, 127.0.0.1 → proxy; else `respond 403`), plus nft drops for the direct
  application ports (7575/3001 from non-loopback) and the Tailscale CGNAT band
  (100.64.0.0/10). Do NOT publish app ports on LAN IPs.

## TLS / DNS

- `.home.arpa` is internal-only → Caddy internal CA is the default; certs are issued
  automatically once the site blocks exist. Root CA export for clients:
  `/opt/miam-dashboard/caddy/data/caddy/pki/authorities/local/root.crt`.
- OPNsense Unbound host overrides are created through the UI-session MVC API path (see
  the proxmox skill's OPNsense reference): addHostOverride + service/reconfigure.
  Verify resolution from BOTH subnet resolvers (10.0.10.1 and 10.0.20.1).
- Pin the VM's resolver to the firewall (`/etc/systemd/resolved.conf.d/`) or the names
  won't resolve from the VM itself.

## LLDAP integration facts (Marion)

- Base DN `dc=example,dc=com`; users at `ou=people,dc=example,dc=com`, uid attribute.
- Homarr LDAP env: AUTH_PROVIDERS=ldap, AUTH_LDAP_URI=ldap://<lldap>:3890 (no LDAPS on
  3890), AUTH_LDAP_BASE, AUTH_LDAP_BIND_DN, AUTH_LDAP_BIND_PASSWORD,
  AUTH_LDAP_USERNAME_ATTRIBUTE=uid, AUTH_LDAP_USER_MAIL_ATTRIBUTE=mail,
  AUTH_LDAP_USER_SEARCH_LOCATION=ou=people,...
- Create a dedicated bind user in `lldap_strict_readonly` and verify with an ldap3 bind
  + `(objectClass=person)` search before wiring Homarr.
- Verify scripted LDAP login via NextAuth: GET `/api/auth/csrf` for csrfToken → POST
  `/api/auth/callback/credentials` (form-encoded csrfToken/username/password/callbackUrl)
  with Referer/Origin headers; success = 200 redirect to `/init` or `/`.
- LLDAP group membership writes are GraphQL-only; password sets are LDAP
  password-modify ext-op only (details in the proxmox-cluster-infrastructure skill).

## Uptime Kuma v2 automation (socket.io over python-socketio 5.x)

- Fresh init: `POST /setup-database` with `{"dbConfig":{"type":"sqlite"}}` (NO /api
  prefix) — the socket.io server is not mounted until DB init completes.
- Client rules: `socketio.Client(ssl_verify=False)`, `transports=["polling"]` ONLY
  (websocket handshake 403s), payloads are TUPLES that arrive as positional args
  (`sio.emit("setup", ("admin", pw), callback=cb)`), callbacks are KEYWORD args
  (`callback=`), and the login ack arrives asynchronously — do not gate on it;
  gate on an authenticated read (`getMonitorList`) instead.
- Monitor CRUD: `monitor/add` / `monitor/edit` with a single object payload
  `{type:"http", name, url, interval, retryInterval, maxretries}`; check the ack for
  `ok`. Idempotency: fetch `getMonitorList`, match by monitor `name`.
- Keep this inside one adapter module; version-check and fail safe (never delete).

## Registry pattern (canonical source of truth)

- FastAPI + Pydantic + YAML persistence + systemd; bearer tokens stored as sha256 JSON
  files in a 0700 tokens dir; soft states (managed/discovered/candidate/disabled/stale),
  no DELETE endpoint. Acceptance: unauth write 401, create 201, duplicate 409.
- Reconciler: 60 s loop — PVE metadata (guest notes `miam-service:*`) + conservative TCP
  scan of the port list → merge into registry keyed by id (never clobber agent-sourced
  entries, never delete) → sync Homarr + Kuma. Idempotency test = run twice, count
  unchanged.
- When a client library needs creds (PVE API), read them from a 0600 env file — never
  embed them in code or handoff docs.

## Common failure signatures

- 000 from the VM to its own published port = docker-proxy/listener not there yet or no
  SNI match (curl with `--resolve host:443:<ip>` to test with correct SNI).
- 502 through Caddy = upstream host:port wrong (127.0.0.1 inside a container is the
  container itself — host-networked Caddy must point at the host's loopback/gateway).
- 426 from Kuma for everything = you are hitting the wrong server (usually Homarr's
  Next.js on the same port after a host-network misconfiguration).
- Registry "works with --resolve, fails without" = DNS overrides not yet in place.
