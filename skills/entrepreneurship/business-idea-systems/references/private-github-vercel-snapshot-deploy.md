# Private GitHub + Vercel Snapshot Deployment Notes

Use this reference when deploying a Next.js idea viewer backed by a private GitHub ideas repository, especially when Vercel should work without checked-in secrets.

## Pattern

1. Keep the source-of-truth idea repository private, e.g. `jordatech/business_ideas`.
2. In the viewer app, check in a sanitized snapshot:
   - `data/ideas.json`
   - `data/ideas/<slug>.md`
3. In the app data layer, attempt live private GitHub reads first when `GITHUB_TOKEN` exists.
4. Fall back to local `data/` files when GitHub reads fail or no token exists.
5. Update docs so `GITHUB_TOKEN` is optional when the snapshot exists.
6. Build locally before deploying:
   ```bash
   npm install
   npm run build
   ```
7. Commit and push the snapshot plus data-layer/docs changes before deployment.
8. Deploy with Vercel CLI if authenticated:
   ```bash
   vercel deploy --prod --yes --logs
   ```
9. Smoke-test the production alias with HTTP 200 and content checks for expected idea titles/count.

## Environment quirk from Jordan's entrepreneur profile

Hermes profile `HOME` can differ from the real user home. GitHub and Vercel CLI credentials may live under `/home/miam`, so authenticated commands may need:

```bash
HOME=/home/miam gh auth status
HOME=/home/miam vercel whoami
HOME=/home/miam vercel deploy --prod --yes --logs
```

## Vercel GitHub-linking pitfall

Vercel can fail to connect a private GitHub repository while still completing an upload-based deployment. Treat these as separate outcomes:

- Upload deployment succeeds: production URL can be used and verified.
- GitHub repository connection fails: automatic Git-triggered deployments may not work until Vercel/GitHub permissions are fixed in the dashboard.

Report both clearly.

## Security

- Never commit `.env`, `.env.local`, `.vercel`, or tokens.
- Prefer Vercel env vars for live private-repo refresh.
- If using a local snapshot, ensure it contains only content safe to publish in the viewer deployment.

## Verification checklist

- `git status` is clean after commit/push, ignoring `.vercel` if present.
- `npm run build` passes locally.
- Vercel build passes.
- Production URL returns status 200.
- Page includes expected title(s), count, and representative idea content.
