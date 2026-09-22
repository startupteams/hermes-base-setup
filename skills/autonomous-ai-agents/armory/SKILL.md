---
name: armory
description: "Production-grade skill registry — 110+ packages across 7 types (skills, agents, hooks, rules, commands, evals, packages). Curated workflows for AI coding agents with profile-based installation and hook installation."
version: 1.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [skills, agents, hooks, rules, commands, evals, packages, profile-install]
    related_skills: [ruflo, openharness, gstack, hermes-agent]
---

# Armory — Production Skill Registry

> **Armory** — Curated, production-grade skills for AI coding agents. Battle-tested workflows for developers who use AI seriously. **110 packages across 7 types. 100% eval coverage.**

**Source:** `github.com/startupteams/armory`
**Package:** PyPI/npm

## When to Use

- Installing **production-grade skills** with one command
- Using **profile-based installation** (core, developer, security, researcher, etc.)
- Setting up **git hooks** that auto-format, lint, or security-scan on file changes
- Enforcing **commit standards** and **security standards** via rules
- Running **pre-landing PR reviews** before merging
- Composing **multi-agent pipelines** (build, research, content, evolution)

## Installation

### One-Line Install (Recommended)

```bash
# Install via Python (includes hooks installer)
pip install armory
armory install --profile core

# Or npm
npm install -g armory
armory install --profile core
```

### Profile-Based Installation

Armory provides curated skill sets for different workflows:

| Profile | What's Included |
|---------|----------------|
| **core** | pr-review, code-refiner, pre-landing-review, git-protection hooks, commit-standards |
| **developer** | Core + test-harness, debug-investigator, architecture-reviewer, github |
| **python-dev** | Core + TDD, type checking, GPU optimizer, test-standards rules |
| **security-engineer** | Core + repo-sentinel, dependency-audit, security-standards rules, security-scan command |
| **content-creator** | humanize, linkedin-post-style, html-presentation, concept-to-image/video |
| **researcher** | literature-review, research-critique, youtube-analysis, tavily, web-fetch |
| **business-analyst** | idea-validator, market-analyzer, competitive-analyzer, feasibility-assessor |
| **skill-evolution** | surrogate-verifier, skill-distiller, paper-to-skill, package-evaluator, immune |
| **full** | Every available package |

```bash
# Install a specific profile
armory install --profile developer

# List available profiles
armory install --list-profiles
```

## 7 Package Types

Armory packages come in 7 types, each serving a different role in the agent workflow:

### 1. Skills (`skills/`)
Individual SKILL.md files for repeatable tasks.

| Skill | Category | Phase | Difficulty |
|-------|----------|-------|------------|
| `pr-review` | review | ship | intermediate |
| `code-refiner` | development | build | intermediate |
| `architecture-reviewer` | review | review | advanced |
| `debug-investigator` | development | debug | intermediate |
| `test-harness` | development | build | intermediate |
| `idea-validator` | business | plan | intermediate |
| `literature-review` | research | research | intermediate |
| `humanize` | content | write | beginner |

### 2. Agents (`agents/`)
Multi-phase orchestrators that compose skills into workflows.

| Agent | Pipeline | Description |
|-------|----------|-------------|
| `project-architect` | build_pipeline | Full project lifecycle from idea to deployment |
| `team-lead` | meta | Delegates to all other agents |
| `security-reviewer` | security | Security auditing and enforcement |
| `secret-scanner` | security | Secrets detection in codebases |
| `codebase-auditor` | security | Full codebase security audit |
| `research-analyst` | research_pipeline | Investigation across multiple sources |
| `content-strategist` | content_pipeline | Content creation and visual production |
| `test-engineer` | evolution_pipeline | Generator-Verifier loop for skill refinement |

### 3. Hooks (`hooks/`)
Git automation that runs on events.

| Hook | Event | Action |
|------|-------|--------|
| `git-protection` | PreCommit | Block commits with secrets, large files, lint errors |
| `security-scan` | PrePush | Run security audit before pushing |
| `auto-lint` | PostWrite | Auto-lint on file write |

```json
// Installed into .claude/settings.json automatically
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "if echo $CLAUDE_TOOL_INPUT | grep -qE 'rm -rf|git push.*--force'; then exit 2; fi",
        "_hook_name": "git-protection"
      }]
    }]
  }
}
```

### 4. Rules (`rules/`)
Standards that enforce code quality.

| Rule | Type | Enforcement |
|------|------|-------------|
| `commit-standards` | Git | Requires conventional commits |
| `test-standards` | Testing | Requires tests for new code |
| `security-standards` | Security | Requires security review for auth changes |
| `project-detection` | Meta | Auto-detects project type and loads matching rules |

### 5. Commands (`commands/`)
Reusable CLI shortcuts.

| Command | Purpose |
|---------|---------|
| `tdd` | Red-Green-Refactor workflow |
| `evolve` | Co-evolutionary skill refinement |
| `security-scan` | Full security audit |

### 6. Evals (`evals/`)
Benchmarks and quality measurements.

| Eval | What it Measures |
|------|-----------------|
| `skillsbench` | Skill effectiveness across task types |
| `evals/results.json` | Historical eval results |

### 7. Packages (`packages/`)
Modular skill groups that can be installed individually.

```bash
# Install a single package
armory install-package skills/pr-review

# List all packages
armory list-packages
```

## Agent Composition System

Armory defines how agents compose skills and other agents:

### Pre-Commit Chain (Sequential)
```
secret-scanner → security-reviewer → code-reviewer
```
Each step must pass before the next runs.

### Post-Write Parallel
```
code-reviewer (parallel) ← code written
security-reviewer (parallel) ← code written
```
Both run simultaneously after code is written.

### Build Pipeline (Sequential)
```
project-architect → project-planner → full-stack-builder → codebase-auditor → release-captain
```

### Evolution Pipeline (Generator-Verifier Loop)
```
test-engineer generates → surrogate-verifies → skill-distills → immune-checks
```

## Enforcement Levels

| Level | What's Reported | What Blocks | Use Case |
|-------|----------------|-------------|----------|
| **strict** | All findings | CRITICAL + HIGH | Production codebases, CI gates |
| **balanced** | CRITICAL + HIGH | CRITICAL only | Active development with quality gates |
| **prototype** | CRITICAL only | CRITICAL only | Rapid prototyping |

```bash
# Set enforcement level
armory set-enforcement strict  # or balanced, prototype
```

## Hooks Installation

Armory's hooks installer automatically merges hook configuration into Claude Code's `settings.json`:

```bash
# Install hooks
armory install-hooks --profile core

# The installer:
# 1. Copies handler files to .claude/hooks/{name}/
# 2. Reads HOOK.md frontmatter for event/matcher/handler config
# 3. Merges hook entry into .claude/settings.json
# 4. Rewrites relative script paths to absolute installed paths
```

### Supported Hook Events

| Event | When It Fires |
|-------|--------------|
| `UserPromptSubmit` | Before Claude processes a prompt |
| `PreToolUse` | Before tool execution (use `exit 2` to block) |
| `PostToolUse` | After tool finishes |
| `Notification` | On permission requests |
| `Stop` | After agent response |
| `SubagentStop` | After subagent completes |
| `PreCompact` | Before context compression |
| `SessionStart` | New session begins |

## Profile Detection

Armory auto-detects project types:

```bash
armory detect-project  # Auto-detects from directory structure
```

Detects: Python, JavaScript/TypeScript, Go, Rust, documentation-only, research, and more.

## Repository Scanning

```bash
# Scan for security issues
armory scan --repo . --level strict

# Scan for secrets
armory scan-secrets --repo .

# Audit dependencies
armory audit-deps --repo .
```

## Pitfalls & Gotchas

1. **Hook installation modifies .claude/settings.json** — This is intentional and managed by armory. Don't manually edit the hooks section.
2. **Profile installation is additive** — Installing `developer` on top of `core` adds to core, doesn't replace it.
3. **Relative paths in hooks are rewritten** — The installer converts `bash handler.sh` to absolute paths. Don't move hook files after installation.
4. **Enforcement levels affect all agents** — Setting `strict` blocks commits with HIGH findings. This is by design for safety.
5. **Evals are historical** — `results.json` shows past eval runs. Re-run to get current results.
6. **Commands are Claude Code slash commands** — They work in Claude Code interactive mode, not as standalone CLIs.
7. **Agent composition is declarative** — The `_registry.yaml` defines what composes what. Changes take effect on next agent invocation.

## Quick Start

```bash
# 1. Install core profile
armory install --profile core

# 2. Install developer skills
armory install --profile developer

# 3. Run a PR review
armory review --pr 42

# 4. Scan for security issues
armory scan --repo . --level balanced

# 5. Use an agent for a multi-phase workflow
armory run-agent project-architect --project "Build auth service"
```

## Related Skills

- `ruflo` — Swarm orchestration that can use armory skills as agent capabilities
- `openharness` — Workspace setup where armory hooks install automatically
- `gstack` — Alternative specialist skill set (more focused on software development)
- `hermes-agent` — Hermes's own skill management (complements armory's packages)
- `nomos` — Structured workflows (complements armory's build pipeline)
