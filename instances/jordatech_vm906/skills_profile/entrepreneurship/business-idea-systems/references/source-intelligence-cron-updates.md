# Source Intelligence + Cron Update Pattern

Use this reference when Jordan asks to add watering holes, market-gap sources, or research inputs to the Business Idea Generator daily automation.

## What to update

1. `jordatech/business_ideas/source_locations.md`
   - Add the source URL.
   - State what it is good for.
   - State cautions/quality risks.
   - Label it as source intelligence, not validation.

2. Optional source-specific playbooks in `jordatech/business_ideas/docs/`
   - Example: Starter Story market-gap analysis should explain how to use case studies to find adjacent underserved workflows, not clones.

3. Optional no-dependency scripts in `jordatech/business_ideas/scripts/`
   - Prefer Python standard library when a cron job should run without dependency changes.
   - Example: a sampler that writes `docs/<source>_latest.md` and gracefully records fetch failures.

4. Live Hermes cron jobs
   - Update the actual job prompt with `cronjob(action="update")`; do not only edit docs.
   - Keep the daily idea job web-enabled if it needs current watering-hole research.
   - Include `business-idea-systems` in the cron job skills list when the job creates or evaluates business ideas.

5. `jordatech/business_idea_generator/docs/`
   - Add a short viewer-side pointer explaining where the canonical source-intelligence instructions live.
   - Source-intelligence docs do not require fallback `data/` sync unless the viewer displays them.

## Operational notes from the 2026-05-14 update

- The business idea repositories were checked out under `/home/miam/jordatech/` and the cron workdirs were updated there:
  - `/home/miam/jordatech/business_ideas`
  - `/home/miam/jordatech/business_idea_generator`
- Use `HOME=/home/miam` for `git`, `gh`, or `npm` commands in the entrepreneur environment when auth or installed tooling is unexpectedly missing due to isolated profile home paths.
- If `git fetch` fails with `could not read Username for 'https://github.com'`, retry with `HOME=/home/miam` before changing remotes or credentials.
- `npm run build` may fail with `next: not found` on a fresh clone; run `npm install` first. Do not commit `node_modules`.
- `npm audit --audit-level=moderate` can report existing Next.js/PostCSS advisories. Do not apply dependency fixes automatically unless the task scope includes dependency updates or Jordan approves.

## Starter Story handling

Starter Story is useful for founder case-study patterns, revenue models, acquisition channels, and crowded niches. Treat it as source intelligence only.

When a generated idea uses Starter Story, add a `Starter Story gap alignment` section that covers:

- observed case-study/category pattern
- adjacent underserved workflow
- why the new idea is not a clone
- what evidence is still missing

Do not scrape aggressively, bypass access controls, or copy paid/member-only content.
