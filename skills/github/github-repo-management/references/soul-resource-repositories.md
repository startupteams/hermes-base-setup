# SOUL.md Resource Repository Checkout Workflow

Use this when a Hermes profile SOUL.md / agent identity file lists resource repositories that the agent should consult or edit.

## Trigger

- User says the soul file was updated and asks to explore it.
- User asks to check out resource repositories referenced by an agent profile / SOUL.md.
- The profile includes a bot name and repository boundaries such as `github.com/jordatech` and a required working branch.

## Workflow

1. Locate the active profile's SOUL.md. Common path:
   - `~/.hermes/profiles/<profile>/SOUL.md`
   - In this session: `/home/miam/.hermes/profiles/entrepreneur/SOUL.md`
2. Read the SOUL.md and extract:
   - bot name, usually the branch name for edits
   - repository URLs
   - allowed GitHub owner/org boundaries
   - ask-first / never-do rules
3. Create a stable local workspace under the profile, for example:
   - `~/.hermes/profiles/<profile>/resource_repositories/`
4. Configure the Git identity if the SOUL.md specifies one.
5. For each referenced `https://github.com/<owner>/<repo>` URL:
   - Ensure the owner/org complies with the SOUL.md boundary. If not, ask before forking.
   - Convert `/tree/<branch>/<path>` URLs into clone URLs: `https://github.com/<owner>/<repo>.git`.
   - Clone or fetch the repo.
   - Check out the bot branch if `origin/<bot_name>` exists.
   - Otherwise create local branch `<bot_name>` from the default remote branch.
6. Verify each checkout:
   - path
   - origin URL
   - current branch
   - upstream branch
   - HEAD SHA
   - dirty status
7. If a repo returns GitHub API `404` or HTTPS clone requests credentials, check whether the active Hermes profile `HOME` differs from the real user home before concluding auth/access is missing. Auth created by a human/admin agent may be in `/home/<user>/.config/gh`, `/home/<user>/.git-credentials`, or `/home/<user>/.ssh` while the agent is running with `HOME=~/.hermes/profiles/<profile>/home`.
8. If real-home auth works, use `HOME=/home/<user>` (or `GH_CONFIG_DIR=/home/<user>/.config/gh` for gh) for clone/fetch operations. If both profile-home and real-home auth fail, report GitHub auth/access is needed rather than inventing an alternate source.

## Shell Pattern

```bash
WORK="$HOME/.hermes/profiles/<profile>/resource_repositories"
BRANCH="<bot_name>"
mkdir -p "$WORK"

git config --global user.email "<email-from-soul>"
git config --global user.name "<name-from-soul>"

clone_or_update() {
  repo_name="$1"
  repo_url="$2"
  dest="$WORK/$repo_name"

  if [ -d "$dest/.git" ]; then
    git -C "$dest" fetch --all --prune
  else
    git clone "$repo_url" "$dest"
    git -C "$dest" fetch --all --prune || true
  fi

  if git -C "$dest" show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
    git -C "$dest" checkout -B "$BRANCH" "origin/$BRANCH"
  else
    default_ref=$(git -C "$dest" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
    default_branch=${default_ref#origin/}
    if [ -z "$default_branch" ] || [ "$default_branch" = "$default_ref" ]; then
      default_branch=$(git -C "$dest" remote show origin | sed -n 's/.*HEAD branch: //p' | head -1)
    fi
    default_branch=${default_branch:-main}
    git -C "$dest" checkout -B "$BRANCH" "origin/$default_branch"
  fi

  printf '%s | %s | %s | %s\n' \
    "$dest" \
    "$(git -C "$dest" branch --show-current)" \
    "$(git -C "$dest" rev-parse --short HEAD)" \
    "$(git -C "$dest" remote get-url origin)"
}
```

## Pitfalls

- `set -u` plus variable names like `name` in wrapper shells can fail unexpectedly if surrounding tooling expands variables; quote carefully or run the script in a clean shell.
- Public GitHub API `404` for `repos/<owner>/<repo>` often means private repo or missing auth, not necessarily that the repo name is wrong.
- `gh auth status` can be unauthenticated under the Hermes profile `HOME` even when auth exists in the real user home. If the user says auth is configured, inspect `/home/$USER/.config/gh/hosts.yml` and try `HOME=/home/$USER git ...` before asking them to log in again.
- Avoid committing or pushing simply because the SOUL.md says to save progress; only commit when there are meaningful edits and no secrets.
- When the user asks to make the active profile `SOUL.md` match an upstream agent identity file, preserve exact source bytes. Do not trim trailing spaces or blank lines with `.rstrip()`; verify with `diff -q` against a freshly fetched source copy before committing.