# Opportunity Goodness Scoring for Business Idea Systems

Use this reference when turning business idea briefs into a Niche Hunter-style opportunity dashboard or when replacing arbitrary card scores with calculated scores.

## Source pattern observed

Niche Hunter-style detail pages show:

- A visible score like `85/100` near the title.
- Category/tag chips.
- Metrics: Competition, Potential, Est. MRR, Best Market, Time to MVP, Difficulty.
- Analysis sections: Opportunity Analysis, Market Analysis, Key Learnings, Improvement Opportunities, Risks to Consider.
- Short, direct copy that explains the gap and recommended move before long detail.

## Recommended score model

Store a `goodness_score` and its inputs in the idea Markdown frontmatter and `ideas.json` index.

Recommended fields:

```yaml
goodness_score: 72
competition: "Medium"
potential: "Very High"
estimated_mrr: "$25K-$150K"
difficulty: "High"
best_market: "AI labs and robotics teams needing permissioned real-world sensor datasets"
time_to_mvp: "6-10 weeks for concierge dataset pilot"
score_inputs:
  competition_score: 62
  potential_score: 88
  mrr_score: 82
  difficulty_score: 46
```

Use the score inputs to calculate the displayed `goodness_score`:

```text
Goodness = Competition × 25% + Potential × 30% + Est. MRR × 25% + Difficulty × 20%
```

Interpretation:

- `competition_score`: higher means easier to compete / less crowded / clearer wedge.
- `potential_score`: higher means stronger market size, urgency, and expansion opportunity.
- `mrr_score`: higher means higher plausible near-term subscription or services revenue.
- `difficulty_score`: higher means easier to execute; hard businesses receive a lower score.

Round to the nearest integer and display as `x/100`.

## Markdown section pattern

Place this after `Next actions` and before the long business model:

```markdown
## Goodness score

**72/100**

Calculated from Competition, Potential, Est. MRR, and Difficulty.

- **Competition:** Medium (62/100, where lower competition earns a higher score)
- **Potential:** Very High (88/100)
- **Est. MRR:** $25K-$150K (82/100)
- **Difficulty:** High (46/100, where easier execution earns a higher score)
- **Formula:** round((Competition 62 × 0.25) + (Potential 88 × 0.30) + (Est. MRR 82 × 0.25) + (Difficulty 46 × 0.20)) = **72/100**

Short rationale.

## Opportunity analysis

### The opportunity

### Market gap

### Recommended move

## Market analysis snapshot

## Potential competitors

Linked competitor/app benchmarks with Monthly Growth, Est. MRR, Strong Market, Category, Key Strengths, and Weaknesses. Treat growth/MRR as directional hypotheses unless sourced.

## Key learnings

## Improvement opportunities

## Risks to consider
```

## Viewer implementation notes

- Do not hardcode ranked scores like `88 - index`; calculate them from `score_inputs`.
- Sort top opportunity cards by calculated score descending.
- Show the formula or score inputs somewhere visible enough that the score is not a mysterious vanity number.
- Show a detail-page metric panel above the Markdown brief with Goodness, Competition, Potential, Est. MRR, Best Market, Time to MVP, and Difficulty.
- Keep the source Markdown primary. If the viewer has a checked-in fallback snapshot (`data/ideas.json`, `data/ideas/*.md`), sync it after modifying the source idea repo.

## Verification checklist

- Validate `goodness_score` equals the rounded weighted formula for every idea.
- Confirm heading order remains: `One-line summary` → `Next actions` → `Goodness score` → longer analysis.
- Build the Next.js viewer with `npm run build`.
- For password-protected deployments, verify unauthenticated requests return `401` and authenticated requests show score markers and analysis headings.
