---
name: fable-strategic-analysis
description: Run structured strategic analysis for founders using Claude Fable 5.
version: 0.1.0
author: Hermes
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Strategy, Claude, Founder, Planning]
---

# Fable 5 Strategic Analysis for Founders

Run comprehensive strategic planning sessions with Claude Fable 5 using a proven prompt structure that captures full founder context and produces prioritized, actionable goal maps. Built from a real 132-line analysis of a YC-aspiring founder's 7-workstream situation.

## When to Use

- Founder asks "what should I focus on next" with complex multi-area context
- Planning a 1-3 month trip/retreat/visit with mixed personal and business priorities
- You need to convert 5+ workstreams into a prioritized execution plan
- Prioritization framework is needed (stop bleeding → family → one bet → team → infrastructure)
- Output needs to be a saveable markdown file with milestones and weekly time allocation
- **Multi-question batch analysis:** Founder asks several strategic questions at once (e.g., "give me infra advice, a revised business model, a roadmap, and new ideas"). See "Multi-Question Batch Analysis" section below.

## Prerequisites

- Claude Code v2.x with Fable 5 model (`claude-fable-5`) installed and authenticated
- `~/.claude/settings.json` contains `"model": "claude-fable-5"`
- Print mode is used (no tmux required — see pitfalls below)
- Output file target path known (e.g., `~/prioritized_goals.md` or Obsidian vault path)

## How to Run

1. Gather founder context from the conversation (business ideas, team, family, cash flow, goals, constraints).
2. Write the full context to a temp file using `write_file`.
3. Run Claude Fable 5 in print mode with the prompt loaded from that file.
4. Parse the output and save the markdown to the target location.
5. Commit to the founder's Obsidian vault or project repo.

## Quick Reference

```bash
# Run from terminal tool — cat the prompt file into -p argument, print mode, structured output
claude -p "$(cat /tmp/fable_prompt.txt)" --max-turns 20

# Alternative: pipe stdin (also works but -p is cleaner for interpolation)
cat /tmp/fable_prompt.txt | claude -p "Analyze this entrepreneur situation..." --max-turns 20

# Check output line count to verify depth
wc -l ~/prioritized_goals.md  # expect 100+ lines for comprehensive analysis

# Set timeout=300 for 2-3KB prompts (180s is minimum for tiny prompts; 300s is safer)
```

## Procedure

1. **Write context file.** Call `write_file` with the full founder context (see template below). Save to `/tmp/fable_prompt.txt`.

2. **Run Fable 5.** Invoke `terminal` with:
   ```bash
   claude -p "$(cat /tmp/fable_prompt.txt)" --max-turns 20
   ```
   Set `timeout=300` — Fable 5 needs 120-300s depending on prompt complexity. 180s for simple single-question prompts under 2KB; 300s for richer 3-4KB prompts with multi-section context.

3. **Verify output.** Call `terminal` with:
   ```bash
   wc -l ~/prioritized_goals.md
   ```
   Expect 100+ lines for a comprehensive analysis. If under 50, the analysis was shallow.

4. **Save to vault.** If the founder uses Obsidian:
   ```bash
   mkdir -p ~/obsidian_vault_jordan_ulmer/TODOS/work/USATasksPrioritization
   cp ~/prioritized_goals.md ~/obsidian_vault_jordan_ulmer/TODOS/work/USATasksPrioritization/
   cp /tmp/fable_prompt.txt ~/obsidian_vault_jordan_ulmer/TODOS/work/USATasksPrioritization/fable_prompt_source.txt
   ```

5. **Commit to git.** Call `terminal` with:
   ```bash
   cd ~/obsidian_vault_jordan_ulmer && git add -A && git commit -m "feat: Add strategic analysis" && git push origin main
   ```

## Context Template

When writing the prompt context file, structure it with these sections:

```
[Founder intro] name, site, vision, current location
[Three core questions] what to focus on, path to profitability, what's becoming obsolete
[Time split areas — each with details]:
1. FAMILY — kids, spouse, location, emotional/mental health needs
2. SERVER BUILDING — hardware, timeline, tech stack, timeline deadline
3. SUPPORT RAISING — current $/mo, target, network size, campaign plan, tool (Epistle)
4. BUSINESS DEVELOPMENT — contacts, potential CEO candidates, incubator plans
5. MANAGING TEAM — each member name, role, strengths, weaknesses, status
6. [Other workstream] media equipment, real estate, etc.
```

Each workstream should include:
- **People:** names, relationships, websites
- **Numbers:** $/mo amounts, headcount, timelines, deadlines
- **Emotional/health context:** stress levels, counseling needs
- **Skills/culture notes:** work ethic differences, management style gaps

## Pitfalls

- **tmux interactive mode is NOT recommended for auth.** See `references/claude-code-tmux-oauth-quirks.md` for the full explanation of why fresh tmux sessions trigger OAuth even with valid cached credentials. Always prefer print mode (`-p`) for programmatic work.
- **Quote escaping in tmux send-keys fails.** Long prompts with mixed quotes break the tmux paste mechanism. Always use a temp file + pipe approach instead.
- **Fable 5 print mode can't write files.** If the `--output-format json` path was used and it timed out, re-run without `--output-format` and let it output plain text, then `write_file` it yourself.
- **Timeout is real.** A comprehensive 7-workstream analysis needs 120-180s for small prompts, up to 300s for richer 3-4KB prompts with multi-section context. Set timeout to 300s as a safe default; 180s works for prompts under 2KB.
- **132 lines is the quality floor.** If the output is under 80 lines, it likely missed depth. Check for P0-P4 prioritization, weekly time allocation, and milestone checkpoints.
- **The prompt file is useful to keep.** Save `fable_prompt_source.txt` alongside the analysis — it's a reusable artifact for future reference or refinement.
- **Fable 5 output begins with a preamble.** The first line often says "The write to X wasn't permitted..." — this is harmless, the actual analysis follows immediately after. Strip this preamble line when saving the output via `write_file`.
- **`--name` flag does NOT appear on claude.ai web portal.** Setting `--name` only sets a TUI label. It does NOT create a visible project entry on your claude.ai.com web sessions page.
- **Session limit exhaustion (2026-07-03).** Fable 5 has a per-session token budget. When running multiple parallel analyses, they can exhaust the budget mid-run, causing all jobs to fail with "You've hit your session limit." If this happens: (1) reduce the number of concurrent Fable jobs to 1, (2) shorten each prompt to the essentials (remove verbose context sections), (3) run them sequentially not in parallel, or (4) fall back to running the analysis yourself using the full prompt + context (same quality, just without Fable's specific reasoning style). The fallback is documented in `references/meta-prompt-harness-audit.md`.
- **Fable 5 session limit ceiling is ~5 sequential calls (2026-07-06).** In a batch of 5 sequential Fable 5 calls (each 2KB prompt, `--max-turns 20`, 120-300s each), all 5 completed successfully. A 6th call (review prompt) immediately hit "You've hit your session limit · resets 11:10am (UTC)". This means: (a) plan for max 5 Fable 5 calls per session window, (b) if you need a 6th call (e.g., review), either wait for the reset window or use the automated verification fallback below, (c) the reset time is shown in the error message and is typically ~1 hour from the last successful call.
- **Fable 5 review fallback — automated verification (2026-07-06).** When Fable 5 session limit prevents using it as a reviewer, perform automated checks via `execute_code` instead. This is NOT the same quality as Fable 5's reasoning, but it catches structural failures reliably. The check script should verify: (1) file existence (all expected output files present), (2) JSON validity (`json.load()` on ideas.json), (3) YAML frontmatter completeness (all required fields present via regex), (4) body section completeness (all required section headers present), (5) word count per file (quality floor), (6) accounting checks (e.g., `killed + absorbed + survivors == input_count`). Save the review output as `data/reorg/review.md` with PASS/FAIL per check. This pattern was used successfully for a 93-idea portfolio reorganization review.
- **Fable 5 prompt size limit.** A 10KB prompt (e.g., full repo survey) timed out at 300s. Keep prompts under 3-4KB for reliable completion. For multi-repo or large-context analysis, split into 3-4 targeted prompts of 2-3KB each, run sequentially. See `references/fable-5-prompt-limits.md`.
- **Running Fable 5 in parallel burns through tokens fast.** Each parallel job consumes a separate token allocation. Always run Fable jobs sequentially or with a maximum of 2 concurrent, not 3+.
- **Git default branch is NOT always `main`.** Before pushing, check `git remote show origin | grep HEAD` or `gh repo view --json defaultBranchRef`. Jordan's Obsidian vault (`obsidian_vault_jordan_ulmer`) uses `master` as its default branch. Pushing to `main` creates an orphan branch that GitHub won't show at the canonical URL. If you accidentally commit to `main` and the default is `master`, merge: `git checkout master && git merge main && git push origin master`.

## Post-Analysis Execution Pipeline

When Fable 5 produces instruction-type outputs (e.g., "prune these ideas", "develop these 10 new ideas"), the natural next step is to delegate execution to subagents, then have Fable 5 review the work.

### Pattern

1. **Fable 5 produces structured instructions** (e.g., REORGANIZE_IDEAS.md, NEW_IDEAS_DEVELOPMENT.md).
2. **Copy instruction files into the target repo** and commit to the working branch.
3. **Delegate execution to subagents** (via `delegate_task`). Give each subagent the instruction file path, the repo context, and the exact toolsets it needs. Run independent tasks in parallel.
4. **Fable 5 reviews the work.** Write a review prompt that checks: structural completeness (all files present, accounting checks pass), quality (claims grounded in evidence, unit economics realistic), and correctness (JSON valid, YAML well-formed, no missing slugs). Run as a standard Fable 5 print-mode call.
5. **Fix any issues Fable 5 identifies**, then commit, merge to default branch, and deploy.

### Subagent timeout on data-heavy follow-up tasks

When Fable 5 produces instruction-type outputs that require processing 50+ files (e.g., "read all 83 ideas, prune by rules, web-validate survivors, merge overlaps"), a single subagent will likely time out at the 600s limit (observed: 38 API calls in 600s, stuck mid-merge). The same applies to idea-development subagents that need web research for 10+ items.

**Mitigation strategies (in order of preference):**

1. **Split into smaller subagent tasks.** Instead of one subagent doing "read 83 files + web-validate 56 + merge + curate + finalize," dispatch one subagent for Steps 1-3 (ingest + prune + validate) and another for Steps 4-7 (merge + curate + finalize). Give the second subagent the first one's intermediate output files.
2. **Use `execute_code` to rescue timed-out subagents.** When a subagent times out but has produced intermediate JSON/CSV files, load those files in `execute_code` and complete the remaining steps programmatically. This is often faster than re-dispatching a subagent because the data is already parsed — you just need to apply merge logic, classification rules, and write the final output files. Example: load `_parsed_data.json` and `_validation_data.json` from the subagent's output directory, apply merge rules in Python, write `FINAL.md` and `final_ideas.json`.
3. **Give subagents the exact schema.** When asking a subagent to create files matching an existing format, read one existing file first and include the full YAML frontmatter in the subagent's context. This prevents the subagent from guessing field names and producing incompatible output.

### Fable 5 as reviewer

Fable 5 is not limited to producing analysis — it's also an effective reviewer of subagent-produced work. The review prompt should:
- List the specific files/directories to check
- Define PASS/FAIL criteria per check
- Ask for specific issues found and recommended fixes
- Use the same `claude -p` print mode, `--max-turns 20`, `timeout=300` pattern

### Subagent delegation tips for idea-system work

- Give subagents the EXACT YAML frontmatter schema from an existing idea file (read one first and include it in the context)
- For web research tasks, use `['web', 'file', 'terminal']` toolsets — `web` for search, not `browser` (StarterStory and similar sites have bot detection)
- For file-processing tasks that don't need web, use `['file', 'terminal']` to reduce token overhead
- Remind subagents: "Do NOT modify existing files in data/ideas/. Only create new files."
- **For tasks involving 50+ file reads or 10+ web searches, expect timeout.** Split the work or plan to complete the final steps yourself via `execute_code`.

## Multi-Question Batch Analysis

When the founder asks several strategic questions at once (e.g., "give me infra advice, a revised business model, a feature roadmap, and new ideas"), run them as a sequential batch — not in parallel (session limit exhaustion) and not as one monolith prompt (timeout at >5KB).

### Procedure

1. **Gather context in parallel.** Before writing any prompts, batch all independent reads: Obsidian vault files, GitHub repo files, local JSON data, basic-auth web apps (curl with credentials), existing skill files. Use parallel `read_file` and `terminal` calls.
2. **Write one prompt file per question.** Each prompt file should be under 3-4KB. Include only the context relevant to that specific question — don't dump everything into every prompt. Save to `/tmp/fable_q{N}_{topic}.txt`.
3. **Use a todo tracker.** Create a todo list with one item per question plus a commit/save item. This keeps the batch on track and shows the user progress.
4. **Run sequentially.** Execute each Fable 5 call one at a time, waiting for completion. After each completes, save the output to the target Obsidian vault path using `write_file` (Fable 5 print mode cannot write files itself).
5. **Commit all outputs at once.** After all 5 (or N) analyses are saved, git add + commit + push in one operation.
6. **Send a summary.** If the founder asks for documentation, email a summary with the GitHub link.

### Prompt construction

Each prompt should be self-contained — Fable 5 has no memory of prior prompts in the batch. Include:
- Who the founder is (1-2 lines)
- The specific question (numbered, exact wording from the founder's request)
- Only the context sections relevant to that question
- Output format instruction ("Output a detailed markdown file...")

### Example batch structure

```
/tmp/fable_q1_infra.txt      → Q1: Physical technology setup
/tmp/fable_q2_business.txt   → Q2: Revised business model
/tmp/fable_q3_roadmap.txt    → Q3: Feature roadmap
/tmp/fable_q4_prune.txt      → Q4: Prune/merge instructions
/tmp/fable_q5_new_ideas.txt  → Q5: New ideas with dev instructions
```

See `references/multi-question-batch-pattern.md` for a detailed session walkthrough.

### Context-gathering checklist

Before writing prompts, gather these in parallel:
- **Obsidian vault:** `find ~/obsidian_vault_jordan_ulmer/TODOS/work/ -type f` to discover existing analyses
- **Prior Fable 5 outputs:** Read any `prioritized_goals.md` or `fable_prompt_source.txt` for accumulated context
- **GitHub repos:** Clone or read files from relevant repos (hardware architecture, business idea data)
- **Web apps with basic auth:** `curl -s -u "user:pass" "https://app.example.com/page"` for deployed idea generators or dashboards
- **Local JSON data:** `python3 -c "import json; ..."` to extract structured data from idea indexes
## Verification

```bash
# Confirm file exists and has substantive depth
wc -l ~/prioritized_goals.md
# Expected: 100+ lines

# Confirm the key sections are present
grep -c "P0\|P1\|P2\|P3\|P4" ~/prioritized_goals.md
# Expected: 4+ (one per priority tier)
```

## References

- `references/multi-question-batch-pattern.md` — Session walkthrough for running 5+ sequential Fable 5 analyses with shared context, todo tracking, and batch commit.
- `references/claude-code-tmux-oauth-quirks.md` — Why fresh tmux sessions trigger OAuth and why print mode is preferred.
- `references/meta-prompt-harness-audit.md` — Fallback analysis approach when Fable 5 is unavailable or session-limited.
- `references/fable-5-prompt-limits.md` — Prompt size, timeout, and concurrency limits observed in practice.
