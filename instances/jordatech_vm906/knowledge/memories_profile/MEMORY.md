STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
ACMS prod 404ad54 (0011): Jira kickoff gate LIVE on ALL dispatch paths (AI acct 712020:520fb263-ef0f-425c-a0be-14e9d258917e = startupteamscompany service acct); reconcile+scheduler LIVE (24h UTC, lease). /ui/work/new route-order fix. Work board + PR panel (merged≠accepted). Bootstrap resumable — PATs can't create repos (human gate). W4 callback notes: ADR-0012 watcher LIVE; post-merge branch check rule stands.
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr prod d021f70 (W5 09-30, PRs #69-71): fleet one-card bug = _physical_host_for_ip .16x prefix collapse + rollback-VM dropped by demotion loop — /admin/fleet + /api/fleet LIVE (6 hosts honest states); /admin/agents list/detail/wizard via svc-server-manager token proxy. Older: clone-hygiene gate; ORM 5+6 via ORM_WRITE_CUTOVER; hour-aligned rollups; CD RUNNER_TEMP/dist/short-sha. VM120: qga works (node miam-00135), wrapper sudo intentional.
§
PVE: API token can't start/stop guests (501) → root SSH nodes (~/.miam_root_pass). onboot=1 guests may not auto-start after node power events — verify. Power-cut latency ~25s+. PDU 151:9=miam-00119; 152:3=miam-00135 (live node). cloudimg→VM via qm importdisk node-SSH; cipassword+reboot. LLDAP :17170 GraphQL.
§
PDU Mgr: ~/work/pdu-marion-ia-usa-project-framework. PROD=VM156@.156; VM154 off fallback. Rev4: asset API + 409 guard + dry-run plans + pdu_manager_client live (fb01ed1f). Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.