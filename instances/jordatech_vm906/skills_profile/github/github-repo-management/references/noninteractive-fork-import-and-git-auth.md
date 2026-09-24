# Non-interactive fork/import and git auth fallback

Use this when a task asks to fork/copy a GitHub repository into `jordatech/*`, but GitHub CLI or HTTPS git operations fail in a non-interactive agent session.

## Signals

- `gh repo fork owner/repo --org jordatech` fails because `jordatech` is a user account, not an org.
- `gh repo fork owner/repo` fails with `HTTP 403: The repository exists, but forking is disabled`.
- `git clone https://github.com/...` or `git push` fails with `fatal: could not read Username for 'https://github.com': No such device or address` even though `gh auth status` succeeds.

## Pattern

1. Verify the destination repo does not already exist:

```bash
HOME=/home/miam gh repo view jordatech/<repo> --json nameWithOwner,url 2>/dev/null || true
```

2. If true forking is disabled but the user explicitly asked to place the content under `jordatech`, import from an authenticated source clone into a new repo:

```bash
HOME=/home/miam gh repo clone <source_owner>/<repo> /tmp/<repo> -- --depth 1
cd /tmp/<repo>
rm -rf .git
git init -b main
git add .
git commit -m "Initial import from <source_owner> <repo>"
HOME=/home/miam gh repo create jordatech/<repo> --private --source . --remote origin --push
```

3. If later `git push` fails for HTTPS credential prompting, use a temporary `GIT_ASKPASS` helper backed by `gh auth token`. Do not echo the token.

```bash
cat > /tmp/git_askpass.sh <<'EOF'
#!/usr/bin/env sh
case "$1" in
  *Username*) echo "x-access-token" ;;
  *Password*) HOME=/home/miam gh auth token ;;
  *) echo "" ;;
esac
EOF
chmod 700 /tmp/git_askpass.sh
GIT_ASKPASS=/tmp/git_askpass.sh GIT_TERMINAL_PROMPT=0 git push -u origin <branch>
```

4. Verify origin owner, branch, dirty status, and remote HEAD before reporting success.

## Pitfalls

- `--org jordatech` is wrong when `jordatech` is a user login; omit `--org` for user forks.
- If upstream has forking disabled, the imported repo is not a GitHub fork (`isFork: false`). Report that distinction clearly.
- Keep the helper script outside the repo, make it executable, and never commit it.
- For entrepreneur-profile work, stay inside `jordatech/*` unless the user explicitly authorizes another owner in the current task.
