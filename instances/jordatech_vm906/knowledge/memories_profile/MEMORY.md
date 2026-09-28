Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
ACMS: ~/work/acms-project-framework (.venv-acms). CT122 LIVE e1cd84ed (alembic 0005, Rev4 ServerManagerClient live). Compose acms-<svc>-1; fetch before checkout; manual re-raise after power-cycle. Worker VM124 @.203 bridge :8402.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA: RoCE 100G MTU1500. PBS 147 @03:05.
§
MARION: no home.arpa DNS (raw IPs); Omen dual-boot tailnet via CT100 ts-ssh (PVE auth root@pam).
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr + Server Manager: ~/work/llm-manager-project-framework; PRs #6-44 merged 09-27. REV4 SHIPPED: server_manager/ (ARM + machine API v1.0.0) LIVE on VM114:8300 (e33093ae, schema 001, 11 releases). ROTATION DONE (master key + DB pw). LXC-130 runner (llm-manager-deploy-runner) does staging+prod CD. qga wedge→qm reset; LLM_MANAGER_PG_HOST override. Recovery dual-trigger: GPU handoffs need power=STOPPED + service=MAINTENANCE both. Next: full-table ORM (TDR-0008), ARM reconciler.
§
PVE: API token can't start/stop guests (501) → root SSH nodes (~/.miam_root_pass). onboot=1 guests may not auto-start after node power events — verify. Power-cut latency ~25s+. PDU 151:9=miam-00119; 152:3=miam-00135 (live node). cloudimg→VM via qm importdisk node-SSH; cipassword+reboot. LLDAP :17170 GraphQL.
§
LLM Manager recovery DUAL trigger: desired_service_state=MAINTENANCE gates only HTTP-probe restarts; desired_power_state=RUNNING + observed VM stop fires outage_detected→vm_start regardless. GPU handoffs need BOTH power=STOPPED + service=MAINTENANCE, restore both after.
§
PDU Mgr: ~/work/pdu-marion-ia-usa-project-framework. PROD=VM156@.156; VM154 off fallback. Rev4: asset API + 409 guard + dry-run plans + pdu_manager_client live (fb01ed1f). Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.