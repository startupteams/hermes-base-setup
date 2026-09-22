# Large Source Catalog Expansion Pattern

Use this pattern when Jordan asks for a large brainstorm of new internet sources for technology business ideas and wants them added to the Business Idea Generator system, not just listed in chat.

## Trigger

- Requests like "brainstorm at least 100 new places on the internet to get technology business ideas"
- Any task where the source catalog needs a major expansion rather than a few incremental additions

## Required outputs

1. Expand `business_ideas/source_locations.md`
2. Update any mirrored repo instructions doc such as `business_ideas/docs/daily_cron_idea_generation_instructions.md`
3. Update the live Hermes cron prompts with `cronjob(action="update")`
4. Commit/push the repo changes after verification

## Recommended structure for `source_locations.md`

Add a dedicated section such as `## 100+ new technology idea sources to add to the rotation`.

Group sources by class so the catalog stays scannable:
- Founder, startup, and trend publications
- Reddit communities with recurring operator pain
- Developer and operator communities / forums
- App marketplaces and integration ecosystems
- Job, contracting, and budget-signal sources
- Review sites, alternatives, and AI/tool directories

For each source, include exactly these two sub-bullets:
- `Use for:` what signal this source is good at revealing
- `Caution:` why the source can mislead or how to avoid over-trusting it

This keeps the catalog operational instead of becoming a raw link dump.

## Cron-specific rule

A large source expansion is incomplete if only docs are edited. Update both live cron jobs:

- The daily idea-generation cron should explicitly say the source list now includes 100+ additional places across multiple classes and should bias toward repeated pains, budget signals, switching intent, and expensive consequences.
- The follow-up system-improvement cron should explicitly preserve the rule that source-intelligence updates require both durable repo docs and live cron prompt updates.

## Verification checklist

- Confirm branch `c01entrepreneur_bot` before editing repos
- Count the added source entries or otherwise verify the requested scale was actually met
- Review `git diff --stat`
- Commit and push the repo change
- Re-list cron jobs after updating to confirm they remain scheduled

## Session note

In the 2026-05-17 update, the catalog was expanded by 140 additional sources and the mirrored instructions doc plus both business-idea cron jobs were updated so the scheduled system uses the larger source rotation.