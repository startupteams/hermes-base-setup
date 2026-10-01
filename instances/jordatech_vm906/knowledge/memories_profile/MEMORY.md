STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
ACMS prod f6ac25b (0013 naming): 5-worker fleet LIVE acms-hermes-worker-uid-001..005 (UUIDs kept; legacy_name/worker_uid; PATCH /agents/{id} display-only). 001=VM124 miam00111 STAYS; 005=VM128/miam-00100 test. Template-121 clones need aiohttp pip. LLM Mgr 66f37a50: /admin/power (PDU 151/152/153+mini split, TOTAL, stale-not-zero). A2A path PROVEN: dispatch→ACK→watcher completion→auto-close; SSE Last-Event-ID exact resume; Jira token=Basic auth, /search retired→POST /search/jql; STNA-87=acceptance issue (comment 10892); heredoc-in-ssh mangles JSON→scp files.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK, document+fix); questions before NEW plans; deliverable = single .md + Telegram upload.
§
LLM Mgr: /admin/fleet+/api/fleet+/admin/agents live. VM120 qga works, wrapper sudo intentional. Clone-hygiene gate, ORM 5+6 cutover, hour-aligned rollups, CD artifact chain.
§
PVE: API token 501 on start/stop → root SSH nodes (~/.miam_root_pass). PDU 151:9=miam-00119; 152:3=miam-00135. cloudimg→qm importdisk node-SSH. LLDAP :17170 GraphQL.
§
PDU Mgr: PROD=VM156@.156; VM154 off fallback. Rev4 asset API + 409 guard + pdu_manager_client live. Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.
§
VM119 dashboards DONE (09-30): homarr_sync.py live (tRPC board.saveBoard, marker=ownership); Kuma v2.5.5 object login + monitorList; team status no-login; CT118=.157 ganesha Bind_Addr trap. Handoff ~/service-dashboard-completion-20260930/.
§
Emporia: creds ~/.secrets/emporia_creds + emporia_env.sh (0600), login verified 10-01. pyemvue venv ~/.secrets/.venv-emporia. WAT001 gid 631093: ch1-3=PDU/compute circuits, ch4=mini-split cooling, '1,2,3'=Main. VM114 adapter reads /etc/llm-manager/secrets/emporia_creds. Measurement only, never PDU control.