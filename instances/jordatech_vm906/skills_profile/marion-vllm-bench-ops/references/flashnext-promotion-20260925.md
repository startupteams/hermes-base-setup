# Flash-Next production promotion — 2026-09-25 session detail (VM102 on MIAM-00111)

Companion to SKILL.md "Production promotion" section. Plan: `MIAM_00111_QWEN38_FLASHNEXT_PRODUCTION_PROMOTION_PLAN_20260925.md` (cached `doc_d8aa07ea4f73…`). Prior state: V3 test deployment (`/home/jordatech/flashnext-v3-20260924/HANDOFF-…V3-20260924.md`).

## End state
- VM102 (10.0.20.168) PRODUCTION: `local/qwen38-flash-next:eed1f3d0-ampere-pp-mtp`, TP2×PP3+EP, 70K, SEQS=6, FP8 PLE pinned host RAM (~85G/106G in use), container `flashnext`, `flashnext.service` enabled, onboot=1.
- VM103 (10.0.20.161) WORKING-ROLLBACK: powered off, onboot=0 (was 1!), unit snapshot `/root/vm103.vllm.service.pre-promo-20260925.txt`, preset #17 + revision 11 intact.
- LLM Manager: hosts id 6 (VM102, RUNNING/MANAGED/SERVING); registry 96377 `qwen3.8-flash-next` healthy/routable/70000 (AUTO-created by recovery tick sync_registry after hosts row insert — no manual SQL); revision 12 ACTIVE/visible (image digest + artifact rev aeae1483 recorded); revision 11 → WORKING-ROLLBACK.
- litellm_config.yaml regenerated (9 entries; qwen3.8-flash-next → .168) + litellm restarted; VM103 gate `STOPPED_INTENTIONAL`.

## Timeline with the two live failures
1. Recon (read-only): live qm config/status both VMs; VM103 200 OK; rollback preset #17 present; recovery source read later proved essential.
2. Gate attempt per plan: MAINTENANCE+STOPPED → recovery restarted VM103 (events 2321/2322) and my `qm start 102` lost the race (`PCI device '0000:61:00.0' already in use by VMID '103'` — task history shows an earlier identical refusal too).
3. Fix: set `STOPPED_INTENTIONAL`, re-stop VM103, verify across 2 ticks, then start VM102. Gate held.
4. Launch `MAXLEN=70000 SEQS=6 run_stage.sh` → healthy ~9 min (note: run_stage.sh logs to `/opt/hf-fork/vllm-run.log`; a `nohup` redirect only captures the wrapper line — poll the right log).
5. Direct validation: chat ✓, vision ✓, 65K needle ✓ — tool-call **400**: "requires --enable-auto-tool-choice and --tool-call-parser".
6. Parser discovery: `--tool-call-parser qwen3` → KeyError listing valid names (`apertus, cohere_command3…, hermes, qwen3_coder, qwen3_xml…`). Chose `qwen3_xml` (Qwen3 reasoning models' tool format). Relaunched (2nd ~9-min boot). Post-fix: tool-call ✓ (`get_weather Tokyo` → correct JSON), all other checks re-✓.
7. Concurrency @8K prompts/256 gen: C1 61.4 · C4 22.0–23.7 · C6 21.6–23.7 tok/s/agent. (15K-prompt shape: C4 dips to ~14.5 — heavier prefill, not regression; KV usage ~10% at C4, no pressure.)
8. Registration: hosts INSERT (id 6) → recovery tick auto-probed → registry row 96377. `litellm_sync.py --dry-run` → apply → `systemctl restart litellm` → proxy model list includes qwen3.8-flash-next. Revision 12 ACTIVE; revision 11 → WORKING-ROLLBACK.
9. Routed smoke via `http://127.0.0.1:4000` + master key (`grep master_key: /etc/llm-manager/litellm_config.yaml`): chat `ROUTED-OK Paris` ✓; tool ✓; vision ✓; needle 55,403 toks 10.6 s ✓ and 65,333 toks 13.0 s ✓; C6 23.6 tok/s/agent ✓.
10. Boot safety: `/etc/systemd/system/flashnext.service` (oneshot RemainAfterExit TimeoutStartSec=1200, ExecStart wraps run_stage.sh with MAXLEN/SEQS) enabled; VM102 onboot=1; VM103 onboot 1→0.

## Token-count pitfall for long-context smoke tests
Prompt tokenization varies ~1.5× by corpus: repetitive "Ledger…" filler ≈ 2.5–3.9 chars/tok across corpora. 250K chars of one filler = 65,140 toks; 195K chars of another = >70K (400 `ContextWindowExceededError` names the requested count). Binary-search prompt size once against the error message's reported token count, then reuse the working char budget. Keep ~5K token headroom below the limit (output tokens + template overhead count too).

## `code` alias gap (open, owner decision)
`sync_registry()` in `/opt/llm-manager/app/v011_core.py` hardcodes aliases `("fast","qwen3.6-35b-a3b"),("code","qwen3.8-27b"),("frontier",None)`. With VM103 dark, `code` has no routable target (alias routable iff target routable somewhere). Repointing = edit tuple to `("code","qwen3.8-flash-next")` + restart llm-manager-web/recovery. Left as-is pending Jordan's routing decision; `qwen3.8-flash-next` works by name today.

## Rollback runbook (Flash-Next → 27B)
1. Gate VM102: `desired_power_state='STOPPED_INTENTIONAL' WHERE guest_ip='10.0.20.168'`.
2. `systemctl stop flashnext` (or `docker rm -f flashnext`) on VM102; `qm stop 102`.
3. Restore VM103: `desired_power_state='RUNNING', desired_service_state='SERVING' WHERE guest_ip='10.0.20.161'`; `qm start 103`.
4. Verify `http://10.0.20.161:8000/v1/models` (qwen3.8-27b, 70K); unit snapshot on VM103; preset #17; revision 11.
5. Registry/litellm: re-syncs on tick; rerun litellm_sync.py + restart litellm only if entries changed.

## Full handoff
`/home/jordatech/flashnext-promotion-20260925/HANDOFF-QWEN38-FLASHNEXT-PRODUCTION-PROMOTION-20260925.md` (DoD checklist all ✓).
