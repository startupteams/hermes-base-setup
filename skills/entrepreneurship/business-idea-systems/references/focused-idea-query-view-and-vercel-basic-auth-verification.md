# Focused Idea Query Views + Vercel Basic Auth Verification

Use this reference when updating the `business_idea_generator` Next.js viewer so a query-selected idea URL such as `/?idea=ai-agent-operations-control-tower#brief` behaves like a focused brief page rather than the full homepage.

## Pattern

Separate the root page into three explicit modes instead of letting the homepage, search results, and selected idea workspace bleed into each other:

```ts
const isFocusedIdeaView = Boolean(requestedSlug);
const isSearchResultsView = hasActiveFilters && !isFocusedIdeaView;
```

When `searchParams.idea` is present:

1. Treat the page as a focused idea view (`isFocusedIdeaView = Boolean(requestedSlug)`).
2. Keep the global navigation and a clear Home link.
3. Keep a search form so users can search for another idea from the focused page.
4. Hide homepage-only and discovery sections:
   - hero / dashboard intro
   - how-it-works explainer
   - top ideas cards
   - broad idea database/filter/list UI if it distracts from the selected idea
   - auto-selected or default homepage workspace content unrelated to the requested slug
5. Render only selected idea content:
   - score / metric overview
   - stable unique ID / slug where useful
   - research plan and assumption audit
   - selected Markdown brief body
   - standalone brief link if useful
6. For the normal homepage with no `idea` query and no active filters, preserve the full discovery dashboard.
7. For search/filter pages with no `idea` query, render a dedicated results-only page: search form, active filters, ranked result cards, and Home link. Do not render the homepage hero or selected-detail workspace.

## Implementation notes

- In `app/page.tsx`, compute `isFocusedIdeaView` immediately after reading `requestedSlug`.
- Compute `isSearchResultsView = hasActiveFilters && !isFocusedIdeaView` so query-selected ideas win over search/filter state.
- Wrap homepage sections with conditional rendering: `{!isFocusedIdeaView && !isSearchResultsView ? <section ...>...</section> : null}`.
- Wrap the detail/workspace section so it does not render during search results pages: `{!isSearchResultsView ? <section ...>...</section> : null}`.
- Add a search form with an `id="idea-search"` on focused and search results views so nav links still work.
- Add an explicit Home link/CTA (`/`) in focused and search results navigation.
- Show stable identifiers (`idea.slug`) in focused detail pages and result cards; preserve lowercase/hyphenated slug rendering with CSS if surrounding meta text is uppercased.
- Sort search result cards by the same calculated goodness score used elsewhere before rendering (for example `rankedIdeas = [...filteredIdeas].sort((a, b) => calculateGoodness(b) - calculateGoodness(a))`).
- Avoid removing the ability to navigate home: make the brand and a visible CTA/link point to `/`.
- If the focused page still shows category/tag/status filters and full idea lists, it may still feel like homepage information. Hide those on focused views unless the user explicitly asks to keep comparison UI.

## Verification

Run:

```bash
npm run build
```

Then locally verify all modes:

```bash
npm run dev
# open / and confirm homepage sections remain
# open /?idea=<known-slug>#brief and confirm homepage sections are absent and only that idea's business model content is shown
# open /?persona=<query>#search-results or another active filter and confirm only search results render, ordered by goodness rating descending
```

Useful browser checks:

- Focused URL should show the selected idea title, slug/unique ID, and brief.
- Focused URL should not show homepage copy such as "Find a business idea you can test this week" or "Three steps. One decision".
- Focused URL should not show unrelated default/homepage idea content.
- Focused URL should preserve search and an obvious Home link.
- Search results URL should show result cards only, not the selected brief workspace.
- Homepage `/` should still show hero, how-it-works, top ideas, search, and filters.

## Vercel protected deployment verification

For this private viewer, production may be protected by Next.js Basic Auth via `proxy.ts` and Vercel env vars:

- `BASIC_AUTH_USER`
- `BASIC_AUTH_PASSWORD`

If browser verification fails with an auth error, that can be expected. Verify deployment health without exposing credentials:

```bash
curl -I -s https://businessideagenerator-three.vercel.app/?idea=<known-slug> | sed -n '1,20p'
HOME=/home/miam npx vercel inspect https://businessideagenerator-three.vercel.app
HOME=/home/miam npx vercel env ls production
```

Expected unauthenticated protected response:

- `HTTP/2 401`
- `www-authenticate: Basic realm="business_idea_generator"`

Expected Vercel inspect result:

- deployment status `Ready`
- alias includes `https://businessideagenerator-three.vercel.app`

Do not print or commit Basic Auth values. `vercel env ls` only shows encrypted values and is safe for confirming the variables exist.