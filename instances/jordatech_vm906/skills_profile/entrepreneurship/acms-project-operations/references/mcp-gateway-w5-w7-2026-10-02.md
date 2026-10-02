# MCP Gateway W5–W7 session detail (2026-10-02)

Session: STEA-004, gateway v0.3.0. Handoffs of record live in `~/acms-jira-mcp-20261002/`
(W5/W6/W7 + final skeleton). This file captures the durable, class-level lessons.

## Session-state lesson: "merged+deployed" ≠ "window closed"

W5 (PR #85) was merged + rsynced by a prior window that died before acceptance. Evidence at
window open: gateway `/health` had the domain, but there was NO handoff, NO live probe, and
4 latent bugs. Rule for gateway windows: close-out requires (1) live probes with a probe
token, (2) denial-path proof, (3) token revocation to 0 ACTIVE, (4) handoff + STEER-LOG.
Check `git log` + `ls ~/acms-jira-mcp-20261002/*W<N>*` at window open before redoing anything.

## Live-found defect classes (each test-pinned in PRs #86–#90)

1. **CLI/store scope split (#86):** `cmd_mint_agent` hardcoded `scopes=["acms.read",
   "acms.write"]` overriding TokenStore defaults → CLI-minted tokens SCOPE_REQUIRED on every
   later domain. The internal auto-mint path was fine. Fix = pass `scopes=None`. Whenever a
   new domain adds scopes, grep BOTH mint paths (CLI + internal) AND add a scope-grant path
   for pre-existing tokens (`grant-scopes` CLI).
2. **Payload-contract drift (#87):** SM `/api/v1/facility/power` nests the aggregate under a
   `totals` DICT; the gateway projected `body["total"]` → TOTAL MARION_IA_USA always null.
   Total-withhold rule: any stale channel ⇒ total null WITH explicit `incomplete_reason`
   (never zeroed). Test fakes must mirror the REAL upstream payload shape, not a simplified
   one — a simplified fake hides exactly this class.
3. **Missing error import (#88):** unknown outlet raised `NameError: NotFoundError` instead
   of the mapped 404 error. One-line import; regression test asserts `type != NameError`.
4. **Endpoint-path assumption (#89):** gateway called `/api/v1/pdus/{key}/outlets/{n}` —
   that's the PDU Manager's OWN API; SM surface is `GET /api/v1/pdu/assets/{id}/power-state`.
   Fix: resolve (pdu_id, outlet) via the SM asset index, then fetch asset power-state.
   Lesson: enumerate the SM routes FIRST (`grep @router` on `pdu_routes.py`; prefix is
   `/api/v1/pdu`) before writing an adapter method.
5. **Timeout vs fan-out read (#90):** per-asset power-state fans out to the PDU Manager SSH
   poll (~20s cold) vs the SM client 10s default → DOMAIN_UNAVAILABLE. PowerClient built with
   `timeout_seconds=45`.
6. **Kuma 0/1 truthiness (W7):** Kuma `active` is 0/1; Python `0 is not False` is True —
   the disabled-count projection silently counted disabled monitors as up. Use truthiness,
   not identity checks, for JSON-native 0/1 fields.
7. **Name collision (W7 build):** `self.registry` was already the PolicyRegistry; assigning
   the RegistryClient to it silently broke capability registration. New gateway attributes:
   `self.svc_registry`, `self.kuma`. Check `__init__` attr names before adding domain clients.

## Gateway-domain env-staging recipe (never echo values)

Stage creds by copying values machine-to-machine with a base64-staged python one-liner;
verify only key NAMES are present (`grep -oE '^MCP_GATEWAY_JIRA_[A-Z_]+' env`). Jira values
come from CT122 `/opt/acms/.env` (same values, `ACMS_JIRA_*` → `MCP_GATEWAY_JIRA_*`).
Nested `ssh vm114 'ssh root@CT122 ...'` does NOT work (no key path VM114→CT122) — pull values
on the workstation, push via base64-staged script. chmod 600 after write.

## Gateway MCP probe patterns

- Probes must speak MCP (stateless streamable-HTTP at `/mcp`); plain GET on resource URIs 404s.
- SDK client quirks: `read_resource` returns `ReadResourceResult` — use `res.contents[0].text`;
  tool errors surface as `isError: True` + TextContent `TYPE: detail` (parse the prefix to
  classify). Token goes via env var to the remote python, NOT stdin (stdin collision with
  python `-` read = NameError garbage).
- `streamablehttp_client` accepts a per-request `timeout` header but the gateway-side client
  timeout governs SM fan-outs.
- Probe hygiene: mint (1-day TTL) → probe → revoke → assert 0 ACTIVE. Executive tokens are
  minted with `--executive`; role-gated denials fire at policy.py BEFORE the handler, so
  worker+SENSITIVE_WRITE raises ApprovalRequiredError (not RoleRequiredError) when no grant.

## Jira domain specifics (W6, plan §28)

- Assignment-scoped issue-key enforcement: `_allowed_issue_keys(identity)` = assignment-token
  `jira_issue_key` → linked work item → ACTIVE assignment linkage; executives skip. Empty set
  ⇒ OUT_OF_SCOPE "no assignment binding".
- Transition policy IN THE GATEWAY: workers only TO START→IN PROGRESS / IN PROGRESS→IN REVIEW
  (`WORKER_ALLOWED_TRANSITIONS`); BLOCKED = executive-only with the §8A message (keep IN
  PROGRESS + comment + Inbox). Policy fires BEFORE the mutation-flag check, so the BLOCKED
  denial is visible even with mutation disabled.
- Global mutation flag `MCP_GATEWAY_JIRA_STATUS_MUTATION_ENABLED` mirrors ACMS's
  `ACMS_JIRA_STATUS_MUTATION_ENABLED` (prod = false both sides = fail-closed, CONFLICT with
  actionable message). Enabling live transitions requires flipping BOTH.
- Local markdown→ADF converter mirrors ACMS's contract incl. heading
  `type:heading+attrs.level` (NOT heading2 — the live-400 class); fenced code → codeBlock.
- Jira comments come back as ADF — `_adf_to_text` flattener for reads.

## Registry/Kuma specifics (W7, plan §29)

- Registry API (VM119, Caddy vhost `registry.miam.home.arpa`): Bearer token from
  `/etc/miam-service-registry/secrets.env` `MIAM_SERVICE_REGISTRY_TOKEN`; `GET /api/v1/services`
  returns `{"version":1,"services":[...]}` (a dict wrapper, NOT a bare list). No dependency
  graph in the schema — the dependencies resource honestly returns same-host services as a hint.
- Kuma read protocol (verified against the VM119 reconciler's `kuma_sync.py`): socket.io
  websocket transport (polling login flaked), `login {username,password,token:""}` + ack
  `[{ok, token}]`, then `getMonitorList` with `callback=` kwarg → ack `[{monitorList:{...}}]`.
  Positional-callback (`sio.emit("getMonitorList", cb)`) raises TypeError.
- Kuma bind question UNRESOLVED: 127.0.0.1:3001 on VM119 (compose) — cross-VM gateway probes
  need Caddy `status.miam.home.arpa` vhost, an SSH tunnel, or verification of the bind before
  staging `MCP_GATEWAY_KUMA_URL`.
- registry/monitoring resources are READ-class only; NO mutation tool registered for any role
  (plan §29: context, not authorization) — enforced by absence + a test asserting all W7
  capabilities are READ.

## VM119 qga incident (2026-10-02, UNRESOLVED at close)

Healthy qga execs 17:30–17:46Z (registry curl, Homarr 17 apps, Kuma login_ok via websocket).
17:47Z exec wedge; from 17:48Z ALL agent paths (exec/file-write/ping/get-osinfo) return PVE
500 "QEMU guest agent is not running" — guest-side daemon dead, not just channel-wedged.
Ruled out: 8+ min self-recovery wait, file-write nudge, alternate endpoints. VM119 sshd
ANSWERS on :22 but has no authorized key. Recovery options documented (wait / `qm reset 119`
/ provision SSH key) — reset NOT run (live dashboard stack). VM119 services unaffected;
the reconciler's Kuma login-fail predates my probes (17:37Z journal) — pre-existing, unrelated.
If qga recovered: stage W7 creds per the recipe above, re-probe, then the final golden workflow.