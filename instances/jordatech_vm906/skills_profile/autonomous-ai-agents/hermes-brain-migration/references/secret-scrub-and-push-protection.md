# Secrets scrubbing + GitHub Push Protection playbook

Condensed from the 2026-09-24 incident (22 real-secret locations caught in conversation
exports). Core lesson: **treat regex self-scans as a first filter only — GitHub Push
Protection is the authoritative backstop, and its rejections are free findings.**

## Scrub patterns (proven needed for chat/conversation exports)

```python
SECRET_SUBS = [
    (re.compile(r'sk-[A-Za-z0-9_\-]{20,}'), 'sk-***REDACTED***'),
    (re.compile(r'ghp_[A-Za-z0-9]{30,}'),   'ghp_***REDACTED***'),
    (re.compile(r'gho_[A-Za-z0-9]{30,}'),   'gho_***REDACTED***'),
    (re.compile(r'github_pat_[A-Za-z0-9_]{20,}'), 'github_pat_***REDACTED***'),
    (re.compile(r'xox[bpars]-[A-Za-z0-9\-]{10,}'), 'xox-***REDACTED***'),
    (re.compile(r'AKIA[0-9A-Z]{16}'),       'AKIA***REDACTED***'),
    (re.compile(r'Bearer [A-Za-z0-9_\-\.]{25,}'), 'Bearer ***REDACTED***'),
    # caught by Push Protection in real exports:
    (re.compile(r'vck_[A-Za-z0-9]{20,}'),   'vck_***REDACTED***'),   # Vercel token
    (re.compile(r'vcp_[A-Za-z0-9]{20,}'),   'vcp_***REDACTED***'),   # Vercel PAT variant
    (re.compile(r'VERCEL_TOKEN[="\\s]+[A-Za-z0-9]{20,}'), 'VERCEL_TOKEN=***REDACTED***'),
    (re.compile(r'[0-9]{10,}[a-z0-9_\-]*\.apps\.googleusercontent\.com'),
     '***REDACTED***.apps.googleusercontent.com'),                    # OAuth client ID
    (re.compile(r'GOCSPX-[A-Za-z0-9_\-]{5,}'), 'GOCSPX-***REDACTED***'),
    (re.compile(r'"token"\s*:\s*"[A-Za-z0-9_\-]{20,}"'), '"token": "***REDACTED***"'),
]
```

Do NOT add a bare `[A-Za-z0-9]{24,40}` catch-all — it mangles legitimate content
(base64, hashes, URLs). Prefix-anchored patterns + Push Protection beats carpet-bombing.

## Verification scan (post-scrub, before any push)

- Scan all text in the export tree for the patterns above + `-----BEGIN [A-Z ]*PRIVATE
  KEY-----` with >200 base64 chars between BEGIN/END (doc-text mentions of "BEGIN
  PRIVATE KEY" without a body are benign).
- Investigate every hit in context; clear false positives explicitly in your notes.

## When Push Protection rejects a push

1. Parse the rejection: `git push 2>&1 | grep -E "—— .*——"` lists secret types;
   `grep -E "path: |commit: "` lists file:line + offending commit.
2. Expect iteration: fixing one class (e.g. `vck_`) can reveal a sibling class
   (`vcp_`) on the next push. Loop until clean.
3. Scrub at SOURCE (the exporter), not by rewriting files in the repo copy.
4. **Rebuild the branch from main** — GitHub scans every commit in the push, so a
   dirty ancestor in history still trips protection even if HEAD is clean:
   ```bash
   git switch main
   git branch -D <branch>
   git switch -c <branch>
   # re-apply .gitignore/instance content, verify scrub, stage, commit, push
   ```
5. Never use the allowlist URL unless the "secret" is provably a test fixture — and
   then only after user authorization.

## Context: where the real secrets were hiding

Not in configs or env — in **old session tool output** (pasted config files,
`export VERCEL_TOKEN=…` command output, `cat ~/.vercel/token` results) exported from
state.db `messages` rows. Any pipeline that exports conversation history for sharing
must scrub at export time. Recommend rotating any token that ever landed in an export.
