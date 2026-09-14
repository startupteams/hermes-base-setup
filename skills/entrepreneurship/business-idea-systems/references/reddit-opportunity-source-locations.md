# Reddit Opportunity Source Locations for Business Idea Systems

Session learning: Jordan provided several Reddit communities/threads as recurring raw sources for technology/SaaS business ideas. These should be treated as opportunity-signal feeds, not validation.

## Current source list

- r/AiMoneyMaking: https://www.reddit.com/r/AiMoneyMaking/
  - Use for AI monetization attempts, side-hustle examples, low-friction automation/SaaS concepts, and recurring "how do I make money with AI?" pains.
  - Caution: many posts may be hype, affiliate-driven, or unsupported passive-income claims.

- r/AiNova: https://www.reddit.com/r/AiNova/
  - Use for AI tool discovery, AI product ideas, agents/workflows, and emergent founder or operator problems.
  - Caution: separate real user pains from generalized AI enthusiasm.

- r/AiNova passive-income analysis thread: https://www.reddit.com/r/AiNova/comments/1rzx9zn/i_analyzed_25_ai_passive_income_ideas/
  - Use as a seed list of AI passive-income claims to deconstruct into personas, pains, business models, and validation assumptions.
  - Caution: ideation input only; not market validation.

- r/BuildCapital: https://www.reddit.com/r/BuildCapital/
  - Use for build-in-public, capital formation, acquisition, funding, distribution, and operator/founder pains.
  - Caution: prioritize posts with concrete obstacles, current workarounds, or paid alternatives.

- r/CofounderHunt: https://www.reddit.com/r/CofounderHunt/
  - Use for cofounder matching, technical/non-technical founder gaps, team formation pains, and founder-market-fit signals.
  - Caution: extract the repeated underlying need, not only the individual request.

## How to incorporate these in a Git-backed idea repo

1. Add a durable source file such as `business_ideas/source_locations.md` with the URLs and source-use rules.
2. Update the idea-generation cron/job prompt to reference that file and the URLs directly.
3. In generated ideas, include source URLs in frontmatter or body when a specific thread materially inspired the idea.
4. Keep idea status as draft/unvalidated unless backed by customer conversations or stronger market evidence.

## Evidence rubric

- Stronger signal: repeated posts across sources, specific dollars/time lost, concrete current workaround, or multiple commenters saying they have the same issue.
- Medium signal: one detailed post with specific context and clear pain.
- Weak signal: generic "wouldn't it be cool if" ideas or passive-income claims without proof.

## Automation prompt note

For daily autonomous idea-generation jobs, include explicit language that Reddit is an opportunity signal source, not validation, and instruct the job to look for repeated pains, current workarounds, dollars/time lost, and consequences of doing nothing.
