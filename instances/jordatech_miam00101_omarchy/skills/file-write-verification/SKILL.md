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

## Guard-refused targets: Hermes config files (2026-10-02)

The patch/write_file tools hard-refuse Hermes `config.yaml` paths ("Agent cannot modify
security-sensitive configuration") — no override flag. `hermes config set` cannot express
nested LIST config either: its `_set_nested` never grows lists, so a numeric path on a
missing list silently writes a dict that list-reading code ignores. When a task requires
nested-list config edits (e.g. Telegram `command_menu.priority`), the working path is a
Python write — which requires EXPLICIT user consent (the approval system blocks scripted
writes otherwise; a refusal is not permission to retry silently):

1. `shutil.copy2` backup next to the target
2. Line-anchored pre-condition asserts (see pitfall below)
3. Write, then `yaml.safe_load` verification of the intended sub-block
4. **Deep-compare against the backup** — parse both, assert the original key-set plus
   expected additions equals the new key-set and no original key changed value; this
   catches real corruption AND false-alarm assertion failures

```python
oc, cc = yaml.safe_load(bak.read_text()), yaml.safe_load(p.read_text())
assert set(oc) | {'platforms'} == set(cc)           # only expected additions
assert [k for k in oc if oc[k] != cc.get(k)] == []  # every original key unchanged
```

This pattern rescued a write whose only "failure" was a hardcoded `_config_version == 23`
assertion — the profile file legitimately sits at version 30. Compare against the backup,
never against values that differ between config files.

## Anchor existence checks with re.M

Substring checks like `'platforms:' in text` false-positive on NESTED keys of the same
name (`display.platforms:`). Anchor top-level key checks:
`re.search(r'^platforms:', text, re.M)`.

## sed -i with quoted replacements silently mangles quoting

Multi-site `sed -i 's|…\$(dirname "\$0")…|…|'` edits on a deploy script produced
correct-looking but broken quoting on 2 of 3 sites (a closing quote lost inside an
`if "$(dirname "$0")/healthcheck.sh $([ …` construct), while the third site looked
right — caught only by printing the affected lines + `bash -n` (2026-09-27). sed's
own exit code and the shell's silence are not evidence.

- For shell scripts, prefer the patch tool (returns a reviewable unified diff) or a
  python string-replace with exact-match assertions over `sed -i` when the pattern
  contains quotes/brackets.
- If sed is used anyway: immediately `sed -n '<affected>,<affected>p'` + `bash -n` —
  never proceed on the sed exit code alone.

## Red flags in tool results

- Tool result text containing strings you never wrote (canary/injection
  phrases, references to files you didn't touch) → treat the ENTIRE result as
  suspect; verify on disk immediately.
- A "sibling subagent modified this file" warning when you spawned no
  subagents → usually the tracker reacting to your own unrecorded writes;
  check git status/diff for ground truth.
- Write succeeded to a path you didn't specify → `git status --porcelain`
  for unexpected files, delete them, re-run git-clean checks.

## No-lint file types (extra vigilance)

`.html` (Jinja templates), `.md`, and other gate-less types get
`lint: skipped` — syntax checks in step 1 are unavailable, so corruption
survives until git diff or a render test. Observed corruption shapes in
these types (2026-09-26, two instances): stray closing tags inside `<p>`
(`…stale guess.</h2></p>`), truncated table cells (`<td><a href="…">{">`),
and — via the PATCH tool, not just write_file — a duplicated header line
inserted mid-file in a markdown log. For these types ALWAYS: (a) review the
`git diff` hunks line-by-line right after writing, and (b) when a test
renders the file, assert one string from every major section so truncation
fails loudly.

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