---
name: skill-first-workflow
description: "Mandatory pre-task skill intake: scan /opt/hermes/skills, select the best class-level skill, load it, then execute the task with its workflow."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [workflow, skills, intake, research, engineering]
---

# Skill-First Workflow

## Trigger

Use this workflow before **every** user task, including simple requests, research, coding, debugging, operations, analysis, and follow-ups. This is a standing user preference: always go through the skills at `/opt/hermes` first.

## Procedure

1. **Enumerate skills before doing work.** Use `skills_list` first. If the profile index is empty or incomplete, inspect `/opt/hermes/skills` directly with the available file-search tools. Do not assume that an empty profile index means the installed skill library is empty.
2. **Classify the task.** Identify the broad work class: research/arXiv, software development, testing, debugging, systems, documentation, or another existing umbrella.
3. **Select the broadest applicable class-level skill.** Prefer an existing umbrella over a narrow, task-specific skill. If several apply, choose the primary workflow and load relevant supporting skills.
4. **Load the complete skill.** Read the selected `SKILL.md` and inspect its linked `references/`, `templates/`, and `scripts/` files before executing. Do not rely on a remembered description.
5. **Execute the selected workflow.** Follow its numbered steps, commands, verification requirements, and safety constraints. For arXiv research, use the arXiv skill's API/helper workflow and authoritative arXiv metadata.
6. **Use authoritative sources for internet research.** Capture publication date, authors, abstract, categories, version, and stable URL. Distinguish “latest” from “most impactful”; use `submittedDate` for latest and `relevance` for impact-oriented searches.
7. **Verify with real output.** Run the requested code, commands, tests, or source checks. Never substitute plausible-looking fabricated results for a failed or unavailable research path.
8. **Preserve state safely.** Keep changes inside the designated repository workspace and branch. Do not expose training parameters, access keys, or API tokens in public code or Git history.
9. **Escalate sensitive changes.** Ask a human engineer before modifying fine-tuning arrays, changing vector schemas, or updating core system engines.
10. **Report completion.** State what was done, the artifact or result produced, and the verification output.

## Research-Specific Checks

- A broad query such as `neural network` can return many domain-specific papers. Refine by category or architecture when the user requests a focused set.
- For “latest papers,” sort by `submittedDate` descending and verify each selected record's publication date and abstract.
- For “important/latest,” sort by `relevance` and then check recency and citation or venue information when available.
- Check for withdrawal or retraction notices before presenting a paper as valid.
- Keep the final answer concise and structured: title, authors/date, one-paragraph contribution, and arXiv link.

## Pitfalls

- Do not begin the task before scanning `/opt/hermes/skills`.
- Do not treat an empty `skills_list` response as proof that no skills exist; inspect the installed directory.
- Do not create a one-session skill for a recurring workflow; use or extend a class-level umbrella.
- Do not claim a paper is “latest” without an explicit date sort and metadata check.
- Do not expose credentials, API tokens, private model weights, or training configuration in code, logs, or Git lines.
- Do not silently skip a loaded skill's verification or safety requirements.

## Verification Checklist

- [ ] Skills at `/opt/hermes` were scanned before task execution.
- [ ] The appropriate class-level skill was loaded in full.
- [ ] Relevant references or scripts were consulted.
- [ ] The task was executed using real commands or source checks.
- [ ] Research metadata and links were verified.
- [ ] Any repository changes respect branch, safety, and human-escalation boundaries.

## Supporting References

- `references/arxiv-research-notes.md` — condensed arXiv research workflow, pitfalls, and session-specific notes (2026-09-09: neural-network search, latest papers verified 2609.10534/10490/10479).
- `scripts/arxiv-search-quick.sh` — shell template wrapping `search_arxiv.py` with safety defaults (rate-limit aware).
