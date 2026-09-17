---
name: fabric-pattern-authoring
description: "Use when creating or modifying Fabric patterns in the user's Fabric resource repository. Covers branch safety, pattern structure, extracting source context, writing system.md files, verification, and committing changes."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [fabric, patterns, prompt-engineering, repositories, authoring]
    related_skills: [github-pr-workflow, hermes-agent-skill-authoring]
---

# Fabric Pattern Authoring

## Overview

Use this skill when the user asks to create, generalize, edit, or commit Fabric patterns. Fabric patterns live in the `jordatech/Fabric` resource repository, usually under `data/patterns/<pattern_name>/system.md` with optional companion files such as `user.md` or `README.md`.

The preferred output is a reusable, class-level pattern that a human can run with Fabric against many inputs, not a narrow one-off transcript of a single source page.

## When to Use

- User asks to create "patterns in Fabric" or "general patterns".
- User provides source articles, Notion pages, examples, prompt libraries, or docs to turn into Fabric patterns.
- User asks to modify patterns in `jordatech/Fabric/data/patterns`.
- You need to capture reusable LLM prompt instructions as a Fabric `system.md`.

Do **not** use this for Hermes Agent skills unless the artifact belongs in `~/.hermes/skills` or a Hermes skills repo; use `hermes-agent-skill-authoring` for that.

## Repository and Branch Safety

1. Work only in the `jordatech/Fabric` repository unless the user explicitly authorizes another repository.
2. Locate the checked-out resource repository, commonly:
   ```bash
   /home/miam/.hermes/profiles/entrepreneur/resource_repositories/Fabric
   ```
3. Before editing, verify the active branch:
   ```bash
   git -C /path/to/Fabric status --short --branch
   git -C /path/to/Fabric branch --show-current
   ```
4. If it is not `c01entrepreneur_bot`, check out or create that branch before editing:
   ```bash
   git -C /path/to/Fabric checkout c01entrepreneur_bot || git -C /path/to/Fabric checkout -b c01entrepreneur_bot
   ```
5. For GitHub operations in this environment, use the real user HOME when auth is required:
   ```bash
   HOME=/home/miam git -C /path/to/Fabric push origin c01entrepreneur_bot
   ```

## Pattern Directory Shape

Typical pattern layout:

```text
data/patterns/<pattern_name>/
  system.md        # main Fabric instruction prompt
  user.md          # optional user-facing input wrapper
  README.md        # optional usage docs
```

Naming guidance:

- Use lowercase snake_case.
- Prefer verb-first names: `create_veo_video_prompt`, `summarize_customer_interviews`, `extract_market_signals`.
- Keep names general enough to be reused.
- Avoid dates, source-page titles that are too narrow, PR numbers, temporary campaign names, or exact error strings.

## Recommended `system.md` Structure

A strong Fabric pattern usually works well with these sections:

```markdown
# IDENTITY and PURPOSE

Who the model is and what it should accomplish.

# SOURCE INSPIRATION

Optional: concise summary of the external source, framework, or examples that informed the pattern.
Do not mirror full copyrighted/source content unless needed and allowed; generalize it.

# INPUT

What the user may provide and how to interpret incomplete inputs.

# PROCESS

Numbered reasoning/workflow steps the model should follow.

# OUTPUT FORMAT

Exact sections, schema, or formatting the model should return.

# TEMPLATES

Reusable prompt or output templates.

# EXAMPLES

Short examples that demonstrate the pattern.

# COMMON PITFALLS

Failure modes to avoid.
```

Not every pattern needs every section, but `IDENTITY and PURPOSE`, `INPUT`, `PROCESS`, and `OUTPUT FORMAT` are the minimum for a robust reusable pattern.

## Turning Source Material into a General Pattern

When given a source page or prompt library:

1. Fetch or inspect the source with tools rather than relying on memory.
2. Extract the reusable structures, formulas, prompt types, examples, constraints, and pitfalls.
3. Convert specific examples into generalized templates.
4. Keep brief attribution in `SOURCE INSPIRATION` when helpful.
5. Avoid producing a private mirror of the full source; the deliverable should be a distilled workflow.
6. Add common failure constraints that make the pattern safer and more useful.

## Notion Source Extraction

Public Notion pages can render only headings/toggles in the browser snapshot. If toggles are collapsed, fetch the Notion page data directly via `loadPageChunk` and recursively load child blocks.

See `references/notion-public-page-extraction.md` for a concise recipe.

## Agent Workspace Capture

If the user asks to "make skills" or store reusable process notes in the Agent Workspace repository, create a concise class-level note under the `jordatech/obsidian_vault_jordan_ulmer` resource repository rather than a narrow session log.

Common location for shared workflow notes:

```text
/home/miam/.hermes/profiles/entrepreneur/resource_repositories/obsidian_vault_jordan_ulmer/Agents/shared/<workflow_name>.md
```

Recommended note shape:

- Purpose / When to use
- Repository rules and paths
- Extraction or authoring workflow
- Category mapping or decision rules
- Verification checklist
- Common pitfalls

Commit and push the Agent Workspace repo separately on `c01entrepreneur_bot` if you edit it.

## Verification Workflow

After writing a pattern:

1. Read the file back to confirm it exists and starts with the expected sections:
   ```bash
   sed -n '1,80p' data/patterns/<pattern_name>/system.md
   ```
2. Check git status and diff/stat:
   ```bash
   git -C /path/to/Fabric status --short
   git -C /path/to/Fabric diff --stat
   ```
3. If the change is complete, commit with a concise message:
   ```bash
   git -C /path/to/Fabric add data/patterns/<pattern_name>/
   git -C /path/to/Fabric commit -m "Add <topic> Fabric pattern"
   ```
4. Push the branch:
   ```bash
   HOME=/home/miam git -C /path/to/Fabric push origin c01entrepreneur_bot
   ```
5. Verify clean state and latest commit:
   ```bash
   git -C /path/to/Fabric status --short --branch
   git -C /path/to/Fabric log -1 --oneline --decorate
   ```

## Common Pitfalls

1. **Editing the wrong repository or branch.** Always verify `jordatech/Fabric` and `c01entrepreneur_bot` before writing.

2. **Creating a one-session pattern.** If the pattern name only makes sense for today's source page, make it more general.

3. **Copying source examples without generalizing.** Fabric patterns should encode reusable method, not just paste a source prompt list.

4. **Leaving output unconstrained.** Include exact section names or schemas so Fabric users get predictable results.

5. **Forgetting to commit/push.** The user's entrepreneur workflow expects repository progress to be saved when reasonably required.

6. **Browser snapshot misses collapsed Notion toggle content.** Use Notion API `loadPageChunk` and recursively load child block IDs.

## Verification Checklist

- [ ] Repository is `jordatech/Fabric`.
- [ ] Active branch is `c01entrepreneur_bot`.
- [ ] Pattern is under `data/patterns/<general_name>/system.md`.
- [ ] Pattern name is reusable and class-level.
- [ ] `system.md` includes identity, input, process, output format, and pitfalls.
- [ ] Source material was distilled into templates and constraints.
- [ ] File was read back or otherwise verified.
- [ ] Git status/diff checked.
- [ ] Commit and push completed when the user asked for repository changes.
