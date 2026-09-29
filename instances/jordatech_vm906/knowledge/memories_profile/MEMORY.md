STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
ACMS prod 6f772aa (0008): dispatch PROVEN (WORK-000002→VM124 budget-gated), PRs #30-34 (FK fix, ADR-0011 Proposed, recovery guardrails, Jira-D/STL/portal/design-memory docs). Smoke on CT122 only. Lessons: template clones must re-identify netplan (VM108 .203 collided w/ VM124→.204); SQLite FK-off let agent_id='' reach PG. NEXT: gpu_samples Option A runbook; ADR-0011/Jira-D authorizations. Handoff ~/flight-work-20260929-acms/.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA: RoCE 100G MTU1500. PBS 147 @03:05.
§
MARION: no home.arpa DNS (raw IPs); Omen dual-boot tailnet via CT100 ts-ssh (PVE auth root@pam).
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr prod cb82bcd (PR51 ARM recovery max-5 + method audit; PR52 ORM slice-4 read-only). VM114 = ssh vm114. QGA: ping 500s = noise; exec/file authoritative. gpu_samples 197MB/1.59M rows, decision pending.
§
PVE: API token can't start/stop guests (501) → root SSH nodes (~/.miam_root_pass). onboot=1 guests may not auto-start after node power events — verify. Power-cut latency ~25s+. PDU 151:9=miam-00119; 152:3=miam-00135 (live node). cloudimg→VM via qm importdisk node-SSH; cipassword+reboot. LLDAP :17170 GraphQL.
§
LLM Mgr recovery DUAL trigger: service=MAINTENANCE gates only HTTP probes; power=RUNNING + observed stop fires vm_start. GPU handoffs need BOTH power=STOPPED + service=MAINTENANCE. Rotation runbook: ~/flight-work-20260928-rev2/ (H1 not yet authorized; H3 branch-protection rec also staged, not authorized).
§
PDU Mgr: ~/work/pdu-marion-ia-usa-project-framework. PROD=VM156@.156; VM154 off fallback. Rev4: asset API + 409 guard + dry-run plans + pdu_manager_client live (fb01ed1f). Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.