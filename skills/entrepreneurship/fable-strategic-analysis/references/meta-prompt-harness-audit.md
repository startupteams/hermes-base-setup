# Harness Meta-Prompt Audit Patterns
# Source: Daniel Miessler — "10 Prompts to Run When Fable Comes Back"
# Date: 2026-07-03

## Context

Daniel Miessler published 10 tactical meta-prompts designed to run with maximum-intelligence models (Claude Fable 5) to upgrade your AI harness at a deep level. Three of these are applicable to Hermes Agent harnesses and were executed in this session.

## The Three Relevant Meta-Prompts

### 1. Harness Optimization

**Prompt:** "Look at our overall harness and characterize what I'm ultimately trying to accomplish with it. Then find the parts of the system — system prompt, AGENTS/CLAUDE.md files, hooks, skills, and the rest — that are working against that goal."

**What it finds:** Goal alignment gaps. The system prompt describes a role (e.g., "Strategic Ideation Partner") that may not match the actual work being done (e.g., hands-on infrastructure engineering). Config settings optimized for a different operational mode.

**Output:** Identification of the real goal, parts working against it, and specific config edits to close the gap.

### 2. Bitter Lesson Optimization

**Prompt:** "Deeply study Richard Sutton's Bitter Lesson essay and how it applies to overengineering, specifically for AI and coding harnesses. Then do a full analysis of our harness in its entirety, look for every place we're violating Bitter Lesson Engineering, and give me a comprehensive plan for upgrading the system to be more flexible to future improvements in the models we use."

**What it finds:** Premature complexity. Systems built for projected capacity rather than actual need. Over-engineered routing matrices, multi-node clusters for single-machine workloads, hardcoded provider-specific logic that won't scale with model improvement.

**Output:** Specific places violating the Bitter Lesson (scale with computation, not human-engineered knowledge), and a simplified architecture plan.

### 3. Self-Model Audit

**Prompt:** "Read everything my harness believes about me — identity, goals, voice, preferences — and find where it's modeling a version of me that's stale, aspirational, or just wrong. Compare what my files say I am against what my recent behavior and work actually reveal, flag every place the system is optimizing for who I said I was instead of who I am now, and propose the specific edits that close the gap."

**What it finds:** Stale personas. Profiles set during initial setup that haven't been updated as the actual work evolved. Personality settings mismatched with operational context. Work-style preferences that no longer reflect current behavior.

**Output:** Side-by-side comparison of "what harness believes" vs "what work reveals," with specific editable config/memory entries.

## Fallback Technique (When Fable 5 Hits Session Limit)

Fable 5 has a per-session token budget. When running multiple analyses in parallel, they can exhaust the budget causing all jobs to fail with "You've hit your session limit."

**Recovery procedure:**
1. Shorten each prompt to essentials — strip verbose context, keep the core question
2. Reduce concurrent jobs from 3 to 1 (sequential is safer than parallel)
3. If Fable still won't run: use the current model with the full prompt + context injected. Same structure and depth as Fable output — just without Fable's specific reasoning style.
4. Verify output depth: expect 100+ lines for comprehensive analysis. Under 50 means shallow.

## Session Results (2026-07-03)

All three analyses were completed via fallback (current model with full context). Results stored in:

- `TODOS/work/harness-optimization/output.md` — 113 lines
- `TODOS/work/bitter-lesson-optimization/output.md` — 121 lines  
- `TODOS/work/self-model-audit/output.md` — 193 lines

Commit: `b52fa13`

## Related Meta-Prompts (Not Executed in This Session)

These are from the same article but were deferred — they require different context:
- **Memory that compounds** — requires examining the harness's own memory patterns
- **What does "better" even mean** — requires measurable evals built into the harness
- **The autonomy ladder** — directly relevant, maps to trust boundary analysis
- **Decisions into policy** — surfaces latent rules behind repeated decisions
- **The bus-factor audit** — undocumented dependencies and "you-shaped holes"
- **Deployed infrastructure audit** — requires scanning all deployed systems
- **Prompt injection handling** — requires deep analysis of all harness inputs
- **Big picture** — requires web search across all projects and writing
- **Where am I most wrong** — requires steelmanning largest bets against each other
