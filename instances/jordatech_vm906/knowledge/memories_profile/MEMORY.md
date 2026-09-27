Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
ACMS: startupteams/acms-project-framework, clone ~/work/acms-project-framework (.venv-acms). LIVE CT122 = 9545123 v0.5.0 (slices 1+2 live: Work UI + Agent Detail). Pipeline ROUTINE: merge → release.sh <sha> → smoke. Remaining: slice 3 heartbeat (ACMS-side only until slice 4 bridge). Quirks: compose-v2 names acms-<svc>-1; app has no host ports (probe in-container); fetch before checkout. No self-merge.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA ring RoCE 100G, MTU 1500 (no jumbo); no persistent netcfg. PBS MIAM-00147 (store marion-pbs, job 03:05).
§
CX5 SR-IOV persistent (09-13): VFs→VM109 A/B, VM103/111 VF+PF; NCCL 95–97Gb/s. Recipe: proxmox skill cx5-sriov-guest-rdma.md.
§
MARION: no home.arpa DNS (raw IPs); CT906 pinned .195; MIAM-00115 owns .115. Omen dual-boot on tailnet (Omarchy 100.69.169.125, Windows 100.125.115.96; via CT100 tailscale ssh; not a PVE guest; PVE auth = root@pam).
§
Jordan: grants broad server autonomy (break OK — document, fix, don't stop); live handover .md; questions before NEW plans then full autonomy; deliverable = single .md in work folder + Telegram upload.
§
MARION infra: LLM Mgr VM114@.108 (v0.11.0); PG CT115@.116; LLDAP@.101. Workspace ~/.llm-manager-v011 (pve.py, creds 0600). PVE: guest-exec arg[]+poll; GET=querystring; LXC exec 501; VM114 qga can wedge.
§
FlashNext V3 prod on VM102 (09-24). PVE quirks: guest console automation impossible via API — deploy LXCs w/ ssh-key at create; 00135 has internet; LLDAP writes via HTTP :17170 GraphQL addUserToGroup only; MARION has NO home.arpa DNS — raw IPs.
§
LLM Manager recovery DUAL trigger: desired_service_state=MAINTENANCE gates only HTTP-probe restarts; desired_power_state=RUNNING + observed VM stop fires outage_detected→vm_start regardless. GPU handoffs need BOTH power=STOPPED + service=MAINTENANCE, restore both after.