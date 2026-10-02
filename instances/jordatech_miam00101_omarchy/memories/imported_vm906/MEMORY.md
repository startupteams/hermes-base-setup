STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
Gateway v0.3.0 LIVE VM114:8202 == ACMS b0d2970. LLM Mgr VM114 = 42099fd0 (W4.1 sandbox DHCP isolation LIVE: SM Kea reservations pool .222-.249, gate flag ON → create UNPAUSED; worker statics .203/.204/.206/.207/.208/.209 reserved). ACMS CT122 = b0d2970. GATES: GitHub PAT Contents:write; STNA-89 TO START. Next: W5 PDU+Emporia.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK, document+fix); questions before NEW plans; deliverable = single .md + Telegram upload.
§
LLM Mgr: /admin/fleet+/api/fleet+/admin/agents live; VM120 qga ok; clone-hygiene gate; ORM cutover; CD artifact chain. W4.1: sandbox template = golden VM135 (121=RETIRED, static .203 netplan); Kea match-client-id=0 REQUIRED (DUID client-ids make Kea ignore hw-address reservations; set/subnet API no-ops it → config-restore only); OPNsense login = JS-shell w/o csrf pair until cookie-test handshake (retry ~24s); PVE DELETE params = query string (form body → 501).
§
PVE API: pve_api.py (proxmox skill, LLDAP bot auth) for login/vmconfig/raw; pve_qga.py (~/bin, root@pam) for exec-wait + sha-verified write. Node names: miam00111 no-dash, miam-00100 dash. PDU 151:9=00119; 152:3=00135. LLDAP :17170 GraphQL. Subagents: route curl-to-CT122 via CT122-local curl (tirith hook).
§
PDU Mgr: PROD=VM156@.156; VM154 off fallback. Rev4 asset API + 409 guard + pdu_manager_client live. Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.
§
STNA-88 lessons: ADF headings = type:heading+attrs.level (heading2 INVALID→400). Unit-green/live-400 class ×3 → live write probe per acceptance run. Hermes 0.19 approval: /v1/runs/{id}/approval {choice: session|once|always|deny}; pre-authorize dispatch tool.
§
MCP SDK: dotted tool names need direct registry insert (GatewayTool subclass, run() override + args contextvar); zero-param templates hit SDK walrus bug → statics CONCRETE. `hermes mcp test <name>` = fast probe.