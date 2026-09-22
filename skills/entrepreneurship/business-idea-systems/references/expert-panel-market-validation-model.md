# Expert Panel Market Validation Model

Use this reference when Jordan asks to critically analyze all or many business ideas, strengthen market validation plans, or roleplay entrepreneurship advisors such as Bill Aulet, Paul Cheek, Allan Dib, Giff Constable, Rob Fitzpatrick, or a skeptical investor.

## Core pattern

Do not merely summarize ideas. Treat every idea as an unvalidated hypothesis and add specific, falsifiable validation steps.

For each idea, add or update a section named:

```markdown
## Market Validation Model — Expert Discussion and Specific Steps
```

The section should include:

1. **Validation status** — usually `unvalidated hypothesis`; scores are prioritization aids, not proof.
2. **Validation priority** — P1/P2/P3 based on score, urgency, and business type.
3. **Primary evidence needed next** — budget-backed repeated pain, artifacts, paid pilots, or behavioral evidence.
4. **Best first recruiting channel** — specific to persona and market type.
5. **Expert panel critique** — short roleplayed bullets:
   - Bill Aulet: beachhead, end user, DMU, next 10 customers, quantified value proposition.
   - Paul Cheek: sequence riskiest assumptions; run concierge MVBP before scalable SaaS.
   - Allan Dib: target market, message, media, lead capture, nurture, conversion, delivery, LTV, referrals.
   - Giff Constable: talk to one person at a time; avoid pitching; target the right participants; capture artifacts; run experiments.
   - Rob Fitzpatrick: ask about past behavior; reject compliments and hypotheticals.
   - Skeptical investor: require budget, urgency, proprietary data/workflow evidence, defensibility, and unit economics.
6. **Specific validation steps** — 5 concrete tests with pass/fail criteria.
7. **Data to capture** — interview notes, artifacts, outreach metrics, pilot conversion, delivery time, gross margin, rejection reasons.
8. **Failure points to watch** — non-buyer users, low urgency, weak manual value, non-proprietary AI/data, too-broad recruiting.

## Segment-specific validation playbooks

### Enterprise B2B

- Interview 10–12 named personas.
- Map DMU: end user, economic buyer, champion, veto, buying trigger.
- Collect 3–5 redacted artifacts from the workflow.
- Manually deliver the core output for 2 design partners.
- Advance only if 6+ interviews confirm a repeated high-cost trigger and 2 companies accept a pilot with defined success criteria.

### Regulated / compliance / healthcare / finance

- Interview 12–15 operators, compliance leaders, implementation teams, or advisors.
- Collect redacted audit packets, checklists, approval emails, exception logs, or evidence records.
- Run a concierge evidence-packet pilot in 5 business days.
- Test legal/compliance/security vetoes before building.
- Advance only if at least 5 interviews confirm an urgent repeated event, 2 buyers accept a manual pilot, and one economic buyer maps it to budget.

### Education / learning

- Interview end users and budget owners separately.
- Observe 3 real teaching, tutoring, or learning sessions.
- Run a 7-day Wizard-of-Oz cohort with 5–8 users.
- Measure one concrete outcome: time saved, completion, quality, applications produced, engagement.
- Kill if users like the content but do not return or no buyer can name a budget.

### Data marketplace / dataset ideas

- Interview buyers before recruiting supply.
- Ask which dataset they failed to acquire, quality requirements, compliance limits, and willingness to pay.
- Interview contributors about consent, payout, deletion, task fatigue, bystander privacy, and trust.
- Run one bounded data-collection bounty; track cost per accepted item and rejection rate.
- Advance only if one buyer pays or signs an LOI and supply cost supports 60%+ gross margin.

### Consumer

- Use behavior interviews, not opinions.
- Run fake-door landing pages with a specific promise.
- Operate a manual newsletter/prototype for 3 weeks.
- Track repeat use, shares, replies, and acquisition cost.
- Kill if novelty creates one-time clicks only.

### Prosumer / founder / freelancer / agency

- Interview 12–15 target operators about the last paid project, search, invoice, proposal, or dependency issue.
- Request redacted artifacts from their current workflow.
- Offer a fixed-price manual audit/report to 3 prospects.
- Test one direct-response channel/message using Allan Dib framing.
- Advance only if 3 prospects expose real artifacts and 1–2 pay or formally request the manual service.

## Portfolio audit artifact

For repo-wide audits, create a durable Markdown file such as:

```text
market_validation_audit_YYYY-MM-DD.md
```

Include:

- Method and advisor lenses used.
- Cross-portfolio critique.
- Expert-panel operating model.
- Validation backlog for all ideas.
- 14-day execution plan.
- Portfolio kill criteria.

## ideas.json metadata

When updating a full idea portfolio, add/update these fields for each idea in `ideas.json`:

```json
{
  "validation_model_version": "expert-panel-v1-YYYY-MM-DD",
  "validation_priority": "P1 - validate now with buyer interviews and concierge pilots",
  "validation_next_step": "Run customer discovery plus the first concierge/fake-door experiment defined in the idea Markdown Market Validation Model section."
}
```

Also add a root-level `market_validation_model` object describing the version, sources, update time, and principle that ideas are not validated until real target customers provide past-behavior evidence, workflow artifacts, and/or paid pilot commitments.

## Source-to-viewer sync

After modifying the source repo:

1. Copy `business_ideas/ideas.json` to `business_idea_generator/data/ideas.json`.
2. Copy every indexed `ideas/<slug>.md` to `business_idea_generator/data/ideas/<slug>.md`.
3. Copy the audit doc to `business_idea_generator/docs/` if the viewer should expose/retain it.
4. Validate JSON.
5. Run `npm run build`.
6. Commit and push both repos on the bot branch.
7. Deploy if the user asks to publish or if the viewer has been materially updated.

## Pitfalls

- Do not call an idea validated because it has a high goodness score or source signal.
- Do not let advisor roleplay become vague commentary; every critique should point to a next test or kill criterion.
- Do not ask customers to design the product; ask about past behavior and current workarounds.
- Do not run consumer-style surveys for enterprise or regulated DMUs.
- Do not build the scalable SaaS before a concierge/manual version proves workflow value.
