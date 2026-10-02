---
name: claude-handoff
description: Hand a Startup Teams implementation plan to Claude Code.
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Claude-Code, Delegation, Implementation-Plans, Handoff]
    related_skills: [claude-code-delegate, claude-code]
---

# Claude Code Handoff

Hand a bounded Startup Teams implementation plan to Claude Code for autonomous
implementation, then independently verify the result and return a concise
handoff report to the user. Hermes delegates; it does NOT implement the plan
itself. Assumes an authenticated Claude Code CLI on this host (see
`claude-code-delegate` for auth/wrapper specifics).

## When to Use

- User says: "hand this off to Claude Code", "delegate this plan to Claude",
  "have Claude implement this".
- User explicitly invokes /claude-handoff.
- Any Startup Teams implementation plan is ready for bounded execution.

## Prerequisites

- Authenticated `claude` CLI on the host (Max subscription OAuth; never set
  ANTHROPIC_API_KEY — it would override subscription billing).
- On MIAM-00101 the wrapper `claude-opus-delegate <repo-dir> <task.md> [model]`
  runs the print-mode invocation below; prefer it.
- A current implementation plan and its target repository path.

## How to Run

Invoke through the `terminal` tool (on Docker-sandboxed hosts, run the claude
invocation on the host per `claude-code-delegate`). Prefer non-interactive
print mode with Opus:

```
claude -p --model opus
```

or the wrapper equivalent:

```
claude-opus-delegate <repo-dir> /tmp/<workid>-claude.md opus
```

## Quick Reference

- Plan file: write the bounded plan to `/tmp/<workid>-claude.md` (durable,
  not a long chat transcript).
- Invocation: `claude -p --model opus` (print mode, fresh session per plan).
- Verification: `git status`, `git diff`/`git log`, run the test suite.
- Report result as: COMPLETE / PARTIAL / BLOCKED.

## Procedure

1. Identify the current implementation plan and target repository.
2. Preserve the parent plan unchanged — hand Claude the plan as written.
3. Verify the repository and current Git branch before delegation (`git -C
   <repo> status && git -C <repo> branch --show-current`).
4. Write the complete bounded implementation plan to a task file: objective,
   repo, in/out of scope, acceptance criteria, safety constraints, required
   result format.
5. Run Claude Code in print mode with Opus (see How to Run) from the repo.
6. Allow Claude to: inspect the repository; edit files; run tests; debug
   failures; prepare implementation changes.
7. Do NOT dump Claude's entire transcript into the Hermes context. Capture
   only the final result (and session_id/cost when using the JSON wrapper).
8. Independently inspect the result — Claude's self-report is not
   verification: check `git status`, `git diff`/commits, run the tests
   yourself, and note any reported blockers.
9. Return a concise handoff to the user containing:
   - result: COMPLETE / PARTIAL / BLOCKED;
   - what Claude changed;
   - tests and exact result;
   - branch / commit / PR if created;
   - deployment state if relevant;
   - blockers;
   - technical debt;
   - recommended next action.

## Safety

- Do not alter unrelated repositories.
- Do not expose secrets to Claude prompts.
- Do not modify production infrastructure unless the parent plan explicitly
  authorizes it.
- Do not interpret delegation as permission to expand product scope.
- Preserve the parent ACMS Work ID when one exists.

## Session Policy

Prefer a fresh Claude Code execution for each bounded implementation plan.
Use durable PLAN.md and HANDOFF.md files rather than maintaining an
unnecessarily long Claude conversation.

## Pitfalls

- Print mode (`-p`) is the only reliable non-interactive path; interactive
  TUI sessions require tmux handling (see `claude-code`) and are overkill
  here.
- Always set `--max-turns` (print mode only) to prevent runaway loops.
- Session resumption (`-c`/`-r`) only finds sessions from the same working
  directory — another reason to keep one fresh session per plan.
- The wrapper's result may carry an unrelated "connectors need authorization"
  notice appended to the text; ignore it.
- Private-LAN infrastructure tasks (Proxmox, PDU, 10.0.20.x) stay with
  Hermes; do not hand them to Claude.

## Verification

From the repo, `git -C <repo> status --porcelain` plus a run of the plan's
home test command returning exit 0 proves the handoff produced a verified,
working change set.
