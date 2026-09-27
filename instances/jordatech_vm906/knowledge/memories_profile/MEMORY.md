Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
ACMS: ~/work/acms-project-framework (.venv-acms). CT122 LIVE 85f3c92 v0.6.0. Next: bridge env + buttons, slices 5-9. Compose acms-<svc>-1; no host ports; fetch before checkout; containers need manual re-raise after node power-cycle.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA: RoCE 100G MTU1500. PBS 147 @03:05.
§
MARION: no home.arpa DNS (raw IPs); Omen dual-boot tailnet via CT100 ts-ssh (PVE auth root@pam).
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr: ~/work/llm-manager-project-framework; PRs #6-17 merged 09-27. Staging VM120@.131. Prod §21 validated. Open: runner install, LITELLM PW+KEY ROTATION (2x DSN exposure), SPRINT refresh. qga wedge→qm reset; LLM_MANAGER_PG_HOST override. Recovery dual-trigger: GPU handoffs need power=STOPPED + service=MAINTENANCE both.
§
PVE: API token can't start/stop guests (501) → root SSH nodes (~/.miam_root_pass). onboot=1 guests may not auto-start after node power events — verify. Power-cut latency ~25s+. PDU 151:9=miam-00119; 152:3=miam-00135 (live node). cloudimg→VM via qm importdisk node-SSH; cipassword+reboot. LLDAP :17170 GraphQL.
§
LLM Manager recovery DUAL trigger: desired_service_state=MAINTENANCE gates only HTTP-probe restarts; desired_power_state=RUNNING + observed VM stop fires outage_detected→vm_start regardless. GPU handoffs need BOTH power=STOPPED + service=MAINTENANCE, restore both after.
§
PDU Mgr: ~/work/pdu-marion-ia-usa-project-framework. PROD=VM156@.156 (real backend, 09-27 cutover); VM154 off fallback. Pipeline: prod env (jordatech; approve via pending_deployments API) → LXC130 runner → SSH pdurunner@VM156. Issues #1/6/10 closed; PRs #2-#19.