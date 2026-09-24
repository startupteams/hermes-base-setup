# Multi-Question Batch Analysis Pattern

Session walkthrough from July 6, 2026 — 5 sequential Fable 5 analyses for incubator strategy.

## Session Structure

The founder asked 5 strategic questions in one message, referencing multiple context sources:
1. Prioritized goals from a previous Fable 5 session (Obsidian vault)
2. Hardware architecture repo (GitHub, private)
3. Business idea generator app (Vercel, basic auth) + local repo data
4. USA tasks prioritization context

## What Worked

### Parallel context gathering
All independent reads were batched into single assistant turns:
- `read_file` for prioritized_goals.md and fable_prompt_source.txt
- `terminal` for Obsidian vault file listing, GitHub repo clone, curl with basic auth for web app content
- `terminal` for `git clone` of hardware research repo
- All ran concurrently, saving ~4-5 round trips

### Prompt file construction
Each of the 5 prompts was under 2.5KB, containing:
- 1-2 line founder intro
- Numbered question (exact from founder's request)
- Only relevant context sections (not all context dumped into every prompt)
- Output format instruction

### Sequential execution with todo tracking
- Created todo list with 6 items (5 questions + 1 commit/save)
- Ran each Fable 5 call with timeout=300, one at a time
- After each completed, saved output via `write_file` to the Obsidian vault
- Marked each todo complete before starting the next

### Batch commit
After all 5 outputs were saved, one `git add -A && git commit && git push` operation committed everything with a descriptive multi-line message.

## Key Observations

- **Fable 5 print mode reliably produces 200-400 line outputs** for 2-3KB prompts with structured context. Quality was consistently high across all 5 questions.
- **Output always starts with a preamble** like "The file write wasn't permitted, so here is the full document inline" — this is harmless. The actual analysis follows. Strip this preamble when saving.
- **300s timeout was sufficient** for all 5 prompts (2-2.5KB each). No timeouts occurred.
- **No session limit issues** when running 5 jobs sequentially (vs. the 3+ parallel failure documented in fable-5-prompt-limits.md).
- **Fable 5 outputs are ready-to-save markdown** — minimal post-processing needed. Just strip the preamble line and save.

## Command Pattern

```bash
# For each question:
claude -p "$(cat /tmp/fable_qN_topic.txt)" --max-turns 20
# timeout=300 in terminal() call

# After all complete:
cd ~/obsidian_vault_jordan_ulmer && git add -A && git commit -m "feat: Add Fable 5 analysis — Q1-Q5" && git push origin main
```

## Failure Modes to Watch For

1. **Prompt too large (>4KB):** Timeout risk. Split into smaller targeted prompts.
2. **Running parallel:** Session limit exhaustion after 2+ concurrent jobs. Always sequential.
3. **Forgetting to save:** Fable 5 can't write files in print mode. You must `write_file` each output.
4. **Not stripping preamble:** First line often says "File write wasn't permitted..." — remove it before saving.
5. **Context not self-contained:** Each prompt must include all needed context — Fable 5 has no memory of prior prompts in the batch.
