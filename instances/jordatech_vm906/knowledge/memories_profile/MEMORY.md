Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
ACMS: ~/work/acms-project-framework (.venv-acms). CT122 LIVE 85f3c92 v0.6.0 slice3+4 (heartbeat/keys/bridge E2E; ADR-0009/0010). Hermes 0.17: pause/resume 404. Next: bridge targets env + buttons, slices 5-9. Compose names acms-<svc>-1; no host ports; fetch before checkout. 09-26 override: self-merge authorized.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA: RoCE 100G MTU1500 (no jumbo). PBS 147 @03:05. CX5 SR-IOV: VFs→109 A/B, 103/111 VF+PF; 95-97Gb/s.
§
MARION: no home.arpa DNS (raw IPs); CT906 pinned .195; MIAM-00115 owns .115. Omen dual-boot on tailnet (Omarchy 100.69.169.125, Windows 100.125.115.96; via CT100 tailscale ssh; not a PVE guest; PVE auth = root@pam).
§
Jordan: grants broad server autonomy (break OK — document, fix, don't stop); live handover .md; questions before NEW plans then full autonomy; deliverable = single .md in work folder + Telegram upload.
§
LLM Mgr: ~/work/llm-manager-project-framework; #5 closed; PRs #6-17 merged 09-27 (VM102 fix incl. collector, deploy tooling, migrations, AgentManager capture, active_deployments, healthz id, CD workflows). Staging VM120@.131 clean-room proven. Prod §21 validated (KeyError-.168 gone; VM102 GPU sampling live). Protected production env live. Open: runner install, LITELLM PW+MASTER KEY ROTATION (2x session DSN exposure), SPRINT refresh. qga wedge→qm reset; LLM_MANAGER_PG_HOST override.
§
FlashNext V3 prod on VM102 (09-24). PVE quirks: guest console automation impossible via API — deploy LXCs w/ ssh-key at create; 00135 has internet; LLDAP writes via HTTP :17170 GraphQL addUserToGroup only; MARION has NO home.arpa DNS — raw IPs.
§
LLM Manager recovery DUAL trigger: desired_service_state=MAINTENANCE gates only HTTP-probe restarts; desired_power_state=RUNNING + observed VM stop fires outage_detected→vm_start regardless. GPU handoffs need BOTH power=STOPPED + service=MAINTENANCE, restore both after.