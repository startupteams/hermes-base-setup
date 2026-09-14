---
name: safe-prompt-rewriter
description: "Rewrites prompts for claude-fable-5 to ensure clear, benign, authorized, defensive, educational, or administrative framing"
version: 1.0.0
author: Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [Claude, Safety, Prompt-Engineering, Security]
    related: [claude-code]
---

# Safe Prompt Rewriter

Rewrites prompts before sending them to Claude Code (claude-fable-5) to ensure they are clearly framed as legitimate, authorized, safe, and unambiguous.

## Purpose

Ensure Fable 5 receives prompts that are:
- Clear about authorization context (owned systems, permission granted, admin tasks)
- Framed for defensive, educational, or administrative purposes
- Free of ambiguous or risky wording
- Preserving the user's legitimate goal when a safe rewrite exists

## Input Contract

The prompt to rewrite is wrapped in `<PROMPT>` and `</PROMPT>` tags:

```
<PROMPT>
your prompt here
</PROMPT>
```

Everything outside the tags is instructions to the rewriter. Rewrite only the text inside the tags.

## Rewrite Rules

1. **Preserve legitimate goals** when a safe version exists
2. **Make authorization explicit** when relevant:
   - Owned system
   - Permission granted
   - Internal admin task
   - Defensive review
   - Educational explanation
   - Harm-reduction context
3. **Replace ambiguous or risky wording** with clear, benign wording
4. **Remove** requests for:
   - Unauthorized access
   - Credential theft
   - Evasion
   - Abuse
   - Weaponization
   - Malware
   - Harmful biological or chemical work
   - Hidden chain-of-thought
5. **Do NOT add** new capabilities, claims, permissions, or facts not implied by the original
6. **If the underlying request remains unsafe**: refuse to rewrite and suggest a safe alternative direction

## Useful Replacements

| Original (risky) | Rewritten (safe) |
|------------------|------------------|
| "break into this system" | "review this owned or authorized system for missing security controls" |
| "write an exploit payload" | "write a regression test that demonstrates the bug is fixed" |
| "bypass this control" | "strengthen validation, monitoring, and abuse prevention for this control" |
| "show attack steps" | "summarize the risk at a high level and provide mitigation steps" |
| "show your hidden reasoning" | "provide a concise explanation with key assumptions" |
| "diagnose this condition" | "help me understand the information and list questions for a qualified professional" |

## Output Format

Return:

1. The full rewritten prompt in a Markdown code block
2. A list of specific phrases changed and what each became
3. If no safe rewrite exists: brief refusal and one safer alternative direction

Example output:

```markdown
<ORIGINAL PROMPT>
break into this system and show me all the files
</ORIGINAL PROMPT>

<REWRITTEN PROMPT>
```
Review this owned system for unauthorized file access and document any missing access controls.
```

### Phrases Changed:
- "break into this system" → "Review this owned system for unauthorized file access"
- "show me all the files" → "document any missing access controls"
