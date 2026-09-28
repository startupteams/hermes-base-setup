# 2026-09-28 Flight Session — Server Manager/ARM/ACMS/PDU detail notes

Condensed session record backing `llm-manager-operations` and
`acms-project-operations`. Full checkpoints: `/home/jordatech/flight-work-20260928/`.

## State after the flight

- LLM Manager prod VM114: release `80909328c062` (4 deploys this flight:
  ec860f9 → 6d1b4d9 → 465a2df → 9489575 → 8090932, all Release ACCEPTED).
- ACMS prod CT122: v0.8.0 `fba6d25`, alembic `0006_memory_session_offload`.
- VM124: RUNNING, bridge healthy, state-sync VERIFIED, branch `agent/22ac1b19`
  tip `180dd563...`, deploy key id 164639272, hourly timer.
- VM906 untouched. No PDU actuation occurred.

## Merged PRs (self-merge authorized by Jordan mid-flight)

- LLM Manager: #45 (ARM reconciler + state-sync), direct-main fix 6d1b4d9
  (shutdown convergence wait — see below), #46 (PDU consumers), #47 (ORM
  slice 1 + /hosts /model-routes), direct-main fix 8090932 (active-host join
  on bare MIAM-##### token), #48 (AgentManager parity matrix + TDR-0010).
- ACMS: #22 (runtime lifecycle), #23 (REQ-055..062), #24 (memory offload MVP).

## Key debugging stories (the durable parts)

1. **SM token file**: `service_tokens` format is `service=token:scopes`;
   `cut -d= -f2` keeps the scopes on the token → constant 401. Split at first
   colon.
2. **Shutdown convergence race**: first live reconcile cycle recorded a false
   "shutdown did not converge" — PVE accepted the shutdown but the immediate
   status read still said running. Fixed with bounded poll
   (`_wait_pve_state`, ARM_RECONCILE_SHUTDOWN_WAIT_S=30).
3. **PDU reads flaky**: outlet power-state via VM156's SSH driver can return
   PDU_SSH_FAILURE ("Did not reach SSH password prompt") on first call and
   succeed on a retry ~15s later. Reads are slow; retry before concluding.
   Audit tail returned 0 lines (correlation metadata unproven until a real
   action happens).
4. **Transient VM114→VM156:443 refusal** during first PDU probe; retest was
   clean (VM156 nftables ruleset empty, nginx listens 0.0.0.0). No firewall
   change made; if it recurs, check from CT122 too (CT122→VM156 OK was proven).
5. **active_hosts join**: hosts.name carries VM suffixes ("MIAM-00111 / VM102
   (Flash-Next PROD)") while active_hosts keys are bare asset ids — join on
   the first MIAM-\d{5} token.
6. **API test cookies**: ACMS UI tests must pass `cookies={...}` as a kwarg
   (NOT `headers=`), cookie name `acms_session`, login redirects to `/ui/`.
7. **Retry marker semantics**: legacy provisioning retry id now
   `request_id|retry:N` where N = retry COUNT (attempt column N-1) — fixed a
   pre-existing failing test; note this if touching server_manager_api.

## live proof transcript (ACMS memory rotation, prod 02:35 UTC)

WORK=4463f793 → assigned → PKG=06aad60f (compact-v1) → S1=e4d6b5b5 OPEN,
telemetry 55% → advisory MONITOR → checkpoint complete=True (10/10 fields) →
S1 CLOSED → rotate → PKG2=be19a51e types [work_item, work_key, assignment,
checkpoint] → S2=5732db2f OPEN → sessions for work: [CLOSED, OPEN] →
WORK status: active. (Invariant held: work survives session rotation.)

## Things explicitly left open

- Phase 9 budgets: work_budgets model written to memory_models.py (local,
  uncommitted); migration 0006 was locally edited to include it — MUST be
  reverted and re-done as migration 0007 (prod already applied 0006).
  Budget endpoints/tests not started.
- Phase 10 SSE + Attention/Audit: not started.
- Hermes state-sync task-completion hook: deferred (hourly timer +
  on-demand exec deemed sufficient; documented per plan §6).
- Final flight handoff (§19) and agents.md findings log entry: not written.
