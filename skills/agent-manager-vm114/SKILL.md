---
name: agent-manager-vm114
description: Agent Manager V2 on VM114 (10.0.20.108) — architecture, paths, auth pattern, template 305, PVE token clone-ACL quirk, known issues
---

# Agent Manager V2 — VM114 deployment notes (created 2026-09-14)

## Architecture (ADR-0001/0002)
- Separate FastAPI app on **127.0.0.1:8200**, systemd unit `agent-manager.service`, deployed at `/opt/agent-manager/main_am.py`. Source of truth local: `~/.llm-manager-v011/agent-manager/main_am.py` (push via `push.py` pattern).
- DB: `agentmanager` **schema** (not database) inside CT115 `llmmanager` DB — llmmanager user lacks CREATEDB. Tables: agents, agent_access, plan_artifacts/versions, projects, work_items, runs, sessions, messages, audit_events, provisioning_jobs/steps. Connect with `options=-csearch_path=agentmanager,public`.
- nginx: `/agents/` + `/agents/ui` proxied to 8200 (config in `/etc/nginx/sites-enabled/llm-manager`, backup `/etc/nginx/llm-manager.bak.pre-agents`).
- Auth: shares LLM Manager session cookie — same `session_key` secret, same SessionMiddleware. Session payload = `{"user","role"}` b64+TimestampSigner. LDAP roles map through.

## Golden template
- **STEA-HERMES-UBU2404-v1 = PVE template VM 305** on node miam00111 (base 303 ubuntu-2404-vllm-golden). Contains st-agentd (port 8765, stdlib-only, bearer token at `/etc/st-agentd/token` 0600, systemd `st-agentd.service`), machine-id + ssh host keys cleared.
- Clone→configure→verify proven: clone ~50s, IP via DHCP ~37s, daemon active immediately. Verification clone 307 passed session/message/task E2E then destroyed.

## Provisioning engine (in main_am.py)
- Full §17 state machine persisted in provisioning_jobs/steps. Clone via PVE API token.
- `next_vmid()` = `/cluster/nextid` **+1** (nextid races; reserve immediately).

## ⚠️ PVE token clone-ACL quirk (UNRESOLVED — needs Jordan)
`llm-manager@pve!manager-control` token (privsep=0) gets **403 on qemu clone** even with role `STAgentProvisioner` (VM.Clone, VM.Config.*, VM.GuestAgent.*, VM.PowerMgmt, Datastore.AllocateSpace, Sys.Audit/Modify, VM.Migrate) granted on /vms, /vms/305, /vms/100-199, /vms/303, /vms/305, /storage/testthin, /nodes/miam00111. `access/permissions` shows VM.Clone=1 for the token. Root@pam cookie clone works. Token CAN do `PUT config` (VM.Config.Options) fine. Likely PVE 9.2 API-token ACL propagation bug or hidden check. Fix options: (a) re-create token with privsep=1 + explicit token ACLs, (b) provisioner uses user password ticket, (c) grant Administrator to the user (too broad).
Note: role privs param must be sent as repeated `privs=` form fields, NOT JSON array; invalid priv names (VM.Start/VM.Stop/VM.Config.HW/VM.Monitor don't exist — power = VM.PowerMgmt only).

## Known issues
- **VM114 qemu-guest-agent wedge (OBSERVED 2026-09-14):** frequent guest-exec via pve.py wedges the agent; reboot does NOT restore the channel; full stop/start restored VM but agent channel stayed dead ~1h. Guest OS + services stay healthy (verify via `curl -k https://10.0.20.108/agents/api/health`). Channel eventually re-attached on its own. Mitigation: avoid chatty guest-exec against VM114; batch scripts; single execs.
- `/cluster/tasks` endpoint doesn't exist; use `/nodes/{node}/tasks`.
- LXC exec endpoint not available on this PVE build (501/404); CT115 SQL must go through psycopg2 from VM114 as llmmanager.
- Role privs must be sent as repeated `privs=` form fields, NOT a JSON array. Invalid priv names: VM.Start, VM.Stop, VM.Config.HW, VM.Monitor (power = VM.PowerMgmt only).
