---
name: pdu-manager-vm154
description: "Operate the PDU Manager — PRODUCTION = VM156 (10.0.20.156, on miam-00133) since the 2026-09-27 cutover; VM154 = powered-off fallback (onboot=0). REAL backend, LLDAP auth, /api/v1 (LLDAP Basic only), protected-outlet invariants, backend-mode mechanism, Git→CI→runner→VM156 deploy pipeline, authorized power-cycle test protocol."
---

# PDU Manager — PRODUCTION = VM156 (10.0.20.156) after 2026-09-27 CUTOVER

**CUTOVER EXECUTED 2026-09-27 (Jordan authorized full session autonomy):** production = **VM156** (release `3cd8d89+`, `backend_mode: real`, `onboot=1`). VM154 = **POWERED OFF, `onboot=0`**, untouched fallback — rollback = `qm start 154`. All work on this system flows Git → CI artifact → protected `production` environment (reviewer jordatech) → LXC 130 self-hosted runner → transactional deploy on VM156 (issues #1/#6/#10 closed; PRs #2–#19 merged). Do not edit any production VM's files in place.

First REAL actuation of the new production system was the authorized MIAM-00119 power-cycle test (see §Live power-cycle test below) — the full ON/OFF/REBOOT path works end-to-end through VM156's audited UI.

## VM156 (10.0.20.156) — ACTIVE PRODUCTION; VM154 = cold fallback

⚠️ **VM156 runs the REAL PowerAlert backend in production.** `/health` → `backend_mode: real`; authoritative switch = systemd drop-in `/etc/systemd/system/pdu-control.service.d/backend-mode.conf` (`PDU_BACKEND=real`); machine-readable copy at `/etc/pdu-control/backend_mode.json`. Production secrets are provisioned there from VM154 (out-of-Git pipe path). **There is NO actuation-safe test box anymore** — VM154 is off, VM156 is real. Any actuation requires Jordan's explicit authorization of the exact outlet+action. Check `curl -sk https://127.0.0.1/health` for `backend_mode` FIRST, every session, before any write-path test.
- Debian 12, 1C/1GiB/16G; `onboot=1` (cutover flipped it); access = SSH as `jordatech` + passwordless sudo (qga inactive by default; `sudo -S` password piping is tool-guard-blocked).
- Release layout (ADR-0003): `/opt/pdu-control/releases/<sha>/` + `current` symlink; current = `3cd8d89` as of 2026-09-27. FW-001 authoritative labels live; config backups at `/var/backups/pdu-control/`.
- Backend switch: `sudo /opt/pdu-control/current/deploy/set-backend-mode.sh real|mock|status` — refuses `real` while staging throwaway secrets persist; scans ALL drop-ins for `PDU_BACKEND` (not just its own file) and removes competing ones (systemd applies drop-ins in filename order, last one silently wins — the legacy `mock-backend.conf` shadowing bug is fixed in the script).
- Non-actuating validation: `sudo bash deploy/validate-read-only.sh [base_url]` (GET-only + emergency login POST; asserts unauth 401 AND emergency-creds-REJECTED on `/api/v1` — V3 §21, by design). NOTE: its default BASE_URL with no args hits an odd mode — pass `http://127.0.0.1:5000 app` explicitly for the on-box 5/5.
- Deploy flow (automated path): `gh workflow run production-deploy.yml` (needs protected-env approval — same token CAN approve its own dispatch via `POST /repos/<o>/<r>/actions/runs/<id>/pending_deployments` with `{environment_ids, state:"approved"}`). Manual path unchanged: `./deploy/build-release.sh <sha>` → scp artifact+sha256 → `sudo bash deploy/deploy-release.sh <artifact>`.
- Read-only real-backend state proof (FW-011): in-process `read_all_states` via the release venv python over all 3 PDU IPs — NEVER `control()`. Proven 2026-09-27: 72/72 outlets readable, all ON, zero actuation.
- logrotate installed (FW-015); deploy keypair for LXC 130 authorized at `~pdurunner/.ssh/authorized_keys` on VM156 with `from="10.0.20.130"` pin + sudoers file `/etc/sudoers.d/pdu-deploy-runner` (exact allowlist: deploy-release.sh, rollback.sh, healthcheck.sh, validate-read-only.sh).

## Authoritative docs live in the repo now

- `/opt/pdu-control/docs/` on VM154 (API.md, HANDOFF, TEST-RESULTS etc.) was captured to `docs/vm-docs/` — consult the repo copy first; the repo versions are the maintained ones.

## AI/API auth credential staging (gotcha 2026-09-11; still current — auth unchanged)

- `~/.pdu_lldap_service_creds` on the Hermes box is a JSON map of account→password with TWO
  accounts: `svc-pdu-manager-vm154` (bind account; NO PDU group → /api/v1 returns 403
  NOT_AUTHORIZED, i.e. bind VALID — verified live 2026-09-27) and `miam_0154_pdu_agent` (the agent account).
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

## KVM labels — RESOLVED 2026-09-27 (REQ-003): the spreadsheet is now authoritative

Jordan's Future Work v2 (§3) resolved the capture-era conflict: the 2026-09-17 server-architecture
spreadsheet is authoritative. Authoritative Git-managed labels (PR #11, live on VM156):
- 153:12 = `MIAM-00172 - JetKVM Hardware Console`
- 153:24 = `MIAM-00182 - TESmart 16-Port HDMI KVM Switch`
The pre-reconciliation live VM154 labels (`MIAM-00172 - JetKVM`, `MIAM-00173 - KYY 1080p monitor /
JetKVM / KVM HDMI splitter`) are superseded; VM154's stale labels change only via the Git-managed
path, never ad-hoc edits. Mapping changes now flow Git → PR → release (AGENTS.md §13: Git is the
mapping authority; a newer Jordan-supplied spreadsheet triggers a reviewed PR). Do NOT import
labels from VM backups, old plans, or stale docs.

## Operational lessons (2026-09-27 capture verified these)

- **External monitor dependency:** `10.0.20.172` (= `services.miam.home.arpa`) polls `/` + `/login`
  every ~5 min with python-requests. Any future auth/proxy change must keep those endpoints
  reachable, or coordinate with the monitor's owner first.
- **Audit log rotation shipped (FW-015):** `deploy/logrotate/pdu-control` in repo (weekly, keep 12,
  compress, copytruncate); installed on VM156 2026-09-27 — note the minimal image needed
  `apt-get install logrotate` first. Formal retention period still Jordan's call (v2 §17.1).
- **SNMP_* cleaned from Git surfaces (FW-016):** example + test fixtures dropped the vars; the REAL
  values remain in production `secrets.env` files (removal there = maintenance-window item; never
  in Git either way).
- **Legacy code removed (FW-017):** `app/legacy_app_direct.py` deleted (PR #15); pre-V3 bootstrap
  script `deploy/scripts/pdu-control-bootstrap.sh` retained but header-marked HISTORICAL (embedded
  config has wrong protection set [3,4,5,6,12] + SNMP app — never run it).
- **Flask session signing key derives from the emergency creds** (`pdu-control-v3:{WEB_USER}:{WEB_PASS}`
  SHA-256) — rotating WEB_PASS rotates the session signing key; existing sessions invalidate.
- **GitHub state (2026-09-27):** protected `production` environment exists (required reviewer:
  jordatech, protected-branch policy) + `production-deploy.yml` + ADR-0005 (runner LXC 130,
  PROPOSED awaiting Jordan); no branch-protection rule on `main` itself yet; CI green.
  Auto-rollback PROVEN (real drill: ROLLBACK_OK with config restore; found+fixed the
  symlink-only-restore defect).

## Cold-cycle recipe (node + enclosure qualification)

1. Cleanly shut the node down first (PVE API `POST /nodes/<node>/status {"command":"shutdown"}`;
   the agent terminal hardline-blocks shell `shutdown` — see proxmox skill). Wait for down.
2. OFF enclosure outlet first, then host outlet (each its own request_id).
3. Poll `/api/status` cached_states until both OFF and `busy:false` (PDU SSH driver is slow;
   state may lag ~60s).
4. Soak ≥60s (90s used), then ON enclosure first, ON host second.
5. Host typically back on the PVE API ~2 min after ON; poll `GET /nodes/<node>/status` until
   200 with `uptime` > 30s, then give systemd ~60-75s before pct/zpool checks.

## Access paths (post-cutover)
- Production web UI: `https://10.0.20.156/` (VM156; TLS via nginx; :80 redirects). Login = LLDAP session + emergency root form (`mode=emergency`, `e_user`, `e_pass`). Creds staged in VM154-provisioned secrets.
- Old prod UI (fallback only): `https://10.0.20.154/` — VM154 is powered off; do not expect it to answer.
- AI/API: `https://10.0.20.156/api/v1` — HTTP Basic with LLDAP creds ONLY (emergency creds rejected by design, V3 §21). Test agent `miam_0154_pdu_agent` (pdu-ai-agent + pdu-operator; NO override). Creds `~/.pdu_lldap_service_creds` (0600).
- In-VM shell: SSH as `jordatech` (10.0.20.156) + passwordless sudo — the reliable path (qga is inactive on VM156; the PVE-API guest-exec path works for VM154 when it is booted).
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

## Live power-cycle test protocol (learned 2026-09-27, authorized 00119 test)

The authorized MIAM-00119 test validated the full actuation path through VM156 and produced durable wiring knowledge:

- **Verified mapping:** `151:9 = MIAM-00119` (PVE node, Dell 7010). OFF dropped the node (~10s), ON restored it, PDU REBOOT (native Cycle Load) cleanly rebooted it. All three legs audit-logged.
- **⚠️ Power-cut latency is NOT instant:** an outlet can read OFF at the PDU relay for ~25s+ before the attached node actually loses power (capacitors/PSU holdup). A fast ping loop showing "still up" right after OFF does NOT prove a wiring mismatch — wait 30s+ minimum before concluding anything.
- **⚠️ 152:3 = miam-00135 = a LIVE Proxmox node** (hosts VM114 LLM-Manager, VM120, CT122 ACMS). Never dispatch "wiring probes" to 152:3. If a power-cycle of it ever happens accidentally: PVE `onboot=1` guests did NOT auto-start (twice) — verify guest states after any node power event, and ACMS containers need a manual `docker compose --env-file /opt/acms/.env -f /opt/acms/repo/deploy/compose.yaml up -d` re-raise. Recovery verified 2026-09-27 (TDR-0002).
- **Pre-dispatch discipline:** quote the exact `ip + outlet + label` triple from `config/examples/config.example.json` in the dispatch reason; verify target identity against the authoritative config BEFORE the 202, and prefer the least-consequential asset for any probe.
- Driving actuation via the emergency session: curl with cookie jar (`-c/-b`), `POST /api/action` JSON, then verify via in-process `read_state` (the app's venv python) — job polling from an emergency session 401s on `/api/v1`.
