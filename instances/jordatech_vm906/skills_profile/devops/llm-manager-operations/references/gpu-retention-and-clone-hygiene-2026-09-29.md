# 2026-09-29 — GPU retention Option A + clone hygiene (flight notes)

Backing detail for `llm-manager-operations`. Handoff of record:
`~/flight-work-20260929-acms/` (window 1) + the 2026-09-29 execution plan doc.

## GPU retention Option A — LIVE (PRs #53–#56)

**Schema** (migration `002_gpu_samples_hourly_retention.sql`):
- `gpu_samples_hourly(hour_bucket, host_id, gpu_index)` PK; columns:
  sample_count, util_min/max/avg, mem_used_min/max/avg_mib, power_min/max/avg_w,
  power_sum_wh, last_ts. Rollup grain chosen to preserve every statistic main.py
  derives from gpu_samples (latest-24 per host, 5-min health count, hourly avg util).
- Config knobs seeded into `manager_settings`: `gpu_samples_retention_days=90`,
  `gpu_samples_hourly_retention_days=730`. Partitioning DEFERRED (TDR-0011) with
  explicit revisit triggers (>2x MB/day growth, >5min delete batches, 2s p95, ingest
  outpacing prune).
- CI trap: migration had `ALTER TABLE ... OWNER TO llmmanager` → CI PG has no such
  role → `db` check failed. Fix: `DO $$ BEGIN IF EXISTS(pg_roles llmmanager) THEN
  ALTER ... END IF; END $$`.
- ASCII trap: `migrate.py` on VM114 decodes with ascii locale — a `§` in a comment
  caused `UnicodeEncodeError` mid-release-transaction and rolled back the candidate.
  Migrations must be ASCII-only.

**Service** `service/app/gpu_retention.py` (run with the release venv python;
system python3 lacks psycopg2):
- `rollup` = idempotent upsert over trailing 3h; `backfill` = resumable 24h chunks;
  `verify` = raw-vs-rollup spot checks; `dry-run-prune` / `prune` / `maintenance`.
- **Verify only CLOSED WHOLE hours.** Two live-found false-failure modes:
  (1) open hours race raw ingest between the raw aggregate and rollup read;
  (2) window-boundary hours: verify's raw aggregate truncates the hour but the
  rollup row holds the full hour. Restrict sampling to
  `date_trunc('hour', ts) < date_trunc('hour', now())` AND whole hours inside the window.
- **Backfill chunks must be hour-aligned.** A 24h chunk ending mid-hour (raw min
  22:40) re-aggregated the straddling hour from partial data and the upsert
  OVERWROTE the full aggregate with the partial one → verify failed with rollup
  count < raw count until re-backfilled with aligned chunks.
- **Prune gates (fail-closed, in order):** rollup table exists → backfill complete
  (raw min ts >= rollup min bucket) → verify passes → backup gate recorded in
  `manager_settings` key `gpu_retention_backup_verified_at` → dry-run reviewed →
  bounded batch deletes (`sample_id IN (SELECT ... LIMIT 50k)`) + `VACUUM ANALYZE`
  outside the transaction.
- **Backup gate live:** CT115 (llm-postgres, 10.0.20.116, on node miam00147) —
  vzdump 115 --storage pbs-marion --mode snapshot from root@10.0.20.147 (VM114 has
  no PVE rights; CT122 not on that node). Then INSERT the gate key.
- Re-measured baseline: 1,597,825 rows / 198 MB total / ~82k rows/day; raw spans
  2026-09-09 → now; prune executed and deleted 0 (nothing older than 90d).
- **Timer installed on VM114:** `llm-manager-gpu-retention.{service,timer}`, hourly,
  `Persistent=true`. ExecStart path MUST be
  `/opt/llm-manager/current/app/gpu_retention.py` (release layout) — the first
  install pointed at `/opt/llm-manager/app/` and failed with exit 2.

## ORM Slice 5 — write-path parity (PR #58)

- `server_manager/llm_manager/repositories/write_paths.py`: HostWrites
  (update_node_vmid_by_ip / set_desired_power_state / set_management_mode),
  ModelRegistryWrites.mark_host_unroutable (by **host_id** — v011_core:266 legacy
  SQL filters host_id, not fingerprint), RecoveryEventWrites.insert_event,
  run_parity_check (row-count + md5 content checksum probe).
- Contract: repos mirror legacy SQL semantics EXACTLY so a shadow-run row diff is
  the cutover verification. Legacy cutover NOT done yet.
- Test traps: CI lacks `greenlet` → any test importing the async repos must
  `pytest.skip` on ImportError (twice caught by CI). Embedded-PG fixture must
  create the `llmmanager` role before schema.sql and seed a second hosts row
  (model_registry FK on host_id). Local workstation needed
  `pip install pgserver psycopg2-binary alembic itsdangerous 'sqlalchemy[asyncio]' asyncpg`.

## Clone hygiene (PR #57, plan Phase H)

`server_manager/agent_runtime_manager/services/clone_hygiene.py`:
`verify_clone_identity(vmid, hostname, mac, ip, expected_agent_id, guest_agent_id,
other_runtime_ips)` — fail-closed `HygieneError` on: invalid/template-default MAC,
hostname starting with "template", IP owned by another runtime's metadata,
**inherited conflicting static netplan** (reads guest netplan via `qm guest exec`
— THE VM108/VM124 .203 collision root cause), guest agent_id mismatch.
Deliberately NOT wired into `provisioning.py _provision_vm` yet — pure additive
module; enforcement-in-path is the next slice. "No current ARP response" ≠ IP free.

## Open items

- PRs #57/#58 merged but NOT yet deployed to VM114 (next release transaction).
- Wire clone-hygiene into `_provision_vm` step 5.5 (needs Jordan's nod — changes
  live provisioner behavior).
- ARM-authoritative bridge discovery deployed on the ACMS side (ACMS PR #42);
  the ARM runtime record may later carry `bridge_base_url`/`bridge_api_key`
  directly, which the discovery module already prefers.
