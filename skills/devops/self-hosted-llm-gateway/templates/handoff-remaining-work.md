# <PROJECT> v<VER> — HANDOFF: Remaining Work (<YYYY-MM-DD>)

**Written by:** <agent profile / model> · **Supersedes:** <prior handoff file or section>
**Basis:** plan doc + LIVE SERVER VERIFICATION (artifacts, DB, services) — not just session notes.
**First move for the next agent:** run the verification pass in §2 yourself before trusting this queue.

## 1. Executive status

| Plan section / phase | Status |
|---|---|
| <phase A — infra> | ✅ done (evidence: report path) |
| <phase B — benchmarks> | 🟡 ~80% (benching done, decision not finalized) |
| <phase C> | ❌ not started |

**Nothing is broken** — OR — list exactly what is broken + workaround.

## 2. Verified live state (<timestamp of checks>)

- Services: `systemctl is-active` for each unit — one line each.
- Fleet table: host · IP · desired vs current state · serving what · registry health/routable.
- Presets/rollback anchors preserved (exact names + where stored).
- Active unit ExecStart **verbatim** (it is the deployed config, not the doc).
- Leftover operational state from the last session (e.g. host left in MAINTENANCE for benching → must be restored; name the exact SQL/command).

## 3. WORK NOT COMPLETE — next agent's queue (in order)

### 3.1 <Phase> finale ⭐ HIGHEST PRIORITY
- Evidence already gathered (paste the comparison table / numbers — never make the next agent re-run settled benchmarks).
- The decision to make + recommendation with reasoning.
- Implementation steps (exact commands/SQL), verification steps.
- Cleanup items (junk rows/presets, stale flags).

### 3.2 <Next phase> — not started
- Scope boundary restated explicitly (e.g. "NO RDMA/SR-IOV/multi-node — out of scope; do not add NICs").

### 3.3 Final deliverable
- Assemble report from existing artifact paths (list every path on every host) — do not re-generate data.

## 4. Access cheat-sheet (verified working <date>)

- Workdir + helper scripts (`pve.py exec <node> <vmid> '<cmd>'`), node/vmid map.
- DB access: venv python + creds file path + password-line format (never the value).
- UI/API auth path (bot account, group id, cookie flow).
- Config regen command (e.g. `litellm_sync.py && systemctl restart litellm`).
- Known quoting trap: deliver scripts via base64 staging (helper → `sudo mv` → run); never inline heredocs/`$$` through guest exec.

## 5. Constraints to keep honoring (unchanged — restate in one line each)

## 6. Gotchas that cost time this chain (so the next agent doesn't re-debug)

- Serial-only bench legs; MAINTENANCE gate before sweeps + restore after.
- Tokenizer/endpoint/HF_HOME flags for `vllm bench serve`.
- Any incident where a subsystem worked as designed but looked like a failure.
