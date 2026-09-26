---
name: file-write-verification
description: "Verify every file write/patch against ground truth (git diff, ast.parse, py_compile, bash -n, git checkout to recover) — never trust the tool echo or lint status alone; repair pattern for mid-write content corruption; when to prefer patch-tool edits over full rewrites."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# File-Write Verification Discipline

Class-level rule for any session that writes or edits files via tool calls.

## Why

In one session the write channel corrupted content mid-write 5+ times:
phantom text injected into file contents and into tool-result echoes, writes
truncated mid-content, and one malformed call writing to a garbage path
(`/home/jordatech/work adversely/...`). The tool's own success echo and lint
status both reported "ok" on corrupted files. The corruption was invisible
until verified against independent ground truth.

## The rule

**Never trust the write tool's echo or its lint verdict alone.** After every
write/patch of a file that matters:

1. **Verify syntax/structure independently:**
   - Python: `python3 -m py_compile <f>` or `python3 -c "import ast; ast.parse(open('<f>').read())"`
   - Shell: `bash -n <f>`
   - YAML/TOML/JSON: parse it
   - Expected size: sanity-check byte/line count against what you intended
2. **Verify content against git:** `git diff <f>` is the authoritative record
   of what actually landed. Review the diff before staging.
3. **Never run repair loops against echo.** Re-read the file (read_file or
   git diff) before any fix; assert pre-conditions before surgical edits.
4. **Prefer patch-tool edits over full rewrites** for existing files — smaller
   diff surface, independently verified by the fuzzy-match result.
5. **Use git to recover:** `git checkout -- <f>` restores a known-good state
   when a write mangles a tracked file; then re-apply changes as small patches.

## Repair pattern (Python, for surgical fixes with pre-checks)

```python
from pathlib import Path
p = Path("path/to/file")
lines = p.read_text().splitlines()
# ASSERT pre-conditions before touching anything — abort on surprise
assert lines[74] == "expected exact line", lines[74]
del lines[179:181]  # drop duplicated fragment
p.write_text("\n".join(lines) + "\n")
```

## Red flags in tool results

- Tool result text containing strings you never wrote (canary/injection
  phrases, references to files you didn't touch) → treat the ENTIRE result as
  suspect; verify on disk immediately.
- A "sibling subagent modified this file" warning when you spawned no
  subagents → usually the tracker reacting to your own unrecorded writes;
  check git status/diff for ground truth.
- Write succeeded to a path you didn't specify → `git status --porcelain`
  for unexpected files, delete them, re-run git-clean checks.

## When verification found corruption (repair order)

1. `git checkout -- <file>` (if tracked and pre-write state is good)
2. Re-apply intended change via patch tool (small, verifiable diffs)
3. For untracked new files: python re-write with assertion pre-checks
4. Re-verify: syntax check + git diff review + (for Python) import test

## Non-durable failures (do NOT capture as rules)

Missing binaries, path mismatches after migration, transient tool outages
that resolved in-session — these are environment state, not discipline. The
durable lesson is the verify-against-ground-truth pattern, not "the tool is
broken".