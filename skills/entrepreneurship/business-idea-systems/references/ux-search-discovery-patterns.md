# UX Search & Discovery Patterns

Patterns for making the Business Idea Generator easier to search, sort, browse, and understand. Implemented July 2026 in `app/page.tsx`, `lib/idea-utils.ts`, and `app/globals.css`.

## 1. Sort Controls (5 modes)

Users need to sort results by different criteria depending on their goal (find newest, find highest MRR, find easiest to build, etc.).

### Implementation

- `SortMode` type in `lib/idea-utils.ts`: `'goodness' | 'newest' | 'mrr' | 'difficulty' | 'competition'`
- `SORT_LABELS` record maps each mode to a human-readable label
- `sortIdeas(ideas, mode)` function handles each sort mode with appropriate ranking logic
- Sort mode persisted as URL param `?sort=newest` so state survives navigation
- Sort chips rendered in both the search results view and the sidebar
- Default sort is `goodness` (score-based); `goodness` is excluded from URL params (clean URLs)

### Sort ranking logic

- **goodness**: `calculateGoodness(b) - calculateGoodness(a)` (descending)
- **newest**: `b.date.localeCompare(a.date)` (descending by date string)
- **mrr**: Parse upper bound from MRR strings like `"$8K-$220K"` → 220000, sort descending
- **difficulty**: Rank map `low=1, low-medium=2, medium=3, medium-high=4, high=5`, sort ascending (easiest first)
- **competition**: Same rank map, sort ascending (lowest competition first)

### CSS classes

- `.sort-bar` — flex container wrapping label + chips
- `.sort-chip` — individual sort button, `.active` state with amber highlight
- Mobile: sort bar goes full-width column at `max-width: 640px`

## 2. Category Explorer (Top-N by Avg Goodness)

Visual tile grid on the homepage showing the top N categories ranked by average goodness score. Designed to surface the strongest opportunity areas first.

### Implementation

- `topCategories(ideas, limit)` in `lib/idea-utils.ts` groups ideas by category, computes `avgGoodness()` for each group, sorts descending by avg score, and returns the top N
- Each tile shows: idea count, avg goodness score (with `/100`), category name, and the best idea title
- `avgGoodness(ideas)` helper: `Math.round(sum(scores) / count)`
- Tiles link to `?category=<category>&idea=<best-idea-slug>#brief` — clicking jumps to that category filtered with its best idea selected
- Active tile state: `.category-tile.active` with amber border

### Homepage display logic

- Only on homepage view (not focused idea view or search results view)
- Show top 10 categories by avg goodness (not all categories)
- Positioned between the hero and "How it works" section
- Nav link `#categories` in topbar for homepage

### CSS classes

- `.category-grid` — `repeat(auto-fill, minmax(180px, 1fr))` on desktop, `1fr 1fr` on mobile
- `.category-tile` — flex column, hover lift effect
- `.category-tile-top` — flex row with count + avg score
- `.category-count` — amber pill with idea count
- `.category-avg` — large amber number with `/100` subscript
- `.category-label` — category name
- `.category-best` — italic "Best: <idea title>" subtitle

## 3. Category Consolidation Workflow

When every idea has its own unique category string (e.g. 51 ideas = 51 categories), the category explorer is useless. Consolidate into 10-15 clean categories.

### Steps

1. Read `data/ideas.json` and build a map from each old category string to a new consolidated category
2. Update every idea's `category` field in `ideas.json`
3. Update every markdown file's YAML frontmatter `category:` field in `data/ideas/*.md` — use `re.sub` with `count=1, flags=re.MULTILINE` to replace only the frontmatter line
4. Update `app/page.tsx` to use `topCategories(ideas, 10)` instead of showing all categories
5. Run `npm run build` to verify
6. Commit, merge to main, push, deploy

### Consolidation mapping approach

Group ideas by theme, not by keyword. Examples:
- All "managed AI agents / X / Y / Z" → "Managed AI Agents"
- All "agency reporting / client portal / proposal automation" → "Agency & Client Operations"
- All "AI security / compliance / governance / DevSecOps" → "AI Operations & Governance"

### Pitfall: only updating JSON

If you update `ideas.json` but not the markdown frontmatter, the app will show the old category when rendering the markdown brief. Always update both.

## 4. Status Badges

Color-coded pills on every idea card so users can see validation status without clicking.

### Implementation

- `statusBadge(status)` function in `lib/idea-utils.ts` normalizes raw status strings to: `Validated`, `Draft`, `Testing`, `Parked`, or title-cased fallback
- **Critical:** Check for `unvalidated` BEFORE `validated` — `"draft/unvalidated"` contains the substring `"validated"` and will match `includes('validated')` incorrectly
- Use: `normalized.includes('validated') && !normalized.includes('unvalidated')` for the validated check
- Rendered as `<span class="status-badge" data-status={normalize(idea.status)}>`
- CSS uses attribute selectors on `data-status` for color-coding:
  - `*="validated"` → green (`#bdf6d5` on `rgba(116, 222, 168, 0.12)`)
  - `*="draft"` or `*="unvalidated"` → amber (`#ffdf9e` on `rgba(255, 206, 122, 0.08)`)
  - `*="testing"` → blue (`#bdd0ff` on `rgba(109, 157, 255, 0.10)`)
  - `*="parked"` → gray (`#999` on `rgba(200, 200, 200, 0.06)`)

### Placement

- Top idea cards: in the `.opportunity-meta` row (after ID, before category)
- Search result cards: in the `.card-topline` row (after score verdict)
- Sidebar idea cards: top-right of `.idea-card-top` flex row

## 5. Card Summaries (ELI5 one-liner)

Each idea card shows a concise "persona — pain" summary so users understand what the business IS without opening the full brief.

### Implementation

- `ideaSummary(idea)` in `lib/idea-utils.ts`: returns `"{persona (80 chars)} — {pain (100 chars)}"`
- Rendered as `<p class="card-summary">` with italic styling
- Replaces the previous card body that only showed `shortText(idea.pain)` without persona context

## 6. Enhanced Search Haystack

The `filterIdeas` function searches `best_market` in addition to title, persona, pain, category, and tags. This was a missing field that caused relevant ideas to not appear in search results.

## 7. Forum VC Frontier Opportunity Areas

A section on the homepage showing emerging venture-scale opportunity areas where no ideas exist yet — frontier signals for where to generate business models next.

### Implementation

- `FORUM_VC_OPPORTUNITY_AREAS` constant in `lib/idea-utils.ts` — array of `{ label, emoji, description }` objects
- Rendered as `.forum-vc-grid` of `.forum-vc-tile` elements with emoji, title, and description
- Positioned below the top categories in the category explorer section
- Visually distinct from existing categories: blue-tinted border/background instead of amber
- Source attribution: link to [forumvc.com](https://forumvc.com)
- CSS: `.forum-vc-section`, `.forum-vc-grid` (auto-fill minmax 240px), `.forum-vc-tile` (blue gradient), `.forum-vc-emoji` (28px)

### When to add frontier areas

- When the user provides external opportunity area lists from VC firms, research reports, or trend analyses
- Label clearly as empty categories — "No ideas in these categories yet"
- These are signals for future idea generation, not current business models

## File map

- `lib/idea-utils.ts` — `SortMode`, `SORT_LABELS`, `sortIdeas()`, `ideaSummary()`, `categoryShort()`, `statusBadge()`, `avgGoodness()`, `topCategories()`, `FORUM_VC_OPPORTUNITY_AREAS`, enhanced `filterIdeas()`
- `app/page.tsx` — sort bar UI, top-10 category explorer, Forum VC section, status badges in cards, card summaries, sidebar sort controls
- `app/globals.css` — `.sort-bar`, `.sort-chip`, `.status-badge[data-status]`, `.card-summary`, `.idea-card-top`, `.category-explorer`, `.category-grid`, `.category-tile`, `.category-tile-top`, `.category-count`, `.category-avg`, `.category-label`, `.category-best`, `.forum-vc-section`, `.forum-vc-grid`, `.forum-vc-tile`, `.forum-vc-emoji`

## Git workflow for UI changes

1. Create feature branch from `main`
2. Implement changes in `lib/`, `app/`, `app/globals.css`
3. Run `npm run build` — must pass with zero TypeScript errors
4. `git checkout -b ux-<feature-name>`
5. Commit with descriptive message
6. Push branch: `git push origin ux-<feature-name>`
7. Merge to main: `git checkout main && git merge ux-<feature-name> --no-ff`
8. Push main: `git push origin main`
9. Deploy: `export VERCEL_TOKEN="vcp_..." && "$HOME/.local/bin/vercel" deploy --prod --yes` (remove `.vercel/` first if stale linkage)
10. Verify with `curl -s -u jordan:<pass> https://businessideagenerator-three.vercel.app/ | grep -c '<new-feature-class>'`
