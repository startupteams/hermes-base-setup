# Focused Brief Legibility and Idea-Specific Validation Content

Session learning from updating the Business Idea Generator focused and standalone idea views.

## Trigger

Use this reference when maintaining founder-facing business idea dashboards or Markdown-backed idea briefs where selected ideas have scorecards, standalone pages, and expert-panel validation sections.

## UI lessons

- Show the selected business model title immediately above the goodness/score panel. A scorecard without a nearby title is ambiguous, especially in focused `/?idea=<slug>#brief` views.
- Standalone detail pages can inherit dark-theme text into light panels. Verify computed CSS for `.brief-body`/rendered Markdown, not just the DOM content.
- A safe standalone content treatment is:
  - light panel background, e.g. `#fffaf0`
  - dark body/heading/list/strong text, e.g. `#17120b`
  - explicit link color with enough contrast
- Browser snapshots confirm structure and content, but use computed style checks for color regressions:

```js
(() => {
  const el = document.querySelector('.detail-page .brief-body');
  const p = el?.querySelector('p');
  const h = el?.querySelector('h1');
  return {
    bodyColor: getComputedStyle(el).color,
    bodyBackground: getComputedStyle(el).backgroundColor,
    paragraphColor: p && getComputedStyle(p).color,
    headingColor: h && getComputedStyle(h).color,
  };
})()
```

## Content lessons

- Move concrete validation steps into the early `Test the riskiest assumption first` section, not below a long expert critique.
- Expert panels must not be repeated generic advisor quotes across all ideas.
- For each idea, tailor critique to the frontmatter/body facts:
  - title
  - persona / beachhead
  - pain statement
  - category or best market
  - estimated MRR ambition
  - difficulty / execution risk
- A useful per-idea expert-panel pattern:
  - Bill Aulet: beachhead, DMU roles, quantified value proposition in current units of pain.
  - Paul Cheek: concierge MVBP, manual workflow first, automate only repeated steps.
  - Allan Dib: one-page marketing plan, precise lead magnet tied to the pain.
  - Giff Constable: artifact-based interviews about the last incident, not pitching.
  - Rob Fitzpatrick: reject compliments/hypotheticals; require recent events, workarounds, budget owner, artifacts.
  - Skeptical investor: fundability depends on paid wedge, defensible workflow data, and why incumbents cannot copy it.

## Portfolio update recipe

1. Patch canonical Markdown in `business_ideas/ideas/*.md` first.
2. Replace old `### Specific validation steps` with `### Test the riskiest assumption first — specific validation steps`.
3. Ensure order inside each validation model section is:
   - validation status/priority/evidence/recruiting channel
   - riskiest-assumption specific validation steps
   - expert panel critique
   - data to capture
   - failure points
4. Sync changed Markdown into `business_idea_generator/data/ideas/*.md`.
5. Validate with a script that checks no old `### Specific validation steps` heading remains and the section order is correct.
6. Build the viewer and verify focused and standalone pages locally before deploy.
