# ADR-0012 Completion Callback — Live Implementation Notes (2026-09-29, PRs #45/#46/#47)

## Canonical architecture (Accepted)

```
Bridge/worker completion callback = PRIMARY immediate completion signal
ACMS reconciliation sweep         = FALLBACK / repair mechanism
```

## Contract

- Endpoint: `POST /api/v1/callbacks/execution-completion`
- Auth: dedicated scoped bearer `ACMS_CALLBACK_TOKEN` (NEVER the admin token).
  Unset ⇒ 503 fail-closed. Missing header ⇒ 401. Wrong token ⇒ 403.
- Payload (durable semantics only — never transcripts/token streams):
  `{task_id, acms_agent_id, a2a_run_id?, status: SUCCEEDED|FAILED|CANCELLED,
    completed_at?, result_reference?, handoff_reference?, error_summary?,
    usage_reference?}`
- Responses: 200 `result=closed` | 200 `result=already_terminal` (idempotent
  replay) | 404 unknown-task (+audit) | 403 agent-mismatch fail-closed (+audit)
  | 422 invalid-status.
- CT122 env: `ACMS_CALLBACK_TOKEN` (hex-24 via openssl rand in /opt/acms/.env)
  + `ACMS_CALLBACK_BASE_URL=https://10.0.20.122`; compose passthroughs in
  PR #47 (which also added ACMS_JIRA_* + ACMS_GITHUB_ECONOMICS_TOKEN —
  compose environment blocks enumerate explicitly, always add new settings).

## Dispatch-side changes (PR #45)

- Execution task is PRE-created before the bridge call (step 4b); failure to
  record it aborts the dispatch (nothing sent, budget not consumed).
- The instruction carries a COMPLETION PROTOCOL block with the endpoint, the
  task_id, the agent id, and the JSON body shape — gated on
  `ACMS_CALLBACK_BASE_URL` (empty ⇒ no hint; reconcile remains the authority).
- After `send_work`, the A2A run id back-fills `task.external_task_id`.
- **Idempotency ledger moved:** dedupe used to live in
  `external_task_id == "disp-<key>"`; now the EXECUTION_DISPATCHED event
  metadata carries `{dedupe_key, task_id}` and `_find_existing_task` scans
  recent dispatch events (PR #32 reassignment-counter pattern — durable audit
  log doubles as the ledger). The reconciler sweep explicitly SKIPS
  `disp-%` external ids (they are not real A2A run ids).

## Reconciliation sweep (telemetry scheduler)

- `_reconcile_execution_results` — rate-limited (`ACMS_CALLBACK_RECONCILE_SECONDS`,
  default 300), bounded batch (20), skips tasks without agent_id.
- Closes RUNNING tasks whose bridge `/v1/runs/<id>` status is terminal
  (`completed|succeeded|failed|cancelled|canceled` mapped to ACMS statuses);
  emits `EXECUTION_RECONCILED` with the session_id in metadata.
- **Closes the correlated OPEN ExecutionSession in the same pass** (ADR-0012 §C5)
  — the live proof exposed the missing half: the first deploy closed the task
  but left the session OPEN (PR #46 fixed; both orderings now repair:
  task-then-session AND orphaned-session-with-terminal-task, incl. when the
  task batch is empty).
- Attention/SSE: EXECUTION_COMPLETED → NO attention item (explicit None in
  `_derive`); FAILED → high; CANCELLED → medium; CALLBACK_REJECTED → high;
  RECONCILED → info. All four new event types added to both allowlists.

## Live proof (2026-09-29, ACMS-WORK-000004)

```
dispatch 200 within_budget (task f2423cae…, run_97ec00a4…)
→ ExecutionSession auto-OPEN
→ Hermes (VM124) run completed: output ADR0012-CALLBACK-PROOF-OK
   (12,578/142 tokens, $0 local — LiteLLM SpendLogs 14:47:46 row;
    SpendLogs lives in the `litellm` DATABASE, not `llmmanager`)
→ worker did NOT call back (GLM-fast ignored the instruction protocol)
→ scheduler sweep closed the task from bridge run status (EXECUTION_RECONCILED)
→ session CLOSED (ended_at set) — zero manual close
→ Attention stayed 0; smoke 12/12
```

**Lesson:** treat the reconcile sweep as the working completion authority
until a runtime-side callback hook exists (Hermes api-server has no
run-completion webhook). The ADR anticipated exactly this — "lost callback →
reconciliation eventually repairs state".

## Probe recipes

From the CT HOST (never from inside the app container — nginx 403s
container-network sources):

```bash
ssh root@10.0.20.122 'CT=$(grep "^ACMS_CALLBACK_TOKEN=" /opt/acms/.env | cut -d= -f2)
B=https://10.0.20.122/api/v1/callbacks/execution-completion
# missing token → 401; wrong → 403; unknown task → 404 (+audit event)
curl -sk -o /dev/null -w "%{http_code}\n" -X POST "$B" -H "Authorization: Bearer $CT" \
  -H "Content-Type: application/json" \
  -d "{\"task_id\":\"no-such-task\",\"acms_agent_id\":\"a\",\"status\":\"SUCCEEDED\"}"'
```

DB-side verification (SQL via file — inline quotes through nested ssh are
fragile; write the SQL locally, scp, `psql -f`):

```sql
SELECT event_type, count(*) FROM agent_events
WHERE event_type LIKE 'EXECUTION%' GROUP BY 1 ORDER BY 1;
```

## Test-suite notes (tests/test_completion_callback.py)

- The shared SQLite unit DB persists rows across tests in one pytest run —
  the state-sensitive suites MUST use the `clean_db` fixture (event-count
  assertions otherwise see prior tests' rows).
- `get_settings()` is lru_cached: env-var fixtures must `get_settings.cache_clear()`
  on entry AND exit (see test_work_creation_guard.py pattern).
- Reconciler tests monkeypatch `acms.bridge.get_bridge_for_agent` (the module
  attribute the scheduler resolves at call time), not the scheduler module.
- Sync `TestClient(app)` + async dependency override (`app.dependency_overrides[get_session]`)
  is the established endpoint-test pattern; httpx.ASGITransport with a SYNC
  client fails ("ASGITransport object has no attribute handle_request").