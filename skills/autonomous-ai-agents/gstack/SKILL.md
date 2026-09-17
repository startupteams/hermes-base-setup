---
name: gstack
description: "AI Engineering Workflow — 23 specialist roles for software development: CEO reviewer, eng manager, designer, QA lead, release engineer, debugger, and more. Includes browser integration, iOS QA, and worktree-aware ship queue."
version: 1.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [gstack, engineering, qa, design, review, ship, browser, ios, specialist]
    related_skills: [armory, ruflo, openharness, claude-code]
---

# GStack — AI Engineering Workflow

> **gstack v1.45.0.0** — Use Garry Tan's exact Claude Code setup: 23 opinionated tools that serve as CEO, Designer, Eng Manager, Release Manager, Doc Engineer, and QA. Structured specialist roles for software development.

**Source:** `github.com/jordatech/gstack`

## When to Use

- **Planning phase:** CEO review, design consultation, eng review before writing code
- **Code review:** Pre-landing PR review, second opinions via Codex
- **Debugging:** Systematic root-cause investigation (no fixes without investigation)
- **Design:** Visual audits, multiple design variants, production HTML/CSS
- **QA:** Live browser testing, bug finding + fixing, iOS device QA
- **Shipping:** Workspace-aware version queue, CI/CD, canary monitoring
- **Documentation:** Diataxis docs generation (tutorial/how-to/reference/explanation)

## Skill Categories

### Plan-Mode Reviews (Before Writing Code)

| Skill | Slash Command | What It Does |
|-------|--------------|--------------|
| Office Hours | `/office-hours` | Start here. Reframes product idea before writing code. |
| CEO Review | `/plan-ceo-review` | Find the 10-star product in the request. |
| Eng Review | `/plan-eng-review` | Lock architecture, data flow, edge cases, and tests. |
| Design Review | `/plan-design-review` | Rate each design dimension 0-10, explain what a 10 looks like. |
| DX Review | `/plan-devex-review` | TTHW (Time To Happy Worker), magical moments, friction points. |
| Tune | `/plan-tune` | Self-tune AskUserQuestion sensitivity per question. |
| AutoPlan | `/autoplan` | One command runs CEO → design → eng → DX review. |
| Design Consultation | `/design-consultation` | Build a complete design system from scratch. |

### Implementation + Review

| Skill | Slash Command | What It Does |
|-------|--------------|--------------|
| Code Review | `/review` | Pre-landing PR review. Finds bugs that pass CI but break in prod. |
| Second Opinion | `/codex` | OpenAI Codex review, challenge, or consult modes. |
| Investigate | `/investigate` | Systematic root-cause debugging. No fixes without investigation. |
| Design Review Live | `/design-review` | Live-site visual audit + fix loop with atomic commits. |
| Design Shotgun | `/design-shotgun` | Generate multiple AI design variants, comparison board, iterate. |
| Design HTML | `/design-html` | Production-quality Pretext-native HTML/CSS. |
| DevEx Review | `/devex-review` | Live developer experience audit (TTHW measured against real flow). |
| QA Browser | `/qa` | Open real browser, find bugs, fix them, re-verify. |
| QA Report Only | `/qa-only` | Same as /qa but report only — no code changes. |
| Scrape | `/scrape` | Pull data from web page. First call prototypes; codified call runs in ~200ms. |
| Skillify | `/skillify` | Codify the most recent successful /scrape flow into a permanent browser-skill. |

### Release + Deploy

| Skill | Slash Command | What It Does |
|-------|--------------|--------------|
| Ship | `/ship` | Run tests, review, push, open PR. Workspace-aware version queue. |
| Land & Deploy | `/land-and-deploy` | Merge PR, wait for CI, deploy, verify production health. |
| Canary | `/canary` | Post-deploy monitoring loop using the browse daemon. |
| Landing Report | `/landing-report` | Read-only dashboard for workspace-aware ship queue. |
| Document Release | `/document-release` | Update all docs to match what you just shipped. |
| Document Generate | `/document-generate` | Generate Diataxis docs from code. |
| Setup Deploy | `/setup-deploy` | One-time deploy config detection (Fly.io, Render, Vercel, etc.). |
| GStack Upgrade | `/gstack-upgrade` | Update gstack to the latest version. |

### Operational + Memory

| Skill | Slash Command | What It Does |
|-------|--------------|--------------|
| Context Save | `/context-save` | Save working context (git state, decisions, remaining work). |
| Context Restore | `/context-restore` | Resume from saved context, even across Conductor workspaces. |
| Learn | `/learn` | Manage what gstack learned across sessions. |
| Retro | `/retro` | Weekly retro with per-person breakdowns and shipping streaks. |
| Health | `/health` | Code quality dashboard (type checker, linter, tests, dead code). |
| Benchmark | `/benchmark` | Performance regression detection (page load, Core Web Vitals). |
| Benchmark Models | `/benchmark-models` | Cross-model benchmark (Claude, GPT, Gemini side-by-side). |
| CSO | `/cso` | OWASP Top 10 + STRIDE security audit. |
| Setup GBrain | `/setup-gbrain` | Set up gbrain for cross-machine session memory sync. |
| Sync GBrain | `/sync-gbrain` | Keep gbrain current with repo's code; refresh agent search guidance. |

### Browser + Agent Integration

| Skill | Slash Command | What It Does |
|-------|--------------|--------------|
| Browse | `/browse` | Headless browser — real Chromium, real clicks, ~100ms/command. |
| Open Browser | `/open-gstack-browser` | Launch visible GStack Browser with sidebar + stealth. |
| Setup Cookies | `/setup-browser-cookies` | Import cookies from real browser for authenticated testing. |
| Pair Agent | `/pair-agent` | Pair a remote AI agent (OpenClaw, Codex, etc.) with browser. |

## iOS QA (v1.43.0.0+)

Drive real iPhones over USB or Tailscale:

| Skill | What It Does |
|-------|-------------|
| iOS QA | Live-device iOS QA via USB CoreDevice tunnel + StateServer. |
| iOS Fix | Autonomous iOS bug fixer with regression snapshot capture. |
| iOS Design Review | Designer's-eye QA on real iPhone — 10-dimension Apple HIG rubric. |
| iOS Clean | Strip DebugBridge + #if DEBUG wiring before Release build. |
| iOS Sync | Regenerate iOS debug bridge against latest upstream templates. |

```bash
# Companion CLI on Mac that's plugged into the device
gstack-ios-qa-daemon --tailnet  # Expose over Tailscale for remote agents
```

## How GStack Skills Work

Each skill is a SKILL.md file that provides structured guidance when the task matches. They're invoked by name:

```
# In Claude Code:
/office-hours "I want to build a SaaS for small business invoicing"

# In Hermes:
skill_view(name='gstack-office-hours')  # Load the skill
# Then follow the structured workflow
```

### Skill Template Pattern

Each gstack skill follows this structure:

```markdown
---
name: gstack-{skill-name}
description: "What this specialist skill does"
---

## When to use
[Trigger conditions]

## Workflow
1. Step one with specifics
2. Step two with specifics
3. Verification step

## Pitfalls
- Common mistake 1
- Common mistake 2

## Output Format
What the skill produces
```

## Worktree-Aware Ship Queue

gstack includes a workspace-aware version queue for managing multiple concurrent changes:

```bash
# Creates isolated worktrees for parallel development
git worktree add -b fix/issue-42 /tmp/issue-42 main

# Ship command handles the queue automatically
/ship  # Runs tests, review, push, open PR for next queued item

# Landing report shows queue status
/landing-report
```

## Browser Integration

gstack's browser tool is ~100ms per command — fast enough for automated QA:

```bash
# Launch headless browser
/browse "Navigate to /pricing and take screenshot"

# Scrape data from page
/scrape "Extract all pricing tiers from /pricing"

# Skillify into reusable skill
/skillify  # Makes the scrape flow permanent and codified
```

## Security Audit (CSO)

Comprehensive security review combining OWASP Top 10 + STRIDE:

```bash
/cso "Audit the authentication module for vulnerabilities"
```

Checks:
- OWASP Top 10 (Injection, Broken Auth, Sensitive Data, etc.)
- STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Elevation, Denial)
- Custom security rules based on project detection

## Pitfalls & Gotchas

1. **Slash commands only work in Claude Code interactive mode** — In Hermes, use `skill_view` to load the skill and follow its workflow manually.
2. **`/investigate` forbids fixes** — The skill explicitly says no fixes without investigation. Follow the methodology.
3. **Browser skills need cookies** — For authenticated testing, run `/setup-browser-cookies` first.
4. **Worktrees must be cleaned up** — After using worktrees for parallel tasks, remove them: `git worktree remove /tmp/issue-42`.
5. **`/skillify` codifies the LAST `/scrape`** — Only works immediately after a successful scrape.
6. **iOS QA requires Mac with device plugged in** — The companion daemon runs on the Mac, not the agent machine.
7. **GBrain sync requires setup first** — Run `/setup-gbrain` before `/sync-gbrain`.
8. **Design review rates 0-10** — Ask for explicit scores on each dimension, not vague feedback.

## Quick Start

```bash
# 1. Plan first — never skip planning
/office-hours "Build a multi-tenant SaaS for task management"

# 2. Get CEO review on the concept
/plan-ceo-review "Find the 10-star product in this request"

# 3. Lock architecture before coding
/plan-eng-review "Lock data flow, edge cases, and tests"

# 4. During development — pre-landing review
/review "Review changes vs main"

# 5. Ship with confidence
/ship "Release v1.2.0"

# 6. Monitor post-deploy
/canary "Check for regressions in production"
```

## Integration with Other Tools

- **Hermes:** Load gstack skills via `skill_view(name='gstack-{name}')` then follow the workflow
- **Claude Code:** Use slash commands directly (`/review`, `/ship`, etc.)
- **Codex:** Use `/codex` skill for second opinions via OpenAI Codex
- **OpenHarness:** gstack skills can be installed into OpenHarness workspaces
- **Armory:** gstack overlaps with armory's review/ship skills; prefer gstack for engineering workflow, armory for broader dev tooling

## Related Skills

- `armory` — Broader skill registry; gstack focuses on engineering workflow
- `ruflo` — Swarm orchestration; gstack is the specialist skill set for agents
- `openharness` — Workspace setup where gstack skills live
- `claude-code` — Where gstack slash commands execute natively
- `openspec` — Spec-driven development that complements gstack planning phase
