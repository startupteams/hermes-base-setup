---
name: jira-sprint-task-writing
description: "Write Jira sprint tasks in the AgentifyMe format: role-based, numbered, with action verbs, specific deliverables, constraints, double-checks, and PM exit criteria."
version: 1.0.0
author: c01entrepreneur_bot
license: MIT
metadata:
  hermes:
    tags: [entrepreneurship, sprint-planning, jira, project-management, agentifyme]
    related_skills: [business-idea-systems]
---

# Jira Sprint Task Writing

Use this skill when asked to create sprint tasks, Jira issues, or engineering work plans for StartupTeams business models. The format is modeled on the AgentifyMe sprint pattern.

## When to use

- An entrepreneur or PM asks for sprint tasks for a business model
- You need to convert an investor-reviewed business model into actionable engineering work
- You need to push tasks to Jira via the Zapier MCP integration
- You need to create a sprint plan that multiple roles (engineer, sales, PM) can execute

## Process

### 1. Angel investor review

Roleplay a skeptical angel investor reviewing the business model. Evaluate:
- Is the pain real and frequent?
- Is the buyer defined and reachable?
- Is there a defensible moat?
- Is this achievable by a SaaS team (software + AI, no physical products)?
- What is the weakest assumption?

Output a clear verdict: FUND, FUND WITH CHANGES, PARK, or KILL.

### 2. Entrepreneur update

Based on investor feedback, update the business model:
- Narrow the persona if too broad
- Pivot the wedge if the original doesn't hold
- Update pricing, assumptions, and competitive moat
- Mark PARKED models explicitly with reason

### 3. Role handoffs

Write specific handoff instructions for:
- **Senior Systems Engineer**: What to build, what NOT to build, tech stack constraints
- **Senior Sales**: Target buyer, outreach channels, discovery questions, success criteria

### 4. PM sprint tasks

Write sprint tasks in this exact format:

```
## Sprint N: [Goal in one sentence]

Sprint goal: [What must be true when this sprint ends]
Sprint duration: [N weeks]

### [Role Name]

1. [Action verb] [specific deliverable] with [constraints].
2. [Action verb] [specific deliverable] with [constraints].

### [Senior Role] double checks

1. [Verify] before [gate condition].
2. [Verify] before [gate condition].

### Senior Project Manager advice

1. [Exit criteria or focus constraint].
2. [Risk assignment or definition-of-done].
```

## Writing rules

1. **Action verbs only**: Build, Add, Implement, Document, Benchmark, Create, Deploy, Test, Prepare, Collect, Write, Confirm, Schedule, Post, Draft.
2. **Specific deliverables**: Not "improve security" but "Add read-only status cards for Proxmox, Tailscale, and uptime checks."
3. **Constraints in every task**: "Deploy behind VPN first; defer public access until security review."
4. **Senior roles do double-checks**: Verification tasks, not implementation.
5. **PM advice = exit criteria + risk ownership**: "Exit criteria: 3 pilots running, dashboard live, feedback collected."
6. **Testable tasks**: Each task has a clear "done" state someone else can verify.
7. **Reference real systems**: ServerM1, Proxmox, GPT-5.4, Next.js, Vercel, specific tools.
8. **No vague scope**: Not "make it better" but "Benchmark 8B Q4 and 14B Q4 on ServerM1."
9. **Include what NOT to build**: Explicitly defer out-of-scope work to future sprints.

## Jira integration

Tasks can be pushed to Jira via Zapier MCP:
- Action: `jira_software_cloud_create_issue`
- Issue type: "Task" for action items, "Story" for features
- Summary: Task text
- Description: Business model slug, sprint number, role, and full context

## Reference document

The canonical sprint format reference is at:
`business_idea_generator/docs/sprint-action-reference.md`

And the live example sprint is at:
`business_idea_generator/docs/sprint-planning-forum-vc.md`

## Pitfalls

- Do not write tasks that are too abstract — "research the market" is not a sprint task
- Do not skip double-checks — senior review prevents quality issues
- Do not let scope creep — explicitly list what NOT to build
- Do not forget exit criteria — the PM must define when the sprint is done
- Do not assign tasks without considering the team's actual capabilities (SaaS team = software + AI, no physical products)
