---
name: openharness
description: "Core agent infrastructure — tool-use, skills loading, memory, ohmo persona engine, workspace management, and multi-platform gateway integration. The Python backbone that powers agent personalization and tool orchestration."
version: 1.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [infrastructure, tools, skills, memory, ohmo, workspace, gateway]
    related_skills: [ruflo, armory, hermes-agent, claude-code]
---

# OpenHarness — Agent Infrastructure

> **OpenHarness** delivers core lightweight agent infrastructure: tool-use, skills, memory, and multi-agent coordination. **ohmo** is the personal AI agent built on top of it — not another chatbot, but an assistant that actually works for you over long sessions.

**Source:** `github.com/startupteams/OpenHarness`
**Package:** `openharness-ai` (pip)

## When to Use

- Setting up **agent workspaces** with persistent memory and personality
- Loading **skills and plugins** from custom directories
- Managing **session continuity** across messaging platforms
- Building **personal agents** (ohmo) with soul, identity, and user context
- Integrating **MCP servers** and external tool providers
- Running **React TUI** for visual agent interaction

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   OpenHarness                       │
├─────────────────────────────────────────────────────┤
│  Platform Gateways                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Telegram │ │ Discord  │ │  Slack   │  + more   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       └────────────┼────────────┘                   │
│                    ▼                                │
│          Stream Events Engine                       │
│     (AssistantTextDelta, ErrorEvent, StatusEvent)   │
│                    ▼                                │
│          ohmo Runtime Layer                         │
│  ┌──────────────┐ ┌──────────────┐                 │
│  │  Persona     │ │  Workspace   │                 │
│  │  (Soul/ID)   │ │  (Memory)    │                 │
│  └──────────────┘ └──────────────┘                 │
│                    ▼                                │
│          Tool & Skill Dispatch                      │
│  ┌──────────────┐ ┌──────────────┐                 │
│  │  Skills Dir  │ │  Plugins Dir │                 │
│  │  .agents/    │ │  .plugins/   │                 │
│  └──────────────┘ └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

## Installation

```bash
# Install OpenHarness
pip install openharness-ai

# Or use the ohmo CLI directly
oh --help
```

## Workspace Structure

OpenHarness uses a personal workspace (default `~/.ohmo`) with a soul-based personality system:

```
~/.ohmo/
├── SOUL.md              # Who the agent is (personality, values, boundaries)
├── IDENTITY.md          # Agent shape (name, kind, vibe, signature)
├── user.md              # About the human (profile, preferences, context)
├── BOOTSTRAP.md         # First-contact script (auto-deleted after setup)
├── memory/              # Durable personal facts
│   ├── index.md         # Memory index
│   ├── preferences.md   # User preferences
│   └── projects.md      # Active project context
├── state.json           # Recent state and session info
└── sessions/            # Conversation history
```

## SOUL.md — Agent Personality

The soul is the agent's personality contract. Here's the template:

```markdown
# SOUL.md - Who You Are

You are [agent-name], a personal agent.

## Core truths
- Be genuinely helpful, not performatively helpful.
  Skip filler like "great question" or "happy to help" unless natural.
- Have judgment.
  You can prefer one option over another, notice tradeoffs, explain reasons.
- Be resourceful before asking.
  Read the file, check the context, inspect state before bouncing work back.
- Earn trust through competence.
  Be careful with public/destructive/costly changes. Be bolder with internal work.
- Remember that access is intimacy.
  Messages, files, notes, history are personal. Treat with respect.

## Boundaries
- Private things stay private.
- When in doubt, ask before acting externally.
- Do not send half-baked replies on messaging channels.

## Vibe
Be concise when the answer is simple. Thorough when stakes are high.
Sound like a capable companion, not a corporate support bot.
```

## Building System Prompts

OpenHarness composes system prompts from multiple sources:

```python
from ohmo.prompts import build_ohmo_system_prompt

# Compose full system prompt for a session
system_prompt = build_ohmo_system_prompt(
    cwd="/path/to/project",
    workspace="/path/to/ohmo",
    extra_prompt="Additional instructions here",
    include_project_memory=True  # Also load CLAUDE.md project context
)
```

**Prompt assembly order:**
1. Base system prompt (core instructions)
2. Additional instructions (from CLI or config)
3. SOUL.md (personality contract)
4. IDENTITY.md (agent shape)
5. user.md (human profile)
6. BOOTSTRAP.md (first-contact script, if present)
7. Memory index (from ohmo/memory/)
8. Project memory (from CLAUDE.md, if enabled)

## Loading Skills from Custom Dirs

```python
from ohmo.workspace import get_skills_dir, get_plugins_dir

# Get workspace skill directory
skills_dir = get_skills_dir(root)  # ~/.ohmo/.agents/skills/

# Get workspace plugin directory
plugins_dir = get_plugins_dir(root)  # ~/.ohmo/.agents/plugins/
```

Skills are loaded from:
1. Default skills directory (`~/.hermes/skills/`)
2. Extra skill dirs (project-specific, workspace-specific)
3. Plugin-provided skills

## Session Continuity

OpenHarness persists session state to enable continuity across breaks:

```python
from ohmo.session_storage import OhmoSessionBackend

# Backend for React TUI sessions
backend = OhmoSessionBackend(workspace_root)

# Sessions are identified by workspace + session ID
# Resuming restores messages, tool results, and context
```

## React TUI

OpenHarness includes a React-based terminal UI:

```bash
# Launch the React TUI
oh

# Or backend-only mode (no frontend)
oh --backend-only
```

The TUI supports:
- Real-time streaming of agent responses
- Visual status indicators
- Tool call inspection
- Session management
- Multi-platform messaging

## Multi-Platform Gateway

OpenHarness integrates with messaging platforms:

```python
from openharness.api.client import SupportsStreamingMessages

# Any platform that supports streaming messages can connect
# Telegram, Discord, Slack, Feishu, and more
```

## CLI Commands

```bash
# Launch ohmo personal agent
oh

# Backend-only mode
oh --backend-only

# Set workspace
oh --workspace /path/to/ohmo

# Set model
oh --model anthropic/claude-sonnet-4

# Set max turns (safety limit)
oh --max-turns 50

# Set working directory
oh --cwd /path/to/project

# Provider profile
oh --profile default

# Resume session
oh --resume session-id

# Continue last session
oh --continue
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OHMO_WORKSPACE` | Custom workspace root path |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENHARNESSE_API_KEY` | OpenHarness API key |

## Pitfalls & Gotchas

1. **SOUL.md is the personality source of truth** — Don't modify personality mid-session; update the file for lasting changes.
2. **Bootstrap auto-deletes** — After first contact completes, BOOTSTRAP.md is removed. Don't expect it to persist.
3. **Memory files are human-readable** — They're markdown, not structured data. Keep them concise and index entries in memory/index.md.
4. **React TUI requires npm** — The frontend uses React + Vite. Install dependencies with `npm install` in the frontend directory.
5. **Session resumption is workspace-scoped** — You can't resume a session from a different workspace.
6. **Extra skill dirs override defaults** — If you add a skill with the same name in an extra dir, it replaces the default.
7. **MCP tool descriptions are capped at 2KB** — Large tool schemas may be truncated.
8. **Stream events include retry info** — `system/api_retry` events contain `attempt`, `max_retries`, and `error` fields.

## Quick Start

```bash
# 1. Install
pip install openharness-ai

# 2. Create workspace
mkdir -p ~/.ohmo/.agents/skills

# 3. Write your soul
cat > ~/.ohmo/SOUL.md << 'EOF'
# SOUL.md
You are jordan's assistant. Be concise, have judgment, and be resourceful.
EOF

# 4. Write user profile
cat > ~/.ohmo/user.md << 'EOF'
# user.md
- Name: Jordan
- Timezone: US (currently visiting for fundraising)
- Projects: AgentifyMe, business_idea_generator
- Tone preference: Direct, no fluff
EOF

# 5. Launch
oh
```

## Related Skills

- `ruflo` — Multi-agent swarm orchestration on top of this infrastructure
- `armory` — Production skill packages that can be installed into OpenHarness workspaces
- `hermes-agent` — Hermes's own configuration (the gateway/profiler that wraps this)
- `claude-code` — Claude Code CLI integration (works with OpenHarness workspaces)
- `nomos` — Structured workflow management (complements OpenHarness memory)
