# Claude Code tmux & OAuth Quirks

Source: Live session debugging July 2026. Auth is managed by `claude-code` skill.

## The Core Quirk

Fresh Claude Code tmux processes ALWAYS trigger OAuth browser flow, even when:
- `claude auth status` confirms cached credentials are valid
- `~/.claude/.credentials.json` contains a valid, non-expired token
- The SAME credentials work perfectly from the host terminal

This means **every new tmux session is an OAuth risk** — it can hang indefinitely waiting for a browser interaction that won't come.

## Solutions

### 1. Use Print Mode (preferred)
```bash
cat /tmp/prompt.txt | claude -p "task" --max-turns 10 --output-format json
```
- Works with cached credentials instantly
- No tmux needed
- No OAuth dialog
- Structured output with session metadata

### 2. Use existing tmux session (if already past auth)
Reuse a tmux session that's already past the auth screen. Don't start new ones.

### 3. Use bare mode with API key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
claude --bare -p "task" --max-turns 10
```
Skips OAuth entirely.

## Other Known Quirks

- `--name "Title"` sets a TUI label but does NOT create a visible project on claude.ai.com
- Quote escaping in tmux send-keys fails with long prompts — always use temp file + pipe
- Deep analysis needs timeout=180s in terminal tool (120s cuts off Fable 5 mid-thought)
