Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
AgentifyMe.co: repo github.com/startupteams/agentifyme_server_setup (authorized); branch AGENT_STEA004_ENTREPRENEUR → main.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
RDMA ring RoCE 100G, MTU 1500 (no jumbo); no persistent netcfg. PBS MIAM-00147 (store marion-pbs, job 03:05).
§
CX5 SR-IOV persistent (09-13): VFs→VM109 A/B, VM103/111 VF+PF; NCCL 95–97Gb/s. Recipe: proxmox skill cx5-sriov-guest-rdma.md.
§
MARION net: DHCP .190–.250; CT906 pinned .195; MIAM-00115 owns .115; MACs bc:24:11:*. Omen: dual-boot on tailnet — Omarchy miam-00101-1-omarchy @100.69.169.125, Windows miam-00101 @100.125.115.96; via miam-00133 → pct exec 100 tailscale ping/ssh; not a PVE guest; PVE auth needs root@pam suffix.
§
Jordan: grants broad server autonomy (break OK — document, fix, don't stop); live handover .md; questions before NEW plans then full autonomy; deliverable = single .md in work folder + Telegram upload.
§
MARION infra: LLM Mgr VM114@.108 (v0.11.0); PG CT115@.116; LLDAP@.101. Workspace ~/.llm-manager-v011 (pve.py, creds 0600). PVE: guest-exec arg[]+poll; GET=querystring; LXC exec 501; VM114 qga can wedge.
§
Brain migration 09-24/25: COMPLETE both sides. VM906 brain = startupteams/hermes-base-setup@jordatech_vm906; Omen synced on branch jordatech_miam00101_omarchy (Jordan directive: Omen uses this branch). Hourly no-agent exporters: VM906 cron 0c9b84306a9f, Omen cron 150481b491a9 (both portable_brain_sync.sh). Omen access: miam-00133 → pct exec 100 -- tailscale ssh jordatech@100.69.169.125 (one-time browser approval per session; plain :22 over tailnet intercepted by TUN RunSSH). hermes import = replacement-restore, never merge. Push Protection caught real vck_/vcp_/GOCSPX secrets in old session exports — rebuild branch from main if push rejected. Import fixes: branch Omen from jordatech_vm906 not main; refspec fetch. FlashNext BLOCKED: vllm 0.30 caps Qwen4Exp TP<=4.