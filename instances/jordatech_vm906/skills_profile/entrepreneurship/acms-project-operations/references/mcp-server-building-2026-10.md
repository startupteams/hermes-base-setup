# MIAM MCP Gateway — building, deploying, and operating agent-facing MCP servers

Class-level guidance for BUILDING (not just consuming) MCP servers in the MARION
estate: SDK integration patterns, per-request auth propagation, policy/audit
spines, and the deployment recipe proven live on VM114 (2026-10-02, Windows
1–4: `miam-mcp-gateway` on :8202 with domains acms/llm/runtime/github/proxmox).
For consuming MCP servers from Hermes, see the bundled `native-mcp` skill; for
the deployed gateway's API surface, see the ACMS repo (`deploy/mcp-gateway/README.md`,
PRs #77/#81/#83, ADRs 0019–0023).

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

## W3+W4 additions (live-proven 2026-10-02, github + proxmox domains)

**SDK template matching (`matches()`) hard-codes `[^/]+` per param** — any
resource whose URI param contains a slash (GitHub `owner/name`!) can NEVER
match an unencoded URI: `github://repos/startupteams/acms-project-framework`
→ "Unknown resource". Contract: clients pass percent-encoded params
(`owner%2Fname`); resolvers must `urllib.parse.unquote` EVERY template param
before validation (live probe: template matched with %2F, but the RAW `%2F`
string reached the adapter VALIDATION → denied). Regression test:
`test_repo_resource_url_encoded_owner`. Wrap unquote once in a module-level
helper; apply in BOTH the transport path (`tpl_fn(**kwargs)`) and the
direct/registry path (tests call `cap.handler(identity, params)`).

**Unknown tool args must REJECT, not silently drop** — `_bind_args` filtered
`kwargs` to the handler signature, so a caller passing a foreign `branch=`
argument got a confusing downstream error instead of an honest denial. Now
raises `VALIDATION: unknown argument(s) [...]` (an ignored ownership-shaped
arg would mask policy violations). Test: `test_unknown_tool_args_rejected`.

**Domain-scope migration for BOTH token kinds** — mint-assignment defaults
lack every domain's scopes (only `acms.read/write`). Each new domain needs:
(1) widen mint defaults, (2) `grant-scopes` CLI unions into agent AND
assignment tokens (`grant_assignment_scopes` added in W3; W2 only covered
agent tokens), (3) mint-assignment has NO --scopes flag — grant AFTER mint.

**Approval-gated SENSITIVE_WRITE ordering (live fact):** the policy gate fires
BEFORE any handler logic — a no-grant call gets `APPROVAL_REQUIRED` without
creating anything. The flow is: call `runtime.request_elevated` (SAFE_WRITE,
needs `runtime.write` scope) → durable PENDING request → executive runs
`cli approval decide <id> APPROVED` (grant TTL 15 min) → re-call the tool
(grant consumed atomically). Tests must `_arm_grant(server, agent, capability)`
before EVERY SENSITIVE_WRITE call — one grant = one call.

**Registry storage names:** tools = dot-normalized storage key
(`proxmox_sandbox_create`), registry capability keys = dotted canonical names
(`proxmox.sandbox.create`). Test helpers map `tool_name.replace(".", "_")`.

**ARM sandbox substrate (W4, Server Manager side):** a sandbox IS an ARM
runtime with `runtime_class="sandbox"` + `sandbox_expires_at` (migration
0004) + `ownership_meta={kind: sandbox, ttl_hours}`. TTL sweep lives in
`ReconciliationService.expire_stale_sandboxes()` called FIRST in
`reconcile_all()` (flip → DESIRED_DESTROYED, API-only; idempotent). extend-ttl
endpoint = sandbox-only (422 otherwise) + bounded by
`SERVER_MANAGER_ARM_SANDBOX_{DEFAULT,MAX}_TTL_HOURS` (8/72). Gateway-side
sandbox name: `sbx-<work_uid>-<agent>` — **PVE rejects underscores in VM
names** ("invalid format — not a valid DNS name"); map `_`→`-`, lstrip/rstrip
dashes, must start alnum. Ownership enforced by deterministic name-resolution
(foreign sandboxes unreachable, not merely denied).

**SM list endpoint shape:** `GET /api/v1/agent-runtimes` returns
`{"runtimes": [...]}` (wrapped dict), NOT a bare list — adapters must unwrap;
accept both shapes. (`GET /provisioning-jobs/{id}` wants a UUID; passing a
request_id 500s.)

**Three live-found ARM provisioning bugs fixed 2026-10-02 (PRs #76/#77/#78):**
1. `clone_template()` pinned `target=template_node` → clone LANDED on the
   template node while `wait_clone_lock_release()` polled the PLACED node →
   240s timeout + orphan VM. All 5 production workers were ADOPTED runtimes —
   the cross-node clone path had never been exercised before the first
   sandbox probe. Fix: `target=spec.node`.
2. Cross-node full clone 500s when the template's node-local storage (golden
   template 121 root disk = `testthin`) is INACTIVE on the target node ("can't
   clone VM to node X (VM uses local storage…)"). Fix: `template_storage()` +
   `storage_active()` checked BEFORE the clone; fail closed with an honest
   error. Fake providers in tests must stub both methods.
3. Sandbox placement pins to the template node (`sandbox_pinned_to_template_node`
   reason in `select_node`) — node-local template storage makes cross-node
   placement impossible until testthin is active cluster-wide or the template
   is replicated.

**🚨 DHCP/static-IP collision (CRITICAL, live-proven):** a sandbox VM's DHCP
lease was `10.0.20.203` — worker-001's STATIC IP. Transient ARP conflict;
bridge traffic at risk ~60s until VM powered off + destroyed; worker unharmed
(bridge 200 after ARP refresh). Worker statics sit INSIDE the Kea lease pool.
Sandbox create is PAUSED until Jordan picks: Kea static reservations / sandbox
DHCP class/range / gateway-managed static pool + `ipconfig0`. Any future
clone-provisioning faces the same risk. Full detail: the 2026-10-02 W4 handoff
(`~/acms-jira-mcp-20261002/HANDOFF-20261002-W4-PROXMOX-SANDBOX-DEPLOYED.md`).

**Gateway probe-token hygiene (proven pattern):** mint with
`cli mint-agent <name> --ttl-days 1`, capture raw from the file (mint output
has a `# NOTE:` comment header BEFORE the JSON — `read().split("\n",1)[1]`,
key is `token` not `raw_token`), `chmod 600`, grant scopes AFTER mint
(grant-scopes unions BOTH token kinds), then REVOKE both tokens
(`cli revoke <id> <reason>`) + delete raw files when done. Assignment mint
requires `--agent-token <agent-raw>` (binding anchor).
