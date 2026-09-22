# Private Founder Dashboard Layout Notes

Use when turning a private idea Markdown repository into a readable web dashboard.

## Trigger

A founder wants an idea viewer to feel closer to a niche/opportunity discovery tool than a raw Markdown renderer.

## Layout pattern

Borrowed from reviewing `nicheshunter.app` during a business idea generator redesign:

1. Sticky top nav with brand, section anchors, and a simple action link.
2. Hero that explains the job in one sentence, e.g. "Find business ideas worth testing before you build."
3. Search box for persona, pain, market, or tag.
4. Proof/status pills: ideas indexed, markets, ideas in current view.
5. Signal card/ticker for detected categories or updated date.
6. "How to use it" cards before the full database:
   - Pick a buyer.
   - Read the next actions.
   - Run one test.
   - Kill weak ideas.
7. Top idea cards with status/confidence and short pain snippets.
8. Sidebar filters for category/status/tags plus idea list.
9. Detail pane rendering the selected Markdown brief.

## Content ordering for idea briefs

For founder-facing idea Markdown, put action near the top:

```markdown
# Idea Title

## One-line summary

## Next actions

## Persona

## Pain

...
```

This keeps the page useful even when the brief is long.

## Ruben-style readability notes

Use the content creator/Ruben Hassid guidance from Jordan's Obsidian vault as copy rules:

- Short paragraphs.
- Direct, specific, action-first copy.
- Avoid hype and generic AI words.
- Use concrete verbs and numbers.
- Tell the reader exactly what to do next.
- Do not over-explain the tool; let the layout teach usage.

Good homepage language:

- "Find business ideas worth testing before you build."
- "Read less. Decide faster."
- "Start with the painful job. Then decide whether the software deserves to exist."
- "Real revenue is still unproven. The useful part is the test plan."

## Verification checklist

- `npm run build` passes.
- Local page includes the new hero, how-to section, idea titles, and `Next actions`.
- If deployed, unauthenticated private pages still return `401` and do not contain private idea markers.
- Authenticated deployment returns `200` and contains the updated layout markers.
- Both the source idea repo and viewer fallback snapshots are committed/pushed when the viewer vendors `data/ideas/*.md`.
