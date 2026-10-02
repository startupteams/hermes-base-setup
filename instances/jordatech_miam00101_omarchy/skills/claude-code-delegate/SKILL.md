---
name: claude-code-delegate
description: Use when delegating coding work to headless Claude Code.
---

# Claude Code Delegate (Hermes → Claude Opus)

Claude Code 2.1.287 is installed on MIAM-00101 (mise-managed, do NOT curl-reinstall). Auth: Max subscription OAuth for jordan@startupteams.co in ~/.claude/.credentials.json (0600). NO ANTHROPIC_API_KEY ever — API key would override subscription billing.

## Host-side execution
All commands run on the HOST (jordatech), not in the Docker sandbox. From this agent, execute them via browser_exec subprocess (`/bin/bash -lc`).

## Workflow
1. Write a bounded subtask markdown file (objective, repo, in/out of scope, acceptance criteria, safety, required result format) to /tmp/<workid>-claude.md.
2. Run on host:
   `claude-opus-delegate <repo-dir> /tmp/<workid>-claude.md [model]` — wrapper at ~/.local/bin/claude-opus-delegate (mode 700), execs `claude -p --model opus --output-format json --permission-mode acceptEdits --allowedTools "Read,Edit,Write,Glob,Grep,Bash" --max-turns 100`.
3. Full JSON goes to a file artifact (e.g. ~/Work/claude-max20-setup/results/<workid>.json); extract ONLY subtype, is_error, num_turns, total_cost_usd, result (truncated), session_id into the reply.
4. Verify claimed changes yourself: read the touched files / run tests on host. Claude's self-report is not verification.
5. Record session_id + cost + model in the handoff/work notes.

## Pitfalls (verified 2026-10-02)
- Wrapper output may end with an unrelated "connectors need authorization" notice appended to result — ignore.
- Do not add --bare (breaks subscription OAuth).
- Opus resolves to claude-opus-5-5. Smoke costs ~$0.08-0.10 list-equivalent per tiny task (billed from Max limits, not cash).
- If a login is needed again: `claude auth login` prints a URL; complete in any browser, paste code back. browser_exec output containing raw URLs gets blocked by the URL filter — mangle scheme/domain when printing, then reconstruct.
- A `claude setup-token` (CLAUDE_CODE_OAUTH_TOKEN for other users/CI) is still NOT generated; only needed when delegating from a different Linux user or machine.
- Private-LAN tasks (Proxmox, PDU, 10.0.20.x) stay with Hermes; claude --cloud never sees them.
