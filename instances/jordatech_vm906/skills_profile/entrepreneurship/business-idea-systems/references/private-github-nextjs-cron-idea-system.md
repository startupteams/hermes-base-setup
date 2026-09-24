# Private GitHub + Next.js + Hermes Cron Idea System

Session pattern captured from building the entrepreneur profile's initial business idea generator.

## Use Case

A user wanted a private nicheshunter-style business idea generator focused on apps, technology products, and SaaS niches. Requirements included:

- Private GitHub ideas repo with human-readable Markdown and YAML frontmatter.
- Private GitHub Next.js viewer app intended for Vercel.
- Source knowledge from entrepreneurship extraction repos and agent workspace notes.
- One new idea per day, committed and pushed automatically.
- A second daily job after idea generation that commits at least one system improvement.

## Concrete Repo Layout

Ideas repo:

```text
business_ideas/
├── README.md
├── ideas.json
└── ideas/
    └── business-idea-generator.md
```

Viewer repo:

```text
business_idea_generator/
├── app/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── docs/
│   └── improvement_backlog.md
├── lib/
│   └── ideas.ts
├── .env.example
├── package.json
└── package-lock.json
```

## Branch and Auth Notes

- Initial repo creation used `main`.
- Implementation work used the active bot branch: `c01entrepreneur_bot`.
- In this environment, GitHub auth was not visible from the Hermes profile HOME. Auth lived under the real user home, so GitHub operations needed:

```bash
HOME=/home/miam gh auth status
HOME=/home/miam git push
```

- Always verify branch before editing when the SOUL/profile requires a bot branch.

## First Idea Pattern

The first idea was the generator product itself. The useful framing was:

- Persona: early-stage entrepreneurs and builders.
- Pain: idea paralysis and weak validation because they start from vague product concepts rather than specific personas, pains, assumptions, and research plans.
- Prompt anchor: "Who is a persona that I can make a product for?"
- Output: business model, assumptions, and preliminary market research strategy.

This self-referential first idea is useful when bootstrapping a generator because it validates the content schema against the product's own target customer.

## Cron Job Pairing

Use paired jobs rather than one overloaded job:

1. `0 3 * * *` — create one idea, update `ideas.json`, commit, push.
2. `30 3 * * *` — make at least one generator-system improvement, commit, push.

The improvement job should read a backlog file and prefer safe, incremental improvements: copy changes, docs, UI polish, parser hardening, validation scripts, or small tests.

## Vercel Blocker Pattern

If Vercel CLI reports:

```text
Error: No existing credentials found. Please run `vercel login` or pass "--token"
```

Do not proceed with fake setup. Document the blocker and keep the app Vercel-ready with `.env.example`. Actual secrets should be set in Vercel env vars, not committed.

## Next.js Build Issue Encountered

A build failed because `@/lib/ideas` path alias was not configured. Quick fix for a small app:

```ts
import { getIdea, getIdeas } from '../lib/ideas';
```

Longer-term alternative: configure `baseUrl`/`paths` in `tsconfig.json` intentionally.

## Dependency Audit Pitfall

`npm audit` reported a moderate `postcss` advisory through `next`. The suggested `npm audit fix --force` would have installed a breaking/old Next.js version. Do not auto-apply force fixes that downgrade or cause major changes. Document the advisory and verify whether an upstream safe version exists.

## Verification Checklist

- `gh repo view <owner>/<repo> --json visibility` shows private when requested.
- Every edited repo is on the required bot branch.
- `git status --short` is clean after commit/push.
- Next.js app passes `npm run build`.
- `.env.example` documents secrets, but no real secrets exist in repo.
- Cron jobs are listed, enabled, and scheduled in the expected order.
