# Jira reconciliation intake and completion write-back

## PROVEN LIVE 2026-10-02 (STNA-88 stop gate PASSED, prod 07043f1)

- Intake chain works end-to-end: eligible issue → fail-closed project map →
  exactly-one Work Item (UID) → idle worker (prefers HEALTHY) → assign_primary →
  dispatch_service (budget+Jira gates) → bridge ACK → watcher completion →
  canonical handoff → Jira BLUF with exact artifact URL. Second reconcile = zero
  duplicates. Probe recipes: docker cp a python script into acms-acms-app-1 and
  run against `http://127.0.0.1:8000` (nginx 403s loopback from the CT host;
  container-internal loopback is fine).
- **ADF heading trap (live 400):** `_markdown_to_adf` MUST emit
  `{"type":"heading","attrs":{"level":N}}` — `type:"heading2"` etc. is INVALID
  ADF; Jira Cloud 400s INVALID_INPUT and only the durable `JIRA_OUTBOUND_FAILED`
  events reveal it. Unit conversion tests never hitting real Jira can't catch
  node-shape bugs — **every acceptance run must make ONE live outbound write
  probe per integration surface** (3rd instance of the unit-green/live-400
  class).
- **Hermes 0.19 run approval:** dispatched runs may pause
  `waiting_for_approval` (last_event `approval.request`). Resolve via bridge
  `POST /v1/runs/{id}/approval` body `{"choice": "session"}` — valid choices
  are once/session/always/deny; "approve"/"approved" are INVALID (400
  invalid_approval_choice). 409 "no pending/active approval" = raced a
  tool-cycle; retry when `approval.request` reappears. For unattended Jira
  intake, pre-authorize the dispatch tool in the worker profile.
- **Self-merge overrides are SESSION-SCOPED.** The 2026-09-26 and 10-02-morning
  overrides expired with their sessions. A new continuation session has NO
  carry-over merge authority: open the PR (CI green + mergeable CLEAN is not a
  merge authorization), leave it for Jordan, and proceed with work that does
  not require the merge (e.g. deploying an independent service from the branch
  when the approved plan authorizes it). Document the non-merge as an honest
  deviation in the handoff.
- Recovery for a missed write-back after a fix deploy: the
  `JIRA_HANDOFF_POSTED` exactly-once guard blocks auto-redelivery (correct);
  re-post the identical body through `JiraClient` in-container and record the
  guard event with `actor_source=operator_recovery`.
- Assignment list API (`/api/v1/work/assignments`) renders
  dispatched_at/acknowledged_at/bound_session_id as NULL/"" even though
  dispatch-time writes succeeded — verify via events, not the list repr.
- **AI-created Jira tickets start at `IDEA/UNVALIDATED`** (Jira project default),
  NOT at a ready status. Reconciliation honestly reports `not_eligible` with
  reason "issue status 'IDEA/UNVALIDATED' is not a configured ready state" and
  creates no work. Moving a ticket out of IDEA/UNVALIDATED is a HARD HUMAN gate
  (Jordan's rule: no AI status mutation on IDEA/UNVALIDATED tickets) — when a
  test ticket is needed for an acceptance proof, create it, hand Jordan the key,
  and route the rest of the proof through OTHER paths until he transitions it.
- Dispatch of any ACMS Work Item is gated on Jira linkage (`jira_gate.py`,
  verdict NOT_LINKED → `jira_gate_not_linked`); there is NO bypass env. A
  work item without a linked Jira issue can only be assigned, never dispatched.

## Failure class: successful run with zero action

A reconciliation run can honestly report `completed` while silently doing no useful work if eligible, unlinked Jira issues are only emitted as candidate observations. Diagnose from all three layers:

1. Read the issue directly from Jira using credentials already inside the ACMS container; report only sanitized identity/status/template fields.
2. Query the reconciliation run ledger **and** per-issue events/counts.
3. Search source for the unlinked-candidate branch and identify whether it imports, links, assigns, and dispatches—or merely observes then returns.

A run with `examined > 0`, `added=0`, `started=0`, `failed=0`, plus candidate-only events is a first-class outcome, not proof of working intake.

## Correct intake contract

When human intent is expressed by both immutable AI-account assignment and a configured ready status:

1. Evaluate eligibility using immutable Jira `accountId`, never display name/email.
2. Map Jira project key to an ACMS Project; fail closed and record `project_unmapped` if absent.
3. Enforce exactly-once intake by immutable Jira issue ID and the unique issue link.
4. Handle the crash window where Work UID allocation committed but issue-link creation did not: detect an orphan Work Item by Jira ID/key, repair its link, and continue rather than duplicate.
5. Create one high-level Work Item with normalized ADF description and immutable Work UID.
6. Select a configured idle worker, preferring healthy telemetry, while treating bridge availability/dispatch as the final gate.
7. Create a primary assignment and dispatch only through `dispatch_service` so Jira, budget, idempotency, and audit gates remain authoritative.
8. Treat bridge acceptance as assignment acknowledgement. If dispatch errors or returns blocked, close/release the assignment immediately so the worker is not permanently locked busy.
9. Emit a durable per-issue outcome for every examined issue (`started`, `not_eligible`, `project_unmapped`, `queued_no_worker`, `queued_dispatch_error`, etc.). Expose these outcomes in API/UI; never make operators infer them from run totals.
10. On repeated reconciliation, create no duplicate Work, assignment, task, or generation.

## Completion write-back contract

After terminal success:

1. Generate/reuse exactly one canonical Markdown handoff Artifact.
2. Move local Work to `in_review` and close active assignments.
3. Build the exact Artifact URL from configured ACMS base URL; UI detail routes accept Artifact UID where supported.
4. Post a concise Jira BLUF containing Work UID, Artifact UID, exact URL, and SHA-256; do not dump raw Markdown.
5. Transition to `IN REVIEW` only behind the explicit disabled-by-default mutation flag.
6. Make duplicate callbacks idempotent with a durable write-back event.
7. Audit Jira write-back failure without rewriting task success. Design a retry path from durable task/artifact state rather than requiring model compliance.

Jira Cloud REST v3 comment bodies must use Atlassian Document Format; use `JiraClient` conversion helpers rather than posting plain strings.

## Secret-safe production probing

Run a temporary Python probe inside `acms-app` and read Jira URL/email/token from `os.environ`. Never echo env values or embed tokens in command lines, evidence, or handoffs. Prefer base64-staged stdin or a world-readable, non-secret script copied into the container; container processes commonly run unprivileged, so root-owned mode `0600` scripts in `/tmp` fail with permission denied. Remove staged files as root after execution.

## Acceptance proof

For a Jira-to-agent stop gate, retain exact evidence for:

- reconciliation run ID and per-issue `started` outcome;
- one Work UID, Project mapping, worker, assignment key, and bridge ACK;
- Jira `IN PROGRESS` transition under policy;
- requested implementation, tests, PR/merge SHA, safe release ID, `/version`, health, migration, smoke;
- one canonical handoff Artifact UID and exact live URL;
- Jira BLUF and `IN REVIEW` transition;
- second reconciliation proving idempotency.

Do not begin a dependent integration phase (for example MCP) until every stop-gate item is proven live.

## Low-budget safe checkpoint

When Jordan says usage is nearly exhausted and asks for an immediate wrap-up:

1. Stop expanding scope.
2. Run the smallest meaningful compile/focused-test/diff checks.
3. Commit and push the current branch if the change is coherent and tested.
4. Open a **draft** PR; do not merge or deploy an unreviewed checkpoint.
5. Produce one Markdown handoff with BLUF, verified live baseline, root cause, commit/PR, test evidence, exact remaining sequence, rollback, and explicit untouched phases.
6. Deliver the file directly to Telegram.

This preserves resumability without falsely reporting the plan complete.