# MIAM Service Registry → Homarr propagation — verified recipe (2026-10-01)

Changing a human-service URL (e.g. ACMS `https://10.0.20.122` → `.../ui`) is a
TWO-hop change with verification at both ends. Executed live for the ACMS
record during the A2A production-path session.

## Access path (no direct SSH to VM119 needed)

Run curls INSIDE VM119 via qga guest exec (miam-00135, VM119 — qga works on
that node):

```bash
TOKEN=$(grep "^MIAM_SERVICE_REGISTRY_TOKEN=" /etc/miam-service-registry/secrets.env | cut -d= -f2-)
BASE="https://registry.miam.home.arpa"
RESOLVE="--resolve registry.miam.home.arpa:443:127.0.0.1"   # Caddy vhost on loopback
```

## Hop 1 — Registry record (FULL-record PATCH only)

1. `GET $BASE/api/v1/services` → find the record (e.g. id `acms`).
2. **PATCH with the COMPLETE record** — PATCH REPLACES the whole record;
   omitting `category`/`host`/`tags` ERASES them (documented 09-30, respected
   10-01). Reconstruct the full JSON from the GET, change ONLY the url.
3. Re-GET to verify the new url + fresh `updated` timestamp.

## Hop 2 — Homarr card (reconciler propagates within its ~60 s cycle)

The reconciler (`miam-service-reconciler.service`) syncs Registry → Homarr
board automatically; Homarr ownership marker =
`[MIAM-REGISTRY-ID:<id>]` in the app description.

Wait one cycle (~70 s), then verify via the Homarr API (ApiKey header — NOT
x-api-key, which 401s):

```bash
KEY=$(grep "^HOMARR_API_KEY=" /etc/miam-service-registry/secrets.env | cut -d= -f2-)
curl -sk -H "ApiKey: $KEY" http://127.0.0.1:7575/api/apps | python3 -c "
import sys, json
for a in json.load(sys.stdin):
    if 'acms' in json.dumps(a).lower():
        print(a.get('name'), '->', a.get('href'), '| ping:', a.get('pingUrl'))"
```

Expected: `href` == the new Registry url. If stale: check
`/var/lib/miam-reconciler/audit.jsonl` and the reconciler service status
before hand-editing anything (never hand-edit Homarr-only state).

## Pitfalls

- `health_url` stays the API health endpoint (`.../health`) even when `url`
  becomes a UI path — Kuma monitors the health URL, humans click the UI URL.
- Reference: `references/miam-service-registry.md` in
  `devops/proxmox-cluster-infrastructure` (API surface, token locations,
  states, the PATCH-replaces-record rule).
