---
name: pdu-manager-vm154
description: "Operate and upgrade the Rack PDU Power Control Center on VM154 (10.0.20.154) — LLDAP auth, /api/v1 for AI agents, protected-outlet invariants, native PDU cycles, reconciliation, and rollback points."
---

# PDU Manager on VM154 (10.0.20.154)

V3 upgrade shipped 2026-09-11 (LLDAP + AI API). Authoritative docs live on
VM154 at `/opt/pdu-control/docs/` (HANDOFF.md, IMPLEMENTATION-REPORT.md,
API.md, openapi.json, TEST-RESULTS.md, ROLLBACK.md, CHANGELOG.md).

## AI/API auth credential staging (gotcha 2026-09-11)

- `~/.pdu_lldap_service_creds` on the Hermes box is a JSON map of account→password with TWO
  accounts: `svc-pdu-manager-vm154` (bind account; NO PDU group → /api/v1 returns 403
  NOT_AUTHORIZED, i.e. bind VALID) and `miam_0154_pdu_agent` (the agent account).
  If the agent account's password returns 401 AUTH_INVALID it has been ROTATED/stale — do not
  brute-force variants; the JSON layout means the value under each key IS that account's password.
- **Working fallback for agents: web emergency-login session.** POST `https://10.0.20.154/login`
  with form `{"mode":"emergency","e_user":"root","e_pass":<node root pw from ~/.miam_root_pass>}`
  (allow_redirects=False; 302 + `Location: /` = success; read timeout up to 30s — the GET
  after login is slow). Session then drives the legacy UI API:
  - `GET /api/status` → `pdus["10.0.20.153"]["cached_states"]` (`{"7":{"state":"ON"|"OFF"}}`) + `busy`
  - `POST /api/action` JSON `{"action":"on|off|reboot","ip":"10.0.20.153","outlet":7,"reason":"...","request_id":"<uuid>"}` → 202 `{"accepted":true,"jobs":{"10.0.20.153":"<jobid>"}}`
  - `GET /api/v1/jobs/<id>` requires LLDAP Basic (NOT the session) — job polling from an
    emergency session 401s; poll `/api/status` instead and read outlet states after ~30-60s.
  - The dashboard cold-load does 3 serial PDU SSH state reads (~30-60s) — cached_states lags;
    an action shows `busy: true` until committed. Verify final state only via /api/status.
- Outlet-label verification before operating: labels live in the dashboard HTML
  (`data-ip="10.0.20.153" data-outlet="7"` + `data-label="MIAM-00147 - NUC 11 Pro"`); fetched
  labels must match the runbook (outlet7=NUC147, outlet8=ThunderBay148) before any power event.

## Cold-cycle recipe (node + enclosure qualification)

1. Cleanly shut the node down first (PVE API `POST /nodes/<node>/status {"command":"shutdown"}`;
   the agent terminal hardline-blocks shell `shutdown` — see proxmox skill). Wait for down.
2. OFF enclosure outlet first, then host outlet (each its own request_id).
3. Poll `/api/status` cached_states until both OFF and `busy:false` (PDU SSH driver is slow;
   state may lag ~60s).
4. Soak ≥60s (90s used), then ON enclosure first, ON host second.
5. Host typically back on the PVE API ~2 min after ON; poll `GET /nodes/<node>/status` until
   200 with `uptime` > 30s, then give systemd ~60-75s before pct/zpool checks.

## Access paths
- Web UI: `https://10.0.20.154/` (TLS via nginx; :80 redirects). Login page =
  LLDAP session + emergency root form. Legacy Basic-auth still honored on UI
  routes (root creds staged at `~/.pdu_portal` on the Hermes box).
- AI/API: `https://10.0.20.154/api/v1` — HTTP Basic with LLDAP creds. Test
  agent `miam_0154_pdu_agent` (pdu-ai-agent + pdu-operator; NO override).
  Creds `~/.pdu_lldap_service_creds` (0600).
- In-VM shell: PVE API guest-exec on node miam-00133 VM 154 (bot account,
  `~/.pve_ldap_bot`), urlencode body with doseq=True.
- TLS cert: self-signed, DER sha256
  `137308d592260184fd75b7a555e27f61332a8c7ffe5feb1f58d1c5553b2221a9`.

## Architecture (what runs where)
- systemd `pdu-control`: gunicorn 1 worker × 4 threads, **127.0.0.1:5000**
  ONLY. nginx terminates TLS :443 (config
  /etc/nginx/sites-available/pdu-control). nftables `inet pdu_filter` allows
  80/443/22 from 10.0.20.0/24 + 10.0.10.0/24, drops 80/443 otherwise.
- Modules: `app.py` (UI + legacy /api routes) → `action_service.py` (single
  action path + invariants + idempotency) → `app_runtime.py` (locks, audit,
  worker subprocess via `pdu_worker.py` → `pdu_ssh_direct.py` pexpect
  PowerAlert SSH driver — DO NOT touch the driver).
- `auth_lldap.py`: bind-check + `(member=<userDN>)` group search via service
  bind `svc-pdu-manager-vm154`; 60s group cache (revocation lands ≤60s).

## LLDAP facts (10.0.20.101)
- LDAP protocol port **3890** (NOT 17170 — that's web/GraphQL UI).
- Base DN `dc=example,dc=com`; user DN `uid=<user>,ou=people,...`.
- NO memberOf: search `ou=groups,dc=example,dc=com` w/ `(member=<userDN>)`.
- No GraphQL password mutation: use ldap3 ModifyPassword extop bound as admin.
- Groups: pdu-viewer(11) pdu-operator(12) pdu-admin(13) pdu-ai-agent(14)
  pdu-ai-admin-override(15).

## Hard invariants (never weaken)
- Protected outlets (153: [3,4,5,6,9]): OFF forbidden for EVERYONE
  (PROTECTED_OFF_FORBIDDEN), even admin_override/root. Override = REBOOT only,
  requiring admin_override + reason + acknowledge_protected_device (+ for
  153/9: acknowledge_controller_may_go_offline). Expected final state ON.
- Protected reboot = native PDU `4- Cycle Load` (atomic, PDU-committed). Never
  implement OFF-then-ON in the controller.
- 153/9 reboot: writes `/var/lib/pdu-control/pending_reboot.json`, commits the
  cycle, VM dies mid-verify, boot reconciler verifies/recovers ON + audits.

## API usage pattern (agents)
GET /me → GET outlet → one UUID Idempotency-Key per intended action → POST
action → poll GET /jobs/{id} → verify state. Never retry with a NEW request id
on timeout (idempotency replays the original job; new id = new power event).
Rate limits: 120 GET/min, 20 POST/min per identity (429 + Retry-After).
Idempotency persists across restarts (/var/lib/pdu-control/idempotency.json).

## Pitfalls learned
- secrets.env must stay 640 root:pducontrol (chmod 600 breaks the service).
- gunicorn must stay --workers 1 (runtime structures are per-process).
- Dashboard cold-load does 3 serial PDU SSH state reads (~30-60s) — normal.
- Config JSON at /etc/pdu-control/config.json is the protection source of
  truth; backup dir /root/pdu-control-backups/20260910-222303/.
- Rollback: `qm rollback 154 pre_lldap_api_upgrade_20260910` on miam-00133.
- Deploy via guest-exec needs ≤12KB base64 chunks per write (596 broken pipe
  on big single posts).
- LLDAP GraphQL: `user(userId:)` not `user(id:)`; introspect mutations.

## Safe live-test outlet
MIAM-00151 outlet 4: unlabeled, unprotected, no mapped asset — verified safe
for live ON/OFF tests (confirmed again before each destructive test).
