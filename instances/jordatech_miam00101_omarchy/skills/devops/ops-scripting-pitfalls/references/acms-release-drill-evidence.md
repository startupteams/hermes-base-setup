# ACMS release-tooling drill evidence (2026-09-26, CT122 10.0.20.122)

Condensed session evidence behind each pitfall in SKILL.md. Context: `deploy/release.sh` (safe-release transaction) + `rollback.sh` (Level-2 app+DB restore) on docker-compose (acms-app + postgres + nginx reverse-proxy), nginx configs bind-mounted from the repo.

## Timeline

- Drill 1 (22:16Z, release 266d0ed): build-tag pollution → auto-rollback → **false** validation failures → exit 4. Root causes: compose build stdout in `IMAGE_TAG="$(build_release_image)"`; no readiness wait; `grep -c` pipefail false-fail; nginx single-file bind mount (stale 503 after maintenance-off).
- Recovery: proxy recreate + app re-pin (depends_on had reverted app to `acms-app:local`, caught via `/version` identity check); transaction cleared.
- Drill 2 (23:08Z, same tip 332f54d): maintenance cycle (ON → re-apply after checkout → OFF) now worked; backup verified; wait_app_ready 2s; Level-2 restore correct. Two residual bugs → exit 4: (a) `info()` log line inside command substitution polluted the tag again; (b) `health_repeats` loop-tail `[ "$i" -lt 3 ] && sleep 2` returned 1 on the final iteration. Recovered ~1 min; live service never left `332f54d`.
- Drill 3 (23:24Z, tip 363cf3c via PR #8 fixes): **first clean end-to-end run — "Release ACCEPTED", exit 0**. Backup verified (PGDMP + sha256), maintenance ON→OFF cycle clean, app ready in 2s, stage-1 app validation 6/6, stage-2 proxy validation 12/12. No code change (same tip re-released). Sequence that reached it: manual bootstrap hop 332f54d→363cf3c (fixed tooling can't install itself), then release.sh drill. Hop hiccup: first stage died on `No such container: acms-reverse-proxy` (compose-v2 name is `acms-reverse-proxy-1`; must use `docker compose exec <service>`) and left `deploy/reverse-proxy/nginx.conf` holding maintenance content — restored with `git checkout --` before retrying the overlay sequence.
- Post-drill sweep: standalone `smoke-test.sh` failed its two direct-backend probes — it curled `127.0.0.1:8000` from the VM host, but the app publishes NO host ports (nginx is the sole ingress by design). Also counted `FAILURES` yet always exited 0. Fixed in PR #9: in-container probes (`compose exec -T acms-app python` + urllib, exact status asserts: /health 200, /version 200, unauth /api/v1/agents 401), Work UI unauth 303 check, real `exit 1`. Not a release gate — validate-release.sh already probed correctly (that's why ACCEPT was legitimate). Verdict-reading trap hit here: `bash release.sh … | tee log | tail -60; echo $?` printed `tail`'s status; the true verdict is `"${PIPESTATUS[0]}"`.

## Exact error strings

- Tag pollution: `invalid tag "acms-app:[2026-09-26T23:08:52Z] INFO Building image acms-app:332f54d …332f54d": invalid reference format`
- Missing fetch: `fatal: git checkout: --detach does not take a path argument '332f54d'`
- Stale-conf symptom: container sees `default.conf` with maintenance marker while host `nginx.conf` is normal (single-file mount pins the inode).

## Recovery commands that worked

```bash
# wrong-image after depends_on recreation → re-pin and verify identity
ACMS_APP_IMAGE_TAG=<sha> docker compose -f deploy/compose.yaml --env-file /opt/acms/.env up -d acms-app
curl -kfsS https://10.0.20.122/version   # must echo deployed git_sha

# stale proxy config / mount topology → recreate under current spec, image pinned
ACMS_APP_IMAGE_TAG=<sha> docker compose up -d reverse-proxy

# what does the CONTAINER actually serve?
docker exec acms-reverse-proxy-1 grep -c "ACMS maintenance" /etc/nginx/conf.d/default.conf

# clear an open release transaction after a physically-correct rollback
rm -f /opt/acms/releases/transaction.json  # then append a manual-recovery line to history.jsonl
```

## Release-record layout (plan §4; outside Git)

```text
/opt/acms/releases/
├── current | previous          # release-id pointers
├── history.jsonl               # append-only ledger
├── releases/<id>.json          # per-release metadata (sha, image tag, backup sha256, alembic before/after)
├── transaction.json            # open transaction; guards Level-2 DB restore
└── backups/<id>.dump           # pg_dump -Fc, magic/size/pg_restore --list + sha256 verified
```

## Bootstrap hop (tooling cannot self-deploy)

First deploy of the tooling must be a manual hop with identical guarantees: verified backup → maintenance ON → stop app → `git fetch` → checkout → SHA-tagged build (tag computed, build to stderr) → migrate → start → wait ready → validate → maintenance OFF → record. Post-#6 spec changes require an explicit proxy recreate at the end.

## Write-channel corruption note

This session's file-write tool corrupted full-file writes several times with injected text ("Full Stack Test…" lines). Ground truth was always `git diff` + `py_compile`/`bash -n`; repairs succeeded via python rewrite with assertion pre-checks, then patch-tool edits. Never commit from a tool echo; commit from a verified diff.
