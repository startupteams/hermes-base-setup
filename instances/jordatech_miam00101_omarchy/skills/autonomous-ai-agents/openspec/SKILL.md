---
name: openspec
description: "Spec-driven development (SDD) for AI coding assistants. Fluid, iterative workflow: propose → design → tasks → apply → archive. Built for brownfield and greenfield projects with agent-friendly artifacts."
version: 1.0.0
author: Hermes Agent + StartupTeams
license: MIT
metadata:
  hermes:
    tags: [specs, sdd, proposal, design, tasks, archive, spec-driven, fission]
    related_skills: [nomos, armory, gstack, ruflo]
---

# OpenSpec — Spec-Driven Development

> **OpenSpec** — The most loved spec framework for AI coding assistants. Fluid not rigid, iterative not waterfall, easy not complex, built for brownfield not just greenfield, scalable from personal projects to enterprises.

**Source:** `github.com/startupteams/OpenSpec`

## When to Use

- **Proposing new features** with structured rationale and requirements
- **Breaking complex work** into implementable tasks with traceability
- **Managing spec changes** through a full lifecycle (proposal → apply → archive)
- **Maintaining living documentation** that stays in sync with code
- **Working in brownfield projects** — OpenSpec adapts to existing codebases

## Philosophy

```text
→ fluid not rigid
→ iterative not waterfall
→ easy not complex
→ built for brownfield not just greenfield
→ scalable from personal projects to enterprises
```

## The Workflow: `/opsx:propose`

OpenSpec uses a guided workflow with slash commands:

```
You: /opsx:propose "add dark mode"
AI:  Created openspec/changes/add-dark-mode/
     ✓ proposal.md — why we're doing this, what's changing
     ✓ specs/       — requirements and scenarios
     ✓ design.md    — technical approach
     ✓ tasks.md     — implementation checklist
     Ready for implementation!

You: /opsx:apply
AI:  Implementing tasks...
     ✓ 1.1 Add theme context provider
     ✓ 1.2 Create toggle component
     ✓ 2.1 Add CSS variables
     ✓ 2.2 Wire up localStorage
     All tasks complete!

You: /opsx:archive
AI:  Archived to openspec/changes/archive/2025-01-23-add-dark-mode/
     Specs updated. Ready for the next feature.
```

## Artifact Structure

```
openspec/
├── config.yaml              # Schema, context, cross-cutting rules
├── changes/
│   ├── add-dark-mode/       # Active change proposal
│   │   ├── proposal.md      # Why + what + who
│   │   ├── design.md        # Technical approach
│   │   ├── tasks.md         # Implementation checklist
│   │   └── specs/
│   │       └── dark-mode/
│   │           └── spec.md  # Requirements + scenarios
│   └── archive/
│       └── 2025-01-23-add-dark-mode/  # Completed changes
└── specs/                   # Living spec references
    └── dark-mode/
        └── spec.md          # Current authoritative spec
```

## Installing OpenSpec

```bash
# npm
npx openspec init

# pnpm
pnpm dlx openspec init

# bun
bunx openspec init
```

This creates:
- `openspec/config.yaml` — Configuration with cross-cutting rules
- `openspec/changes/` — Working directory for proposals
- `openspec/specs/` — Living specs that evolve

## Config Structure

```yaml
# openspec/config.yaml
schema: spec-driven

context: |
  Tech stack: TypeScript, Node.js, ESM modules
  Package manager: pnpm
  CLI framework: Commander.js

  Product language:
  - Write specs in user-facing product behavior language
  - Requirements describe observable behavior, not internal mechanisms
  - Put internal mechanisms in design.md

  Cross-platform requirements:
  - This tool runs on macOS, Linux, AND Windows
  - Always use path.join() or path.resolve() for file paths

rules:
  specs:
    - Include scenarios for cross-platform behavior
    - Prefer user-facing behavior over internal mechanics
  tasks:
    - Include cross-platform testing considerations
  design:
    - Document platform-specific behavior
    - Prefer Node.js path module over string manipulation
```

## Proposal Template

```markdown
<!-- openspec/changes/add-dark-mode/proposal.md -->
# Change: Add Dark Mode

## Why
Users have requested dark mode. Our competitor X already has it.

## What Changes
- Add a dark mode toggle to settings
- Persist preference in localStorage
- Apply dark theme via CSS variables
- Support OS-level preference (prefers-color-scheme)

## What's NOT Included
- Dark mode for email (phased later)
- Custom color themes (phased later)

## Affected Specs
- ui:theme — New requirement for dark theme support

## Implementation Notes
- Use CSS custom properties for all colors
- Respect prefers-color-scheme media query as default
- Toggle stored in localStorage under "theme" key
```

## Spec Template

```markdown
<!-- openspec/changes/add-dark-mode/specs/dark-mode/spec.md -->
# Requirement: Dark Theme Support

## Scenarios

### Scenario 1: User enables dark mode
- **WHEN** user clicks dark mode toggle in settings
- **THEN** the app switches to dark theme immediately
- **AND** the preference is saved to localStorage

### Scenario 2: User returns after refresh
- **WHEN** user refreshes the page
- **THEN** the app loads in the previously selected theme
- **AND** the toggle reflects the current theme state

### Scenario 3: OS-level preference detection
- **WHEN** user has not explicitly chosen a theme
- **THEN** the app respects the OS `prefers-color-scheme` setting
- **AND** the toggle shows the matching option as selected
```

## Design Template

```markdown
<!-- openspec/changes/add-dark-mode/design.md -->
# Design: Dark Mode

## Technical Approach

### CSS Variables
```css
:root {
  --bg-primary: #ffffff;
  --text-primary: #000000;
}

[data-theme="dark"] {
  --bg-primary: #1a1a1a;
  --text-primary: #ffffff;
}
```

### Theme Provider
```typescript
// src/context/ThemeContext.tsx
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(
    () => localStorage.getItem("theme") || 
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
  );
  
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);
  
  return <ThemeContext.Provider value={{ theme, toggleTheme: () => setTheme(...) }}>{children}</ThemeContext.Provider>;
}
```
```

## Task Template

```markdown
<!-- openspec/changes/add-dark-mode/tasks.md -->
# Tasks: Dark Mode

## Phase 1: Foundation
- [ ] 1.1 Create CSS variable file with light/dark palettes
- [ ] 1.2 Add `data-theme` attribute toggle script
- [ ] 1.3 Implement localStorage persistence

## Phase 2: React Integration
- [ ] 2.1 Create ThemeContext provider
- [ ] 2.2 Create ThemeProvider component
- [ ] 2.3 Create useTheme custom hook
- [ ] 2.4 Create ThemeToggle component
- [ ] 2.5 Add toggle to settings page

## Phase 3: OS Preference
- [ ] 3.1 Detect prefers-color-scheme on mount
- [ ] 3.2 Add system option to toggle dropdown
- [ ] 3.3 Test with browser dev tools theme emulation
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `/opsx:propose "idea"` | Start a new change proposal |
| `/opsx:design` | Write the design document |
| `/opsx:tasks` | Generate the task checklist |
| `/opsx:apply` | Apply all tasks in the active change |
| `/opsx:archive` | Archive the completed change |
| `/opsx:status` | Show all changes and their status |
| `/opsx:list` | List all changes |
| `/opsx:diff` | Show spec changes vs code |

## Spec Rules

OpenSpec enforces these rules (configurable in `config.yaml`):

### Spec Writing Rules
- Write in user-facing product behavior language
- Requirements describe observable outcomes
- Include scenarios for edge cases
- Cross-platform behavior when dealing with files/paths

### Task Writing Rules
- Tasks are implementation-level (not design-level)
- Include testing considerations
- Group by phase for sequential execution
- Each task should be independently verifiable

### Design Document Rules
- Document technical approach
- Include code examples for non-obvious patterns
- Document platform-specific behavior
- Reference specs for requirements

## Multi-Language Support

OpenSpec works with any language:

```yaml
# Custom rules per language
rules:
  typescript:
    - Use path.join() for file paths
    - Type annotations on public functions
  python:
    - Type hints on all functions
    - Docstrings in Google style
  go:
    - Exported names start with uppercase
    - Error handling with if err != nil
```

## Integration with Coding Agents

### OpenSpec + Claude Code
```bash
# In Claude Code:
/opsx:propose "add user authentication"

# Claude Code reads proposal.md, design.md, tasks.md
# and implements tasks sequentially
```

### OpenSpec + Hermes
```bash
# Create a proposal
npx openspec propose "improve error handling"

# Implement via Hermes
# Read tasks.md to understand the scope
# Execute tasks using terminal/file tools
# Report completion back to spec

# Archive when done
npx openspec archive
```

### OpenSpec + Ruflo
```bash
# Use OpenSpec proposals as swarm objectives
ruflo swarm init --topology hierarchical
ruflo task create --from "openspec/changes/add-dark-mode/tasks.md"
# Each task becomes an agent assignment
```

## Pitfalls & Gotchas

1. **Specs must be user-facing** — Don't write "use localStorage" in specs. Write "persist preference" and put localStorage in design.md.
2. **Tasks are implementation-level** — "Add dark mode" is a proposal. "Create ThemeContext provider" is a task.
3. **Archive moves, doesn't delete** — Archived changes are preserved in `archive/` for reference. Don't worry about losing work.
4. **Design is separate from specs** — Specs say WHAT. Design says HOW. Tasks say WHICH steps to do.
5. **Multi-language projects need config** — Default config assumes TypeScript/Node. Customize rules for your stack.
6. **`/opsx:apply` executes ALL tasks** — Review tasks.md before applying. There's no "apply only these three" command.
7. **Specs update on archive** — When you archive, the living specs in `openspec/specs/` are updated to match the change.
8. **Cross-platform rules are mandatory** — If your spec involves files, always include Windows path handling scenarios.

## Quick Start

```bash
# 1. Initialize in your project
cd /path/to/project
npx openspec init

# 2. Propose a change
npx openspec propose "add user dashboard"

# 3. Design the approach
npx openspec design

# 4. Create tasks
npx openspec tasks

# 5. Implement tasks
#    (Hermes reads tasks.md and executes each)

# 6. Archive when done
npx openspec archive
```

## Related Skills

- `nomos` — NOMOS workflows implement OpenSpec tasks
- `gstack` — gstack's planning phase feeds into OpenSpec proposals
- `armory` — Armory skills can be referenced in OpenSpec tasks
- `ruflo` — Ruflo swarms can parallelize OpenSpec task execution
- `hermes-agent` — Hermes orchestrates OpenSpec workflows via terminal tools
