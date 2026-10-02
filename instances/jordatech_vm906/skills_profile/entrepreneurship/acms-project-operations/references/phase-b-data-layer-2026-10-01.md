# Phase B data layer session detail (2026-10-01 late session, Releases 2–4)

Prod chain: f6ac25b → f14ab2f (#67) → 78c8162 (#68) → 2c67f26 (#69) → ef62e2a (#70) → 11a39de (#71).
LLM Manager: 66f37a50 → fce5ba7 (#74). Alembic 0013 → 0016. Suite 273→303.
Handoff: `~/acms-hygiene-ui-20261001/HANDOFF-20261001-PHASE-B-RELEASES-2-4-COMPLETE.md`.

## Release 2 — UIDs + canonical handoffs (PRs #67, #68)

- `acms/uid_keys.py`: `allocate_work_uid(db, created_at)` / `allocate_artifact_uid` →
  `(seq, "ACMS-WORK-000127-20261001_082241")`. `_next_counter` = INSERT-ON-CONFLICT + UPDATE-RETURNING
  on `acms_key_counters`. `work_uid_from_key(key, created_at)` for backfill derivation.
- Migration `0014_work_artifact_uids`: two-pass backfill (first compute max existing seq from
  `work_key`, then assign), unique indexes created AFTER backfill, counter seeding uses
  portable SQL (SQLite AND PG). Downgrade drops index before columns (SQLite batch trap).
- PG concurrency test pattern: `async_sessionmaker(engine)` per-worker sessions, each commits,
  20 `asyncio.gather` allocations → 20 distinct seqs. NOTE: sessions must COMMIT or
  UPDATE…RETURNING rolls back (first run measured all-1s).
- Canonical handoff hook sites: `completion_callback.process_completion_callback` (after
  `record_execution_usage`) + `telemetry_scheduler._reconcile_execution_results` (after
  EXECUTION_RECONCILED event). Body source: `HandoffRecord` latest for the work item wins
  (`created_by=f"canonical-handoff:{agent|acms_fallback}"`); BLUF extracted from body.
- Artifact resolution order (API + UI `_resolve_artifact`): PK UUID → `artifact_uid == "ACMS-…"`
  → `sha256.startswith(prefix>=8)`.
- PR #68: `JiraClient._markdown_to_adf` — headings→heading1-6, "- "→bulletList, ```→codeBlock,
  multi-line para→paragraph+hardBreak. Doc format: `{"type":"doc","version":1,"content":[…]}`.

## Release 3 — repositories + slop (PRs #69, #70)

- Tables: `repositories` (unique owner+repo, last_* measurement columns),
  `product_repository` / `project_repository` (composite PKs, unique pairs),
  `repository_metric_snapshot` (snapshot_id PK, captured_at idx, error column).
- Collector `measure_repository(owner, repo)`: repos API → default branch → commits/{branch} (HEAD sha)
  → git/trees?recursive=1 → filter `is_code_file` (EXCLUDED_DIRS/SUFFIXES) minus `is_adr_file`
  → per-file contents fetch (base64) → `count_loc` (strips blank/#-line/--- comments, block
  comments, docstrings). Error path: `snap["error"]` set, snapshot still written.
- Human-ADR markers (v1): `status:accepted.*human`, `approved-by|accepted-by|reviewed-by|decided-by`,
  `human (approved|accepted|authored|decision)`, `\bjordan\b`.
- API: POST/GET `/repositories`, POST `/repositories/{id}/refresh`, POST `/repository-metrics/refresh`,
  POST/DELETE `/products/{id}/repositories`, POST `/projects/{id}/repositories`,
  GET `/products/{id}/slop`, GET `/products/{id}/slop-history`.
- Live §39 proof: repo 4bd12a51 (startupteams/acms-project-framework) → product AgentifyMe
  (b325c52c): LOC 22,637 · 21 ADRs · 5 human · True 4,527.4 · Precision 1,077.95.

## Release 4 — power/usage/fleet/search (ACMS PR #71, LLM Mgr PR #74)

- LLM Mgr side: `server_manager/llm_manager/api/facility_power.py` — `GET /api/v1/facility/power`
  (require_identity "usage:read"), self-contained SQL over `get_session_factory("llm")`
  (does NOT import the web app's power_view — layout boundary). Channel labels + STALE_SAMPLE_SECONDS=600
  + rate constants mirror `service/app/power_view.py`. Wired via include_router in api_app.py.
- **Deploy gap re-hit:** deploy-release.sh restarted web/collector/emporia/recovery but NOT
  server-manager-api → endpoint 404'd until `systemctl restart server-manager-api`.
- ACMS side: `acms/power_ingest.py` — `PowerSnapshotRecord` (0016 `power_cost_snapshot`),
  `FacilityPowerClient` (urllib, settings `server_manager_base_url/token`), `ingest_power_snapshot`
  (current_watts = sum of channels only when none stale; last_sample_ts = max), `_summary_from`
  shapes stale→NULL-never-0, `usage_summary(db, hours)` (cost_attribution GROUP BY model+provider,
  cloud=ACTUAL, local=None+ESTIMATE note).
- `acms/search_api.py`: `/power/summary?refresh=`, `/usage/summary?hours=`, `/search?q=` (grouped:
  work/artifacts/agents/projects/products/inbox; min_length=2). Fleet sort/filter extracted to
  `acms.main._fleet_rows_filtered(db, q, sort, harness)` so tests can exercise logic without Depends.
- Live §40 proof (via ACMS): 2,335.7W total; PDU-151 942.1W / PDU-152 706.5W / PDU-153 288.5W /
  mini-split 398.6W; 24h 11.174 kWh $1.7976; 30d 215.225 kWh $34.6232; collector healthy age 41s.

## Debugging war stories (value = the technique)

- **Phantom empty-INSERT integrity error** (`products.product_id NOT NULL`, params all-None +
  status='active'): NOT a bad seed value — it was the double-close flush at generator cleanup
  surfacing a DIFFERENT pending object than the failing test's. Debug sequence that cracked it:
  print `db.new` identity-map contents + mapper column attrs → correct objects → conclude the
  failing INSERT isn't from these → the error traceback pointed at `get_session.__aexit__` close.
  Fix = direct `SessionLocal()` ownership in test helpers.
- **Tests pass isolated / fail in suite** = shared-DB or session-lifecycle pollution, not logic.
  Pairwise-repro (run suspect + one neighbor) narrows fast.
- **SM route 404 after a clean release** = unit not restarted (deploy-release restart list doesn't
  include server-manager-api). openapi.json on :8300 is the instant check.
- **STNA-87 comment flow**: container recreate wiped `/tmp/stna87_comment.txt` — re-scp + docker cp
  after ANY app-container recreate (tmp is ephemeral per container).

## Route-mount map (2026-10-01 verified via /openapi.json)

ROOT: `/artifacts[/{id}][/content]`, `/projects`, `/products`, `/repositories`,
`/repository-metrics/refresh`, `/products/{id}/slop[-history]`, `/model-policy/...`,
`/inbox/...`, `/execution/...`, `/power/summary`, `/usage/summary`, `/search`.
PREFIXED: `/api/v1/work/...`, `/api/v1/agents...`, `/api/v1/budgets/...`, `/api/v1/dispatch/...`,
`/api/v1/memory/...`, `/api/v1/callbacks/...`, `/api/v1/jira/...`.