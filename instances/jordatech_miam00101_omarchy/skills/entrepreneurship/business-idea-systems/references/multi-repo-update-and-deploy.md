# Multi-Repo Update and Deploy Workflow

**When to use:** Every time you update the Business Idea Generator — both `business_idea_generator` (Next.js app) and `business_ideas` (data/content) repos need changes.

## Quick Reference

| Repo | Purpose | Vercel Source |
|---|---|---|
| `business_idea_generator` | Next.js app (`app/`, `lib/`, `vercel.json`) | **YES — Vercel deploys this** |
| `business_ideas` | Data (`ideas.json`, `ideas/*.md`, `source_locations.md`) | No — data only |

## Step-by-Step

### 1. Create feature branch on both repos

```bash
cd /home/jordatech/business_ideas && git checkout -b feat/<name>
cd /home/jordatech/business_idea_generator && git checkout -b feat/<name>
```

### 2. Make changes

Update the markdown brief first, then update `ideas.json` metadata to match.

**Markdown** (`ideas/*.md`): full rewrite of the frontmatter + body. Use `skill_view(name='business-idea-systems')` to know the required sections.

**JSON metadata** (`ideas.json`): update numeric fields (`goodness_score`, `score_inputs`), string fields (`competition`, `difficulty`, `best_market`, `estimated_mrr`), and arrays (`tags`, `source_urls`). Use a Python script to modify in-place — never hand-edit JSON.

### 3. Commit and push the feature branch

```bash
cd /home/jordatech/business_ideas && git add -A && git commit -m "message" && git push origin feat/<name>
cd /home/jordatech/business_idea_generator && git add -A && git commit -m "message" && git push origin feat/<name>
```

### 4. Merge into main and push main (triggers Vercel)

**IMPORTANT: Push `business_idea_generator` main first** — it is the Vercel deployment source.

```bash
cd /home/jordatech/business_idea_generator && git checkout main && git merge feat/<name> --no-edit && git push origin main
cd /home/jordatech/business_ideas && git checkout main && git merge feat/<name> --no-edit && git push origin main
```

### 5. Verify deployment

- The Vercel build runs from `business_idea_generator`
- If build fails with "Missing vercel.json", Vercel is connected to the wrong repo — report the issue, do NOT try to fix by adding a file to the wrong repo

## Competition Re-Analysis Pattern

When the user asks to re-analyze competition:

1. **Search per beachhead** — vertical-specific competitors AND horizontal DIY tools
2. **Create comparison table** — Competitor, Category, Strengths, Weakness/Wedge, Verification Checks
3. **Identify the wedge** — what AgentifyMe does that competitors can't/don't
4. **Cover both DIY tools and incumbents** — entrepreneurs have ChatGPT/Zapier; brokers have Relitix/Brivity
5. **Note the data moat** — accumulated deployment experience creates defensibility over time

## Scoring Updates

Score formula: `Competition × 25% + Potential × 30% + Est. MRR × 25% + Difficulty × 20%`

When updating scores:
- Competition and difficulty scores of 72+ are MORE favorable (not more competitive/harder)
- Recalculate goodness_score from updated inputs
- Update both frontmatter `goodness_score` and JSON `goodness_score` to match

## Vercel CLI Auth Workaround

The Vercel CLI does NOT accept `--token` flag on the `login` command. Device code flow also fails through browser automation due to OAuth redirect loops to blank pages.

**Preferred approach:**
```bash
export VERCEL_TOKEN="vck_..."
# Add to ~/.bashrc for persistence
```

Then `vercel ls` works immediately. The env var approach is reliable and avoids all auth UI issues.
