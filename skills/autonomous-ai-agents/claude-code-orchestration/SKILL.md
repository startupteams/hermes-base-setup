---
name: claude-code-orchestration
description: "Practical Hermes integration patterns for orchestrating Claude Code — authentication, tmux, file I/O, long prompts, model selection, session management"
version: 1.0.0
author: "Jordan Ulmer + StartupTeams"
platforms: [linux, macos]
license: MIT
metadata:
  hermes:
    tags: [Claude, CLI, Orchestration, tmux, Auth, Session-Management]
    related_skills: [claude-code, ruflo, hermes-agent]
---

# Claude Code — Hermes Orchestration Patterns

Practical field-tested lessons for running Claude Code from Hermes terminal sessions. These are battle-proven workarounds from real production usage, not theoretical guidance.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Hermes     │────▶│   tmux layer     │────▶│  Claude Code    │
│  (Agent)     │     │  (Session mgmt)  │     │  (AI Agent)     │
│              │     │                  │     │                 │
│ • Send tasks │     │ • Create session │     │ • Write code    │
│ • Monitor    │     │ • Capture pane   │     │ • Run commands  │
│ • Parse result│    │ • Kill session   │     │ • Read files    │
└─────────────┘     └──────────────────┘     └─────────────────┘
       │                     │                      │
       │              stdout/stderr          CLAUDE.md
       │                     │                  (project context)
       ▼                     ▼                      ▼
  Hermes response     tmux pane capture    Git repo changes
```

## PITFALLS & GOTCHAS

### 1. OAuth code paste via tmux `send-keys` fails

Pasting OAuth verification codes through `tmux send-keys` treats them as password input (masked with asterisks) and never reaches the OAuth callback. The terminal stays stuck on the "Paste code here if prompted" screen.

**Fix:** If the user says they pasted the code but the terminal is still stuck, kill the session and try a different approach. Check if credentials already exist at `~/.claude/.credentials.json`. If not, the user must log in on their local machine with a browser.

**Prevention:** Always verify auth status before launching:
```bash
claude auth status --text
cat ~/.claude/.credentials.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print("OAuth:", "accessToken" in d)'
```

### 2. Print mode cannot write files directly

Claude Code in print mode (`-p`) refuses to write files even when the prompt explicitly says "save to X". The output stops at "The write to X wasn't permitted, so I couldn't save the file."

**Workaround:** Redirect stdout to a file via shell:
```bash
cat /tmp/prompt.txt | claude -p "Analyze this" --max-turns 15 > output.md 2>&1
```

Or use a background script:
```bash
cat /tmp/prompt.txt | claude -p "Analyze this" --max-turns 15 > output.md 2>&1
```

### 3. Long prompts need file-based delivery

`tmux send-keys` has quote-escaping problems with long multi-line prompts. Never try to embed a multi-paragraph prompt inside `tmux send-keys` with escaped quotes — it will almost always fail.

**Fix:** Write the prompt to a temp file and use shell redirection:
```bash
cat /tmp/prompt.txt | claude -p "Analyze this" --max-turns 15
```

### 4. Complex strategy prompts take 2-3+ minutes

Multi-turn deep analysis (business strategy, code review, market research) takes much longer than expected. A 120s timeout is not enough.

**Fix:** Use generous timeouts (180s+) for complex prompts. Use background processes with `notify_on_complete=true` to avoid blocking.

### 5. Pre-existing credentials — check before re-authenticating

Claude Code may show an auth dialog even though credentials are already saved.

**Fix:** Always check `~/.claude/.credentials.json` and run `claude auth status --text` before attempting a fresh login.

### 6. Set default model in `~/.claude/settings.json`

Adding `"model": "claude-fable-5"` persists across all sessions. Verify with:
```bash
claude -p "Confirm your model name" --max-turns 1
```

### 7. Session resumption requires same directory

`--continue` only works in the same working directory. For cross-directory work, capture the session ID from output and resume explicitly:
```bash
claude -p "task" --output-format json --max-turns 10 | \
  python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])'
```

### 8. Context degradation is real

AI output quality measurably degrades above 70% context window usage. Monitor with `/context` and proactively `/compact`.

### 9. tmux sessions persist after Claude exits

If Claude Code crashes or is killed mid-session, the tmux session remains running with a zombie process. Always clean up:
```bash
tmux kill-session -t claude 2>/dev/null
```

### 10. Fable 5 session token budget

Fable 5 has a per-session token budget. When running multiple parallel analyses, they can exhaust the budget mid-run. If this happens:
1. Reduce concurrent Fable jobs to 1
2. Shorten each prompt to essentials
3. Run them sequentially, not in parallel
4. Fall back to running analysis with any available model

## WHEN TO USE

- **Multi-turn coding tasks** — When Claude Code needs to iterate on code (refactor → review → fix → test)
- **Complex strategic analysis** — Business reviews, market research, prioritized planning
- **PR reviews requiring context** — Tasks needing to read multiple files across a codebase
- **Long-running sessions** — Tasks expected to take 2-5+ minutes
- **Tasks requiring slash commands** — When Claude Code's `/compact`, `/model`, `/review` etc. are needed

Use **print mode (`-p`)** instead when the task is a single-shot command (simple bug fix, one-file edit, quick question).

## Quick Reference

```bash
# Check auth status
claude auth status --text

# Print mode with file output
claude -p "your task" --max-turns 15 > output.md 2>&1

# Pipe a prompt file to Claude
cat /tmp/prompt.txt | claude -p "Analyze this" --max-turns 15

# Set default model (persistent)
echo '{"model": "claude-fable-5"}' >> ~/.claude/settings.json

# Check if credentials exist
cat ~/.claude/.credentials.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print("OAuth:", "accessToken" in d)'

# Kill stale tmux session
tmux kill-session -t claude 2>/dev/null

# Resume last session in directory
claude -p "What did you do last time?" --continue --max-turns 1

# Create isolated worktree
claude -w feature-x --tmux

# Use bare mode (fastest, no OAuth)
claude --bare -p "task" --max-turns 10

# Streaming output
claude -p "task" --output-format stream-json --verbose | jq -rj 'select(.type == "stream_event") | .event.delta.text'
```

## Proven Orchestration Patterns

### Pattern A: Print Mode — Single Task
Best for: one-shot tasks that don't need conversation or slash commands.

```bash
cat /tmp/prompt.txt | claude -p "Task description" --max-turns 10 > output.md 2>&1
# Then read output.md
```

### Pattern B: Interactive tmux — Multi-Turn
Best for: tasks needing iteration, slash commands, or Claude Code's full TUI.

```bash
# 1. Create session
terminal(command="tmux new-session -d -s claude -x 140 -y 40")

# 2. Launch Claude
terminal(command="tmux send-keys -t claude 'cd /project && claude' Enter")

# 3. Wait for startup, send task
terminal(command="sleep 5 && tmux send-keys -t claude 'Refactor auth module' Enter")

# 4. Monitor progress
terminal(command="sleep 30 && tmux capture-pane -t claude -p -S -50")

# 5. Send follow-up
terminal(command="tmux send-keys -t claude 'Now write tests' Enter")

# 6. Clean up
terminal(command="tmux send-keys -t claude '/exit' Enter")
terminal(command="sleep 2 && tmux kill-session -t claude")
```

### Pattern C: Background Long-Running Task
Best for: tasks expected to take 2+ minutes.

```bash
terminal(command="cat /tmp/prompt.txt | claude -p 'Deep analysis' --max-turns 30 > output.md 2>&1",
          background=True, notify_on_complete=True, timeout=300)
# Continue working; Hermes will notify on completion
# Then read output.md
```

### Pattern D: Fable 5 Strategic Analysis
Best for: founder strategy, prioritization, market analysis.

```bash
# 1. Write context to temp file
write_file(path="/tmp/fable_prompt.txt", content="...full founder context...")

# 2. Run Fable 5 with print mode
cat /tmp/fable_prompt.txt | claude -p "Analyze this entrepreneur situation and output a prioritized goals markdown file. Save it to ~/prioritized_goals.md." --max-turns 20

# 3. Capture to file
cat /tmp/fable_prompt.txt | claude -p "..." --max-turns 20 > ~/prioritized_goals.md 2>&1

# 4. Verify depth
wc -l ~/prioritized_goals.md  # expect 100+ lines

# 5. Save to vault
cp ~/prioritized_goals.md ~/obsidian_vault_jordan_ulmer/TODOS/work/
cd ~/obsidian_vault_jordan_ulmer && git add -A && git commit -m "feat: strategic analysis"
```

## Integration Points

### With Ruflo
- **Ruflo is orchestrator, not executor** — ruflo tracks state and coordinates agents but does NOT write code or run commands
- Claude Code is the executor that actually performs the work
- Use Claude Code as a ruflo agent's tool interface
- Ruflo's 314 MCP tools complement Claude Code's built-in capabilities

### With Armory
- Armory provides pre-built skills that Claude Code can use via `.claude/skills/`
- Install armory skills into Claude Code's skill directory for domain-specific behavior
- Armory's enforcement levels (strict/balanced/prototype) apply to Claude Code's tool permissions

### With OpenHarness
- OpenHarness provides the ohmo persona system — SOUL.md, IDENTITY.md, user.md
- These persona files can be injected into Claude Code's system prompt via `--append-system-prompt-file`
- OpenHarness workspace management integrates with Claude Code's worktree support (`-w`)

### With NOMOS
- NOMOS workflows can invoke Claude Code via terminal as a step
- Use Claude Code's print mode for automated NOMOS tool integration
- NOMOS state machines coordinate Claude Code sessions across workflow phases

## Cost & Performance Tips

1. **Use `--max-turns`** — prevents runaway loops; start with 5-10 for most tasks
2. **Use `--max-budget-usd`** — cap API spend; minimum ~$0.05 for system prompt cache
3. **Use `--bare`** — for CI/scripting, skip hooks/plugins/MCP for fastest startup
4. **Use `--allowedTools`** — restrict to only what's needed (e.g., `Read` only for reviews)
5. **Use `--model haiku`** for simple tasks (cheaper), `--model opus` for complex work
6. **Pipe input** instead of having Claude read files when you just need analysis
7. **Start new sessions** for distinct tasks — sessions last 5 hours, fresh context is more efficient
8. **Monitor context window** — proactive `/compact` prevents quality degradation above 70%
