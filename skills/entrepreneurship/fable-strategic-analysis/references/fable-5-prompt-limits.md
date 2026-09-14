# Fable 5 — Prompt Size & Concurrency Limits

## Session Token Budget (2026-07-04)

Fable 5 (`claude-fable-5`) has a finite per-session token budget. When exhausted, all parallel jobs fail with "You've hit your session limit."

### Observed Limits

| Scenario | Result |
|----------|--------|
| 1 x ~10KB prompt (full repo survey) | Timed out at 300s — rejected by timeout before hit budget |
| 1 x ~3KB prompt (strategic analysis) | ~2.5 min, ~132 lines — succeeded |
| 3+ parallel Fable 5 jobs | Session budget exhausted, all fail with "You've hit your session limit" |
| 2 concurrent Fable 5 jobs | May succeed or hit budget depending on prompt size |

### Rules

1. **Never run 3+ parallel Fable 5 jobs.** Max 2 concurrent. For more tasks, run sequentially.
2. **Keep prompts under 3-4KB** for reliable single-job completion. Above 5KB, timeout risk increases.
3. **For multi-repo analysis**, split into targeted prompts (one per repo category) rather than one monolith:
   ```
   # Bad: One 10KB prompt covering 13 repos
   # Good: 3-4 prompts of 2-3KB each, run sequentially
   ```
4. **Use `--max-turns 20`** — Fable 5 needs 120-180s for deep analysis. Set timeout to 180s.
5. **Fallback is always available** — If Fable 5 fails, run with any available model using the same prompt. Quality may differ but task completes.

### Diagnostic

To check if budget is near exhaustion:
```bash
# If multiple jobs fail with "session limit" simultaneously, budget is exhausted
# Solution: wait for current sessions to complete, then run next batch
```
