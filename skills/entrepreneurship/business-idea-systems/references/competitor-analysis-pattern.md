# Competitor Analysis Pattern for Business Idea Briefs

Use this reference when adding Niche Hunter-style competitor/app analysis to business idea Markdown and private founder dashboards.

## Source pattern observed

Niche Hunter's demo detail page has a `Trending Apps` tab with competitor cards. Each card shows:

- Ranked competitor/app name.
- Category.
- Short positioning description.
- Monthly growth signal such as `+340%`.
- Estimated MRR signal such as `$70K+ MRR`.
- A click-through affordance for deeper analysis.

For Jordan's business idea system, adapt this pattern into a durable Markdown section called `Potential competitors`.

## Markdown section pattern

Place `Potential competitors` after `Market analysis snapshot` and before `Key learnings` so the reader sees market context before lessons/opportunities/risks.

```markdown
## Potential competitors

These are directional benchmarks, not validated financial claims. Treat Monthly Growth and Est. MRR as research hypotheses to verify with customer interviews, review mining, traffic tools, app marketplaces, founder posts, job postings, and sales conversations.

### [Competitor Name](https://example.com/)

- **Monthly Growth:** Directional growth signal or hypothesis. Include source confidence if known.
- **Est. MRR:** Directional estimate or `Unknown`; do not present unverified numbers as fact.
- **Strong Market:** Buyer/user segment where the competitor appears strongest.
- **Category:** Product/category label.
- **Key Strengths:** Specific defensible strengths, distribution, workflow, data, trust, or UX advantages.
- **Weaknesses:** Gaps the idea could exploit; avoid generic weaknesses.
```

## Quality bar

- Link every competitor heading.
- Use at least 3-4 competitors per idea when possible.
- Label growth/MRR as estimates or hypotheses unless backed by public evidence.
- Compare against the idea's wedge, not just broad category incumbents.
- Include both direct competitors and adjacent substitutes when the market is young.
- Do not fabricate exact revenue. Use ranges, `Unknown`, or source-qualified language.

## Viewer implementation notes

- Ensure Markdown links render visibly; competitor headings should be easy to scan.
- If the viewer vendors fallback snapshots (`data/ideas/*.md`), sync them after editing the source idea repo.
- Verify protected deployments do not expose competitor/private markers without authentication.
- Verify authenticated pages include `Potential competitors`, `Monthly Growth`, `Est. MRR`, `Strong Market`, `Key Strengths`, and `Weaknesses`.

## Suggested verification script

```bash
python3 - <<'PY'
from pathlib import Path
base = Path('ideas')
markers = [
  '## Potential competitors', '**Monthly Growth:**', '**Est. MRR:**',
  '**Strong Market:**', '**Category:**', '**Key Strengths:**', '**Weaknesses:**',
  '## Key learnings', '## Improvement opportunities', '## Risks to consider'
]
for path in sorted(base.glob('*.md')):
    text = path.read_text()
    for marker in markers:
        assert marker in text, f'{path.name} missing {marker}'
    assert text.count('### [') >= 3, f'{path.name} needs linked competitor headings'
    print(path.name, 'ok')
PY
```
