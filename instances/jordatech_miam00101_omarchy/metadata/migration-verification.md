# Migration Verification — MIAM-00101 (Omen) ← VM906

Executed 2026-09-25 (~00:31 +05:45) via import-portable-brain.sh from branch jordatech_vm906.

## Plan §19 validation questions

1. **What servers do you know I manage?**
   The MARION-IA-USA Proxmox cluster (16 nodes, Marion, Iowa): PVE hosts miam-00100/111/112/113/114/115/117/118/119/133/135/143/144/147/149, guests including the vLLM fleet (VM103/109/111/401), LLM Manager (VM114 @10.0.20.108), PostgreSQL (CT115), LLDAP (CT101), PBS on MIAM-00147 (marion-pbs datastore, 03:05 backups), plus the HP Omen desktop (MIAM-00101, this machine) and VM906 (the Hermes source agent on miam-00100, CT906 @10.0.20.195).

2. **What is VM906?**
   `hermes-jordan` — LXC CT906 on PVE node miam-00100, IP 10.0.20.195. The previous primary Hermes agent (profile agent_stea004_entrepreneur) whose portable brain was exported to startupteams/hermes-base-setup@jordatech_vm906 and imported here.

3. **What is the purpose of MIAM-00101?**
   This machine: Jordan's HP Omen desktop running Omarchy (Arch). The new Hermes Desktop agent home (~/.hermes, default profile). Dual-boots Windows (tailscale node miam-00101 @100.125.115.96; the Windows side was offline during migration).

4. **Which recurring server-management preferences have you inherited?**
   Power via Emporia, never poll PDUs .151–.153 (control only). Static IPs below .190 (DHCP pool .190–.250). Infrastructure handoffs as live .md docs + chat summary. Questions before NEW major infra plans, then full autonomy (roadblock → pivot, never stop). Credentials staged into root-owned 0600 files, never echoed or stored in agent memory. Requests features by analogy to products he knows; the /admin web UI is the expected control plane. MTU stays 1500 on RDMA ring (no jumbo).

5. **Which custom skills were imported from VM906?**
   Additive import (--ignore-existing) of both trees: 16 MB global (28 categories) + 26 MB profile (34 categories) — incl. agent-manager-vm114, proxmox-cluster-infrastructure, self-hosted-llm-gateway, marion-vllm-bench-ops, business-idea-systems, jira-sprint-task-writing, fable-strategic-analysis, hermes-agent, native-mcp, github suite, etc. Omen-side originals preserved where names collided (conflict reports: ~/hermes-skill-conflicts-{global,profile}.txt).

6. **Can you locate the imported VM906 conversation archive?**
   Yes: ~/.hermes/memories/imported_vm906_history/ — INDEX.md (186 sessions / 20,867 messages), sessions/*.md per-session transcripts, raw/*.jsonl. Also memory_records.jsonl (4 durable memory facts) and ~/.hermes/memories/imported_vm906{,_shared}/ (MEMORY.md, USER.md).

7. **What configuration files were deliberately preserved rather than imported?**
   .env, auth.json, config.yaml, install_id, gateway state, channel_directory.json, cron state, state.db (live sessions untouched — quick_check ok, 4 pre-existing sessions preserved), WAL/SHM. Checksums verified unchanged before/after (CONFIG_UNCHANGED). SOUL.md was NOT overwritten — VM906 variants kept at ~/.hermes/migration_sources/vm906/ and merged semantically (backup: ~/.hermes/SOUL.md.backup-pre-vm906-merge-*).

## Post-import actions completed

- Branch jordatech_miam00101_omarchy created and pushed (instance metadata + SOUL copies + imported memories + synced skills).
- Phase R hourly exporter installed: ~/.hermes/scripts/portable_brain_sync.sh, Hermes cron job 150481b491a9 (0 * * * *, no-agent) → pushes this instance's portable brain to instances/jordatech_miam00101_omarchy.
- SOUL semantic merge applied (Omen base + inherited role/constraints).

## Outstanding (human/agent follow-up)

- Verify Hermes Desktop starts normally and answers the §19 questions fluently (this doc is written by the VM906 agent — the Omen agent should re-answer them itself as its own first exercise).
- Review ~/hermes-skill-conflicts-{global,profile}.txt (252 lines) and merge useful VM906 customizations where wanted.
- Rotate the leaked Vercel tokens (vck_/vcp_) and Google OAuth creds found in June-2026 session exports (scrubbed from the archive, but live secrets should still be rotated).
