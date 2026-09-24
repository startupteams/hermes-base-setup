# DE Canvas + OPMP Advisor Roundtable Workflow

Use this reference when Jordan asks to turn a rough venture idea, DE Canvas template, One-Page Marketing Plan template, framework dependencies, UX audit, or Drive folder into business-model documents.

## Trigger examples

- “Create/update a disciplined entrepreneurship canvas.xlsx” from a business idea and DE Canvas template.
- “Roleplay as Bill Aulet / Allan Dib / Giff Constable / Paul Cheek.”
- “Create an updated one page marketing plan.docx.”
- “Repeat the discussion process considering the UX Audit files.”
- “Create after UX Audit review disciplined entrepreneurship canvas.xlsx.”

## Class-level workflow

1. **Load the governing entrepreneurship skill first.** For this class, use `business-idea-systems` and follow DE / customer-discovery / skeptical-investor principles.
2. **Extract dependencies before drafting.**
   - Zip bundles may include markdown books, `.xlsx` canvas templates, `.docx` OPMP templates, PDFs, Google Docs exports, images, and Figma/design assets.
   - Preserve source traceability in a worksheet or markdown record.
3. **Inspect the spreadsheet/doc templates structurally.**
   - For `.xlsx`, use `openpyxl` to list sheets, merged ranges, and populated cells before editing.
   - For `.docx`, use `python-docx` if available; otherwise create a new valid Word document rather than hand-editing XML unless necessary.
4. **Create an advisor role sheet / section when requested.**
   - Bill Aulet: beachhead discipline, 24-step sequence, persona, MVBP, TAM caution, quantified value proposition, long-term viability.
   - Allan Dib: target market, message, media, lead capture, nurture, conversion, world-class experience, LTV, referrals.
   - Giff Constable: assumptions, past behavior, evidence quality, failure points, practical experiments.
   - Paul Cheek: tactical prioritization, feasibility tools, data capture, experiment operations, sprintable implementation.
5. **Simulate the staged roundtable explicitly.**
   - Stage 1: enumerate break-the-business hypotheses.
   - Stage 2: use accessible online/source evidence and supplied docs to pressure-test each hypothesis; label what is only directional evidence.
   - Stage 3: debate pivots and strategic changes.
   - Repeat for the requested number of rounds; include critique/counterarguments, not just parallel monologues.
6. **Generate durable artifacts, not only chat summaries.** Typical outputs:
   - Updated / recommended DE Canvas `.xlsx`.
   - Updated / recommended OPMP `.docx`.
   - Market hypotheses/testing strategy `.docx`.
   - Markdown meeting/advice decision record.
   - If UX audit is included, an evidence-map worksheet linking UX findings to canvas changes.
7. **Verify every artifact.**
   - Reopen `.xlsx` with `openpyxl`, assert key cells/sheets exist and are populated.
   - Use `file` or equivalent to confirm `.docx` / `.xlsx` types.
   - Report actual file paths with MEDIA links.

## Google Drive UX Audit pattern

When the user provides a Google Drive folder:

1. Use the Google Workspace skill and check auth first.
2. List children with the folder ID.
3. Recurse into subfolders.
4. Resolve Google Drive shortcuts via `shortcutDetails.targetId`; the visible file may be a shortcut, not the real document.
5. Export Google Docs to text/plain; Sheets to CSV; Slides to text/plain or PDF; download binary PDFs/images/assets directly.
6. For PDFs, extract text with `pypdf`/`pdftotext` where possible. Some design PDFs are image-only; if text extraction is empty, still include the filename in traceability and rely on text-based audit docs unless visual analysis is specifically required.
7. For UX audit deliverables, prioritize strategic text sources such as:
   - UI/UX audit reports
   - rebranding / positioning frameworks
   - implementation checklists
   - meeting notes
   - action item documents
   - initial problem statements
   - deliverables maps
8. Add an `UX Audit Evidence Map` sheet: source file, finding used, canvas impact.

## AgentifyMe-specific strategic lessons from the UX-audit workflow

For AgentifyMe, the UX audit changed the canvas emphasis from a broad “managed AI agents” story to:

- **Managed AI Operations for Real-Estate Teams**.
- Primary CTA: **Book a Brokerage AI Audit**.
- Product modules: Recruiting Agent, Onboarding Agent, Broker Desk, Performance Reporting.
- Funnel: Hero → proof strip → use-case cards → how it works → human handoff & safety → pricing/starting packages → customer proof → audit CTA.
- Packaging: Audit → Pilot → Managed Monthly; avoid vague custom pricing and confusing task-based pricing.
- Trust system: human-reviewed handoffs, approval gates, clear scope, incident logs, and monthly ROI reporting.
- Validation: 5-second clarity tests, first-click/CTA tests, paid audit conversion, artifact-sharing rate, demo comprehension, pilot economics.

## Pitfalls

- Do not treat a UX audit as market validation. It is strong source intelligence and hypothesis generation, but payment, artifact sharing, and observed buyer behavior remain the validation bar.
- Do not preserve two beachheads in customer-facing copy if the audit says target clarity is weak. Keep secondary beachheads internal until the first motion works.
- Do not lead with generic “AI-as-a-Service” or model/infrastructure claims. Lead with the buyer’s workflow outcome.
- Do not create broad freemium offers for a managed-service business unless the user explicitly requests it; freemium can fight scope discipline. Prefer paid audit / pilot gates.
- Do not let visuals/brand assets become cosmetic only. Tie UX changes to measurable acquisition/conversion assumptions.
