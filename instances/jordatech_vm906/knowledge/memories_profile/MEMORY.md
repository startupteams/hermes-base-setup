STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
ACMS prod 404ad54 (0011): Jira kickoff gate on ALL dispatch paths (AI acct 712020:520fb2… = startupteamscompany svc acct); reconcile+scheduler live (24h UTC lease). Work board + PR panel (merged≠accepted). Bootstrap resumable (PATs can't create repos). ADR-0012 watcher live; post-merge branch-check rule stands.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr prod d021f70 (W5 09-30): fleet-card bug (.16x prefix collapse + demotion loop) fixed — /admin/fleet + /api/fleet live; /admin/agents via svc token proxy. VM120: qga works, wrapper sudo intentional. Older: clone-hygiene gate, ORM 5+6 cutover, hour-aligned rollups, CD artifact chain.
§
PVE: API token can't start/stop guests (501) → root SSH nodes (~/.miam_root_pass). onboot=1 guests may not auto-start after node power events — verify. Power-cut latency ~25s+. PDU 151:9=miam-00119; 152:3=miam-00135 (live node). cloudimg→VM via qm importdisk node-SSH; cipassword+reboot. LLDAP :17170 GraphQL.
§
PDU Mgr: PROD=VM156@.156; VM154 off fallback. Rev4 asset API + 409 guard + pdu_manager_client live. Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.
§
VM119 dashboards DONE (09-30): homarr_sync.py live (tRPC board.saveBoard, marker=ownership); Kuma v2.5.5 object login + monitorList; team status no-login; CT118=.157 ganesha Bind_Addr trap. Handoff ~/service-dashboard-completion-20260930/.
§
Emporia: creds ~/.secrets/emporia_creds + emporia_env.sh (0600), login verified 10-01. pyemvue venv ~/.secrets/.venv-emporia. WAT001 gid 631093: ch1-3=PDU/compute circuits, ch4=mini-split cooling, '1,2,3'=Main. VM114 adapter reads /etc/llm-manager/secrets/emporia_creds. Measurement only, never PDU control.