# W2 MCP gateway session detail (2026-10-02) — llm/runtime adapters, approvals, auto-mint

Condensed session record for the gateway W2 window. Full handoff:
`~/acms-jira-mcp-20261002/HANDOFF-20261002-W2-LLM-RUNTIME-DEPLOYED.md`.

## Architecture decisions (documented in STEER-LOG, stable)

- **llm.* domain authority = Server Manager API (:8300, bearer svc-acms from
  `/etc/llm-manager/secrets/service_tokens`).** LLM-Manager web `/api/fleet` is
  LDAP-session-auth (humans) — the gateway never uses web-session surfaces.
  SM identity file format trap: lines are `service=token:scopes`; strip everything
  from the first colon.
- runtime.self = caller's own ACMS fleet view (`/api/v1/fleet/agents/{id}/runtime`);
  runtime.fleet = SM `GET /api/v1/agent-runtimes`, executive/infra_admin only.
- llm.request_model / llm.request_fallback = ACMS `PUT /model-policy` scoped to the
  caller's own work item; model validated against SM `/model-routes` BEFORE any write.
- Approval model (ADR-0021 W2): SENSITIVE_WRITE + worker ⇒ ApprovalRequiredError +
  durable request in gateway-local `approvals.sqlite3`; executive APPROVED arms a
  ONE-TIME TTL-bounded (15 min default) grant consumed atomically on the next attempt,
  matched on exact (agent_name, capability). DESTRUCTIVE remains deny-for-all.

## Live-found bugs (both fixed in PR #80)

1. **Scope gap:** pre-W2 agent tokens carried `[acms.read, acms.write]`; every llm.*/runtime.*
   call raised `SCOPE_REQUIRED`. Fix: mint defaults to full domain scope set +
   `grant-scopes` CLI (unions into ACTIVE tokens). Applied live to stea-004/uid-001/uid-005.
2. **Static resolver signature:** resources registered as static (zero-param) URIs but
   resolvers declared `(uri_params, identity)` → `TypeError` on read. Static resolvers
   must take `(identity)` only; parametrized templates take `(identity, uri_params)`.
   Related registration traps (W1, still true): dotted tool names need direct
   `_tool_manager._tools` insertion; zero-param templates hit the SDK walrus bug →
   register statics as CONCRETE resources.

## Live verification matrix (evidence class to reproduce)

| Probe | Method | Result |
|---|---|---|
| Internal auth | GET /internal/capability-card with wrong token | 401 + audited |
| Capability card | GET /internal/capability-card/{agent} | mcp_connected, 18 resources/9 tools, approval-required list, NO raw tokens |
| llm reads | MCP resources/read `llm://models` etc. via tools/call on raw JSON-RPC (stateless) | 9 model routes, 6 hosts, 24h usage |
| runtime.self | worker token (uid-001) | VM124 DESIRED_RUNNING/RUNNING, state_sync VERIFIED |
| runtime.fleet | worker token | OUT_OF_SCOPE; exec token without ACMS binding → honest NOT_FOUND |
| Approval cycle | tools/call runtime_restart_self → APPROVAL_REQUIRED; runtime_request_elevated → PENDING; POST /internal/approvals/{id}/decide | APPROVED + grant armed (no live consumption against a real worker VM) |
| Auto-mint | POST /internal/mint-assignment from CT122 container (exact dispatch path) | 201 mcpt_…, assignment token reads own work, cross-work read OUT_OF_SCOPE |
| UI | issue_token() in-container + GET /ui/agents/{id} | "MCP capability — Connected: yes"; work page activity table with real rows |

## Tool addressing quirk

`tools/call` addresses tools by their STORAGE key (dots→underscores: `llm_request_model`);
canonical dotted names live in tool `meta.gateway_canonical_name` and policy registry.
Resources read via `resources/read` with the real URIs (`llm://models`).

## Environment wiring (recreate trap re-applied)

- VM114 `/etc/miam-mcp-gateway/env` += MCP_GATEWAY_LLM_BASE_URL/TOKEN,
  MCP_GATEWAY_INTERNAL_TOKEN, MCP_GATEWAY_APPROVALS_PATH (0600).
- CT122 `/opt/acms/.env` += ACMS_MCP_GATEWAY_BASE_URL/INTERNAL_TOKEN/
  DISPATCH_MINT_ENABLED/ASSIGNMENT_TTL_HOURS; then recreate with the PINNED current
  image tag (`ACMS_APP_IMAGE_TAG=<sha> docker compose up -d --force-recreate acms-app`)
  — env resolves at container CREATE time.
- Internal token transfer pattern: `openssl rand -hex 32` on VM114 → stage 0600 file →
  base64 over scp → append into CT122 .env without echoing → verify lengths only.
