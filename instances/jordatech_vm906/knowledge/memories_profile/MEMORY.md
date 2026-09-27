Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
ACMS: ~/work/acms-project-framework (.venv-acms). CT122 LIVE 85f3c92 v0.6.0 slice3+4 (heartbeat/keys/bridge E2E; ADR-0009/0010). Hermes 0.17: pause/resume 404. Next: bridge targets env + buttons, slices 5-9. Compose names acms-<svc>-1; no host ports; fetch before checkout. 09-26 override: self-merge authorized.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA: RoCE 100G MTU1500. PBS 147 @03:05.
§
MARION: no home.arpa DNS (raw IPs); Omen dual-boot tailnet via CT100 ts-ssh (PVE auth root@pam).
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr: ~/work/llm-manager-project-framework; #5 closed; PRs #6-17 merged 09-27 (VM102 fix incl. collector, deploy tooling, migrations, AgentManager capture, active_deployments, healthz id, CD workflows). Staging VM120@.131 clean-room proven. Prod §21 validated (KeyError-.168 gone; VM102 GPU sampling live). Protected production env live. Open: runner install, LITELLM PW+MASTER KEY ROTATION (2x session DSN exposure), SPRINT refresh. qga wedge→qm reset; LLM_MANAGER_PG_HOST override.
§
PVE cloudimg→VM: download-url needs checksum+alg+.img; content POST lacks import-from → qm importdisk via node SSH (paramiko+root pass); ssh-keys alone fail → cipassword+reboot. LLDAP :17170 GraphQL only.
§
LLM Manager recovery DUAL trigger: desired_service_state=MAINTENANCE gates only HTTP-probe restarts; desired_power_state=RUNNING + observed VM stop fires outage_detected→vm_start regardless. GPU handoffs need BOTH power=STOPPED + service=MAINTENANCE, restore both after.
§
PDU Mgr repo: ~/work/pdu-marion-ia-usa-project-framework; capture+CI/CD DONE 09-27 (issues 1+6 closed, PRs 2-9 merged). Staging VM156@.156 mock; prod VM154 untouched. Next: runner ADR + prod env + 1st supervised deploy; KVM labels live=JetKVM+KYY.