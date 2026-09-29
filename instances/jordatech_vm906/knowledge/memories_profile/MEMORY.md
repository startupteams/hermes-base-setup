STL: repo agentifyme-speed-to-lead (React prototype, P0 15/15, High Point demo pending Utkarsh). Separate product; ACMS internal-only; agents sanitized; dedicated gateway.
§
ACMS prod fa0e0fc (0008): PR#44 merged; ADR-0012 callback LIVE (CT122 .env CALLBACK_TOKEN+BASE_URL; 401/403/404 verified; reconciler closes tasks+orphaned sessions; dedupe ledger in event metadata). PRs #45-47. Rule: after 'gh pr merge --delete-branch' check branch BEFORE committing. Handoff FINAL-HANDOFF-20260929-W3.md
§
Jordan writes his own llama-server/vLLM commands (MoE offload, tensor-split, KV quant). Engage at systems-engineer level.
§
Jordan: broad server autonomy (break OK — document, fix); questions before NEW plans then full autonomy; deliverable = single .md + Telegram upload.
§
LLM Mgr prod 1cea3e4 (PRs #59-66): clone-hygiene HYGIENE_GATE; ORM Slice 5+6 LIVE via ORM_WRITE_CUTOVER=1 drop-ins (sqlalchemy pip-installed into prod venv). orm_write_adapter: UNIQUE(name,host_id) no NULL dedupe → aliases delete-then-insert. gpu_orm: bulk + hour-aligned rollups + prune by sample_id. cmd_rollup start MUST be hour-aligned. CD: RUNNER_TEMP staleness, dist/ untracked, SHORT-sha naming. VM120 no shell access (CT130 runner key only). Awaiting human: Jira token + economics PAT (HUMAN-SETUP files in flight-work dir).
§
PVE: API token can't start/stop guests (501) → root SSH nodes (~/.miam_root_pass). onboot=1 guests may not auto-start after node power events — verify. Power-cut latency ~25s+. PDU 151:9=miam-00119; 152:3=miam-00135 (live node). cloudimg→VM via qm importdisk node-SSH; cipassword+reboot. LLDAP :17170 GraphQL.
§
PDU Mgr: ~/work/pdu-marion-ia-usa-project-framework. PROD=VM156@.156; VM154 off fallback. Rev4: asset API + 409 guard + dry-run plans + pdu_manager_client live (fb01ed1f). Pipeline: prod env → LXC130 runner → SSH pdurunner@VM156.