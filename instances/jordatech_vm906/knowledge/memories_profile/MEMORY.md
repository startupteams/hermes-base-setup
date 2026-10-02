STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
ACMS prod 07043f1 (10-02, alembic 0017). PRs #75 Jira intake/write-back (STNA-88 gate PASSED: WORK-000017→uid-002→artifact 000005→Jira BLUF) + #72-74 operator UI. MCP w1 next per ~/acms-jira-mcp-20261002/. §31 lifecycle Qs open; hourly schedulers + SSE streaming = FUTURE_WORK.
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
STNA-88 lessons: ADF headings = type:heading+attrs.level (heading2 INVALID→Jira 400). Unit-green/live-400 bug class ×3 → acceptance runs need a live outbound write probe. Hermes 0.19 approval: /v1/runs/{id}/approval {choice: session|once|always|deny}; worker approval gates pause unattended dispatch — pre-authorize dispatch tool.
§
Emporia: creds ~/.secrets/emporia_creds + emporia_env.sh (0600), login verified 10-01. pyemvue venv ~/.secrets/.venv-emporia. WAT001 gid 631093: ch1-3=PDU/compute circuits, ch4=mini-split cooling, '1,2,3'=Main. VM114 adapter reads /etc/llm-manager/secrets/emporia_creds. Measurement only, never PDU control.