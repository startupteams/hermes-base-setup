# Window 2 evidence — P2 gateway domain + P3 ingestion (2026-10-03, session continuation)

Condensed live-evidence ledger for the second DKMS window (continuation of
`p0-p1-execution-evidence-2026-10-03.md`). All claims were verified against
live systems, not self-reports.

## P2 — dkms.* MCP gateway domain (COMPLETE, merged)

- **ACMS PR #93 → main `62cfadc`** (`feat/dkms-mcp-domain`, 2 commits:
  `ccd62a2` domain + `43981cf` mint-default scopes). CI syntax/tests/secret-scan all PASS.
- Claude Code P2 run ended `error_max_turns` (81 turns, $6.67): allowlist had
  `Bash(python3 *)` but worker emitted `python -m pytest …` → every verify
  call denied → code written but never self-verified. Orchestrator ran the
  suite itself: 13 failed → root cause = shared test helper
  `tests/test_mcp_gateway_w4.py::make_identity()` lacked `dkms.read/dkms.write`
  scopes. One-line helper fix → 18/18 → merged.
- **Deploy to VM114 = rsync, NOT the ACMS release transaction.** The gateway
  repo checkout at `/opt/mcp-gateway/repo` has NO `.git` (rsync-staged install
  from the workstation per `deploy/mcp-gateway/install-gateway.sh`).
  Procedure: `rsync -a --delete --exclude='.venv-mcp' mcp_gateway/
  vm114:/opt/mcp-gateway/repo/mcp_gateway/` + tests → run suite ON VM114
  (`.venv-acms/bin/python -m pytest tests/test_mcp_gateway_dkms.py` → 18
  passed) → append env → `systemctl restart miam-mcp-gateway`.
  Sha-verify: `git show origin/main:mcp_gateway/server.py | sha1sum` must
  equal `sha1sum` on VM114.
- **Env wiring:** append `MCP_GATEWAY_DKMS_BASE_URL` +
  `MCP_GATEWAY_DKMS_TOKEN` to `/etc/miam-mcp-gateway/env` (0600), then
  restart. healthz `"domains"` must list `dkms` (8th).
- **Token rotation-pair trap (live-found):** first token pair FAILED (48-hex
  vs 64-hex mismatch: gateway env got a truncated/old value). Working pair =
  64-hex. Rotation procedure: generate on VM117 → write to k8s secret
  `dkms-secrets` field `DKMS_API_TOKEN` → `rollout restart deployment/dkms`
  → capture to `/root/.dkms_api_token` (0600) → transfer to VM114 env
  WITHOUT echoing (python heredoc over ssh) → restart gateway → probe
  `GET /api/v1/records?limit=1` = 200.
- **MCP live gate (all through real MCP `resources/read` / `tools/call`):**
  - `tools/list` → 8 dkms tools (ingest_plan, ingest_handoff,
    record_timeline_entry, record_failure, record_recovery_attempt,
    record_lesson, record_decision, mark_training_eligibility).
  - `resources/templates/list` → 5 dkms templates; static
    `dkms.audit.recent` in resources/list.
  - `dkms_record_lesson` write from a minted probe token with NO work item →
    record created (plan §9.6 STEA direct path); `agent_uid` arrives empty
    from a fresh agent token (documented; assignment tokens stamp it).
  - Quarantine: `dkms_ingest_plan` with `AWS_SECRET_KEY=…` in body →
    `QUARANTINED: Content contains potential secrets` (no retry).
  - 5/5 resources read OK after the template fix (below).
- **SDK template-matching bug (gateway-wide, PR #94 → main):**
  `FastMCP ResourceTemplate.matches()` builds its regex via naive
  `{`→`(?P<` substitution — regex specials in URI literals stay UNESCAPED,
  so the `?` of `?q={query}` becomes an optional-quantifier and
  `dkms://search?q=x` can NEVER match ("Unknown resource"). Affects any
  domain using query-string templates. Fix =
  `GatewayServer._patch_template_matching()` (idempotent monkeypatch,
  regex-escapes literal chunks) applied in `__init__`. Unit test
  `test_template_matching_handles_query_strings`. Live gate after deploy:
  search / records-recent?limit / export?work_uid / record/{uid} /
  record/{uid}/related — 5/5. (export WITHOUT the work_uid param =
  "Unknown resource" — template requires the var; document as UX limit.)
- **Existing-token scopes:** mint defaults gained dkms.read/dkms.write (PR
  #93 follow-up); existing tokens patched via
  `.venv-mcp/bin/python -m mcp_gateway.cli grant-scopes stea-004
  dkms.read,dkms.write` (unions into ACTIVE tokens; DB-verified).

## P3 — ingestion endpoints (COMPLETE, merged)

- **DKMS PR #8 → main `a6a06af`** (`feat/dkm-p3-ingestion-paths`), written
  autonomously by background Claude Code (34 turns, $1.89), CI green,
  handoff file `HANDOFF-P3-INGESTION.md` written by the worker (Jordan's
  steering: autonomous background + markdown handoff on completion).
- Adds `/api/v1/ingest/plan`, `/ingest/handoff` (source+summary+summarizes
  link), `/ingest/timeline` — all idempotent on (source_uid, content_sha256)
  reusing PR #6 semantics. No migration needed.

## P4 seed — failure learning LIVE (schema + lifecycle + links)

- `POST /api/v1/failures` → failure `8c1a74405…` (qga wedge VM117,
  class infrastructure_guest_agent). Body contract: `signature`,
  `failure_class`, `system`, `symptoms`/`evidence` as DICTS (dict_type
  validation errors on strings — the gateway tool maps string args into
  dicts).
- `POST /api/v1/failures/{uid}/attempts` → attempt #1 (method, result,
  time_to_recovery_seconds, side_effects dict, rollback_used, confidence,
  validation_status). attempt_number is server-assigned (count+1) — do not
  send it.
- Lessons as records: `lesson_learned` with `authority_class=VALIDATED_LESSON`,
  `training_eligibility=approved`, `training_approval_mode=auto_policy`,
  `training_eligibility_reason=…` → stored as
  `approved/auto_policy/not_reviewed` (plan §11.1 auto-approval PROVEN live).
  Seeded: 5c756007 (qga wedge), 92cb2208 (PVC affinity).
- Link failure→lesson: `POST /api/v1/links
  {from_uid:<failure_uid>, to_uid:<lesson_uid>, link_type:"fixed_by"}` →
  works only AFTER PR #7 (FKs dropped, API-layer existence validation).
  `GET /api/v1/records/{uid}/related` returns the lesson.
- UIDs are 32-hex, full length required (FK/validation on truncated uid →
  500 IntegrityError / 422).

## K3s infra lessons (VM117)

- **Stale-node deletion leaves PV affinity pinned:** after force-deleting
  the old control-plane node (`acms-worker-template`), the local-path PV
  kept `nodeAffinity kubernetes.io/hostname In [acms-worker-template]` →
  postgres pod Pending ("didn't match PersistentVolume's node affinity").
  PV nodeAffinity is IMMUTABLE (apply of patched PV 422s). Fix: delete pod →
  delete PVC → delete the stale PV dir under
  `/var/lib/rancher/k3s/storage/` → re-create the PVC (local-path
  auto-reprovisions on the live node) → statefulset rebinds. Data was
  throwaway; for real data copy the PV dir to the new node path first.
- **Postgres durability PROVEN:** `delete pod dkms-postgres-0` → recreate →
  18 records before = 18 after (closes plan P1 residual acceptance).
- **Init-container embedded GitHub token:** the build-init overlay shipped
  with the token inline in the clone URL. Fixed live: token moved into k8s
  secret `dkms-secrets` field `GITHUB_TOKEN`, init env wired
  `envFrom: secretRef dkms-secrets` (+ `k3s kubectl set env deployment/dkms
  --containers='*' --from=secret/dkms-secrets --prefix=''` to give the APP
  container the same envFrom), manifest scrubbed
  `sed -i 's/gho_[A-Za-z0-9]*/REDACTED/'`. Keep this shape for future overlays.
- **Hot-fix deploy into a running pod (no registry):** `k3s kubectl cp
  <file> dkms/<pod>:/tmp/x.py -c dkms` → python `shutil.copyfile` to
  `/usr/local/lib/python3.12/site-packages/dkms/<mod>.py` (wheel install;
  there is NO /app dir) → restart via `python3 -c 'import os;
  os.kill(1, 15)'` (the `kill` BINARY is absent from python:3.12-slim —
  `exec kill 1` fails) → verify the NEW process has the patch (stale pod
  file-surgery across restarts silently reverts — delete the pod instead
  and re-apply into the fresh pod).
- **Idempotency cleanup pattern:** pre-fix duplicate records were marked
  `status=superseded` + `supersedes_uid` (keep-oldest) via a pod-exec
  python/SQLAlchemy script — never DELETE (AGENTS.md rule 7).
- **record_type vocabulary (live):** `plan, raw-transcript, raw-log,
  source-file, source-artifact, raw-event, summary, handoff-summary,
  decision, lesson_learned, playbook, architecture, implementation, review,
  test-result` — 400 error lists it; `handoff-summary` (dash) not
  `handoff_summary`; `lesson_learned` (underscore) not `lesson-learned`.

## Plan §15 checkpoint after this window

P0 ✅ P1 ✅ P2 ✅ P3 ✅ · P4 seeded (lifecycle UI/playbook promotion remain) ·
P5 context_pack · P6 ACMS artifact pointers · P7 retention purge + training
export + restore proof + PG backup install · P8 golden workflow with
intentional safe failure. Handoff:
`~/dkms-build-20261003/HANDOFF-20261003-DKMS-WINDOW.md`.
