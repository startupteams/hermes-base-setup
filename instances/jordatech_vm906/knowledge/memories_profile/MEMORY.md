Gateway v0.3.0 VM114:8202, 8 domains incl dkms. FastMCP bugs fixed: query-string templates (?k={v}) regex-? bug (ACMS PR #94); zero-param templates skipped (walrus) → register statics concretely. PVE: qga wedge fix = POST .../status/reset (NOT /reset). K3s local-path PVs pin node affinity. Jira/ACMS: clone = re-PUT ADF; eligibility = AI acct + transition 2; artifacts POST /artifacts + /content; auto-mint needs AGENT token/worker. Claude CLI = opus-4-5 medium. PDU Mgr PROD=VM156@.156.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK, document+fix); questions before NEW plans; deliverable = single .md + Telegram upload.
§
LLM Mgr: fleet APIs live; VM120 qga ok; clone-hygiene gate; ORM cutover. W4.1 sandbox template = golden VM135 (121 RETIRED); Kea match-client-id=0 REQUIRED. Sandbox block .222-.249; worker statics reserved.
§
PVE API: pve_api.py (proxmox skill, LLDAP bot auth) for login/vmconfig/raw; pve_qga.py (~/bin, root@pam) for exec-wait + sha-verified write. Node names: miam00111 no-dash, miam-00100 dash. PDU 151:9=00119; 152:3=00135. LLDAP :17170 GraphQL. Subagents: route curl-to-CT122 via CT122-local curl (tirith hook).
§
Telegram menu = PROFILE config (gateway unit's HERMES_HOME), not main config.yaml. command_menu priority reorders CORE/PLUGIN cmds; skills alphabetical Tier-2 trimmed at cap 60. config set can't grow YAML lists; patch refuses Hermes configs (python write w/ asserts works). Handoff: ~/hermes-config-claude-code-20261002/.
§
DKMS (STNA-91) 10-03: P1-P3 DONE live — VM117 K3s @10.0.20.190, app NodePort 30800 PLAIN HTTP (gateway base http://…:30800; https probe=000). Buildinit deploy: sed DKMS_COMMIT_SHA→main-tip sha (older SHAs fail closed, PR #9; clone uses GITHUB_TOKEN in dkms-secrets; sed rewrites guard literals → split sentinel). VM117 rebuilt 10-03 → host-key change EXPECTED. Gateway token DB hash-only. Rotation list: dkms GITHUB_TOKEN + svc-server-manager. Jordan steer: Claude autonomous bg w/ handoff; Hermes supervises/merges.