---
name: agent-task-workflow
description: "Standard workflow for approaching tasks — always review available skills at /opt/hermes/skills/ first, then execute methodically with verified tool output."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Agent, Workflow, Task-Execution, Skills, Standing-Rule]
    category: agent
---

# Agent Task Workflow

## Standing Rule: Review Skills First

**Before starting ANY task, always scan the skills directory at `/opt/hermes/skills/`** to identify the appropriate skill for the work at hand. This is a non-negotiable first step that applies to every task, regardless of type or complexity.

### Why This Matters

- Skills contain pre-built workflows, scripts, and references that save time and prevent reinventing solutions
- The skills directory may contain updates or new capabilities not yet documented elsewhere
- Skipping this step risks using outdated approaches or missing available tooling
- The user has explicitly requested this as a standing rule for all future tasks

### How to Review Skills

1. **List the skills directory:**
   ```bash
   search_files(target='files', path='/opt/hermes/skills', pattern='*')
   ```
   Or use `skills_list` to check the loaded skill registry.

2. **Read relevant SKILL.md files:**
   - Match skill names/descriptions to the task domain
   - Load the full SKILL.md via `skill_view(name='<skill-name>')` or direct `read_file`
   - If the skill references support files (scripts/, templates/, references/), load those too

3. **If no skill matches:**
   - Proceed with general problem-solving
   - Note the gap for potential skill creation

## Task Execution Pattern

### 1. Skill Discovery (Always First)
- Scan `/opt/hermes/skills/` before any task
- Load relevant skills and their support files
- If a skill provides scripts, prefer them over hand-writing solutions

### 2. Understand the Problem
- Clarify ambiguous requirements before executing
- Break complex tasks into discrete, verifiable steps
- Identify dependencies between steps

### 3. Execute with Verification
- Prefer skill-provided scripts and templates
- Verify each step with **actual tool output**, not assumptions
- If a tool fails, try alternatives before reporting failure
- Never substitute plausible-looking fabricated output for real results

### 4. Complete and Report
- Deliver working artifacts backed by real execution results
- Summarize what was done and any caveats
- If the task produced a reusable pattern, consider saving it as a skill

## When to Create a New Skill

Create a new class-level skill when:
- A non-trivial technique or workaround emerged that would benefit future sessions
- The user corrected your approach and the correction applies to a class of tasks
- You discovered a new tool-usage pattern that solves a recurring problem
- A skill was loaded but turned out to be wrong, missing a step, or outdated — patch it immediately

### Do NOT Create Skills For

- One-off tasks with no reusable pattern
- Environment-dependent failures (missing binaries, fresh-install errors, unconfigured credentials)
- Session-specific transient errors that resolved before the conversation ended
- Negative claims about tools or features that may be fixed later
- Task narratives (e.g., "summarize today's market") — these are not classes of work

## Multi-Profile / Memory-Security Audit Practice (session-derived)

When a task involves hermes agent memory (state.db, memories/, auth.json, profile branches):

- Always check `/opt/hermes/skills` first (skill-first-workflow).
- Before changing core engine / memory schemas or fine-tuning arrays, ask user confirmation.
- When multi-profile isolation is relevant (`profiles/biraj/` vs `profiles/robin/` branches): verify cross-branch file access (same repo clone = same filesystem), `auth.json`, `state.db`, `memories/`, `gateway_routing`, `init_employee.py` defaults.
- Security audit pattern: list profile files (`find -ls`), check `.gitignore` for auth, `chmod` on `auth.json` vs `MEMORY.md`, DB WAL mode / FTS5 sanitization, note branch isolation ≠ filesystem isolation.
- Capture fix proposals but do NOT apply without explicit confirmation.
- References: `references/memory-security-audit.md`.

## Skill Update Signals

Update a skill when any of these fire:

| Signal | Action |
|--------|--------|
| User corrected your style, tone, format, or verbosity | Update the relevant skill to embed the preference |
| User corrected your workflow or sequence of steps | Encode as a pitfall or explicit step |
| Non-trivial technique, fix, or workaround emerged | Capture in the skill that governs that task class |
| A loaded skill was wrong, missing a step, or outdated | Patch it immediately |

## User Preference Embedding

When the user expresses a style/format/workflow preference:

- **Put it in the SKILL.md body**, not just in memory
- Memory captures "who the user is and what the current state is"
- Skills capture "how to do this class of task for this user"
- The next session starts already knowing the preference