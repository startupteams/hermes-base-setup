# Stale Data Fallback Troubleshooting

## Symptom

Vercel reports "Deployment completed" and the deployment is tagged to the correct commit, but the live site serves old content (wrong personas, old scores, missing sections).

## Root Cause

The Next.js viewer in `business_idea_generator` uses a **try-then-fallback** pattern:

```typescript
// lib/ideas.ts
async function ideaIndex() {
  try {
    const text = await githubFetch('ideas.json');
    return JSON.parse(text);
  } catch {
    const text = await localFetch('ideas.json');  // <-- stale fallback
    return JSON.parse(text);
  }
}
```

When GitHub API hits rate limits (unauthenticated requests), SSL errors, network blips, or the branch is wrong, the app silently falls back to `data/ideas.json` and `data/ideas/*.md` — which is a **checked-in snapshot that can drift behind the latest committed idea Markdown**.

Vercel's build runs at deploy time. If the local `data/` is stale, the build is stale regardless of what Git commit Vercel thinks it's building from.

**Note:** As of July 2026, there is no separate `business_ideas` source repo. Both the ideas and the viewer code live in `business_idea_generator`. The `data/` directory IS the canonical fallback — keep it in sync with the latest idea Markdown committed to the repo.

## Diagnostic Steps

1. **Check the live site against the local repo data:**
   ```bash
   # What's on the deployed site?
   curl -s -u "jordan:<pass>" "https://<site>/ideas/<slug>" | grep -c "Midwest"
   
   # What's in the repo data?
   head -20 data/ideas/<slug>.md
   ```
   If the repo has the new content but the site does not, the fallback is serving stale data or the deployment hasn't picked up the latest commit.

2. **Check the local `data/` in `business_idea_generator`:**
   ```bash
   cat data/ideas.json | python3 -c "import sys,json; d=json.load(sys.stdin); [print(i['goodness_score'], i.get('best_market','')[:80]) for i in d['ideas'] if i['slug']=='<slug>']"
   ```
   If this shows old scores or old personas, `data/` needs syncing.

3. **Check GitHub API rate limit status:**
   ```bash
   curl -sI "https://api.github.com/repos/jordatech/business_idea_generator/contents/data/ideas.json" | grep -i "x-ratelimit"
   ```
   If rate-limited and no `GITHUB_TOKEN` env var, the fallback triggers.

## Fix

### Quick fix: sync data/ and push

```bash
cd /home/jordatech/business_idea_generator

# Ensure data/ideas.json is up to date with the latest idea Markdown
python3 -m json.tool data/ideas.json > /dev/null  # validate JSON

# Commit and push
git add -A
git commit -m "Sync data/ with latest idea Markdown"
git push origin main

# Redeploy (if Vercel auto-deploy is not connected)
vercel deploy --prod --yes
```

### Proper fix: set GITHUB_TOKEN

Add a GitHub Personal Access Token to Vercel environment variables:
- `GITHUB_TOKEN` → a fine-grained token with `contents: read` on `jordatech/business_ideas`
- This prevents rate-limit fallback and eliminates the need for local data syncing

## Prevention

- The `data/` directory is the **fallback snapshot**, but since the repo is now the single home for both code and data, keep `data/` in sync with the latest idea Markdown at all times.
- Whenever content changes in `data/ideas/`, always validate `ideas.json` and run `npm run build` before committing.
- Set `GITHUB_TOKEN` in Vercel env to eliminate rate-limit fallback entirely.
- See `business-ideas-source-to-viewer-sync.md` for the sync procedure.

## Related

- `business-ideas-source-to-viewer-sync.md` — sync pattern for the single-repo workflow
- `private-github-vercel-snapshot-deploy.md` — fallback-snapshot deployment pattern
- `lib/ideas.ts` in `business_idea_generator` — the fallback code itself
