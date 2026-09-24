# LinkedIn Jobs as Opportunity Signals

Use this reference when Jordan asks for LinkedIn-derived business ideas but public LinkedIn posts/feed content is unavailable or login-gated.

## Context

LinkedIn feed posts and content search may be inaccessible without an authenticated browser session. In that case, public LinkedIn Jobs listings can still provide useful **demand signals**: companies are hiring people to do a workflow, mitigate a risk, deploy a process, or coordinate a new function.

Treat these listings as source intelligence, not validation. A job post proves only that at least one organization is spending headcount budget around a problem area. It does not prove willingness to buy a SaaS product.

## Workflow

1. **Inspect existing ideas first**
   - Read `business_ideas/ideas.json` and existing `ideas/*.md` titles/slugs.
   - Avoid duplicates by comparing persona, pain, and workflow, not only title.

2. **Search LinkedIn Jobs public pages / guest endpoints**
   - Query for pain/workflow phrases, not only product nouns.
   - Useful patterns:
     - `AI agent implementation business operations`
     - `AI adoption specialist CRM sales operations`
     - `AI governance compliance manager enterprise`
     - `AI security engineer agentic AI`
     - `procurement tariff analyst`
     - `AI clinical documentation workflow`
   - Preserve job title, company, date if available, and URL.

3. **Translate job clusters into opportunity hypotheses**
   - Look for repeated hiring around the same workflow.
   - Identify what manual work the role is meant to absorb.
   - Ask: could software reduce the headcount burden, risk, delay, or measurement gap?

4. **Rank with skeptical investor criteria**
   - Buyer urgency: is the pain tied to security, compliance, revenue, margin, or executive mandate?
   - Budget trigger: is there existing spend via hiring, consultants, tools, or risk mitigation?
   - Defensibility: can the product accumulate proprietary workflow data, benchmarks, evaluation sets, or integrations?
   - Kill criteria: what evidence would make the idea obviously weak?

5. **Document the source limitation explicitly**
   - Example language:
     > Scope: recent public LinkedIn Jobs signals from roughly the last five months / current postings. LinkedIn feed posts were not accessible without login, so this scan uses LinkedIn job postings as observable demand signals. Treat this as source intelligence, not validation.

6. **Produce durable artifacts**
   - Source repo: `source_locations_linkedin_<YYYY-MM-DD>.md`
   - Viewer repo: `docs/linkedin_opportunity_scan_<YYYY-MM-DD>.md`
   - For selected ideas, create one full idea brief per slug and update `ideas.json`.

7. **Sync and deploy as usual**
   - Copy source JSON/Markdown into the viewer fallback snapshot.
   - Validate JSON.
   - Run `npm run build`.
   - Run `npm audit --audit-level=moderate`; do not force-fix breaking dependency changes without user approval.
   - Deploy with Vercel if requested.

## Caveats

- LinkedIn Jobs postings are not customer interviews.
- A hiring signal may imply a service business before it implies SaaS.
- Do not overclaim recency if LinkedIn omits posting dates; label the data as current/public job signals.
- Do not present generated competitor metrics, MRR, or demand as confirmed unless sourced.
- If production is Basic Auth protected, report deployment success separately from unauthenticated browser verification.

## Good output shape

For each selected idea, include:

- Persona and painful workflow
- Why the job cluster suggests budget urgency
- MVBP
- Mom Test questions
- Goodness score inputs and formula
- Data moat / proprietary advantage
- Human-in-the-loop approach
- Unit economics
- FAQ for skeptical investors
