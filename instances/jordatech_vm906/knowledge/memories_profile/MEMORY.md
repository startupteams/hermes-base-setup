Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
ACMS: ~/work/acms-project-framework (.venv-acms). Prod d696826 (0008): budgets, economics, attention, dispatch gate (PR28), Attention UI+SSE (PR29). dispatch_service = single A2A path w/ budget gate. NEXT: ACMS_BRIDGE_TARGETS_JSON on CT122 → first real dispatch to acms-worker-001. Smoke-test.sh runs ON CT122 only.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA: RoCE 100G MTU1500. PBS 147 @03:05.
§
MARION: no home.arpa DNS (raw IPs); Omen dual-boot tailnet via CT100 ts-ssh (PVE auth root@pam).
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr: ~/work/llm-manager-project-framework; PRs to #50. ORM 2-3 + SUPERSEDE (e773750) LIVE on VM114 prod; 5 stale rows SUPERSEDED→56c1b849. VM114 ops = dedicated keypair (ssh vm114). QGA: ping 500s = QEMU-side noise; exec/file channels authoritative; file-write = literal base64. gpu_samples: rollup+90d proposal, awaiting Jordan.
§
PVE: API token can't start/stop guests (501) → root SSH nodes (~/.miam_root_pass). onboot=1 guests may not auto-start after node power events — verify. Power-cut latency ~25s+. PDU 151:9=miam-00119; 152:3=miam-00135 (live node). cloudimg→VM via qm importdisk node-SSH; cipassword+reboot. LLDAP :17170 GraphQL.
§
LLM Mgr recovery DUAL trigger: service=MAINTENANCE gates only HTTP probes; power=RUNNING + observed stop fires vm_start. GPU handoffs need BOTH power=STOPPED + service=MAINTENANCE. Rotation runbook: ~/flight-work-20260928-rev2/ (H1 not yet authorized; H3 branch-protection rec also staged, not authorized).
§
PDU Mgr: ~/work/pdu-marion-ia-usa-project-framework. PROD=VM156@.156; VM154 off fallback. Rev4: asset API + 409 guard + dry-run plans + pdu_manager_client live (fb01ed1f). Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.