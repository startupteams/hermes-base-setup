STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
ACMS prod 07043f1 (alembic 0017). STNA-88 gate PASSED. MCP W1: gateway LIVE VM114:8202 — PR #77 open CI green awaiting Jordan; stea-004/uid-001/uid-005 tokens minted; golden §20 steps 1-3+5-8 proven from VM124; STNA-89 (id 10995) awaits human TO START. W2 = LLM/runtime adapter + capability card + auto-mint.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK, document+fix); questions before NEW plans; deliverable = single .md + Telegram upload.
§
LLM Mgr: /admin/fleet+/api/fleet+/admin/agents live. VM120 qga works, wrapper sudo intentional. Clone-hygiene gate, ORM 5+6 cutover, hour-aligned rollups, CD artifact chain.
§
PVE API: pve_api.py (proxmox skill, LLDAP bot auth) for login/vmconfig/raw; pve_qga.py (~/bin, root@pam) for exec-wait + sha-verified write + 596-retry. Node names: miam00111 no-dash, miam-00100 dash (500s if wrong). SEARCH SKILLS TREE BEFORE BUILDING HELPERS. Subagents hit tirith raw_ip_url hook on curl-to-CT122 — route via CT122-local curl. PDU 151:9=00119; 152:3=00135. LLDAP :17170 GraphQL.
§
PDU Mgr: PROD=VM156@.156; VM154 off fallback. Rev4 asset API + 409 guard + pdu_manager_client live. Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.
§
STNA-88 lessons: ADF headings = type:heading+attrs.level (heading2 INVALID→400). Unit-green/live-400 class ×3 → live write probe per acceptance run. Hermes 0.19 approval: /v1/runs/{id}/approval {choice: session|once|always|deny}; pre-authorize dispatch tool.
§
§ MCP SDK: dotted tool names need direct registry insert (GatewayTool subclass, run() override + args contextvar); zero-param templates hit SDK walrus bug → statics CONCRETE. `hermes mcp test <name>` = fast probe.