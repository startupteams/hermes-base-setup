# Business Ideas Source-to-Viewer Sync Pattern

As of July 2026, `business_idea_generator` is the **single repository**. The old `business_ideas` repo is deprecated and archived. There is no longer a separate source repo and viewer repo — everything lives in `business_idea_generator`.

## Repository

- Repository: `jordatech/business_idea_generator` at `/home/jordatech/business_idea_generator`
  - Markdown: `data/ideas/<slug>.md` (checked-in fallback snapshot)
  - Index: `data/ideas.json`
  - Viewer code: `app/`, `lib/`
  - Runtime fetches from GitHub API first (if `GITHUB_TOKEN` is set), then falls back to local `data/` files

## Workflow

1. Verify the remote is `jordatech/business_idea_generator` and the branch is correct (typically `main` or the bot branch).
2. Add or edit the Markdown idea in `data/ideas/<slug>.md`.
3. Update `data/ideas.json` with matching metadata and `file: "ideas/<slug>.md"`.
4. Validate the JSON index with `python3 -m json.tool`.
5. Run the viewer build: `npm run build` from `business_idea_generator`.
6. Commit and push, then verify clean status and the GitHub commit URL.
7. If Vercel auto-deploy is connected, verify the live site. Otherwise deploy with `vercel deploy --prod --yes`.

## Pitfalls

- If `GITHUB_TOKEN` is set in Vercel env, the app fetches from the GitHub API at runtime. If the token is missing or rate-limited, it falls back to `data/`. Keep `data/` in sync even when the token is active.
- Do not rely on `ideas.json` alone. Each indexed `file` should have a corresponding Markdown file in `data/ideas/`.
- If a build updates generated framework folders (`.next/`, `node_modules/`), check status carefully and avoid committing unrelated artifacts.
