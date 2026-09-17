---
description: Skills for spawning and orchestrating autonomous AI coding agents and multi-agent workflows — running independent agent processes, delegating tasks, and coordinating parallel workstreams.

**Umbrella skill.** Each subdirectory contains a detailed SKILL.md with instructions for a specific agent/harness.

## Agentic Harness Skills (13 skills, 163KB total)

### Core Infrastructure
| Skill | Version | Size | Purpose |
|-------|---------|------|---------|
| [`armory`](armory/) | v1.0.0 | 9.7KB | Production-grade skill registry — 110+ packages across 7 types (skills, agents, hooks, rul... |
| [`nomos`](nomos/) | v1.0.0 | 12.5KB | Structured LLM-powered assistant framework — configurable flows, state machines, tool chai... |
| [`openharness`](openharness/) | v1.0.0 | 10.0KB | Core agent infrastructure — tool-use, skills loading, memory, ohmo persona engine, workspa... |
| [`openspec`](openspec/) | v1.0.0 | 10.7KB | Spec-driven development (SDD) for AI coding assistants. Fluid, iterative workflow: propose... |
| [`ruflo`](ruflo/) | v1.0.0 | 9.9KB | Meta-harness for multi-agent orchestration — hierarchical swarm coordination, agent federa... |

### Coding Agent Delegation
| Skill | Version | Size | Purpose |
|-------|---------|------|---------|
| [`claude-code`](claude-code/) | v2.2.0 | 33.5KB | Delegate coding to Claude Code CLI (features, PRs).... |
| [`codex`](codex/) | v2.0.0 | 9.0KB | Delegate coding to OpenAI Codex CLI — one-shot execution, background mode, parallel worktr... |
| [`opencode`](opencode/) | v1.2.0 | 7.1KB | Delegate coding to OpenCode CLI (features, PR review).... |

### Specialist Roles & Tools
| Skill | Version | Size | Purpose |
|-------|---------|------|---------|
| [`gstack`](gstack/) | v1.0.0 | 10.3KB | AI Engineering Workflow — 23 specialist roles for software development: CEO reviewer, eng ... |
| [`hermes-agent`](hermes-agent/) | v2.0.0 | 30.5KB | Configure, extend, or contribute to Hermes Agent.... |

### Optimization & Patterns
| Skill | Version | Size | Purpose |
|-------|---------|------|---------|
| [`caveman`](caveman/) | v1.0.0 | 7.6KB | Token compression skill — cuts 65-75% of AI coding agent output tokens while maintaining f... |
| [`fabric-pattern-authoring`](fabric-pattern-authoring/) | v1.0.0 | 8.4KB | Author and manage Fabric patterns — modular prompt templates for AI augmentation organized... |

### Orchestration
| Skill | Version | Size | Purpose |
|-------|---------|------|---------|
| [`claude-code-orchestration`](claude-code-orchestration/) | v1.0.0 | 3.4KB | Practical Hermes integration patterns for orchestrating Claude Code CLI — authentication, ... |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Our Agentic Harness                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   ruflo       │  │  nomos       │  │  armory       │      │
│  │  Meta-Harness │  │  Workflow    │  │  Skill Reg.   │      │
│  │  (15-agent    │  │  (State      │  │  (110+ pkgs)  │      │
│  │   mesh)       │  │   machine)   │  │  (7 types)    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              openharness                              │  │
│  │    Core Infrastructure: Tools, Skills, Memory,       │  │
│  │    Persona (ohmo), Workspace, Gateway Integration    │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ▼                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ claude-  │ │  codex   │ │ opencode │ │ gstack   │     │
│  │  code    │ │  (OpenAI)│ │          │ │ (23       │     │
│  │          │ │          │ │          │ │  roles)   │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
│         │              │              │                   │
│  ┌──────────┐ ┌──────────────────────────┐                │
│  │hermes-   │ │   fabric-patterns         │                │
│  │  agent   │ │   (Prompt Library)        │                │
│  └──────────┘ └──────────────────────────┘                │
│                                                             │
│  ┌──────────┐ ┌──────────────────────────┐                │
│  │ openspec │ │     caveman               │                │
│  │ (SDD)    │ │  (Token Compression)      │                │
│  └──────────┘ └──────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## Key Dependencies Between Repos

| Source Repo | Used By | What It Provides |
|-------------|---------|-----------------|
| `github.com/startupteams/ruflo` | ruflo | Meta-harness, 15-agent mesh, 314 MCP tools, AgentDB |
| `github.com/startupteams/OpenHarness` | openharness | Tool-use, skills, memory, ohmo persona engine |
| `github.com/startupteams/armory` | armory | 110+ production-grade packages, 7 types |
| `github.com/jordatech/gstack` | gstack | 23 specialist engineering roles |
| `github.com/startupteams/nomos` | nomos | Structured workflows, state machines |
| `github.com/startupteams/OpenSpec` | openspec | Spec-driven development lifecycle |
| `github.com/jordatech/caveman` | caveman | Token compression (65-75% savings) |
| `github.com/danielmiessler/Fabric` | fabric-pattern-authoring | Modular prompt system |
| `github.com/NousResearch/hermes-agent` | hermes-agent | Hermes framework docs |

## Quick Reference: When to Use What

| Task | Skill to Load |
|------|--------------|
| Orchestrate multiple coding agents | `ruflo` |
| Set up agent workspace/personality | `openharness` |
| Build structured multi-step workflows | `nomos` |
| Install production skill packages | `armory` |
| Spec-driven feature development | `openspec` |
| Delegate to Claude Code | `claude-code` |
| Delegate to OpenAI Codex | `codex` |
| Delegate to OpenCode | `opencode` |
| Engineering specialist roles (CEO/QA/Release) | `gstack` |
| Configure/extend Hermes itself | `hermes-agent` |
| Compress agent output tokens | `caveman` |
| Create prompt templates | `fabric-pattern-authoring` |
| Orchestrating Claude Code from Hermes | `claude-code-orchestration` |

## Usage

Load a specific skill with:
```
skill_view(name='autonomous-ai-agents/{skill-name}')
```

For example, to load the ruflo skill:
```
skill_view(name='autonomous-ai-agents/ruflo')
```

## Git Workflow
- **Branch:** `AGENT_STEA004_ENTREPRENEUR`
- **Repo:** `github.com/jordatech/` (or `startupteams/` if authorized)
- **Deploy:** feature branch → merge main → push to live
- **Rule:** Never commit sensitive configs, API keys, or credentials
