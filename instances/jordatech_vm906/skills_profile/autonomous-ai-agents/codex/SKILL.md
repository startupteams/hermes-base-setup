---
name: codex
description: "Delegate coding to OpenAI Codex CLI — one-shot execution, background mode, parallel worktrees, PR reviews, and batch issue fixing. Full CLI reference with flags, sandboxes, and session management."
version: 2.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [codex, openai, coding, pr-review, parallel, sandbox, background]
    related_skills: [claude-code, ruflo, nomos, hermes-agent]
---

# Codex CLI — OpenAI's Autonomous Coding Agent

> Codex is OpenAI's autonomous coding agent CLI. Use it for building features, refactoring, PR reviews, and batch issue fixing with full sandboxing and parallel execution.

## When to Use

- **Building features** end-to-end with self-correction
- **Refactoring** existing codebases with safety nets
- **PR reviews** with deep code analysis
- **Batch issue fixing** — parallel worktrees, concurrent fixes
- **Long-running coding sessions** with progress monitoring
- **Sandboxed execution** — isolated environments for unsafe operations

## Prerequisites

```bash
# Install Codex CLI
npm install -g @openai/codex

# Verify
codex --version

# Authenticate
codex auth login  # OAuth flow
# OR set API key
export OPENAI_API_KEY=sk-...
```

## Core Usage Patterns

### One-Shot Tasks (Fastest Path)

```bash
# Simple one-shot — runs and exits when done
codex exec 'Add dark mode toggle to settings page' \
  --workdir ~/project

# With model selection
codex exec 'Refactor auth module to use JWT' \
  --model gpt-4o \
  --workdir ~/project

# Limit turns to prevent runaway
codex exec 'Fix all TODO comments' \
  --max-turns 20 \
  --workdir ~/project
```

### Background Mode (Long Tasks)

```bash
# Start background session
codex exec 'Refactor the entire API layer to async/await' \
  --workdir ~/project \
  --full-auto &

# Monitor with process tool
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Submit input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

### Interactive Mode (PTY Required)

```bash
# MUST use pty=true — Codex is an interactive terminal app
terminal(command="codex --workdir ~/project", pty=true, background=true)

# Send prompt
process(action="submit", session_id="<id>", data="Review this PR")

# Exit
process(action="write", session_id="<id>", data="\x03")  # Ctrl+C
```

## Sandbox Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `bubblewrap` | Default. Isolated filesystem, network | Safe development work |
| `danger-full-access` | No sandbox | Hermes gateway contexts where bubblewrap fails |
| `yolo` | No sandbox, no approvals | Trusted environments, fast iteration |

```bash
# Default sandbox (recommended)
codex exec 'Task' --sandbox bubblewrap

# No sandbox — use when bubblewrap fails
codex exec 'Task' --sandbox danger-full-access

# Yolo mode — no checks
codex exec 'Task' --yolo
```

## PR Review Pattern

### Quick Review
```bash
cd ~/project
codex exec 'Review this PR for bugs, security issues, and style problems' \
  --from-pr 42 \
  --workdir ~/project
```

### Deep Review
```bash
# Clone to temp dir for isolation
REVIEW=$(mktemp -d)
git clone https://github.com/user/repo.git $REVIEW
cd $REVIEW
gh pr checkout 42
codex exec 'Thorough PR review. Check for: bugs, security, performance, missing tests' \
  --workdir $REVIEW
```

### Batch PR Reviews
```bash
# Fetch all PRs
git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'

# Review in parallel
codex exec 'Review PR #86' --workdir ~/project &
codex exec 'Review PR #87' --workdir ~/project &
codex exec 'Review PR #88' --workdir ~/project &
wait

# Post comments
gh pr comment 86 --body '<codex-review-output>'
gh pr comment 87 --body '<codex-review-output>'
```

## Parallel Issue Fixing with Worktrees

```bash
cd ~/project

# Create worktrees
git worktree add -b fix/issue-78 /tmp/issue-78 main
git worktree add -b fix/issue-99 /tmp/issue-99 main

# Launch Codex in each (concurrently)
codex exec 'Fix issue #78: <description>. Commit when done.' \
  --workdir /tmp/issue-78 --yolo &

codex exec 'Fix issue #99: <description>. Commit when done.' \
  --workdir /tmp/issue-99 --yolo &

wait

# Push all
cd /tmp/issue-78 && git push -u origin fix/issue-78
cd /tmp/issue-99 && git push -u origin fix/issue-99

# Create PRs
gh pr create --repo user/repo --head fix/issue-78 --title 'fix: #78'
gh pr create --repo user/repo --head fix/issue-99 --title 'fix: #99'

# Cleanup
git worktree remove /tmp/issue-78
git worktree remove /tmp/issue-99
```

## Key Flags Reference

### Session & Environment
| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--workdir /path` | Working directory |
| `--model gpt-4o` | Model selection |
| `--max-turns 20` | Limit agentic loops |
| `--continue` | Resume last session |
| `--session id` | Resume specific session |
| `--yolo` | No sandbox, no approvals |

### Sandboxing & Safety
| Flag | Effect |
|------|--------|
| `--full-auto` | Auto-approve file changes in workspace |
| `--sandbox danger-full-access` | No sandbox |
| `--yolo` | Full access, no approvals |

### Output
| Flag | Effect |
|------|--------|
| `--verbose` | Detailed output |
| `--dry-run` | Show what Codex would do without executing |

## Hermes Integration Patterns

### Pattern 1: Quick Code Review
```python
from hermes_tools import terminal

# One-shot review
result = terminal(
    command=f"cd {project_dir} && codex exec 'Review these changes for bugs' --from-pr {pr_num}",
    timeout=120
)
# Parse and present review results
```

### Pattern 2: Feature Implementation
```python
from hermes_tools import terminal, search_files

# 1. Understand the codebase
terminal(command="codex exec 'Summarize the architecture of the auth module'")

# 2. Implement the feature
terminal(
    command=f"codex exec 'Implement OAuth refresh flow' --workdir {project_dir}",
    background=True,
    timeout=300
)

# 3. Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")
```

### Pattern 3: Batch Bug Fixes
```python
# Find all TODOs
todos = search_files(pattern="TODO", path=project_dir, output_mode="content")

# Delegate each to parallel Codex instances
for todo in todos[:5]:  # Process 5 at a time
    terminal(
        command=f"codex exec 'Fix: {todo}' --workdir {project_dir} --yolo",
        background=True,
        timeout=120
    )

# Monitor all
process(action="list")
```

## Pitfalls & Gotchas

1. **MUST use `pty=true` for interactive mode** — Codex is an interactive terminal app. Without PTY, it hangs.
2. **Must run inside a git repository** — Codex refuses to run outside a git directory. Use `mktemp -d && git init` for scratch.
3. **Bubblewrap fails in Hermes gateway** — When running from a Hermes service context, bubblewrap sandbox may fail with permission errors. Use `--sandbox danger-full-access` instead.
4. **Session resumption requires same directory** — `--continue` only works in the same working directory.
5. **No built-in rate limit display** — Codex doesn't show rate limit status. Monitor API usage separately.
6. **Turn limits prevent runaway but not all issues** — `--max-turns` stops the agent loop but doesn't prevent bad decisions within those turns.
7. **Background sessions leave processes** — Always monitor and kill background Codex sessions when done.
8. **Yolo mode is dangerous** — `--yolo` gives Codex full access with no approvals. Only use in trusted environments.
9. **Model selection affects quality** — `gpt-4o` for complex reasoning, `gpt-4o-mini` for simpler tasks (cheaper/faster).
10. **Git status must be clean** — Codex may fail if there are uncommitted changes it can't manage.

## Cost Estimation

| Model | Input/Output | Example Task Cost |
|-------|-------------|-------------------|
| gpt-4o-mini | $0.15/$0.60 per 1M tokens | ~$0.01-0.05 |
| gpt-4o | $2.50/$10 per 1M tokens | ~$0.05-0.25 |
| o-series | Higher | ~$0.10-0.50 |

**Cost control tips:**
- Use `--max-turns` to cap worst-case spend
- Use `--yolo` to skip unnecessary approval dialogs
- Batch small fixes together to amortize context setup cost
- Use gpt-4o-mini for simple tasks, gpt-4o for complex reasoning

## Quick Start

```bash
# 1. Install and auth
npm install -g @openai/codex
codex auth login

# 2. One-shot review
cd ~/project && codex exec 'Review PR #42' --from-pr 42

# 3. Background feature build
codex exec 'Implement user settings page' --workdir ~/project --full-auto &

# 4. Batch issue fixing
cd ~/project && git worktree add -b fix/temp /tmp/temp main && \
  codex exec 'Fix bug' --workdir /tmp/temp --yolo && \
  git worktree remove /tmp/temp
```

## Related Skills

- `claude-code` — Claude Code alternative; both are autonomous coding agents
- `ruflo` — Ruflo can orchestrate multiple Codex instances in a swarm
- `nomos` — NOMOS workflows can invoke Codex as a tool
- `gstack` — gstack has its own review/deploy skills; Codex can serve as `/codex` second opinion
- `hermes-agent` — Hermes spawns Codex via terminal or delegation
