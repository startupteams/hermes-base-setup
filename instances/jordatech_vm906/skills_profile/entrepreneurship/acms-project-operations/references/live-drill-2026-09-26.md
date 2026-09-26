# Live drill 2026-09-26 — CT122 release tooling: bugs, evidence, recovery

Timeline (UTC): 22:11 dry-run pipeline test OK → 22:15 bootstrap hop put
PR 0 (650d6f8) live → 22:16 first real `release.sh 266d0ed` failed + auto-
rolled back → 22:19–22:31 diagnosis + recovery.

## What the drill proved (the good)

Level-2 auto-rollback chain worked end-to-end on real production data:
trigger → `rollback.sh --in-flight` → backup checksum verified → active
connections terminated → restore into `acms_restore_tmp` → swap with rename
(live DB kept as `acms_old` for forensics) → previous image `acms-app:650d6f8`
started → alembic revision re-checked. Data intact after (rev
0002_work_orchestration, 1 agent, 0 work items).

## The 6 bugs (all fixed in PR #6, branch fix/ACMS-release-tooling-live-drill)

1. **Build-tag pollution.** `IMAGE_TAG="$(build_release_image ...)"` captured
   compose's entire build log via stdout → `docker: invalid tag
   "acms-app:<68 lines>"`. Fix: build output to `>&2` inside the function;
   tag is computed from the SHA, never captured.
2. **No readiness gate.** Validation started ~1s after `up -d` → false
   `repeated /health (x3)` FAIL → false rollback-failure. Fix:
   `wait_app_ready()` (60s cap, `ACMS_APP_READY_SECONDS`) in release Phase C
   and both rollback paths.
3. **pipefail false positive.** `logs | grep -cE "..." | grep -q '^0$'` — the
   first grep exits 1 on zero matches; under `set -o pipefail` the check
   "fails" when logs are clean. Fix: capture count with `|| true`, numeric
   compare.
4. **nginx single-file bind-mount inode pinning (the sneaky one).**
   `- ./reverse-proxy/nginx.conf:/etc/nginx/conf.d/default.conf` pins the
   file's inode inside the container. Editing/copying/replacing the file on
   the host creates a NEW inode; the container keeps serving the OLD content.
   `nginx -s reload` (HUP) re-reads from the container's (stale) inode →
   maintenance 503 page served forever even after "restore". Fix: directory
   mount `./reverse-proxy:/etc/nginx/conf.d` (in-place `cp` edits are
   visible), maintenance template named `nginx.maintenance.conf.template`
   (excluded from the conf.d include glob), every reload guarded by
   `nginx -t`, fallback = `compose restart reverse-proxy` (single container),
   and release.sh reconciles the proxy spec post-maintenance-off.
5. **depends_on recreation hazard.** `compose up -d --force-recreate
   reverse-proxy` ALSO recreated acms-app — with `ACMS_APP_IMAGE_TAG`
   unset it fell back to the default `acms-app:local` (stale code, /version
   without git_sha). Caught by the /version identity check; fixed by pinning
   `ACMS_APP_IMAGE_TAG` on every compose up in tooling.
6. **Rollback Level-2 start-order.** A mid-edit version started the app
   before the DB swap (writes-during-restore hazard, plan §8 violation).
   Final order: stop app → terminate connections → restore temp DB → swap
   (keep acms_old) → checkout previous SHA (restore tracked nginx.conf
   first — maintenance conf dirties it) → start previous image → wait ready
   → validate → record as `restored` with a NEW release id (never overwrite
   the previous release's metadata).

## Recovery playbook (stuck maintenance / wrong image)

```bash
C="docker compose -f /opt/acms/repo/deploy/compose.yaml --env-file /opt/acms/.env"
$C up -d --force-recreate reverse-proxy          # pick up normal conf inode
ACMS_APP_IMAGE_TAG=<release-tag> $C up -d acms-app   # re-pin app image
curl -kfsS https://10.0.20.122/version           # verify git_sha identity
rm -f /opt/acms/releases/transaction.json        # ONLY after physical restore verified
```

Also worth capturing: clearing a completed-but-unrecorded transaction is a
manual-recovery action, logged into `history.jsonl` as
`action=manual-recovery`.

## Bootstrap hop (first deploy of the tooling itself)

`release.sh` cannot exist at the old commit. Manual sequence (identical
guarantees, ~2-min window): verified pg_dump (+ magic/parse/sha256) → stop
app → `git checkout --detach <sha>` → build `acms-app:<short>` with
`ACMS_BUILD_GIT_SHA`/`ACMS_BUILD_TIME` → `alembic upgrade head` → start →
validate (identity + proxy + login + redirect) → write `current`, release
metadata JSON (mark `"mode": "manual-bootstrap"`), history line.

## Dry-run pattern (zero production impact)

Before first real use: pg_dump to /tmp, check `PGDMP` magic + sha256, pipe
through `pg_restore --list`, restore into `acms_drill_tmp`, count rows, drop
temp DB, probe app via in-container python urllib. All without touching the
live `acms` DB or stopping anything.
