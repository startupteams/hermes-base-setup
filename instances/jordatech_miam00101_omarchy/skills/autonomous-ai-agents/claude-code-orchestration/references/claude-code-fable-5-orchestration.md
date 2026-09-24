# Claude Code Fable 5 — Orchestration Lessons

## Session 2026-07-03: Login + Deep Analysis

### OAuth through tmux `send-keys` fails
**Symptom:** Terminal shows `Paste code here if prompted > ****************` (masked asterisks) and never proceeds. OAuth callback is never reached.
**Root cause:** tmux `send-keys` sends characters to stdin which the terminal treats as password input — masking is intentional, but the characters never reach the OAuth flow's code-reading logic.
**Fix attempted:** User pasted code `YG1q47lHWNLelVA2NGnejh3BkQ7ZpfbC4u6n0TWPDfzjh2Q5#gy_Qq7qW8OFG8UUPBK6TncSsr8y0E9IwVUyEKHxhEns` via `tmux send-keys`. Terminal was stuck for 2+ minutes on the same screen. Killed session and checked existing credentials.
**Resolution:** Credentials already existed at `~/.claude/.credentials.json` (Pro subscription, `jordatech@gmail.com`). Auth confirmed via `claude auth status --text`. User must log in on local machine with browser for initial auth.

### Print mode file write refusal
**Prompt asked:** "output a markdown file locally of prioritized goals and objectives"
**Symptom:** Claude responded with full analysis but prefaced it with: "The write to `~/prioritized_goals.md` wasn't permitted, so I couldn't save the file."
**Root cause:** Print mode (`-p`) runs Claude Code in a restricted context where the Write tool is not available by default. Even with `--allowedTools 'Read,Bash'`, Claude Code's internal policy refuses file writes.
**Fix:** Shell redirect — `claude -p "..." --max-turns 15 > ~/prioritized_goals.md 2>&1`. Captured stdout to file, then manually saved to Obsidian vault and pushed to GitHub.

### Long prompt escaping via tmux
**Problem:** Tried to pass the entire entrepreneur prompt via `tmux send-keys` with escaped quotes. Command failed with: `unexpected EOF while looking for matching '`
**Fix:** Wrote prompt to `/tmp/fable_prompt2.txt`, then used shell redirection: `cat /tmp/fable_prompt2.txt | claude -p "..." --max-turns 15`.

### Deep analysis timeout
**Observation:** A 132-line analysis took ~2.5 minutes. 120s timeout was insufficient.
**Fix:** Used `background=true` with `notify_on_complete=true` and waited via `process(action='wait')`.

### Fable 5 confirmed as default
Verified by asking Claude "Confirm your model name" and getting response: "I'm Claude Fable 5 (model ID: `claude-fable-5`), the first model in Anthropic's Claude 5 family."
Settings file `~/.claude/settings.json` was updated with `"model": "claude-fable-5"`.

### Output delivery
Final file saved to:
- `~/prioritized_goals.md` (132 lines, 10921 bytes)
- `obsidian_vault_jordan_ulmer/TODOS/work/USATasksPrioritization/prioritized_goals.md`
- Pushed to `github.com/jordatech/obsidian_vault_jordan_ulmer` on branch `main` (commit `6fda3e6`)
