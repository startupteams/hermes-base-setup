# Making MARION internal services reachable over Tailscale (subnet router + split DNS)

Proven 2026-09-30 (dashboard URLs on VM119). Read-only inventory FIRST; never replace route sets.

## 1. Inventory the existing router before touching anything

Candidate on MARION: CT100 `tailscale-router-00133` @ 10.0.20.218 (tailscale IP 100.70.198.0).

```
pct exec 100 -- tailscale version
pct exec 100 -- tailscale ip -4
pct exec 100 -- tailscale status          # peers + online state
pct exec 100 -- tailscale debug prefs     # AdvertiseRoutes (the truth for advertised subnets)
pct exec 100 -- tailscale status --json   # Self.AllowedIPs = live/approved routes; peer list
pct exec 100 -- sysctl net.ipv4.ip_forward
```

- `AdvertiseRoutes` listing `10.0.10.0/24` + `10.0.20.0/24` and their presence in Self
  `AllowedIPs` = routes are advertised AND approved — reuse them, add nothing.
- OPNsense is ITSELF a tailnet peer (`opnsense` 100.110.87.100) — factor that into DNS-path reasoning.

## 2. NAT reality — decides your allowlist problem

tailscaled's iptables: `ts-postrouting MASQUERADE` matches ONLY fwmark `0x40000/0xff0000`
(tailscale-internal traffic). Subnet-routed traffic is forwarded **UNMASQUERADED** — LAN services
see the client's `100.64.0.0/10` CGNAT source IP. Consequence: any source-IP allowlist on the
target service (Caddy `remote_ip`, nginx allow, app firewall) MUST include `100.64.0.0/10`, or
tailnet clients get 403 even with routing + DNS perfect. This was the actual blocker for the
dashboard URLs (fixed 09-30 by appending the CGNAT range to VM119's Caddyfile; backup kept).

## 3. DNS path

- CT100 resolv.conf = `100.100.100.100` (MagicDNS), and `*.miam.home.arpa` resolved through it →
  split DNS for the zone is present tailnet-side (at least for the router).
- OPNsense Unbound (10.0.20.1) has host overrides `*.miam.home.arpa → 10.0.20.172`
  (verify: `dig +short @10.0.20.1 <name>`).
- If a client resolves but direct IP also works while the URL fails: check accept-dns/routes
  client-side. If `ERR_NAME_NOT_RESOLVED` while direct IP works: split-DNS entry missing
  tailnet-wide → add via admin console (DNS → nameserver restricted to `miam.home.arpa` →
  10.0.20.1). No admin API key staged as of 09-30 (console is a human step).

## 4. Client-side test ladder (Nepal or any tailnet client)

```
sudo tailscale set --accept-routes=true        # Linux clients; macOS/Windows use approved routes
ping 10.0.20.172                               # routing proof (bypasses DNS)
curl -kI --resolve services.miam.home.arpa:443:10.0.20.172 https://services.miam.home.arpa/
curl -kI https://services.miam.home.arpa/      # full path incl. split DNS
```

- `tailscale ssh` to a peer needs a one-time browser approval URL per session (tailscaled prints it).

## 5. TLS trust

Caddy internal CA (~6h certs). Do NOT disable verification globally; export only the public root
(`/opt/miam-dashboard/caddy/data/caddy/pki/authorities/local/root.crt`), record its SHA256
fingerprint, trust it on admin devices. Never export the private key.

## 6. Guardrails

- Never add a second subnet router when one already covers the zone; never replace
  `AdvertiseRoutes` wholesale (preserves existing routes).
- No Funnel, no public DNS records, no WAN port forwards — exposure boundary stays the tailnet.
- Allowlist edits: narrowest scope that works. CGNAT `/10` is acceptable when the tailnet is
  single-owner; otherwise pin specific peer IPs.
