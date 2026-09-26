---
name: implementation-package-execution
description: "Execute a user-delivered implementation package (zip archive + instruction markdown) against a GitHub repo: extract, secret-scan, apply docs bootstrap and/or code overlay per the plan's steps, re-validate in the live repo, open PR, honor human-review STOP gates, log to agents.md. Class-level workflow for 'unzip this and run the plan' handoffs (ACMS, llm-manager-project-framework, future frameworks)."
metadata:
  hermes:
    tags: [GitHub, Packages, Handoffs, PRs, Validation, agents-md]
    related_skills: [github-pr-workflow, deployed-service-capture, github-repo-management]
---

# Execute a Delivered Implementation Package (zip + instructions → GitHub)

Use when Jordan sends a zip (repo content / overlay trees) plus an instruction markdown ("UPLOAD_AND_EXECUTE_…", runbook, or plan) targeting a GitHub repo. The instruction file is the authoritative spec — follow its steps literally, **including its STOP/human-review gates** (e.g. "Do not merge PR-001 autonomously", "human must approve ADR-0007 before merge"). Two occurrences so far: LLM-Manager docs package and ACMS bootstrap + PR-001 (`startupteams/acms-project-framework`, 2026-09-25); both share the shape: one docs tree for `main`, one code overlay for a feature branch + PR.

## Workflow

1. **Extract & inventory.** `unzip` may not be installed — fall back to `python3 -c "import zipfile; zipfile.ZipFile(p).extractall(d)"`. List all files in every tree; read the instruction MD fully before acting.
2. **Secret scan the whole package BEFORE any commit** (same rule as `deployed-service-capture`): grep for `sk-[A-Za-z0-9_-]{8,}`, DSNs `://…@`, `ghp_`/`github_pat_`, private-key headers, password/api-key lines. Filter out legitimate prose/placeholders (`change-me`, `test-token`, `replace-with-…`, `os.environ`). Report clean/hits to Jordan.
3. **Check GitHub access + repo existence** (`gh auth status`, `git ls-remote`). If the target is under `startupteams` (or any org outside `jordatech`), get **explicit per-task authorization via clarify** before pushing — user-profile boundary. A direct-to-`main` bootstrap commit is allowed ONLY if the instruction file states it's human-authorized (one-time exception); all later feature work goes through branch + PR.
4. **Clone fresh** to `~/work/<repo>` (don't reuse stale clones). Apply each tree per the plan's `cp -a "<tree>/." "$REPO_DIR/"`, stage **only the file lists the plan specifies**, commit with the plan's message, push.
5. **Re-run validation in the live repo before opening the PR**, even if the plan says validation already passed on the prepared overlay. Match the project's `requires-python` (check `pyproject.toml`) — system python may be older; create a venv with the right interpreter (`/usr/bin/python3.12 -m venv .venv-<name>`), `pip install -e '.[dev]'`, run the test command from the plan.
6. **Artifact-cleanliness gate before staging** (see Pitfalls).
7. **Open the PR** with `gh pr create --body-file <package>/PR_BODY.md` — keep the PR body as a file in the extract dir, do NOT commit `PR_BODY.md` into the repo. Verify with `gh pr view <n> --json state,baseRefName,headRefName,additions,fileCount`.
8. **Stop at the plan's human gate.** Never self-merge. State clearly in the final reply which decision is waiting on Jordan (e.g. approve/modify a specific ADR).
9. **Log the milestone to `~/agents.md`** (repo, commits, PR link + number, gate status, any fixes made during execution, local paths) and update memory only with durable facts (repo authorization, clone location) — not PR numbers/commit SHAs as standalone memory entries; agents.md is the log.

## Continuing/revising an OPEN PR across sessions

When a plan says "revise the existing PR, do not open a new one" (e.g. the ACMS PR #1 async-stack revision after ADR-0007 acceptance):

1. Re-derive state from the live repo first: `git status`, `git log --oneline`, `gh pr view N --json state,updatedAt`, and re-read the plan's stop conditions. Prior-session work may sit uncommitted in the working tree — validate it, don't redo it.
2. Re-run the FULL validation suite in the live repo before committing (tests, stack-validation script, compile check, secret scan) — never trust the previous session's "it passed".
3. Commit as focused follow-up commits on the same branch (`feat(...)` / `test(...)` / `docs(...)` split), push, and **update the PR body** to reflect the revision (see pitfall below — `gh pr edit` fails silently on this). Merge stays a human action.
4. Write a new dated handoff doc in the repo (`docs/handoffs/<date>-<slug>.md`) with a validation table of exact executed commands + results, commit it on the branch, attach the path in the final reply.

## Pitfalls

- **`gh pr edit --body-file` silently fails on orgs with projects-classic**: errors with a "Projects (classic) is being deprecated" GraphQL message, exits non-zero, and the body is NOT updated. Use the REST fallback `gh api -X PATCH repos/OWNER/REPO/pulls/N --input -` (JSON `{"body": ...}` on stdin), then VERIFY with `gh pr view N --json body -q .body | grep -c "<unique-marker>"`.
- **`&&` chains abort on a no-match grep.** `grep -c pattern file && git add ...` returns rc=1 when the count is 0, silently skipping the rest of the chain (a commit+push never ran and looked "done"). Run commits/pushes as their own commands, or append `|| true` to informational greps.
- **Foreground terminal refuses inline scripts that spawn a server** ("appears to start a long-lived server/watch process") even when the script self-terminates. Write the script to a file (e.g. `scripts/validate_*.py`) and run it with `terminal(background=true, notify_on_complete=true)`; keep it printing a clear PASS line.
- **No Docker needed to validate a real PostgreSQL stack**: the `pgserver` dev extra runs embedded PostgreSQL 16 — `pgserver.get_server(dir, cleanup_mode="delete")` gives a URI for Alembic-upgrade-from-zero, uvicorn-subprocess HTTP checks, and after-exit durability queries. Recipe: `references/pg-stack-validation-no-docker.md`. Do NOT record "docker is unavailable" as an environment constraint; use this path.
- **Accidental branch creation from defensive commands**: a guard like `git checkout -b <branch>-tmp 2>/dev/null` succeeds and leaves you on the temp branch with the same content — verify `git branch --show-current` before committing, and delete stray temp branches.

- **Build artifacts sneak into `git add` of directories.** Running pytest/pip-install inside the repo creates `__pycache__/`, `*.egg-info/`, `.venv*/`, local `*.db`; `git add acms tests` sweeps the .pyc files in even when the plan lists exact paths. Before committing: `git status --short --ignored`, check `.gitignore` covers `__pycache__/`, `*.py[cod]`, `.venv*/`, `*.egg-info/`, `*.db`; extend it (with `patch`/append, never overwrite) or delete artifacts first. If a commit already caught them: `git rm -r --cached <dirs>` + extend `.gitignore` + follow-up `chore:` commit on the same PR branch (don't rewrite pushed history).
- **Instruction scripts assume `unzip`, a writable `$HOME/work`, and exact python availability** — substitute equivalents (python zipfile, explicit REPO_DIR, versioned interpreter + venv) rather than failing.
- **Plan file-lists omit generated files you create while validating** (venv, egg-info from `pip install -e`). If `gh pr create` warns "uncommitted change", check whether it's untracked local junk (gitignore it) vs. genuinely missing content.
- **Don't apply the whole package blindly at repo root** — the instruction MD itself and `PR_BODY.md` belong outside the tree (the plan's `git add` lists show exactly what enters the repo).
- Overlay trees may MODIFY files already on `main` (bootstrap case): `git status` after `cp -a` shows ` M` entries — that's expected; still stage only the plan's listed paths.

## Related

- `deployed-service-capture` — sibling direction (live VM → repo); shares the two-pass secret-scan rule and `references/secret-scan-patterns.md` patterns there.
- `github-pr-workflow` — generic PR lifecycle commands (gh and curl fallbacks).
- `github-repo-management` — clone/remote basics.
