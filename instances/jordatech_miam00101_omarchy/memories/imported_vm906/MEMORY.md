Business ideas: skeptical-investor review before MVP (Data Moat, HITL, Unit Economics); see business-idea-systems skill.
§
BIG: Vercel businessideagenerator-three.vercel.app; repo ~/business_idea_generator.
§
AgentifyMe.co: repo github.com/startupteams/agentifyme_server_setup (authorized); branch AGENT_STEA004_ENTREPRENEUR → main.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
PDM: CT105 @ miam-00133, https://10.0.20.181:8443/ (LLDAP realm).
§
RDMA ring RoCE 100G, MTU 1500 (no jumbo); no persistent netcfg. PBS MIAM-00147 (store marion-pbs, job 03:05).
§
CX5 SR-IOV persistent (09-13): VFs→VM109 A/B, VM103/111 VF+PF; NCCL 95–97Gb/s. Recipe: proxmox skill cx5-sriov-guest-rdma.md.
§
MARION net: DHCP pool .190–.250; statics below .190; CT906 pinned .195; MIAM-00115 owns .115. Guest MACs bc:24:11:*.
§
VM149 @.165 llama-server :8000 alias startupteams/llamacpp (Qwen3-4B; 27B CPU lane measured 0.8 t/s = useless).
§
Jordan: grants broad server autonomy (break OK — document, fix, don't stop); live handover .md; questions before NEW plans then full autonomy; deliverable = single .md in work folder + Telegram upload.
§
MARION infra: LLM Mgr VM114@.108 (v0.11.0); PG CT115@.116; LLDAP@.101. Workspace ~/.llm-manager-v011 (pve.py, creds 0600). PVE: guest-exec arg[]+poll; GET=querystring; LXC exec 501; VM114 qga can wedge.
§
Agent Mgr V2 live: VM114 :8200 (systemd agent-manager), nginx /agents/, schema agentmanager@CT115, template 305. BLOCKER: PVE token clone-403 (root works) — Jordan console fix. Skill: agent-manager-vm114.
§
Hermes local-models: router llm-manager.marion-ia-usa.internal/v1 (cert in venv certifi), custom:marion. max_tokens=16384. tools.tool_search.enabled='on' (string) or 70K models overflow.
§
FlashNext 09-24: BLOCKED — vllm 0.30 caps Qwen4Exp TP<=4 (PP banned by PLE; TP6 fails GDN 16 k-heads); 76 GiB weights vs ~18.2 usable/GPU. PLE CPU-offload works (DP1 pinned 47.8 GiB). Loader fails unfused AWQ-gemm under TP. VM102@.168 (off) holds model disk while stopped; VM103 prod restored after riser AER wedge→host reboot. Handoff ~/flashnext-miam00111-20260924/.