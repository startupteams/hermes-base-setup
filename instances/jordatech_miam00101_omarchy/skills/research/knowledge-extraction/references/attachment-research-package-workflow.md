# Attachment-Based Research Package Workflow

Use this when the user provides a document/archive (for example `message.txt` plus `attached.zip`) and asks for researched answers saved as markdown in a GitHub knowledge repository.

## Trigger

- User asks to read a prompt/document, extract an attached archive, perform research, and commit markdown answers.
- Source materials may include sensitive credentials or private business context.
- Deliverable is a reusable markdown research package, not just a chat answer.

## Workflow

1. **Load relevant skills first**
   - `knowledge-extraction` for extraction/documentation.
   - GitHub repo/PR skills when committing/pushing.
   - Any domain skill that governs the topic.

2. **Extract safely**
   - Use Python `zipfile` when `unzip` is unavailable.
   - Extract to `/tmp/<task_name>/extracted`, not directly into the repo.
   - Generate a file inventory and inspect headings before copying anything.

3. **Sanitize before committing**
   - Do not commit raw prompts if they include secrets.
   - Create a sanitized source-context file that records:
     - task summary,
     - attachment inventory,
     - headings/metadata,
     - explicit note that secrets were redacted.
   - Redact usernames/passwords/API keys/tokens as `[REDACTED]`.

4. **Parallelize bounded research**
   - For broad research tasks, delegate independent tracks in parallel:
     - provider/pricing/privacy research,
     - local model/server capacity research,
     - hardware/network procurement research.
   - Merge into a coherent package rather than dumping worker summaries verbatim.

5. **Write class-level package files**
   - `README.md` — executive recommendation and file map.
   - `00-source-context-sanitized.md` — safe source summary.
   - Topic-specific files, e.g. provider recommendations, capacity, hardware BOMs, networking, implementation plan.
   - `sources.md` — URLs, caveats, date checked.

6. **Verify before commit**
   - Run `git status --short --branch`.
   - Run a simple secret scan over generated markdown before staging/committing.
   - Count/list generated files for sanity.
   - Commit and push on the correct bot branch.

## Example secret scan snippet

```bash
python3 - <<'PY'
from pathlib import Path
import re
root = Path('servers_and_bots_for_startupteams')
patterns = [
    r'Password:\\s*(?!\\[REDACTED\\])\\S+',
    r'Username:\\s*(?!\\[REDACTED\\])\\S+',
    r'api[_-]?key\\s*[:=]\\s*[A-Za-z0-9_\\-]{16,}',
    r'token\\s*[:=]\\s*[A-Za-z0-9_\\-]{20,}',
]
found = []
for p in root.rglob('*.md'):
    txt = p.read_text(errors='replace')
    for pat in patterns:
        for m in re.finditer(pat, txt, re.I):
            found.append((str(p), pat, m.group(0)[:80]))
if found:
    for item in found:
        print('FOUND', item)
    raise SystemExit(1)
print('No obvious secrets found')
PY
```

## Pitfalls

- **Raw prompt leakage:** Do not commit complete prompts/documents if they contain credentials, even if the user gave them in chat.
- **Wrong branch:** Use the user-specified branch if explicitly provided; otherwise use the bot branch convention for the profile.
- **Narrow one-off docs:** Keep the package organized into durable topic files rather than a single transcript dump.
- **Marketplace price precision:** For hardware BOMs, mark prices as target ranges and caveat that live listings change/block automated access.
