# Vercel Token Expiration & API Behavior

## Token expiration pattern

Vercel `vck_` tokens can expire or be revoked without warning. Same token may work for one API call in one session but fail the next session:

**Working indicators:**
- `curl -H "Authorization: Bearer $VERCEL_TOKEN" https://api.vercel.com/v2/user` returns user data
- `VERCEL_TOKEN=... vercel ls` returns deployments or empty list without errors

**Dead token indicators:**
- `vercel whoami` → "Error: You are not authorized"
- `vercel deploy` → "Error: The token provided via VERCEL_TOKEN environment variable is not valid"
- `vercel link` → "Error: You cannot set your Personal Account as the scope"

**Critical: `curl` API calls may still work when `vercel whoami` fails.** This is a trap — the token can have partial API scope (user-level read) but not CLI auth scope (which requires team/organization access). Do NOT use `curl` success as proof that `vercel` CLI will work.

## Empty results vs errors

The Vercel API often returns `[]` (empty list) instead of useful errors when:
- Token lacks team scope but has user scope
- Project doesn't exist under that team
- Team ID is wrong or team is inaccessible

There is no reliable way to distinguish "token is dead" from "no projects found" from "wrong team" via API alone. Always run `vercel whoami` first as the primary diagnostic.

## No programmatic repo reconnection

When the wrong repo is connected to Vercel (data-only repo instead of Next.js app repo):
- `vercel link` fails with scope/permission errors
- `vercel ls` returns `[]` or errors
- Team API endpoints return 404 or empty results
- **No CLI or API call can fix this** — requires manual Vercel dashboard interaction

**Required fix (manual only):**
1. Vercel dashboard → project Settings → Git
2. Disconnect the wrong repo
3. Connect the correct repo
4. Set environment variables in Settings → Environment Variables

## Diagnostic sequence

When Vercel operations fail:

```
1. vercel whoami          → if fails, token is dead, ask user for fresh token
2. If whoami succeeds:
   a. vercel ls           → if returns [], project may not be linked
   b. vercel link --name X → if fails with scope error, CLI lacks team context
   c. If all fail above, user must reconnect repo in Vercel dashboard
```

## Session from 2026-06-23

Context: Business Idea Generator deployment. Token `vck_5rBj...` worked for `curl` API calls to `/v2/user` at 02:58 UTC but `vercel whoami` returned "not authorized" and `vercel deploy` returned "token not valid" by 03:28 UTC. Attempted fixes:
- `vercel link --name ... --scope team_...` → "Not able to load teams"
- `vercel link --name ... --scope jordatech` → "Personal Account as scope"
- `curl https://api.vercel.com/v2/projects` → returned `[]` (empty)
- `curl https://api.vercel.com/v2/teams/jordatech/projects` → 404 Not Found

Conclusion: Token had partial API scope (user read) but not full CLI/team scope. No programmatic fix possible. User must provide fresh token or connect repo manually in Vercel dashboard.
