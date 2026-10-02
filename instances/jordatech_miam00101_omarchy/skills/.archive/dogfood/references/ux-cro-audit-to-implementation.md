# UX/CRO audit-to-implementation notes

Use this reference when a user asks not only for a UX audit, but also for the site to be changed, committed, and deployed.

## Pattern from a successful session

1. Start with the live URL.
   - Try browser navigation first for real UX evidence.
   - If browser navigation fails, use `curl -I -L <url>` to distinguish app errors from access protection.
   - A Vercel response with `HTTP/2 401` and `www-authenticate: Basic realm=...` means the production site is password protected; do not treat that as an app regression.

2. Fall back to the repository/local app when production is protected.
   - Verify repo owner/branch before edits.
   - Run the app locally (`npm run dev`) and inspect with browser tools.
   - Keep the audit honest: state that production was protected and local app was used for implementation review.

3. For CRO/UX audits, produce findings in this shape:
   - Observation
   - UX principle / heuristic violated
   - Severity
   - Actionable recommendation
   - Implemented change, if the task includes editing the app

4. High-ROI changes for SaaS/founder-research dashboards:
   - Clarify the hero around the concrete job-to-be-done.
   - Collapse competing CTAs into one primary action.
   - Add examples near search inputs so users recognize valid queries.
   - Preserve filter/search state across filter links; clearing context unexpectedly is a high-severity UX bug.
   - Add visible result counts and active filter chips for system status.
   - Give clickable cards explicit CTAs such as `View brief →`.
   - Translate numeric scores into human labels, e.g. `Strong candidate`, `Worth interviewing`, `Needs sharper proof`.
   - Put the next concrete action before long-form content.
   - Add `:focus-visible` and accessible labels for search/filter controls.

5. Verify after implementation.
   - Run the build (`npm run build` for Next.js).
   - Re-open locally and inspect the DOM snapshot, visual screenshot, key interactions, and console errors.
   - Commit and push only after build and smoke test pass.

6. Deploying a Vercel-linked repo manually.
   - Confirm CLI auth with `HOME=/home/miam vercel whoami` when using Jordan/Hermes profile auth.
   - Deploy with `HOME=/home/miam vercel deploy --prod --yes` from the repo root.
   - Verify the deployment is ready and aliased with `HOME=/home/miam vercel inspect <deployment-url>`.
   - If the public alias remains Basic Auth protected, verify readiness via Vercel inspect and mention the 401 protection explicitly.

## Pitfalls

- Do not stop after writing an audit if the user asked to make the site easier to use. Implement the highest-ROI fixes.
- Do not ask clarifying questions when the user also asks for immediate implementation and the business context is inferable; state assumptions in the report and proceed.
- Do not mistake Vercel Basic Auth (`401`, `www-authenticate: Basic`) for a broken deployment.
- Do not let filter links rebuild a query from scratch unless clearing filters is the intended behavior.
