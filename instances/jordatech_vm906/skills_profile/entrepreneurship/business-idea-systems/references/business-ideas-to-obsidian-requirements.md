# Business ideas to Obsidian requirements template

Use this when Jordan asks to convert business ideas into requirements/test cases or to prepare an Obsidian requirements-management vault for LLM use.

## Repository pattern

- Requirements template repo: `jordatech/requirements_management_obsidian`.
- Work on a purpose branch such as `template` for generalized template edits.
- Do not edit `.obsidian/` unless the user explicitly asks for Obsidian settings/plugin changes.
- Preserve existing filenames when instructed. In the requirements template, this means keeping:
  - `1 SYS-REQ/SYS-REQ-001-PROJ_NAME.md`
  - `1 SYS-TC/SYS-TC-001-PROJ_NAME.md`
  - `2 SW-REQ/SW-REQ-001-PROJ_NAME.md`
  - `2 SW-TC/SW-TC-001-PROJ_NAME.md`
- Preserve exact note names inside Obsidian wikilinks `[[...]]` when the user says not to change text references to filenames.

## Template generalization approach

Replace overly specific product examples with generic LLM-friendly examples while keeping traceability:

- System requirement: target user completes the primary business workflow and gets a verifiable output.
- Software requirement: app stores a workflow record with ID, actor, UTC timestamp, payload, validation status, output reference, and traceability metadata.
- System test case: user completes the workflow end-to-end with valid and invalid data.
- Software test case: stored record has required fields, valid timestamp/status formats, retrieval by ID, and traceability.

Keep authoring notes short and operational: atomic requirements, shall-language, one actor/action/outcome, and do-not-rename-link reminders.

## Portfolio examples

When adding examples for each idea in `business_ideas`:

1. Read `ideas.json` from `jordatech/business_ideas` as the index.
2. For each idea, generate a concise block with:
   - product slug
   - template wikilinks
   - persona
   - pain to verify
   - example system requirement
   - example software requirement
   - example system test case
   - example software test case
3. Keep examples reusable rather than overfitting to implementation details.
4. If adding a new business idea in the same session, update the requirements examples after updating `ideas.json` so the count and examples include the new idea.

## Two-repo sync + viewer publication pattern

When the user wants the examples available in both the source ideas repo and the deployed viewer app:

1. Fetch or read `BUSINESS_IDEA_REQUIREMENT_EXAMPLES.md` from `jordatech/requirements_management_obsidian` on the intended template branch.
2. Copy it into `jordatech/business_ideas/BUSINESS_IDEA_REQUIREMENT_EXAMPLES.md`.
3. Copy it into `jordatech/business_idea_generator/data/BUSINESS_IDEA_REQUIREMENT_EXAMPLES.md` so the viewer has a checked-in snapshot.
4. Update both READMEs so humans can discover the file/route.
5. Add a Next.js page such as `app/requirements-examples/page.tsx` that reads the checked-in markdown from `data/`, renders it with the same remark/html pipeline used for idea briefs, and links back to the dashboard.
6. Add navigation links from the dashboard and standalone brief page to `/requirements-examples`.
7. Run JSON validation for the source/viewer idea indexes, run `npm run build`, deploy to Vercel if requested, and verify the protected alias with `curl -I` expecting `401` on both `/` and `/requirements-examples` when Basic Auth is enabled.

This pattern keeps the canonical source in the requirements template repo while making the examples visible in both the markdown repo and the founder-facing viewer app.

## Verification

Run these checks before commit:

```bash
git diff --name-only -- .obsidian | wc -l   # should be 0 unless explicitly editing settings
python3 -m json.tool /home/miam/jordatech/business_ideas/ideas.json >/tmp/ideas.valid
python3 -m json.tool /home/miam/jordatech/business_idea_generator/data/ideas.json >/tmp/viewer.valid
```

If syncing the viewer, also run `npm run build` in `business_idea_generator` and verify the private Vercel deployment with `curl -I` expecting `401` when Basic Auth is active.
