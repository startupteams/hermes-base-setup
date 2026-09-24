# Batch Idea Intake and Analysis

Use this reference when Jordan provides a numbered list of rough business ideas, domains, personas, pains, product sketches, or prototype links and asks to analyze them into the `business_idea_generator` system.

As of July 2026, `business_idea_generator` is the **single repository**. The old `business_ideas` repo is deprecated and archived.

## Workflow

1. Load `business-idea-systems` and `github-pr-workflow`.
2. Verify the repository is on the correct branch (typically `main` or the bot branch) and clean enough to edit.
3. Treat rough user notes as source material, not finished positioning. Preserve the core persona/pain/product, but normalize into one idea per durable slug.
4. If the user references a non-`jordatech` repo, treat it as context only unless explicitly authorized to edit/fork it. Mention this in the brief when relevant.
5. For each idea, create `data/ideas/<slug>.md` with:
   - one-line summary
   - `Next actions` directly under the summary
   - opportunity analysis, market gap, recommended move
   - market analysis snapshot
   - calculated goodness score based on competition, potential, estimated MRR, and difficulty
   - linked potential competitors with Monthly Growth, Est. MRR, Strong Market, Category, Key Strengths, Weaknesses
   - persona, pain, product concept, business model
   - assumptions, customer-discovery strategy, Mom Test questions, MVBP
   - Key learnings, Improvement opportunities, Risks to consider
6. Update `data/ideas.json` with matching score inputs and metadata. Keep Markdown as the human-readable source of truth.
7. Verify every indexed `file` exists in `data/ideas/` and every brief has the required Niche Hunter-style sections.
8. Run `npm run build` in `business_idea_generator`.
9. Commit/push, deploy the protected Vercel app, and verify Basic Auth still blocks unauthenticated access.

## Scoring reminder

Use the established formula unless the user changes it:

`Goodness = competition_score * 0.25 + potential_score * 0.30 + mrr_score * 0.25 + difficulty_score * 0.20`

Important wording: higher `competition_score` and `difficulty_score` mean more favorable conditions — less crowded competition and easier execution.

## Competitor estimates

Do not present competitor Monthly Growth or Est. MRR as confirmed unless sourced. If using judgment, label the section as directional benchmarks or research hypotheses and recommend later verification with Similarweb, app marketplaces, public filings, founder posts, job postings, and customer interviews.

## Verification snippet

```bash
python3 - <<'PY'
import json
from pathlib import Path
base = Path('data')
required = ['## One-line summary','## Next actions','## Market analysis snapshot','## Potential competitors','## Key learnings','## Improvement opportunities','## Risks to consider']
idx = json.loads((base / 'ideas.json').read_text())
missing = []
for idea in idx['ideas']:
    p = base / idea['file']
    if not p.exists():
        missing.append(str(p))
        continue
    text = p.read_text()
    for marker in required:
        if marker not in text:
            missing.append(f"{idea['slug']} missing {marker}")
print(f'ideas: {len(idx["ideas"])}, missing: {len(missing)}')
if missing:
    print('\n'.join(missing))
    raise SystemExit(1)
PY
```
