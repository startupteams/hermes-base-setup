# MIAM Service Registry + dashboard stack (VM119) — API & operations reference

Verified live 2026-09-30 during the full cluster inventory run.

## Topology (VM119 `miam-service-dashboard`, 10.0.20.172, node miam-00135, onboot=1)

- Docker compose at `/opt/miam-dashboard/compose.yaml`: `caddy:2` (80/443), `homarr`
  (127.0.0.1:7575), `uptime-kuma` (3001). The registry + reconciler are SYSTEMD services
  (not containers): `miam-service-registry.service` (uvicorn app:app on 127.0.0.1:8720) and
  `miam-service-reconciler.service` (60s loop, `/opt/miam-dashboard/reconciler/reconcile.py`).
- Caddy vhost map: `services.miam.home.arpa` → 7575 (Homarr), `status.` → 3001 (Kuma),
  `registry.` → 8720. `@allowed remote_ip 10.0.10.0/24 10.0.20.0/24 127.0.0.1 100.64.0.0/10`
  (CGNAT range added 09-30 for Tailscale clients — subnet-routed traffic keeps its 100.x source).
- TLS: Caddy internal CA (ECC, ~6h auto-rotated certs). Root CA exportable from
  `/opt/miam-dashboard/caddy/data/caddy/pki/authorities/local/root.crt`.
- Dashboard docs live on the VM: `/opt/miam-dashboard/REGISTERING-SERVICES.md` (the mandatory
  agent rule) and `MARION-IA-USA-SERVICE-DASHBOARD-HANDOFF.md`.

## Registry API (`https://registry.miam.home.arpa`)

- Auth: `Authorization: Bearer <token>`. Token files in
  `/etc/miam-service-registry/tokens/<name>.json` store ONLY
  `{name, scopes, token_sha256}`. The RAW agent-registrar token lives in
  `/etc/miam-service-registry/secrets.env` as `MIAM_SERVICE_REGISTRY_TOKEN` (0600).
  Read it server-side; never print or copy it out.
- Endpoints (openapi at `/openapi.json`, swagger at `/docs`):
  `GET /api/v1/services`, `POST /api/v1/services`, `GET|PATCH|PUT /api/v1/services/{sid}`,
  `POST /api/v1/services/{sid}/disable`, `POST .../enable`, `GET /api/v1/discoveries`, `GET /health`.
- POST with duplicate id → `{"detail":"id already exists"}` (safe, non-destructive).
- ⚠ **PATCH REPLACES THE ENTIRE RECORD** — a PATCH that omits `category`/`host`/`tags` ERASES
  them (hit live 2026-09-30, restored on a second PATCH). Always PATCH the complete desired record.
- No DELETE: use `/{sid}/disable` (reversible via `/enable`).
- From the LAN use `curl --resolve registry.miam.home.arpa:443:10.0.20.172`; from inside VM119,
  `--resolve ...:127.0.0.1` against https works (Caddy on loopback-bound vhosts).
- Registrar token scopes: `services:read`, `services:register`, `services:update`.
- States: `managed | discovered | candidate | disabled | stale`.

## Reconciler behavior (`reconcile.py`)

- Reads `/etc/miam-service-registry/secrets.env` for `HOMARR_API_KEY`, `KUMA_URL/USER/PASS`,
  `MIAM_SERVICE_REGISTRY_TOKEN`. Loop ~60s; audit at `/var/lib/miam-reconciler/audit.jsonl`.
- **Kuma sync:** for every NON-disabled registry service, ensure an HTTP monitor named
  `<service name>` with `url = url || health_url` (socket.io `monitor/add` / `monitor/edit`,
  interval 60s). Verified live: registering 16 managed records flipped monitors 11 → 19 → 34
  across cycles. Disabled services are skipped (not monitored).
- **Homarr sync:** SKIPPED with log `homarr: no API key configured yet — sync skipped` until
  `HOMARR_API_KEY` exists. Homarr v1.x API keys are created ONLY in the UI (Settings → API Keys);
  with LDAP-only auth and zero local users there is NO headless path. Human step: create key →
  `echo "HOMARR_API_KEY=<key>" >> /etc/miam-service-registry/secrets.env` → picked up next cycle.
  (Instruction file staged 09-30: `/etc/miam-service-registry/HOMARR-API-KEY-SETUP.md`.)
- Discovery: port-list scan produces `discovered`/`candidate` records (`source=network-scan`).
  Dynamic-test lifecycle evidence: a prior run's `dashboard-test-service` went managed → disabled
  and remains disabled (correct stale behavior, no deletion).

## Read-only inspection notes

- Homarr sqlite (`docker cp miam-dashboard-homarr-1:/appdata/db/db.sqlite` → local sqlite3):
  tables `user`, `apiKey`, `board`, `app`. 2026-09-30 state: 0 users, 0 API keys, 1 board
  ("dashboard"), 4 default demo apps (Homarr Docs/GitHub/Translate/Support).
- VM119 qga works fine (`qm guest exec` on miam-00135) — registry curls run through it.
- Seed data: `/opt/miam-dashboard/registry/services.yaml`.
