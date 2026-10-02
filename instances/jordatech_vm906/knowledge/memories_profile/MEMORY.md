STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
Gateway v0.3.0 VM114:8202, 7 domains; env /etc/miam-mcp-gateway/env. STNA-90 golden loop DONE 10-03. Idea afterhours-ai live; org→mirror sync workflow live. Vercel NOT git-connected (manual deploy). Gates: STNA-89, VM119 qga, ADR-0023, Jira flag, Vercel git. Handoff ~/agentifyme-workflow-20261003/.
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
Jira/ACMS gotchas: clone = re-PUT template ADF (purge hints); eligibility = AI acct + transition 2; IN REVIEW = id 11. ACMS artifacts POST /artifacts (no /api/v1 prefix); /content = JSON {sha256,content}. Dispatch auto-mint needs an AGENT token per worker (CLI mint-agent --acms-agent-id). Claude CLI default opus-4-5 effort=medium (10-03).
§
Telegram menu = PROFILE config (gateway unit's HERMES_HOME), not main config.yaml. command_menu priority reorders CORE/PLUGIN cmds only; skills alphabetical Tier-2, trimmed at cap 60. Skill visible: cap 61+ → last slot; plugin cmd → real priority. config set can't grow YAML lists; patch refuses Hermes configs (python write w/ asserts works). Restart: /restart or external systemctl. Handoff: ~/hermes-config-claude-code-20261002/.