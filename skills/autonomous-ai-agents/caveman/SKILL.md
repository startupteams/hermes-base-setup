---
name: caveman
description: "Token compression skill — cuts 65-75% of AI coding agent output tokens while maintaining full technical accuracy. Ships as Claude Code plugin, Codex plugin, Gemini CLI extension, and 40+ agent rule files."
version: 1.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [compression, tokens, cost, efficiency, caveman, compressed-output]
    related_skills: [ruflo, openharness, hermes-agent]
---

# Caveman — Token Compression for AI Agents

> 🪨 **Caveman** — Why use many token when few token do trick. Cuts ~65-75% of AI coding agent output tokens by talking like caveman — full technical accuracy, dramatically reduced cost and context window usage.

**Source:** `github.com/jordatech/caveman`

## When to Use

- **Cost reduction** — Dramatically lower API costs on per-token billing
- **Context window savings** — More work fits in the same context window
- **Faster generation** — Less output to generate = faster responses
- **Long sessions** — Extend agent sessions by delaying context window exhaustion
- **Batch operations** — Process more items within token budgets

## Installation

### All-in-One Installer

```bash
# macOS / Linux / WSL
curl -fsSL https://raw.githubusercontent.com/jordatech/caveman/main/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/jordatech/caveman/main/install.ps1 | iex

# Manual: npx
npx skills add git@github.com:jordatech/caveman.git
```

### Per-Agent Installation

Caveman supports 40+ AI coding agents. Common ones:

| Agent | Install Method |
|-------|---------------|
| Claude Code | Plugin: `npx @anthropic-ai/claude-code` + caveman skill |
| Codex | Plugin: Caveman rule file |
| Gemini CLI | Extension: Gemini CLI extension |
| Cursor | Rule: `.cursorrules` file |
| Windsurf | Rule: `.windsurfrules` file |
| Cline | Rule: `.clinerules` file |
| Copilot | Rule: `.github/copilot-instructions.md` |
| OpenCode | Rule: `.opencode/rules/` |
| Hermes | Skill: `caveman` in skills directory |

### Manual Installation (Claude Code)

```bash
# Clone into Claude Code skills directory
git clone https://github.com/jordatech/caveman.git ~/.claude/skills/caveman

# Or manually install the SKILL.md
curl -fsSL https://raw.githubusercontent.com/jordatech/caveman/main/skills/caveman/SKILL.md \
  > ~/.claude/skills/caveman/SKILL.md
```

## How It Works

Caveman compresses output by using direct, minimal language while preserving ALL technical content:

| Standard AI | Caveman | Token Savings |
|-------------|---------|---------------|
| "I will now examine the authentication module to identify potential vulnerabilities" | "Examine auth module for vulns" | ~67% |
| "Let me create a new file called `auth.py` with the following content:" | "Create auth.py:" | ~50% |
| "Based on my analysis, I have identified three issues: first, the token expiration..." | "3 issues: 1) Token expires in 24h" | ~75% |
| "I'd recommend implementing the following changes to address these vulnerabilities" | "Fixes:" | ~70% |

The compression preserves:
- ✅ All code, commands, and technical details
- ✅ File paths and line numbers
- ✅ Error messages and stack traces
- ✅ Configuration values and parameters
- ✅ Logical reasoning (condensed)

## Three Caveman Skills

### 1. Core Compression (`caveman`)

Base compression for all agent output.

```bash
# Load in Hermes
skill_view(name='caveman/caveman')

# Or use directly:
# Add to your agent's system prompt:
# "Respond in compressed caveman style. No filler. No intros. Direct output only."
```

### 2. Commit Compression (`caveman-commit`)

Compressed but meaningful commit messages.

```bash
# Instead of:
"feat: add authentication module with JWT token support and refresh token rotation"

# Caveman produces:
"feat(auth): add JWT auth + refresh rotation"
```

### 3. Review Compression (`caveman-review`)

Condensed code reviews that keep all actionable items.

```bash
# Instead of:
"I've reviewed the code and found the following issues:
1. In line 42, there's a potential null pointer exception..."

# Caveman produces:
"Review (3 issues):
L42: null ptr risk
L87: missing error handling
L103: inefficient loop"
```

## Compression Levels

Caveman supports different compression levels:

| Level | Description | Savings |
|-------|-------------|---------|
| **Standard** | Compress output, keep technical accuracy | ~65% |
| **Aggressive** | Maximum compression, minimal words | ~75% |
| **Light** | Small compression, more readable | ~40% |
| **Ultra** | Maximum compression, may lose readability | ~80%+ |

Set level via agent config or prompt:

```markdown
# In CLAUDE.md or system prompt:
Respond in caveman style, level: standard
```

## Cavecrew — Team Caveman

For multi-agent scenarios, Cavecrew coordinates compressed output across agents:

```bash
# Create a cavecrew configuration
cat > ~/.cavecrew/config.yaml << 'EOF'
agents:
  - name: coder
    style: caveman
    level: aggressive
  - name: reviewer
    style: caveman
    level: standard
  - name: writer
    style: plain
    level: none
EOF
```

## Benchmark Results

Caveman has been evaluated on multiple benchmarks:

| Metric | Standard | Caveman | Change |
|--------|----------|---------|--------|
| Output tokens | 100% | 25-35% | **-65 to -75%** |
| Technical accuracy | 100% | 100% | No change |
| API cost | 100% | 25-35% | **-65 to -75%** |
| Generation time | 100% | 30-40% | **-60 to -70%** |

All evaluations use real runs in `benchmarks/` and `evals/`. Results are never fabricated.

## Integration with Hermes

### Via Skill

```bash
# Add caveman to Hermes profile
npx skills add git@github.com:jordatech/caveman.git
```

### Via System Prompt

Add to your Hermes agent's prompt:

```markdown
# Output Style
- Use compressed, direct language
- No filler words ("I will", "Let me", "Based on my analysis")
- No introductions or conclusions
- Direct to content
- Technical content preserved in full
```

### Via Claude Code CLAUDE.md

```markdown
# CLAUDE.md

## Output Style (Caveman Mode)
Respond in compressed caveman style. No filler. No intros. Direct output.
Example: "Create auth.py:" not "Let me create a new file called auth.py with the following content:"
```

## Pitfalls & Gotchas

1. **Compresses output, not input** — Caveman only affects the AI's response, not how you write prompts.
2. **May feel unnatural** — Standard AI speech patterns are trained over millions of examples. Caveman fights that. It may require adjustment.
3. **Not for documentation** — Don't use caveman for README files, docs, or user-facing text. Only for agent output.
4. **Brand voice preserved in README** — The official caveman README uses caveman speak intentionally. Don't normalize it.
5. **Some agents need config** — Claude Code needs the skill file. Codex needs a rule file. Gemini needs an extension.
6. **Install script modifies agent config** — The installer touches `.claude/`, `.cursor/`, `.windsurf/` etc. Review the changes.
7. **Caveman is not obfuscation** — All technical content is preserved. Just expressed more concisely.

## Quick Start

```bash
# 1. Install
curl -fsSL https://raw.githubusercontent.com/jordatech/caveman/main/install.sh | bash

# 2. Verify
npx skills list | grep caveman

# 3. Use in a project
cd /path/to/project

# 4. Add to CLAUDE.md
cat >> CLAUDE.md << 'EOF'

## Output Style
Respond in compressed, direct style. No filler. No intros.
EOF

# 5. Observe token savings in API logs
```

## Related Skills

- `ruflo` — Ruflo swarms can use caveman compression per-agent
- `openharness` — OpenHarness workspaces can include caveman
- `hermes-agent` — Hermes profile can enable caveman globally
- `gstack` — gstack skills benefit from caveman in agent output
