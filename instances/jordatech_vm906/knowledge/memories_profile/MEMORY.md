Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
ACMS: ~/work/acms-project-framework (.venv-acms). CT122 LIVE a67bef9 (v0.11.0, alembic 0008). Budgets(0007)+economics+attention live. Worker VM124 @.203. PG booleans: server_default=sa.false().
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA: RoCE 100G MTU1500. PBS 147 @03:05.
§
MARION: no home.arpa DNS (raw IPs); Omen dual-boot tailnet via CT100 ts-ssh (PVE auth root@pam). qga exec needs JSON body (urlencoded→500).
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr: ~/work/llm-manager-project-framework; PRs to #49. ORM slices 1-3 done; staging 094b067 live; VM114 prod BLOCKED (qga wedge — needs SSH key or reset window; restart server-manager-api after deploy). Stale ARM rows = failed attempts of acms-22ec3237 (supersede queued). Worker-bridge key rotation runbook: ~/flight-work-20260928-rev2/. Recovery dual-trigger: GPU handoffs need power=STOPPED + service=MAINTENANCE both.
§
PVE: API token can't start/stop guests (501) → root SSH nodes (~/.miam_root_pass). onboot=1 guests may not auto-start after node power events — verify. Power-cut latency ~25s+. PDU 151:9=miam-00119; 152:3=miam-00135 (live node). cloudimg→VM via qm importdisk node-SSH; cipassword+reboot. LLDAP :17170 GraphQL.
§
LLM Manager recovery DUAL trigger: desired_service_state=MAINTENANCE gates only HTTP-probe restarts; desired_power_state=RUNNING + observed VM stop fires outage_detected→vm_start regardless. GPU handoffs need BOTH power=STOPPED + service=MAINTENANCE, restore both after.
§
PDU Mgr: ~/work/pdu-marion-ia-usa-project-framework. PROD=VM156@.156; VM154 off fallback. Rev4: asset API + 409 guard + dry-run plans + pdu_manager_client live (fb01ed1f). Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.