STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
Phase C DONE (10-02): ACMS prod 7daad53 (alembic 0017_power_payload_text). PRs #72 operator UI (Home zones/kanban §12/agent chat §20-24/product detail/artifacts/usage/global search), #73 facility-payload+legacy-handoff fixes, #74 migration 0017 payload_json→Text. §44 demo 45/45; §41 chat 7/7; §42 inbox 17/17; suite 325. operator_data.py = shared UI data layer. gitleaksignore per-test-file pattern. §31 lifecycle Qs open; hourly slop/power schedulers + SSE chat streaming = FUTURE_WORK.
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