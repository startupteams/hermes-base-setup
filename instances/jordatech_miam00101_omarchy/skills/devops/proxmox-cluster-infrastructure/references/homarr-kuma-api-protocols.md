# Homarr v1.x + Uptime Kuma 2.5.5 API protocols (MARION dashboard stack, VM119)

Wire-protocol facts verified LIVE 2026-09-30 while building the real registry→Homarr/Kuma sync
(the pre-existing reconciler had never actually worked: wrong Homarr header + wrong Kuma login shape).
Working sync implementations deployed on VM119: `/opt/miam-dashboard/reconciler/{homarr_sync,kuma_sync,kuma_status_page}.py`.

## Homarr (ghcr.io/homarr-labs/homarr:latest, v1.x, LDAP auth)

- **Auth header is `ApiKey: <key>`** — NOT `x-api-key` (the obvious guess 401s). Header name comes from
  the OpenAPI `securitySchemes.apikey.name`, discoverable at `GET /api/openapi`.
- API keys are created ONLY in the UI (Settings → API Keys); DB stores a bcrypt hash — the raw key exists
  nowhere else. With LDAP-only auth there is NO headless key creation path.
- **REST app CRUD (verified):** `GET /api/apps` (full list), `POST /api/apps`, `GET|PATCH|DELETE /api/apps/{id}`.
  POST/PATCH body requires ALL of: `name`, `description`, `iconUrl`, `href`, `pingUrl` (empty strings OK).
- **Boards (REST):** `GET|POST /api/boards` (POST needs `name`, `columnCount`, `isPublic`);
  `PATCH /api/boards/{id}/home {"isHome":true}` and `/mobile-home {"isMobileHome":true}`.
- **Board content save = tRPC** `POST /api/trpc/board.saveBoard`, body `{"json": {id, sections[], items[]}}`:
  - section: `{id, kind:"category", xOffset, yOffset, collapsed:false, name, options:{}, integrationIds:[], layouts:[]}`
  - item: `{id, kind:"app", options:{appId, openInNewTab, showTitle}, advancedOptions:{}, integrationIds:[],
    layouts:[{layoutId, sectionId, xOffset, yOffset, width, height}]}`
  - **Client-generated ids are accepted** (stable deterministic ids like `msec-<slug>` / `mitm-<reg-id>`
    make saves idempotent).
  - **saveBoard REPLACES the board's sections+items — anything absent from the payload is DELETED.**
    There is no REST/tRPC item-delete endpoint; this replace-semantics IS the headless delete path.
  - Same payload twice = zero change (verified).
- **Reads:** `GET /api/apps`, `GET /api/boards` (with isHome flags). There is NO REST board-content read —
  the board's Base `layoutId` and current section/item ids are only reachable via a READ-ONLY sqlite copy
  (`docker cp <homarr>:/appdata/db/db.sqlite` → `layout`/`section`/`item` tables). Writes stay API-only.
- tRPC is mounted at `/api/trpc` with FLAT procedure keys (`app.all`, `board.saveBoard`) — NOT
  `routerName.procedure` (`boardRouter.saveBoard` 404s with "No procedure found").
- **Trap: deleting an app that still has board items leaves a dangling card** (verify via sqlite read; fix
  by re-saving the board without that item). Never DELETE marker-owned apps with live items.
- Ownership pattern that works: app `description` carries `[MIAM-REGISTRY-ID:<service-id>]`; apps without
  the marker are human-managed and NEVER touched.

## Uptime Kuma 2.5.5 (louislam/uptime-kuma:2, socket.io v4)

All facts below verified live; they DIFFER from v1 lore (which the internet and old code assume):

- **login: object payload** `sio.emit("login", {"username": u, "password": p, "token": ""}, cb)` →
  ack `{"ok": bool, "token": jwt}`. The v1 tuple form `emit("login", (u, p, ""), cb)` gets **no ack at all**
  (silent failure — this is why an older sync "worked" in logs but never wrote anything).
- **Event names changed from v1:** add = `add`, edit = `editMonitor`, delete = `deleteMonitor(id, deleteChildren, cb)`
  — NOT `monitor/add` / `monitor/edit`. `getMonitorList` exists but **its callback ack returns `{}` on this
  build** — the real monitor list arrives via the **`monitorList` EVENT** (register the handler BEFORE the
  login emit; the post-login push races the login ack).
- **Transport: websocket.** `transports=["polling"]` intermittently drops ACK packets under load (login ack
  observed as `None` repeatedly while server logs said "Successfully logged in"). Websocket fixed it.
- **Add/edit payload:** needs `"conditions": []` (NOT NULL column — omitting it fails the insert with
  `NOT NULL constraint failed: monitor.conditions`); must NOT include `upsideDownMode` (v2 renamed it
  `upsideDown`; sending the v1 key fails the insert). `ignoreTls: true` for https targets on self-signed
  internal TLS. Port monitors: `{type:"port", hostname, port, ...}` (needs accepted_statuscodes too or the
  handler throws on `.every`).
- **Rate limiter:** login = 20 tokens/min per IP (token bucket); concurrent sync instances drain it and can
  hang login acks. Single-instance enforcement: `flock` lockfile around the whole sync (a manual run racing
  the 60s reconciler loop duplicated 56 monitors once).
- **Status pages:** `addStatusPage((title, slug), cb)` then
  `saveStatusPage((slug, config, "", publicGroupList), cb)` — multi-arg emits must be packed as a TUPLE in
  `data` because python-socketio `Client.emit(event, data, namespace, callback)` has NO `*args`; positional
  args after the first silently become the namespace (`BadNamespaceError: marion is not a connected namespace`).
  config needs `analyticsType: None` explicitly (absent ≠ null → "Invalid analytics type") and
  `public: True`; groups = `{"name": g, "monitorList": [{"id": mid, "sendUrl": True}]}` (NOT `monitorIds`).
  Published page: `GET /status/<slug>` (200, no login).
- **Password recovery (official, unattended):** `docker exec <kuma> npm run reset-password -- --new-password=<pw>`
  (interactive prompt tool; the arg form skips prompts). No old-password required.
- **Auth-honesty:** Kuma 2.5.5 has NO native LDAP/OIDC user login (its OIDC code is monitor-token only).
  401-gated endpoints read as DOWN to http monitors — use `type:"port"` TCP monitors for bearer-gated
  services instead (honest liveness without false alarms).