# Jira-to-outcome golden workflow — end-to-end run (2026-10-03, STNA-90 / ACMS-WORK-000019)

Session: STEA-004 overnight autonomous run. Full handoff of record:
`~/agentifyme-workflow-20261003/HANDOFF-20261003-AGENTIFYME-JIRA-BUSINESS-IDEA-WORKFLOW.md`
(also registered as ACMS-ARTIFACT-000008). This file holds the durable, repeatable recipe.

## The proven chain (every step verified live)

1. **Fetch live template STNA-86 via Jira REST** (gateway-held credential on VM114:
   source `/etc/miam-mcp-gateway/env`, values `MCP_GATEWAY_JIRA_EMAIL` +
   `MCP_GATEWAY_JIRA_API_TOKEN`, base `https://startupteams.atlassian.net`).
   Capture the FULL ADF description to JSON (55-node structure: SP guide +
   Title/Product/Project/Sprint/Problem/Scope/Output Artifacts/Assignee/Reporter
   fields separated by hardBreak nodes).
2. **Clone = re-PUT the template ADF.** POST a new issue with
   `{project: STNA, issuetype: Epic, summary, description: <template ADF>, priority,
   reporter}` (createmeta: Epic requires summary/issuetype/project/reporter).
   The Jira create API REORDERS/merges ADF content — after creation, PUT the
   template description back with scope edits (3 purge passes were needed to
   strip residual template hint lines like "(i.e. ...)"). Verify by comparing
   node-type sequences AND rendered text between template and clone.
3. **Eligibility (authorized move):** the clone starts at IDEA/UNVALIDATED.
   Reconcile honestly reports `not_eligible` until: (a) assignee = AI account
   (PUT `{"fields":{"assignee":{"id":"712020:520fb263-ef0f-425c-a0be-14e9d258917e"}}}`
   — the integration's own service account), (b) transition id 2
   (Validated/Committed → TO START). Both via direct Jira REST under session
   authorization; gateway mutation flag stays fail-closed (policy decision for
   Jordan). Then ACMS "Check Jira" = `POST /api/v1/jira/reconcile` with
   ACMS_SERVICE_TOKEN bearer.
4. **One Check-Jira run does everything:** examined → exactly-one Work Item
   (ACMS-WORK-000019-20261002_191836) → assignment ACMS-ASG-000016 ACKed →
   runtime accepted → EXECUTION_DISPATCHED → session auto-OPEN → task RUNNING.
   Re-run reconcile → added=0 (idempotent; no duplicates).
5. **Completion is fully automatic:** bridge run SUCCEEDED → task SUCCEEDED →
   session auto-CLOSED (watcher/reconciler path) → `JIRA_HANDOFF_POSTED`
   (started-comment + BLUF-success comment with artifact UID, handoff URL,
   SHA-256). Zero manual close.
6. **Worker dispatch model note:** effective_model resolved from the agent
   default route (qwen3.8-flash-next); execution_sessions.model_id stays NULL
   at open (known gap).

## Dispatch auto-mint needs an AGENT token per worker (live-found)

`MCP_ASSIGNMENT_MINT_FAILED` fired on dispatch because worker uid-002 had NO
agent token in the gateway token store (only uid-001/005 had them). The mint
API (`POST /internal/mint-assignment` with `MCP_GATEWAY_INTERNAL_TOKEN`
bearer) needs `agent_name` + `work_uid` and resolves the agent's EXISTING
token; 404 OUT_OF_SCOPE "no active agent token" otherwise.

Fix recipe (raw token printed EXACTLY ONCE — pipe to a 0600 file, never logs):
```
ssh vm114 'cd /opt/mcp-gateway/repo && \
  /opt/mcp-gateway/repo/.venv-mcp/bin/python -m mcp_gateway.cli \
  mint-agent acms-hermes-worker-uid-002 --acms-agent-id <uuid>'
```
(Do NOT run the CLI without cd — module resolution fails outside the repo.
The venv python alone can't find mcp_gateway either; run from the repo dir.)
Deliver to the worker via qga write (`pve_qga.py write <node> <vmid>`) to
`/root/.mcp-assignment-token`, chmod 600, sha-verify both sides. Verify MCP
path live from the worker: `curl POST http://10.0.20.108:8202/mcp` with
initialize → 200, tools/list → full domain surface (32 tools for a full-scope
assignment).

## Worker identity resolution (which VM is which uid)

Server Manager `GET /api/v1/agent-runtimes` (bearer MCP_GATEWAY_LLM_TOKEN on
VM114) → find the runtime whose `acms_agent_id` matches the ACMS agent →
`node` + `vmid` + `hermes_profile_name` + state fields are on the SAME row
(the list response embeds full records despite sparse-looking first fields).
Then qga for exec/write.

## Transition map discovered live (STNA project workflow)

- IDEA/UNVALIDATED → (2) TO START, (15) back to IDEA, (13) DEFERRED, (14) BLOCKED
- TO START → (4) IN PROGRESS
- IN PROGRESS → (11) IN REVIEW, (10) back to TO START, (13) DEFERRED, (14) BLOCKED
- COMPLETED is a HUMAN reviewer action. Discover transitions at runtime:
  `GET /rest/api/3/issue/<KEY>/transitions` (ids 2/4/11 proven live).

## ACMS artifact registration (REST, no /api/v1 prefix)

`POST https://10.0.20.122/artifacts` (ACMS_SERVICE_TOKEN bearer) — schema
ArtifactCreate: work_item_id, project_id, jira_issue_key, artifact_type,
title, content (full text), mime_type, metadata. Returns artifact_uid
`ACMS-ARTIFACT-######-YYYYMMDD_HHMMSS` + server-computed sha256 of content.
`GET /artifacts/{artifact_id}/content` returns a JSON ENVELOPE
`{artifact_id, title, sha256, content}` — hash-verify by sha256ing the
embedded `content` string (matching the envelope + original file proves E13).
The `/artifacts?work_item_id=` list shows type + sha per artifact.

## Vercel business-idea viewer (protected) — verification + deploy

- Site: businessideagenerator-three.vercel.app; unauth → 401, Basic Auth
  (user `jordan`), creds in Vercel env (BASIC_AUTH_*, NOT retrievable via
  `vercel env pull` — sensitive values come back as empty strings). The
  working credential lives in Jordan's convention: stage to a 0600 file.
- `VERCEL_TOKEN` (vcp_…) in ~/.bashrc; the line is QUOTED — strip quotes
  before use (`tr -d '"'`); `--token` with embedded quotes errors
  "contents are invalid".
- **Vercel project is NOT git-connected** (as of 2026-10-03): pushes to the
  repo do NOT auto-deploy (last prod deploy 89d stale before tonight).
  Deploy manually: `vercel deploy --prod --yes --token <vcp_...>` from the
  repo checkout (~35-40s Ready, aliased automatically). Jordan should
  reconnect Git integration in the dashboard.
- ideas.json `file` field convention: `ideas/<slug>.md` RELATIVE TO data/
  — writing `data/ideas/<slug>.md` doubles the path and fails `npm run
  build` on the [slug] page (caught by build, not by JSON validation).
- data/ideas.json is build-time input, NOT a served route (404 — good for
  privacy). Verify live content by curling the idea page authed and grepping
  for distinctive phrases from the repo markdown.

## One-way GitHub sync workflow (org source → jordatech mirror)

Implemented in `.github/workflows/sync-from-org-source.yml` (jordatech/
business_idea_generator, PR #2 → squash 28feef2):
- Triggers: repository_dispatch + workflow_dispatch + daily safety poll.
- Already-synced check via `git merge-base --is-ancestor <src-sha> HEAD` →
  clean no-op (idempotent, loop-safe).
- FF when histories align (`git merge --ff-only`); sync branch + PR when
  diverged (org history lacks mirror-side commits — the real run took the PR
  path: org probe 7bbfb45 → sync/from-org-7bbfb455 → PR #3 → merged).
- Durable marker: `synced/<sha-prefix>` tags. No reverse sync workflow.
- Secrets SYNC_SOURCE_TOKEN + SYNC_MIRROR_TOKEN set via `gh secret set`.
- Direction caveat flagged for Jordan: after proving org→mirror, the org
  main was fast-forwarded once to converge histories (FF-only, zero org
  content overwritten). Standing direction remains org→mirror.

## Claude Code CLI defaults (Jordan steer 2026-10-03)

"please ensure you use claude opus 5.5 medium reasoning" + "set claude opus
5.5 medium reasoning as default for the claude cli" → `~/.claude/settings.json`
got `"model": "claude-opus-4-5-20251101"` + `"effort": "medium"` (opus 5.5 =
opus-4-5 in the CLI's naming; effort reports as 75). Verify with a probe:
`claude -p "Reply with your model id and effort level only" --output-format
json --effort medium` → parse modelUsage keys. Note: without `--effort`,
claude-4-5 reports "default (no extended thinking)" even with the settings
default — pass `--effort medium` explicitly on -p calls.

## Session-shape lessons (autonomous overnight run)

- Mid-turn steers arrived as out-of-band messages (model choice); apply them
  immediately, record in the handoff's model table with the exact quote.
- Idempotency at every layer: Jira clone search-before-create (JQL on summary),
  reconcile re-run (added=0), sync marker check, artifact registration
  (register v2 as a separate versioned artifact when the file changed after
  v1 registration — supersedes note in a follow-up Jira comment).
- Honest evidence discipline: every acceptance claim tied to a tool output
  (run IDs, comment IDs, SHAs, HTTP codes); UI screenshots explicitly listed
  as NOT captured rather than implied.