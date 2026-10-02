# Hermes state portability tooling (v0.17) + state.db schema notes

Verified 2026-09-24 on VM906 (Hermes Agent v0.17.0, source at `~/.hermes/hermes-agent`).

## Native CLI semantics — what is safe for merging vs not

| Command | Semantics | Use for brain migration |
|---|---|---|
| `hermes sessions export OUT.jsonl` | JSONL archive (per-session, `--session-id`/`--source` filters) | ✅ SAFE — archive/knowledge |
| `hermes import <zip>` | **Replacement-restore** of the Hermes home (`--force` overwrites) | ❌ NEVER into a live agent you don't want replaced |
| `hermes profile export NAME` | tar.gz of full profile (includes config + env) | ❌ for sharing — leaks credentials/config |
| `hermes profile import FILE` | Restores profile archive | ❌ same replacement concern |
| `hermes_state_portability.py` | Not present in v0.17 tree (plan §9 anticipated it) | n/a — decision rule: if no additive importer exists, use archive route |

Decision rule (from migration plan §9): additive importer proven → may use; replacement-only → archive route.

## state.db schema (profile `agent_stea004_entrepreneur`, 2026-09-24)

Tables: `schema_version`, `sessions`, `messages`, `state_meta`, `compression_locks`,
`messages_fts*` (FTS5 + trigram), plus WAL sidecars on the live DB.

`sessions` (186 rows): `id TEXT PK, source, user_id, model, model_config, system_prompt
(the big blob — hash it, don't export it), parent_session_id, started_at REAL,
ended_at REAL, end_reason, message_count, tool_call_count, input_tokens, output_tokens,
cache_read_tokens, cache_write_tokens, reasoning_tokens, cwd, billing_*,
estimated_cost_usd, actual_cost_usd, cost_status, title, api_call_count, handoff_*,
rewind_count, archived, session_key, chat_id, chat_type, thread_id, git_branch,
git_repo_root`. Session IDs look like `20260622_094534_c788d6db`, `cron_<job>_<ts>`.

`messages` (20,867 rows): `id INTEGER PK, session_id TEXT FK, role, content TEXT,
tool_call_id, tool_calls, tool_name, timestamp REAL, token_count, finish_reason,
reasoning, reasoning_content, reasoning_details, codex_*_items, platform_message_id,
observed, active, compacted`.

Exporter notes that mattered:
- `memory_store.db` `facts` has **no bank_id** — don't join `facts`→`memory_banks` on a
  nonexistent column (the exporter errors `no such column: f.bank_id`); export facts
  flat with `fact_id, content, category, tags, trust_score, created_at, updated_at`.
- `verification_evidence.db`: `meta`, `verification_events`, `verification_state`.

## Consistent snapshot recipe (live gateway running)

```python
import sqlite3
s = sqlite3.connect("/path/state.db")     # live, WAL mode
d = sqlite3.connect("/backup/state.db")
with d:
    s.backup(d)                            # page-by-page consistent copy
d.close(); s.close()
ok = sqlite3.connect("/backup/state.db").execute("PRAGMA quick_check;").fetchone()[0]
assert ok == "ok"
```

CLI `sqlite3 .backup` is equivalent but may be absent (PEP668 boxes, no sudo password);
the Python API needs nothing beyond stdlib.

## Portable-archive export shape (proven)

```
conversation_exports/
├── INDEX.md                     # chronological table: started, source, title, msgs, file
├── messages.jsonl               # joined messages+sessions, content scrubbed, truncated
├── memory_records.jsonl
├── sessions/<session_id>.md     # per-session transcript (title/source/model/times header,
│                                #   per-message ts+role+tool, content scrubbed, 20k cap)
└── raw/ (optional)              # sessions.jsonl / messages.jsonl if Omen-side wants raw
```

On the destination it becomes `~/.hermes/memories/imported_<instance>_history/` —
searchable knowledge, zero DB risk.
