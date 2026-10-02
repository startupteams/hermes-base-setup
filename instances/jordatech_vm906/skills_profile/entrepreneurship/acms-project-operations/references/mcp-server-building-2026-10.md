# MIAM MCP Gateway — building, deploying, and operating agent-facing MCP servers

Class-level guidance for BUILDING (not just consuming) MCP servers in the MARION
estate: SDK integration patterns, per-request auth propagation, policy/audit
spines, and the deployment recipe proven live on VM114 (2026-10-02, Window 1,
`miam-mcp-gateway` on :8202). For consuming MCP servers from Hermes, see the
bundled `native-mcp` skill; for the deployed gateway's API surface, see the ACMS
repo (`deploy/mcp-gateway/README.md`, PR #77, ADRs 0019–0022).

## Authority/context (STEA-004 estate)

- Approved plan: STEA-004 2026-10-02 "Jira Workflow Recovery and Internal MCP
  Gateway" (§9–§20 = W1; §21+ = W2+ windows). Requirements live in the ACMS repo
  (`ACMS-REQ-064`) — implementation must trace to it.
- The gateway is ADDITIVE and logically separate: never replaces REST/A2A/SSE,
  never becomes the sole control path, never offers a generic root-shell
  capability. Domain services keep authority — the gateway's adapter calls ACMS
  REST; it never opens the ACMS DB.
- Risk classes: READ → any authed caller; SAFE_WRITE → own-assignment scope,
  audited; SENSITIVE_WRITE → executive/infrastructure_admin only (fail-closed
  typed denial for workers until an approval workflow exists); DESTRUCTIVE →
  DENIED at the gateway for everyone (adding one later needs an ADR amendment).

## Official `mcp` SDK server quirks (live-verified 2026-10-02, mcp 1.26–1.30)

These cost real debugging cycles; encode them before writing a new gateway:

1. **Dotted tool names** (required by namespace discipline like `acms.work.…`)
   are REJECTED by the decorator path (`@m.tool()`) via SDK schema validation.
   Register directly on the tool manager with a custom Tool subclass instead:
   - `Tool.from_function` fails on non-function signatures; a plain `_Tool(...)`
     ctor requires callable `fn` + real `FuncMetadata`
     (`func_metadata(_placeholder_fn)`), and pydantic forbids `custom.run = …`
     (no extra field). Correct shape: **subclass Tool and override `run()`**
     (signature: `run(self, arguments: dict, context=None, convert_result=False)`).
   - Storage keys must be dot-normalized (`acms.work.x` → `acms_work_x`); keep
     the canonical dotted name in the tool's `_meta` (e.g.
     `gateway_canonical_name`) so clients see the namespace contract.
   - Hermes' MCP client additionally replaces dots with underscores at
     registration — tool listing still works; call routing follows storage keys.
2. **Zero-param resource templates are UNREACHABLE via the template path**: the
   SDK's `ResourceManager.get_resource` uses `if params := template.matches(uri)`
   — an empty dict `{}` (static templates like `acms://agent/self`) is falsy, so
   the template is skipped and the read fails "Unknown resource". Fix: register
   static resources as **CONCRETE resources** (`add_resource` +
   `FunctionResource.from_function`) and only parametrized ones as templates.
3. **Per-request auth propagation works** via an outer ASGI middleware that
   resolves the bearer token and sets a `contextvars.ContextVar`, read by tool/
   resource handlers — verified under the SDK's anyio task structure INCLUDING
   interleaved calls from two different tokens (per-call isolation holds). Wrap
   the FastMCP ASGI app; handlers read `CTX.get()` — no SDK auth plumbing needed.
4. **Stateless + JSON transport** (`stateless_http=True, json_response=True`)
   serves `tools/call` / `resources/read` without any prior initialize
   handshake and returns plain JSON (no SSE). Client compatibility verified with
   the official SDK `ClientSession` and `hermes mcp test`. SSE-only clients are
   NOT supported in this mode — document it.
5. **Resource-read errors surface as JSON-RPC ERRORS** (no `result` key) while
   **tool-call errors surface as `result.isError=true` + content text**. Tests
   asserting the wrong shape will false-fail. Prefix typed error codes
   (e.g. `OUT_OF_SCOPE: …`) into exception messages, since resource errors get
   double-wrapped into `ValueError("Error creating resource from template: …")`
   chains that would otherwise lose the classification.
6. **Host-header DNS-rebinding protection** defaults OFF unless
   `TransportSecuritySettings(allowed_hosts=[…])` is passed; in tests the
   default blocks everything with 421 Misdirected Request. For quick ASGI-level
   probes use `TransportSecuritySettings(enable_dns_rebinding_protection=False)`.
7. **HTTP layer details:** requests need `Accept: application/json,
   text/event-stream` (else 406); the session manager refuses multiple `.run()`
   calls per instance (production runs once forever; tests that need several
   token identities must share ONE run via a multi-client fixture helper).
8. **Fixture injection order:** resolvers built at capability-registration time
   close over the adapter client — inject test doubles BEFORE
   `GatewayServer(...)` construction, never by attribute-poking afterwards.

## Gateway package architecture (proven shape, reuse it)

`mcp_gateway/` (top-level package in the ACMS repo, NOT mounted in the ACMS
FastAPI app): `server.py` (FastMCP + IdentityMiddleware + policy spine) ·
`tokens.py` (gateway-local SQLite token store; agent `mcp_…` + assignment
`mcpt_…` tokens; **hash-only storage**, raw printed exactly once at mint) ·
`policy.py` (Capability registry: risk × roles × scopes, URI-template matcher) ·
`acms_adapter.py` (REST client with TLS-CA/insecure gate) · `manifest.py`
(context manifest: pointers, not dumps) · `audit.py` (SQLite + JSONL mirror,
args hashed) · `cli.py` (serve/mint-agent/mint-assignment/list-tokens/revoke/
activity). Assignment tokens mint ONLY with proof of the agent's raw token;
they bind exactly one Work UID (+ project/Jira/repo) with a short TTL.

## Deployment recipe (VM114 pattern)

1. rsync the repo tree to `/opt/mcp-gateway/repo` (exclude `.venv*`, `.git`,
   `__pycache__`); dedicated venv `.venv-mcp` with `mcp>=1.26`.
2. systemd unit: **`WorkingDirectory` + `PYTHONPATH=<repo>` are REQUIRED** —
   `python -m mcp_gateway.cli` fails ModuleNotFoundError without them (live
   restart-loop hit). Harden: `ProtectSystem=strict`,
   `ReadWritePaths=/var/lib/miam-mcp-gateway`.
3. env file `/etc/miam-mcp-gateway/env` (0600): ACMS_BASE_URL, ACMS_SERVICE_TOKEN
   (transfer host→host via `ssh A 'grep …' | ssh B 'cat > file'`, then shred the
   intermediate; verify with awk length checks, never echo), ACMS_INSECURE_TLS=1
   for the self-signed raw-IP endpoint (explicit config gate).
4. Data at `/var/lib/miam-mcp-gateway/` (tokens/activity SQLite + JSONL), 0700.
5. Verify: `systemctl is-active` + `curl /health` + sha256-compare a source file
   against repo HEAD to prove the deployed code identity.

## Verification playbook (proven live 2026-10-02)

- Raw JSON-RPC over httpx (Accept header + bearer) for the transport layer.
- Official SDK `ClientSession(streamablehttp_client(...))` for client compat.
- `hermes --profile <scratch> mcp test <server-name>` — the FAST Hermes-native
  connect probe (Connected, tools discovered). Scratch profile config:
  `mcp_servers: <name>: {url, headers.Authorization, timeout, connect_timeout}`.
- Golden workflow from a REAL worker VM: stage a token (via qga base64+sha write,
  see the acms-project-operations qga reference) + a stdlib-only client script,
  run `acms://assignment/current` + `acms://context/current` reads and one
  SAFE_WRITE tool (handoff), then verify the effect landed in ACMS via its API.
- Negative proofs: out-of-scope read → JSON-RPC error containing OUT_OF_SCOPE;
  unauthenticated → 401; expired/revoked → 401 with distinct EXPIRED/REVOKED
  types; no RUNNING task → honest CONFLICT (never fabricate progress).

## Pitfalls

- Tests calling the ASGI app must enter `session_manager.run()` exactly once;
  nested/repeated runs raise "Task group is not initialized" / "can only be
  called once per instance". Use a shared-run helper yielding one client per
  token identity.
- Circular/wrong self-quotes: `curl` from a VM to its own gateway works, but
  nested ssh quoting mangles `python3 -c "…"` in three layers — prefer
  base64-staged scripts or scp for anything with nested quotes.
- Never put raw tokens in audit rows, logs, or handoffs (hash-only); the CLI's
  mint output is the single exposure point by design.
