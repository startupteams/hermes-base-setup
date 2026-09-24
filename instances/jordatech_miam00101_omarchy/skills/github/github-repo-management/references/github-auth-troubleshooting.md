# GitHub Authentication Troubleshooting

## Issue: `gh` commands not recognizing `GITHUB_TOKEN` environment variable

During a session attempting to create the `jordatech/knowledge_extracted` repository, the following symptoms were observed:

1. `GITHUB_TOKEN` environment variable was set with a valid personal access token
2. `gh auth status` returned "You are not logged into any GitHub hosts"
3. Direct curl commands with `-H "Authorization: token $GITHUB_TOKEN"` worked correctly
4. `gh repo create` failed with authentication errors despite the token being valid

## Root Cause

The GitHub CLI (`gh`) does not always reliably pick up the `GITHUB_TOKEN` environment variable in all execution contexts, particularly when:
- Running in certain containerized or restricted environments
- When the token contains special characters that interfere with shell parsing
- When there are conflicting authentication sources

## Recommended Solutions

### 1. Use Interactive Login (Most Reliable)
```bash
gh auth login
```
Follow the prompts to authenticate via browser or paste token when prompted.

### 2. Explicit Token Passing (For Scripts)
When you need to use `gh` commands in scripts where interactive login isn't feasible:
```bash
# For individual commands, you can't directly pass token to gh
# Instead, ensure you're authenticated via one of the methods below
gh auth login --with-token <<< "$GITHUB_TOKEN"
```

### 3. Fallback to Direct API Calls
When `gh` authentication proves problematic, use curl directly:
```bash
# Check auth status
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Create repository
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d '{"name":"knowledge_extracted","private":false,"description":"Repository for extracted knowledge from YouTube videos"}'
```

### 4. Environment Variable Best Practices
- Ensure no conflicting tokens in `~/.config/gh/hosts.yml` or `~/.git-credentials`
- Consider using `gh auth login` to store credentials properly in the gh config
- Avoid exporting tokens in shell history; use `read -s` or password managers when possible

## Verification
After attempting authentication, verify with:
```bash
gh auth status  # Should show logged in as your username
gh api user     # Should return your user data
```

## Related References
- [GitHub CLI Authentication Docs](https://cli.github.com/manual/gh_auth_login)
- [GitHub API Authentication](https://docs.github.com/en/rest/overview/authenticating-to-the-rest-api)