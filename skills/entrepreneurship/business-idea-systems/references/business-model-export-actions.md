# Business Model Export Actions

Session pattern from the Business Idea Generator viewer: selected/focused business model briefs should be easy to export without exposing private data or credentials.

## When to use

Use this when a Next.js business-idea viewer needs selected ideas to be downloadable, printable, or saveable as PDF.

## Implementation pattern

1. Keep Markdown as the source export format.
   - Add a `getIdeaMarkdown(slug)` helper near `getIdea()`.
   - Resolve the slug through the indexed idea list so arbitrary file paths cannot be fetched.
   - Fetch the same canonical/fallback Markdown used by the detail renderer.
2. Add a route handler such as `app/ideas/[slug]/markdown/route.ts`.
   - Return `text/markdown; charset=utf-8`.
   - Add `Content-Disposition: attachment; filename="<slug>.md"`.
   - Sanitize the filename by allowing only simple slug characters.
3. Add a small client component for export actions.
   - `.md` can be a normal anchor with `download` pointing to the route above.
   - Print/PDF should call `window.print()` on the standalone detail page.
   - In compact/focused dashboard views, link to the standalone page as the printable/PDF page instead of trying to print a complex comparison/dashboard layout.
4. Add print CSS.
   - Hide navigation, sidebars, export controls, dashboard-only links, and heavy controls.
   - Use white background and dark text.
   - Remove shadows, borders, rounded panels, and constrained widths that make browser PDFs awkward.
   - Keep scorecard, validation, and brief body readable; avoid dark-theme inheritance in printed output.
5. Verify locally before deployment.
   - `npm run build` should show the new dynamic Markdown route.
   - `curl -s -D /tmp/headers.txt http://localhost:3000/ideas/<slug>/markdown -o /tmp/idea.md` should return `200`, `content-type: text/markdown`, and `content-disposition: attachment`.
   - Browser snapshot of `/ideas/<slug>` should show `Download .md` and `Print / save PDF`.
   - Browser snapshot of `/?idea=<slug>#brief` should show `Download .md` and `Printable / PDF page`.

## Pitfalls

- Do not require server-side PDF generation unless the user explicitly asks; browser print-to-PDF is simpler and avoids adding dependencies.
- Do not expose raw arbitrary file-path fetching from a route handler. Look up the slug in `ideas.json` first.
- Do not print the whole dashboard/sidebar by default; provide a standalone page for clean print/PDF output.
- Do not let global dark-theme CSS make printed or standalone body text white on a light background.
