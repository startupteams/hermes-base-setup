---
name: vercel-cli-setup
description: "Install, authenticate, and deploy with the Vercel CLI — including restricted machine workarounds and token-based auth."
version: 1.0.0
author: c01entrepreneur_bot
license: MIT
metadata:
  hermes:
    tags: [devops, deployment, vercel, cli, saas]
---

# Vercel CLI Setup

Use this skill when the user needs to install, authenticate, or deploy with the Vercel CLI (`vercel`). Covers admin-restricted machines, token-based auth, and common pitfalls.

## Installation on Admin-Restricted Machines

If `npm install -g vercel` fails with `EACCES: permission denied` (cannot mkdir in `/usr/lib/node_modules`):

```bash
npm install -g --prefix "$HOME/.local" vercel
# Run as: "$HOME/.local/bin/vercel" <command>
```

## Authentication (Preferred: Token)

**DO NOT use `vercel login --token X`** — the CLI explicitly rejects this flag.

**DO NOT use `vercel login` device code flow** — it fails through browser automation due to OAuth redirect loops to blank pages. Google OAuth with passkey-only accounts (no password) cannot be automated either.

### Token-based auth pattern:

1. **Get the token** from Vercel dashboard: Settings → Account → Tokens (generate or copy an existing one).
2. **Set as environment variable:**
   ```bash
   export VERCEL_TOKEN="vck_..."
   ```
3. **Make it persistent** by adding to shell profile:
   ```bash
   echo 'export VERCEL_TOKEN="vck_..."' >> ~/.bashrc
   echo 'export VERCEL_TOKEN="vck_..."' >> ~/.zshrc  # if it exists
   ```
4. **Verify** with `VERCEL_TOKEN=... "$HOME/.local/bin/vercel" ls` — should list deployments or return empty without errors.

### Token scope

- `vck_` prefixed tokens are production tokens.
- They provide the same access as a browser login for CLI operations (deploy, inspect, env, etc.).
- Store in Vercel project environment variables for server-side use (deployments), never commit to source.

## Deployment Workflow

### Standard deploy (after code changes):

```bash
cd /path/to/nextjs/app
"$HOME/.local/bin/vercel" deploy --prod --yes
```

### Linked repo deploy

If the project is linked to a Git repo, pushing to a branch triggers automatic Vercel builds. No CLI deploy needed — Vercel pulls from the repo.

### Environment variables for deployments

```bash
# Add to Vercel project (persistent, available to all future deploys)
export VERCEL_TOKEN="vck_..."
"$HOME/.local/bin/vercel" env add VERCEL_VAR_NAME production
# or for a single deployment
"$HOME/.local/bin/vercel" deploy -e VERCEL_VAR_NAME=value --prod --yes
```

## Common Pitfalls

### Wrong repo connected to Vercel

If Vercel is connected to the wrong repository (e.g., a data-only repo instead of the Next.js app repo), builds will fail with "Missing vercel.json" or the project won't build at all.

**Fix:** Vercel dashboard → Settings → Git → disconnect the wrong repo → import the correct one.

### Token becomes invalid mid-session

Vercel `vck_` tokens can expire or be revoked without warning. An earlier session may authenticate successfully, then a later session sees:
- `vercel whoami` → "Error: You are not authorized"
- `vercel deploy` → "Error: The token provided via VERCEL_TOKEN environment variable is not valid"
- `vercel link` → "Error: You cannot set your Personal Account as the scope" (even though the token works for `curl` API calls)

**Detect early**: Run `vercel whoami` as the first diagnostic. If it fails, the token is dead — do not attempt `vercel link`, `vercel deploy`, or API calls as a fallback; they will also fail silently.

**Fix**: The user must generate a fresh token from [vercel.com/accounts/tokens](https://vercel.com/accounts/tokens) and share it. There is no programmatic way to refresh a dead token.

**Prevention**: When the user shares a token, note it in memory with the generation date so future sessions know to check if it's expired.

### Can only reconnect Vercel Git repo via dashboard

When the wrong repo is connected to Vercel (e.g., a data-only repo instead of the Next.js app repo), **there is no programmatic way to fix this via CLI or API**. The `vercel link`, `vercel ls`, and team API endpoints either fail with permission errors or return empty results.

**Required fix**: The user must manually:
1. Go to Vercel dashboard → project Settings → Git
2. Disconnect the wrong repo
3. Connect the correct repo
4. Set environment variables in Settings → Environment Variables

**Prevent this upstream**: Always verify Vercel is connected to the correct repo (the one with `vercel.json`, `package.json`, and `app/` directory) before assuming a deployment failure is a build issue.

### EACCES on global install

If `npm install -g vercel` fails with permission denied, use `--prefix "$HOME/.local"` as documented above.

## Verification

After setup or deployment, verify with:

```bash
# Check CLI is working
"$HOME/.local/bin/vercel" --version

# Check auth works
VERCEL_TOKEN="vck_..." "$HOME/.local/bin/vercel" ls

# Inspect a deployment
"$HOME/.local/bin/vercel" inspect <deployment-url-or-id>

# List project environment variables
"$HOME/.local/bin/vercel" env ls production
```

## References

- `references/vercel-token-auth-pattern.md` — Token-based Vercel CLI authentication pattern for admin-restricted machines.
- `references/vercel-deployment-checklist.md` — Post-deploy verification checklist covering repo connections, merge status, and stale content detection.
- `references/vercel-token-exhaustion-and-empty-api-results.md` — Token expiration patterns, empty API result traps, diagnostic sequence, and the impossibility of programmatic repo reconnection.
