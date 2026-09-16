#!/usr/bin/env bash
set -Eeuo pipefail

# ==============================================================================
# Hermes Master Sync Script (Memory Sync + External Skills Sync)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK_FILE="$REPO_DIR/.git/hermes_sync.lock"
LOG_FILE="$REPO_DIR/.git/hermes_sync.log"

TEMP_DIR="/tmp/external_skills_src"
EXTERNAL_REPO_URL="https://github.com/startupteams/agentifyme_stea_hermes_memory_and_skills.git"
SOURCE_BRANCH="jordatech_crmmiam02_906"
SOURCE_SUBPATH="profiles/agent_stea004_entrepreneur/skills"

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$LOG_FILE"
}

fail() {
  log "ERROR: $*"
  printf 'Hermes git sync failed: %s\n' "$*" >&2
  exit 1
}

cd "$REPO_DIR"

# Ensure non-overlapping execution using file descriptor 9
{
  flock -n 9 || {
    log "Another sync process is currently running. Exiting cleanly."
    exit 0
  }

  current_branch="$(git branch --show-current)"
  if [ -z "$current_branch" ]; then
    fail "Detached HEAD state; cannot determine active branch."
  fi

  # Guardrail: Avoid running operations directly on main or master
  if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
    log "Active branch is '$current_branch'. Skipping auto-sync to protect base branch."
    exit 0
  fi

  log "Starting sync on branch '$current_branch'..."

  # Safely pull latest changes for the active branch of the parent repo
  git pull origin "$current_branch" --rebase --autostash >> "$LOG_FILE" 2>&1 || log "Warning: git pull --rebase failed or remote unavailable."

  # Pull and sync skills from the external source repository into skills/
  log "Fetching external skills from '$SOURCE_BRANCH'..."
  rm -rf "$TEMP_DIR"
  if git clone --depth 1 --branch "$SOURCE_BRANCH" "$EXTERNAL_REPO_URL" "$TEMP_DIR" >> "$LOG_FILE" 2>&1; then
    rsync -av --delete "$TEMP_DIR/$SOURCE_SUBPATH/" "$REPO_DIR/skills/" >> "$LOG_FILE" 2>&1
    rm -rf "$TEMP_DIR"
  else
    log "Warning: Failed to clone external skills repo. Skipping skills sync."
    rm -rf "$TEMP_DIR"
  fi

  changes_detected=0

  # Check and track changes in profiles/ (original memory sync behavior)
  if ! git diff --quiet profiles/ || ! git diff --cached --quiet profiles/ || [ -n "$(git ls-files --others --exclude-standard profiles/)" ]; then
    git add profiles/ >> "$LOG_FILE" 2>&1 || fail "git add profiles/ failed"
    changes_detected=1
  fi

  # Check and track changes in skills/ (external skills sync behavior)
  if ! git diff --quiet skills/ || ! git diff --cached --quiet skills/ || [ -n "$(git ls-files --others --exclude-standard skills/)" ]; then
    git add skills/ >> "$LOG_FILE" 2>&1 || fail "git add skills/ failed"
    changes_detected=1
  fi

  if [ "$changes_detected" -eq 1 ]; then
    commit_msg="chore: auto-sync memory and skills for [$current_branch] at $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    git commit -m "$commit_msg" >> "$LOG_FILE" 2>&1 || fail "git commit failed"
    log "Committed updates: $commit_msg"

    if git remote get-url origin >/dev/null 2>&1; then
      git push origin "$current_branch" >> "$LOG_FILE" 2>&1 || log "Warning: git push failed or remote unavailable."
    fi
  else
    log "No memory or skills changes detected. Up to date."
  fi

} 9>"$LOCK_FILE"
