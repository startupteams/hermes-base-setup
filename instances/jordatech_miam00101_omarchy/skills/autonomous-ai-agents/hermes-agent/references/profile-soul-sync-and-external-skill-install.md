# Profile SOUL Sync and External Skill Install Notes

Use when a user asks to update the active Hermes profile `SOUL.md` from an agent identity file in a GitHub repo, then install a companion skill such as `jordatech/caveman`.

## Exact SOUL Sync Pattern

For the entrepreneur profile on this machine, the authoritative live profile repository is `/home/miam/.hermes` on `main` with remote `https://github.com/jordatech/crmmiam01_hermes`.

Fetch the source markdown from GitHub and write it byte-for-byte into the profile SOUL file:

```bash
export HOME=/home/miam
cd /home/miam/.hermes

gh api repos/jordatech/obsidian_vault_jordan_ulmer/contents/Agents/entrepreneur/c01entrepreneur_bot_AgentMD.md \
  --jq '.content' | base64 -d > profiles/entrepreneur/SOUL.md

# Verify exact match. Do not trim trailing spaces or blank lines if user asked to match.
tmp=$(mktemp)
gh api repos/jordatech/obsidian_vault_jordan_ulmer/contents/Agents/entrepreneur/c01entrepreneur_bot_AgentMD.md \
  --jq '.content' | base64 -d > "$tmp"
diff -q "$tmp" profiles/entrepreneur/SOUL.md
rm -f "$tmp"
```

## External Skill Install Pattern

`hermes skills install` may prompt for category and confirmation. In non-interactive tool runs, pass both `--category` and `--yes`:

```bash
export HOME=/home/miam
hermes skills install \
  https://raw.githubusercontent.com/jordatech/caveman/main/skills/caveman/SKILL.md \
  --profile entrepreneur \
  --name caveman \
  --category creative \
  --yes
```

Then load/verify:

```bash
hermes skills list | grep -i caveman
```

Runtime location after this install:

```text
/home/miam/.hermes/profiles/entrepreneur/skills/creative/caveman/SKILL.md
```

## Git Commit Pattern

Commit in the Hermes profile repository, not a separate clone:

```bash
export HOME=/home/miam
cd /home/miam/.hermes
git add profiles/entrepreneur/SOUL.md profiles/entrepreneur/skills/creative/caveman/SKILL.md
git commit -m "docs: update entrepreneur profile soul and skills"
git push origin main
git status --short --branch
```

If a background cron has created local commits, the repo can be ahead of `origin/main`; push those commits instead of creating a duplicate sync clone.

## Pitfalls

- The GitHub contents API returns base64; decode with `base64 -d`.
- Exact-match requests mean preserve trailing whitespace/blank lines. Avoid `.rstrip()` when writing the source file.
- `hermes skills install` without `--yes` cancels in non-interactive runs after the confirmation prompt.
- `hermes skills install --help` may omit profile-wide context; still use `HOME=/home/miam` and `--profile entrepreneur` when targeting the live entrepreneur profile.
- `search_files` may not find installed skill files if cache/path filtering differs; verify with `read_file` and `git ls-files` against the exact expected path.
