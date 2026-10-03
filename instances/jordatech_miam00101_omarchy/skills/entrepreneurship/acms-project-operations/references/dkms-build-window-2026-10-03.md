# DKMS build window (2026-10-03) — ACMS-side facts

The DKMS service itself lives in `startupteams/dkms-project-framework` on its
own VM (see the `dkms-operations` skill). This file records what touched the
ACMS side during the first DKMS window.

## STNA-91 epic clone (Jira → ACMS golden loop re-proven)

- Created **STNA-91** (id 10997) as an Epic clone of live template STNA-86:
  fetched `/rest/api/3/issue/STNA-86` (fields + description ADF), built the
  clone by text-filling paragraphs IN PLACE (keep hardBreak structure; fill
  SP/Title/Problem/Scope/Output Artifacts/Assignee/Reporter), POST
  `/rest/api/3/issue` with `description: <ADF doc>`, assignee = AI account
  (`ACMS_JIRA_AI_ACCOUNT_ID`), labels `dkms/roadmap-01/agent-instruction`.
- Eligibility move (authorized precedent): assignee=AI account + transition
  id 2 → TO START. All Jira REST calls run inside the acms-app container
  reading creds from `os.environ` (never on command lines).
- Reconcile (Check-Jira): POST `/api/v1/jira/reconcile` via **in-container
  loopback `http://localhost:8000`** (nginx 403s loopback TLS; the app
  publishes no host ports). Run a1b7f3c1 → examined/added/started per-issue
  outcomes at `/api/v1/jira/reconcile/runs/{id}/outcomes`.
- Result: **ACMS-WORK-000020-20261003_082241** (7d4db4be-…) → assignment
  ACKed → dispatched to uid-002 (VM125) → run SUCCEEDED 08:29:13Z → canonical
  fallback handoff **ACMS-ARTIFACT-000009-20261003_082913** (artifact_type
  work_handoff, sha e2b17432…, jira_issue_key STNA-91) → Jira comments 10913
  (started) + 10914 (BLUF succeeded, artifact UID + URL).
- Note: `GET /artifacts/{uid}` works by UID but `/content` needs the UUID;
  the BLUF comment body carries the UID — resolve via the list endpoint.

## Pending: dkms.* MCP gateway domain (P2)

- Branch `feat/dkms-mcp-domain` in this repo (reset to d8363e5=main).
- Implementation packet: `~/dkms-build-20261003/claude-p2-packet.md`
  (DkmsClient adapter + server.py wiring + cli env mapping + tokens default
  scopes `dkms.read`/`dkms.write` + ≥12 tests; backend live at
  `http://10.0.20.190:30800`).
- Claude Code dispatch in background; result JSON at `/tmp/claude-p2-result.json`.
- After merge: rsync gateway to VM114 `/opt/mcp-gateway/repo/` + systemctl
  restart + **grant-scopes for existing agents** (tokens minted before the
  domain exists carry only old scopes — the W2 SCOPE_REQUIRED class).
- Gateway context-manifest/policy surfaces should list `dkms` only when the
  client is configured (absent-domain is the designed health behavior).

## Cross-references

- `dkms-operations` skill — DKMS service, VM117/K3s, verification playbook.
- `references/jira-to-outcome-golden-workflow-2026-10-03.md` — the STNA-90
  loop this window re-used (same clone/eligibility/reconcile mechanics).
