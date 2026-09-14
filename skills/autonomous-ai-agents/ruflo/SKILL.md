---
name: ruflo
description: "Meta-harness for multi-agent orchestration — hierarchical swarm coordination, agent federation, memory management, and MCP tool integration. Based on ruflo (15-agent mesh, 314 MCP tools, AgentDB vector search)."
version: 1.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [swarm, orchestration, multi-agent, mcp, memory, flock]
    related_skills: [hermes-agent, claude-code, openharness, armory]
---

# Ruflo — Multi-Agent Meta-Harness

> 🌊 **Ruflo v3.6+** — The leading agent meta-harness. Deploy intelligent multi-agent swarms, coordinate autonomous workflows, and build conversational AI systems. Features adaptive memory, self-learning swarm intelligence, RAG integration, and native Claude Code / Codex integration.

**Source:** `github.com/startupteams/ruflo`

## When to Use

- Coordinating **multiple coding agents** across parallel tasks
- Building **swarm topologies** (hierarchical, mesh, leader-follower)
- Managing **agent memory** and cross-agent knowledge sharing
- Integrating **MCP tool servers** into agent workflows
- Orchestrating **Claude Code + Codex dual-mode** collaboration
- Setting up **governance controls** and safety rails

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              Ruflo Meta-Harness                  │
├─────────────────────────────────────────────────┤
│  Swarm Topology (hierarchical/mesh/leader)      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ Agent 1 │ │ Agent 2 │ │ Agent 3 │  ... N   │
│  │ (Coder) │ │(Reviewer)│ │(Deployer)│         │
│  └────┬────┘ └────┬────┘ └────┬────┘          │
│       └───────────┼───────────┘                │
│                   ▼                            │
│         AgentDB (Vector Memory)                │
│         HNSW Search + RaBitQ Quantization      │
│                   ▼                            │
│         MCP Tool Server (314+ tools)           │
└─────────────────────────────────────────────────┘
```

## Installation

```bash
# Install ruflo CLI
npm install -g ruflo@latest

# Verify installation
ruflo --version

# Initialize in a workspace
ruflo init --topology hierarchical --max-agents 8
```

## Swarm Topologies

### Hierarchical (Default — Recommended)
Best for structured development teams with clear role boundaries.

```bash
ruflo swarm init \
  --topology hierarchical \
  --max-agents 6 \
  --strategy specialized
```

**Roles:**
| Agent | Domain | Priority |
|-------|--------|----------|
| Queen Coordinator | Core orchestration | 1 |
| Security Architect | Security | 1 |
| Core Developers x4 | Core development | 2 |
| Quality Engineer | Testing | 2 |
| Performance Engineer | Optimization | 3 |
| Deployer | CI/CD | 4 |

### Mesh (Flat)
Best for fast parallel work where all agents have equal capability.

```bash
ruflo swarm init --topology mesh --max-agents 4 --strategy general
```

### Leader-Follower
Best when one agent should direct others.

```bash
ruflo swarm init --topology leader-follower --max-agents 5 --leader-type strategist
```

## MCP Tool Integration

Ruflo exposes 314+ MCP tools. Key ones:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `swarm_init` | Initialize swarm topology | Starting any multi-agent task |
| `agent_spawn` | Spawn a new agent with role | Adding specialized workers |
| `memory_store` | Store knowledge in AgentDB | After successful patterns |
| `memory_search` | Retrieve past patterns | Before starting new work |
| `task_create` | Create tracked tasks | Breaking complex work into steps |
| `task_assign` | Assign task to specific agent | Delegating to specialized agents |
| `governance_check` | Validate against safety rules | Before production changes |
| `hook_fire` | Trigger automation hooks | Post-tool-use automation |

### Using MCP Tools in Hermes

```python
# Example: Search memory, spawn agents, then execute
from hermes_tools import terminal, search_files, write_file

# 1. Search past patterns
result = terminal(command='ruflo memory search --query "api error handling" --top-k 3')

# 2. Initialize swarm
terminal(command='ruflo swarm init --topology hierarchical --max-agents 4')

# 3. Spawn specialized agents
terminal(command='ruflo agent spawn --type coder --name api-writer')
terminal(command='ruflo agent spawn --type reviewer --name api-reviewer')

# 4. Execute the actual work (Hermes does this, not ruflo!)
write_file(path='src/api.py', content='...')

# 5. Store successful pattern for future
terminal(command='ruflo memory store --key "api-pattern" --value "Use FastAPI + Pydantic" --namespace patterns')
```

## 3-Tier Model Routing

Ruflo implements intelligent model routing to minimize cost and latency:

| Tier | Handler | Latency | Cost | Use Case |
|------|---------|---------|------|----------|
| **1** | Deterministic codemod | ~1ms | $0 | Structural transforms (var-to-const, remove-console) |
| **2** | Haiku / light model | ~500ms | $0.0002 | Simple tasks, low complexity (<30%) |
| **3** | Sonnet / Opus / flagship | 2-5s | $0.003-0.015 | Complex reasoning, architecture, security |

**Rule:** Always check for `[CODEMOD_AVAILABLE]` before spawning agents. If available, use `hooks_codemod` MCP tool — it applies transforms at $0 with no LLM.

## Agent Roles & Specialization

Define agents with explicit role contracts:

```bash
# Create a specialized agent
ruflo agent create api-expert \
  --role "Senior API Engineer" \
  --tools "Read,Write,Bash,WebFetch" \
  --constraints "No database changes, use type hints, add tests"

# Create a security agent
ruflo agent create security-auditor \
  --role "Security Engineer" \
  --tools "Read,Bash" \
  --constraints "Scan for injection, auth bypass, secret leaks"
```

## Governance & Safety

Ruflo includes a governance control plane:

```bash
# Check code against governance rules
ruflo governance check --scope src/ --rules security,quality

# Set governance level
ruflo governance set-level strict  # or balanced, prototype
```

**Enforcement Levels:**
- **Strict:** All findings reported. CRITICAL and HIGH block commits.
- **Balanced:** CRITICAL and HIGH reported. MEDIUM as suggestions.
- **Prototype:** CRITICAL only. All else suppressed.

## Dual-Mode: Claude Code + Codex

Ruflo supports running Claude Code and OpenAI Codex in parallel with shared memory:

```bash
# Initialize dual-mode collaboration
ruflo dual-mode init --claude-sonnet --codex-gpt4

# Both agents share AgentDB memory
ruflo memory store --key "shared-knowledge" --value "..." --namespace shared

# Each works on different tasks, shares results
```

**Why dual-mode?** Redundancy (if one provider has outage), cost optimization (use cheaper model for simple tasks), and capability diversity (Claude excels at reasoning, Codex at code generation).

## Hooks & Automation

17 built-in hooks fire on events:

| Hook | Fires When | Common Use |
|------|-----------|------------|
| `PostToolUse` | After any tool call | Auto-format, lint, test |
| `PreToolUse` | Before tool execution | Security gates, block dangerous commands |
| `Stop` | After agent response | Completion logging |
| `SessionStart` | New session begins | Load dev context |
| `PreCompact` | Before context compression | Backup session transcripts |

```json
// .agents/config.toml — hook configuration
[hooks.PostToolUse]
matcher = "Write(*.py)"
handler = "ruff check --fix $CLAUDE_FILE_PATHS"

[hooks.PreToolUse]
matcher = "Bash"
handler = "if echo $CLAUDE_TOOL_INPUT | grep -q 'rm -rf'; then exit 2; fi"
```

## Performance Targets

| Metric | Measured | Status |
|--------|----------|--------|
| HNSW Search | ~1.9x at N=20k vs brute force | ✅ Measured |
| Int8 Quantization | 3.84x compression, 0.99999 cosine | ✅ Measured |
| RaBitQ Quantization | 32x compression, 0.60ms/query | ✅ Measured |
| MCP Response | <100ms target | 🎯 Target |
| CLI Startup | <500ms target | 🎯 Target |

## Pitfalls & Gotchas

1. **Ruflo is an orchestrator, not an executor** — It tracks state and coordinates but does NOT write code or run commands. Hermes must do the actual work.
2. **Always initialize swarm before spawning agents** — `swarm_init` must be called first.
3. **Use hierarchical topology by default** — Mesh works for flat teams, hierarchical for structured workflows.
4. **Check for `[CODEMOD_AVAILABLE]`** — Don't use LLM for deterministic transforms.
5. **Clean up swarms when done** — Don't leave zombie agents consuming resources.
6. **Memory namespace isolation** — Use different namespaces (`patterns`, `results`, `shared`) to avoid conflicts.
7. **Governance is optional** — Enable for production codebases, skip for prototypes.

## Quick Start — One Pattern

```bash
# 1. Search past patterns → LEARN
ruflo memory search --query "auth refactor" --top-k 3

# 2. Init swarm → COORDINATE
ruflo swarm init --topology hierarchical --max-agents 4

# 3. DO THE WORK YOURSELF (Hermes terminal/file tools)
#    ← This is where real work happens

# 4. Store patterns → REMEMBER
ruflo memory store --key "auth-pattern" --value "Use JWT with refresh tokens" --namespace patterns
```

## Related Skills

- `openharness` — Core infrastructure (tool-use, skills, memory, ohmo persona)
- `armory` — Production skill registry (110 packages)
- `gstack` — Specialist roles (CEO, Eng, DX, QA, Release)
- `hermes-agent` — Hermes configuration and spawning
- `nomos` — Structured workflow management
- `openspec` — Spec-driven development
- `claude-code` — Claude Code CLI delegation
- `codex` — OpenAI Codex CLI delegation
