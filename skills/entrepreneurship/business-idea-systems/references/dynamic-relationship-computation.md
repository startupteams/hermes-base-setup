# Dynamic Relationship Computation Pattern

Pattern for computing business-model relationships dynamically from `ideas.json` instead of maintaining a static relationship database file. Implemented July 2026 in `lib/relationships.ts` and `app/relationships/page.tsx`.

## Problem

The original `data/idea_relationships.json` was a 1,694-line static file containing:
- A full copy of every idea's `title`, `category`, `tags`, `score`, `score_inputs` (duplicated from `ideas.json`)
- Manually computed `risk_score`, `reward_score`, `recommendation` fields (all derivable from `score_inputs`)
- 99 hand-written relationship entries with `relatedness_score` and `rationale` strings

This was:
1. **Not scalable** — every new idea required manually updating the relationship database
2. **Stale-prone** — duplicate data drifted from the source `ideas.json`
3. **Hard to maintain** — rationales were hand-written strings like `"shared tags: ai, b2b saas, saas, starterstory; shared market/workflow terms: age..."`

## Solution: Compute everything dynamically

### Token-based similarity (lightweight embeddings)

Instead of vector embeddings requiring a database, use **tokenized feature sets** with cosine similarity. Each idea is tokenized into a `Set<string>` of lowercase tokens from:

- Tags (as-is, lowercased)
- Category (split on `/`, `-`, spaces; tokens > 2 chars)
- Persona (same tokenization)
- Pain (same tokenization)
- Best market (same tokenization)
- Title (same tokenization)

Cosine similarity: `|intersection| / sqrt(|a| * |b|)`

This acts as a bag-of-words embedding — not as precise as dense vector embeddings, but:
- Zero dependencies (pure TypeScript)
- Runs at build time (SSG)
- Scales to 100+ ideas with no performance issue
- New ideas automatically get relationships on next build

### Derived scores (no storage needed)

| Field | Formula | Source |
|---|---|---|
| `riskScore` | `100 - difficulty_score` | `score_inputs.difficulty_score` |
| `rewardScore` | `(potential_score + mrr_score) / 2` | `score_inputs` |
| `goodness score` | weighted formula (mirrors `calculateGoodness` from `idea-utils.ts`) | `score_inputs` |

These are computed in `toRelationshipIdea()` and never stored.

### Threshold

Default cosine similarity threshold: `0.12` (12%). This captures ~354 relationships from 51 ideas (vs 99 in the old static DB). The broader threshold catches meaningful connections the old heuristic missed.

## Implementation file map

- `lib/relationships.ts` — all computation logic:
  - `tokenize(text)` — splits text into lowercase token sets
  - `ideaFeatures(idea)` — builds feature set from tags + fields
  - `cosineSimilarity(a, b)` — `|intersection| / sqrt(|a| * |b|)`
  - `computeRisk(idea)` / `computeReward(idea)` — derived scores
  - `getRelationshipIdeas()` — returns ideas with computed risk/reward
  - `getRelationships(threshold)` — computes all pairwise similarities above threshold
  - `relatedIdeasFor(slug)` — finds related ideas for a single slug
  - `getRelationshipDatabase()` — returns ideas + relationships + category clusters
- `app/relationships/page.tsx` — server component rendering:
  - Category clusters (with internal link counts)
  - SVG network graph (nodes positioned by score, colored by risk/reward)
  - Top 50 strongest pairs table (with shared tags and category match)
  - Per-idea adjacency list (top 5 related per idea)

## Category clusters

`getRelationshipDatabase()` also computes category clusters: for each category, count how many relationship edges exist between members of that category. This shows which categories are internally cohesive (e.g. "Managed AI Agents" with 18 internal links) vs isolated.

## Comparison: old static vs new dynamic

| Metric | Old (static JSON) | New (dynamic) |
|---|---|---|
| File size | 1,694 lines / 55KB | 0 (deleted) |
| Relationships found | 99 | 354 |
| Maintenance per new idea | Manual: update ideas array + compute relationships | Zero: automatic on next build |
| Data duplication | Full copy of title/category/tags/score/score_inputs | None |
| Risk/reward fields | Stored, could drift | Computed from score_inputs |
| Rationale strings | 99 hand-written | Replaced by shared tags + shared category boolean |

## Pitfalls

- **Function declaration syntax:** When converting `export const uniqueValues = (ideas, field) => ...` to `export function uniqueValues(ideas, field) { ... }`, the body must use `return` — leaving the arrow `=>` body without braces causes a parse error. Always add `{ return ... }` wrapping.
- **Old category strings in relationship DB:** If you still have a static relationship JSON, it will contain old (pre-consolidation) category strings. Delete the file rather than trying to update it — the dynamic computation uses current `ideas.json` categories.
- **Threshold tuning:** 0.12 is a good default for 50+ ideas. For smaller datasets (< 20), lower to 0.08 to find more connections. For very large datasets (200+), raise to 0.15 to keep the graph readable.

## When to use this pattern

- Any Next.js idea/portfolio dashboard where relationships between items are useful
- When a static relationship file is becoming a maintenance burden
- When new items are added frequently and manual relationship updates are forgotten
- When you want to avoid adding a vector database dependency for a small-to-medium dataset
