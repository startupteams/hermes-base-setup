# First 10 Clients Prospect Lists

Use this reference when adding outbound/customer-discovery targets to business idea briefs.

## Pattern

Add a section near the top of each idea, usually after `## Next actions`:

```markdown
## First 10 clients

Use this as a first outbound/account-research list. These are hypotheses about likely buyer pain, not validation; confirm the need with direct customer discovery before pitching.

1. **[Prospect name](https://example.com/about)**
   - **Specific need:** Why this exact organization/community likely has the pain described in the brief.
   - **How to contact:** Start with [public contact path](https://example.com/contact); ask for the owner of the workflow named in this brief.
```

Acceptable prospect types:

- buyer organizations
- communities with concentrated target users
- accelerators/associations/partner programs
- vendors/platforms that could be design partners or channel partners
- public marketplaces/directories with obvious workflow ownership

## Quality Bar

Each entry must be specific enough that a founder can take action without another research pass:

- Link to an about, product, community, or organization page.
- Name the workflow or business consequence that creates the need.
- Use a public contact path, demo form, partnership page, community route, or support path.
- Do not include private/personal emails unless the organization clearly publishes them for that purpose.
- Do not present prospects as validated customers. Phrase them as hypotheses for outreach or interviews.

## Validation

The skill includes `scripts/validate_first_10_clients.py` to check source and viewer snapshots:

```bash
python /home/miam/.hermes/profiles/entrepreneur/skills/entrepreneurship/business-idea-systems/scripts/validate_first_10_clients.py \
  /home/miam/.hermes/profiles/entrepreneur/resource_repositories/business_ideas/ideas

python /home/miam/.hermes/profiles/entrepreneur/skills/entrepreneurship/business-idea-systems/scripts/validate_first_10_clients.py \
  /home/miam/.hermes/profiles/entrepreneur/resource_repositories/business_idea_generator/data/ideas
```

Run this before committing source and viewer snapshot changes.

## Sync reminder

For Jordan's current business idea system:

1. Update canonical Markdown in `business_ideas/ideas/*.md`.
2. Copy changed Markdown to `business_idea_generator/data/ideas/*.md`.
3. Validate both directories with the script above.
4. Run the viewer build.
5. Commit/push source and viewer separately.
6. Deploy and verify Vercel production; unauthenticated `401` can be expected when Basic Auth is enabled.
