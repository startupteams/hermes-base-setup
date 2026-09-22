# Private Next.js/Vercel Idea Viewer: Protection, Takedown, and Snapshot Pattern

Use when a private business-idea viewer or founder dashboard is deployed to Vercel and may expose sensitive repo-backed content.

## Emergency Takedown

If a Vercel deployment exposes private idea data, prioritize removal and verification over code cleanup.

Prerequisites in the entrepreneur profile:

- Vercel CLI auth may require `HOME=/home/miam`.
- Work from the app repo when possible, e.g. `business_idea_generator`.

Commands:

```bash
cd /home/miam/.hermes/profiles/entrepreneur/resource_repositories/business_idea_generator
HOME=/home/miam vercel project ls
HOME=/home/miam vercel ls business_idea_generator
HOME=/home/miam vercel remove business_idea_generator --yes
```

Verification pattern:

```bash
python3 - <<'PY'
import urllib.request, urllib.error
urls = [
  'https://businessideagenerator-one.vercel.app',
  'https://businessideagenerator-pdoqa9iny-jordatech-team.vercel.app',
]
markers = ['CRE Permit Pack Analyst', 'Common Sense - Dataset Collector', 'Business Idea Generator']
for url in urls:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=20) as r:
            body = r.read(5000).decode('utf-8', 'ignore')
            print(url, 'status', r.status, 'contains_private_markers', any(m in body for m in markers))
    except urllib.error.HTTPError as e:
        body = e.read(5000).decode('utf-8', 'ignore')
        print(url, 'HTTPError', e.code, 'contains_private_markers', any(m in body for m in markers))
PY
```

Expected after removal:

- Alias URL returns `404`.
- Deployment URL returns `410`.
- Private content markers are absent.

## Snapshot Branch Before Cleanup or Redeploy Work

When the user asks to preserve the state that was deployed to Vercel, create a branch name containing `vercel` in each related repo and push it. Do not switch away from the bot branch unless needed; branch from current `HEAD`.

```bash
export HOME=/home/miam
BASE=/home/miam/.hermes/profiles/entrepreneur/resource_repositories
BRANCH="vercel-snapshot-$(date -u +%Y%m%d-%H%M%S)"
for repo in business_idea_generator business_ideas; do
  cd "$BASE/$repo"
  git fetch origin --prune
  test -z "$(git status --porcelain)" || { git status --short; exit 1; }
  git branch "$BRANCH" HEAD
  git push -u origin "$BRANCH"
  echo "$repo $BRANCH $(git rev-parse HEAD)"
done
```

Verify both local and remote SHAs:

```bash
for repo in business_idea_generator business_ideas; do
  cd "$BASE/$repo"
  git rev-parse "$BRANCH"
  git rev-parse "origin/$BRANCH"
  git ls-remote --heads origin "$BRANCH"
done
```

## Free/Simple Password Protection Recommendation

Vercel native Password Protection is convenient but not the best free default: Vercel docs state Password Protection is available on Enterprise or as a paid add-on for Pro plans. Vercel Authentication is available on all plans, but is mainly for Vercel team/project-member access.

For a small private Next.js founder dashboard, the best free/simple default is app-level HTTP Basic Auth in Next.js Proxy/Middleware with credentials stored only as Vercel env vars.

For Next.js 16, prefer root-level `proxy.ts` because Middleware was renamed to Proxy while preserving the same core behavior.

Example plan file location used in the app repo:

- `docs/vercel_password_protection_plan.md`

Minimal implementation sketch:

```ts
import { NextRequest, NextResponse } from 'next/server';

function unauthorized() {
  return new NextResponse('Authentication required', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="business_idea_generator", charset="UTF-8"',
      'Cache-Control': 'no-store',
    },
  });
}

export function proxy(request: NextRequest) {
  const expectedUser = process.env.BASIC_AUTH_USER;
  const expectedPassword = process.env.BASIC_AUTH_PASSWORD;

  if (process.env.NODE_ENV === 'production' && (!expectedUser || !expectedPassword)) {
    return new NextResponse('Basic auth is not configured', {
      status: 503,
      headers: { 'Cache-Control': 'no-store' },
    });
  }

  if (!expectedUser || !expectedPassword) return NextResponse.next();

  const authHeader = request.headers.get('authorization');
  if (!authHeader?.startsWith('Basic ')) return unauthorized();

  try {
    const decoded = atob(authHeader.slice('Basic '.length));
    const separatorIndex = decoded.indexOf(':');
    const user = decoded.slice(0, separatorIndex);
    const password = decoded.slice(separatorIndex + 1);
    if (user === expectedUser && password === expectedPassword) return NextResponse.next();
  } catch {}

  return unauthorized();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)'],
};
```

Vercel env setup:

```bash
HOME=/home/miam vercel env add BASIC_AUTH_USER production
HOME=/home/miam vercel env add BASIC_AUTH_PASSWORD production
```

For non-interactive runs, pipe the value via stdin. Use temp files with restrictive permissions or shell variables; do not commit credentials. Redact command output before displaying it.

```bash
umask 077
printf '%s' 'jordan' > /tmp/business_idea_generator_basic_auth_user
python3 - <<'PY'
import pathlib, secrets, string
alphabet = string.ascii_letters + string.digits + '-_.~'
pathlib.Path('/tmp/business_idea_generator_basic_auth_password').write_text(
    ''.join(secrets.choice(alphabet) for _ in range(32))
)
PY

export HOME=/home/miam
printf '%s\n' "$(cat /tmp/business_idea_generator_basic_auth_user)" \
  | vercel env add BASIC_AUTH_USER production
printf '%s\n' "$(cat /tmp/business_idea_generator_basic_auth_password)" \
  | vercel env add BASIC_AUTH_PASSWORD production
HOME=/home/miam vercel env list production
```

If immediate deployment is needed, `vercel deploy --prod --yes -e BASIC_AUTH_USER=... -e BASIC_AUTH_PASSWORD=...` attaches run-time variables to that deployment, but it does **not** replace verifying/persisting project env vars with `vercel env add` for future production deploys.

Deploy after env vars are present:

```bash
HOME=/home/miam vercel deploy --prod --yes --logs
```

Vercel may print a GitHub repository connection warning for private repos while still completing a CLI upload deployment. Treat the warning as an automation/linking issue, but verify the deployed URL directly.

Verify before sharing URL:

```bash
curl -i https://YOUR_VERCEL_URL/ | head -40
curl -i -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD" https://YOUR_VERCEL_URL/ | head -40
```

More robust verification with content-marker checks:

```bash
python3 - <<'PY'
import base64, os, urllib.error, urllib.request
url = 'https://YOUR_VERCEL_URL/'
user = os.environ['BASIC_AUTH_USER']
pw = os.environ['BASIC_AUTH_PASSWORD']
markers = ['CRE Permit Pack Analyst', 'Common Sense - Dataset Collector', 'Business Idea Generator', 'ideas indexed']
try:
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=25) as r:
        body = r.read(20000).decode('utf-8', 'ignore')
        print('unauth_status', r.status, 'contains_private_markers', any(m in body for m in markers))
except urllib.error.HTTPError as e:
    body = e.read(20000).decode('utf-8', 'ignore')
    print('unauth_status', e.code, 'contains_private_markers', any(m in body for m in markers), 'www_authenticate', e.headers.get('www-authenticate'))

token = base64.b64encode(f'{user}:{pw}'.encode()).decode()
req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0', 'Authorization':'Basic ' + token})
with urllib.request.urlopen(req, timeout=25) as r:
    body = r.read(80000).decode('utf-8', 'ignore')
    print('auth_status', r.status, 'contains_title', 'Business Idea Generator' in body, 'contains_idea', 'CRE Permit Pack Analyst' in body)
PY
```

Unauthenticated response should be `401` and must not contain private idea titles. Authenticated response should be `200` and render normally. If the user explicitly asks for a shared Basic Auth password in chat, provide it in the final response, but never commit it to Git and avoid echoing it unnecessarily in intermediate logs.

## Pitfalls

- Do not redeploy a private idea viewer until protection is implemented, env vars are configured, and unauthenticated `401` is verified.
- Do not commit real Basic Auth credentials; `.env.example` should contain placeholders only.
- Do not rely on obscurity of Vercel deployment URLs.
- If a repo might become public, remove or sanitize checked-in `data/` snapshots before changing visibility.
- Basic Auth is a pragmatic low-friction shield, not enterprise auth: no per-user accounts, MFA, or audit trail.
