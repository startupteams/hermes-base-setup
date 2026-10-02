STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
Gateway v0.3.0 VM114:8202, 7 domains. Registry/monitoring ABSENT — VM119 qga DOWN 10-02 (reset NOT run). Jira mutation fail-closed. Gates: GitHub PAT write; STNA-89 TO START; W7 creds; VM119 qga. Handoffs ~/acms-jira-mcp-20261002/.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK, document+fix); questions before NEW plans; deliverable = single .md + Telegram upload.
§
LLM Mgr: fleet APIs live; VM120 qga ok; clone-hygiene gate; ORM cutover. W4.1 sandbox template = golden VM135 (121 RETIRED); Kea match-client-id=0 REQUIRED. Sandbox block .222-.249; worker statics reserved.
§
PVE API: pve_api.py (proxmox skill, LLDAP bot auth) for login/vmconfig/raw; pve_qga.py (~/bin, root@pam) for exec-wait + sha-verified write. Node names: miam00111 no-dash, miam-00100 dash. PDU 151:9=00119; 152:3=00135. LLDAP :17170 GraphQL. Subagents: route curl-to-CT122 via CT122-local curl (tirith hook).
§
PDU Mgr: PROD=VM156@.156; VM154 off fallback. Rev4 asset API + 409 guard. Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.
§
STNA-88: ADF headings = type:heading+attrs.level (heading2 INVALID→400). Unit-green/live-400 class ×3 → live write probe per acceptance run. Hermes approval choice: session|once|always|deny; pre-authorize dispatch tool.
§
MCP SDK: dotted tool names need direct registry insert (GatewayTool subclass, run() override + args contextvar); zero-param templates hit SDK walrus bug → statics CONCRETE. `hermes mcp test <name>` = fast probe.
§
Telegram menu = PROFILE config (gateway unit's HERMES_HOME), not main config.yaml. command_menu priority reorders CORE/PLUGIN cmds only; skills alphabetical Tier-2, trimmed at cap 60. Skill visible: cap 61+ → last slot; plugin cmd → real priority. config set can't grow YAML lists; patch refuses Hermes configs (python write w/ asserts works). Restart: /restart or external systemctl. Handoff: ~/hermes-config-claude-code-20261002/.