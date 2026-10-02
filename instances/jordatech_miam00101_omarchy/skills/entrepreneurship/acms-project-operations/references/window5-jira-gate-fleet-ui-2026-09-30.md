# Window 5 (2026-09-30) — Jira kickoff gate, fleet visibility, product bootstrap: session detail

Handoff: `~/flight-work-20260930-llm-fleet-ui/FINAL-HANDOFF-20260930-W5.md`
Prod end state: ACMS CT122 `404ad54` (alembic 0011) / LLM Manager VM114 `d021f70`.

## Fleet one-card bug — root cause chain (the investigation is the reusable part)

Symptom: LLM Manager dashboard showed ONE inference-host card; 5 of 6 hosts served `/v1/models → 200`.

Investigation ladder that found it:
1. Read `/api/status` handler — returns `_active_hosts()` (all hosts, active first, inactive demoted). Looked correct.
2. **Reproduced by importing the DEPLOYED module on prod** (`sys.path.insert(0, "/opt/llm-manager/current/app")` + call `_active_hosts()`) → returned 1 host. This was decisive — code reading alone kept saying "fine".
3. Stepped the loop manually → `_physical_host_for_ip()` returned MIAM-00111 for EVERY ip.

Root causes (PR #69):
- `ip.startswith("10.0.20.16")` matched .161/.162/.163/.164/.165/.168 — ALL guests collapsed onto one physical label; `_active_hosts()` promoted only the first DB match.
- The demotion loop's docstring said "demoted to the END" but the code checked `if phys not in promoted` — a rollback VM sharing its physical host was silently DROPPED, not demoted.

Fix pattern: exact-IP checks BEFORE any prefix/range match; demote-but-never-drop via an `active_ips` set. Regression tests assert the distinct-label invariant over the real inventory.

Lesson: **prefix/range IP→group mapping must list exact IPs first, and every "demote" path must append — write the test that counts distinct groups over the real inventory.**

## Verifying the /api/status bug is real (398-byte smoking gun)

nginx access.log showed `200 398` for browser `/api/status` requests — a 6-host payload is ~1.5–2 KB, 398 bytes ≈ 1 host. Log-line payload-size arithmetic on an endpoint you can't auth into is a fast truth check.

## Jira kickoff gate facts (live-verified)

- STNA workflow statuses: BLOCKED / TO START / IN PROGRESS / COMPLETED / IDEA-UNVALIDATED / IN REVIEW / DEFERRED; transition id 2 = `Validated/Committed` → TO START (human gate). Ready = `TO START` via `ACMS_JIRA_READY_STATUSES` (never assume globally).
- The Jira integration's service account IS `startupteamscompany@gmail.com` = accountId `712020:520fb263-ef0f-425c-a0be-14e9d258917e` (resolved via `/rest/api/3/users/search?query=…`). Assignments matched by accountId only.
- Deployed activation trap (recurring): compose `environment:` resolves at container CREATE — after adding env to `/opt/acms/.env`, recreate with the PINNED image tag, then verify in-container non-emptiness (length only).

## Test-fixture lessons (Settings lru_cache + import bindings)

- Mutating a cached Settings instance then `cache_clear()` silently no-ops — the mutation is discarded. Set env vars via monkeypatch + cache_clear on entry/exit.
- `from .x import Y` binds at import time: patching `acms.x.Y` does not rebind `acms.z.Y` for a module that did `from .x import Y` — patch every importing module (hit with JiraClient in jira_api vs jira_client).
- Mock DB-bound fields with real values (SimpleNamespace), never `mock.Mock` — a Mock attribute hits SQLite `Error binding parameter: type 'MagicMock' is not supported`.
- Pinned-revision migration tests must pin the EXACT revision (0009), not head, once later migrations (0010+) exist.

## Product bootstrap honesty contract

- Parser (`acms/product_bootstrap.parse_idea_markdown`): grounded metadata only; unknown frontmatter preserved verbatim under `extra`; one nested level (score_inputs) supported.
- `draft/unvalidated` → requirements_class `assumption` — tests assert assumptions NEVER become accepted requirements (real fixture `home-service-missed-call-agent-ops.md`, clone at `~/work/business_idea_generator`).
- Repo adapter: fine-grained PATs CANNOT create repos (403) → `repo-create-forbidden` human-gate error, artifacts retained, request resumable; reuse-if-exists; per-file docs push is update-or-create (idempotent).
- Resumable core: `bootstrap_requests` table, per-step durable results in `steps_json`; retries return identical hierarchy ids (test-verified); ambiguous outcomes await operator; nothing deleted to compensate.

## Live UI verification recipes (no LDAP creds needed)

- Mint an HMAC session cookie in-container from `ACMS_SESSION_SECRET` (payload {"u","r":"administrator","exp"}; b64url(payload).b64url(hmac)) → probe `http://127.0.0.1:8000/ui/...` inside the container. Never print the secret.
- Machine-API probes use `ACMS_ADMIN_TOKEN` bearer inside the container.
- Move files into the container via `docker cp` (compose exec can't see CT /tmp).

## Open items carried to next window

1. Jordan creates private repo `startupteams/home-service-missed-call-agent-ops` → re-run bootstrap request `6f5e1f65-9eef-4225-a62b-e236b4611136` (completes docs → hierarchy → Jira link → gate check).
2. Jordan validates + assigns one designated Jira issue → full §13.2 live transition proof (everything else deployed).
3. Optional: disposable wizard-created test agent (§4.4) with a chosen disposition.