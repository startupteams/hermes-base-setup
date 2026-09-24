# Reddit-Sourced Skeptical Investor Idea Batch Pattern

Use when the user asks for several technology-service business ideas based on recent Reddit pain signals, especially with an investor/skeptical framing.

## Workflow

1. Treat Reddit posts as **pain-signal sourcing**, not validation.
2. Prefer posts from the last 3 months with clear operational pain, business consequences, and active discussion.
3. Capture source metadata for each selected signal:
   - subreddit
   - post date
   - score and comment count when available
   - source URL
   - the exact painful situation that inspired the idea
4. Select ideas with buyer urgency and a plausible route to budget. Strong signals include:
   - compliance or liability exposure
   - revenue/cash-flow delays
   - manual review burden
   - one-person/key-person operational risk
   - client SLA or evidence requirements
5. Generate full business-model Markdown entries, not short summaries.
6. Include the skeptical investor sections in every idea:
   - Data Moat & Proprietary Advantage
   - Human-in-the-Loop Approach
   - Unit Economics
   - FAQ for Skeptical Investors
7. Update both repositories when using Jordan's current setup:
   - canonical source: `jordatech/business_ideas`
   - viewer snapshot: `jordatech/business_idea_generator/data/`
8. Validate and deploy:
   - validate `ideas.json` with `python3 -m json.tool ideas.json`
   - run `npm install && npm run build` in the viewer
   - run `npm audit --audit-level=moderate`
   - deploy with Vercel CLI if requested
9. If the Vercel site returns `401`, inspect the app auth middleware before treating it as failed. In this project, production Basic Auth can be expected behavior.

## Useful idea archetypes observed

- One-person IT/key-person continuity service for SMBs.
- MSP vulnerability SLA evidence and noise-reduction desk.
- Compliance release gate for AI/vibe-coded internal apps.
- AI-generated consulting deliverable integrity review desk.
- Agency client-dependency queue for asset/approval bottlenecks.

## Pitfalls

- Do not call Reddit evidence validation. It is a lead list for customer discovery.
- Do not preserve or print Vercel Basic Auth credentials when verifying protected deployments; use `[REDACTED]` in notes.
- Do not force-fix `npm audit` when it proposes a breaking Next.js downgrade or major framework change.
- Avoid generic “AI for X” framing; every idea needs a buyer, budget trigger, workflow wedge, and kill criteria.
