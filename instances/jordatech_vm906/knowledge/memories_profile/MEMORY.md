STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
ACMS prod 89fb4e4 (0012 A2A path, 10-01): envelope+ACK, busy-lock, model policies (sys local-preferred/qwen3.8-flash-next), inbox, artifacts, SSE. Jira kickoff gate on all dispatch (AI acct=startupteamscompany svc). 10-01 Jordan: VM124 STAYS miam00111 (CPU mismatch, cpu=host); 1 worker/inference-node OK; MIAM00100 default only for NEW workers.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK, document+fix); questions before NEW plans; deliverable = single .md + Telegram upload.
§
LLM Mgr prod d021f70 (W5 09-30): fleet-card bug (.16x prefix collapse + demotion loop) fixed — /admin/fleet + /api/fleet live; /admin/agents via svc token proxy. VM120: qga works, wrapper sudo intentional. Older: clone-hygiene gate, ORM 5+6 cutover, hour-aligned rollups, CD artifact chain.
§
PVE: API token 501 on start/stop → root SSH nodes (~/.miam_root_pass). PDU 151:9=miam-00119; 152:3=miam-00135. cloudimg→qm importdisk node-SSH. LLDAP :17170 GraphQL.
§
PDU Mgr: PROD=VM156@.156; VM154 off fallback. Rev4 asset API + 409 guard + pdu_manager_client live. Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.
§
VM119 dashboards DONE (09-30): homarr_sync.py live (tRPC board.saveBoard, marker=ownership); Kuma v2.5.5 object login + monitorList; team status no-login; CT118=.157 ganesha Bind_Addr trap. Handoff ~/service-dashboard-completion-20260930/.
§
Emporia: creds ~/.secrets/emporia_creds + emporia_env.sh (0600), login verified 10-01. pyemvue venv ~/.secrets/.venv-emporia. WAT001 gid 631093: ch1-3=PDU/compute circuits, ch4=mini-split cooling, '1,2,3'=Main. VM114 adapter reads /etc/llm-manager/secrets/emporia_creds. Measurement only, never PDU control.