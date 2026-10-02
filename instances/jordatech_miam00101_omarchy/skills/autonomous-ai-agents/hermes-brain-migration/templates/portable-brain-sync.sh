#!/usr/bin/env bash
# =============================================================================
# Source-side hourly portable-brain exporter (class template).
# Adapted from the proven ~/.hermes/scripts/portable_brain_sync.sh on VM906
# (2026-09-24). Replaces any whole-~/.hermes git sync with a portable export.
#
# Copy to ~/.hermes/scripts/<name>.sh, set CONFIG values, chmod +x.
# For Hermes cron: create a wrapper in the PROFILE scripts dir
#   (profiles/<profile>/scripts/<name>.sh: `exec <abs path to this script>`)
#   and create the cron with no_agent=true + script=<relative wrapper filename>.
#
# Behavior: refresh SOUL/skills/memories + DB snapshots + conversation archive,
#   then autostash-pull --rebase, commit only on change, push. Read-only on the
#   live Hermes DBs. flock prevents overlap.
# =============================================================================
set -Eeuo pipefail

# ---- CONFIG -----------------------------------------------------------------
export HOME=/home/jordatech
HERMES=/home/jordatech/.hermes
PROFILE="$HERMES/profiles/agent_stea004_entrepreneur"   # live profile (or =HERMES for default)
REPO=/home/jordatech/hermes-base-setup
REPO_BRANCH=jordatech_vm906                              # this instance's branch
INSTANCE=jordatech_vm906                                 # instances/<id> in the repo
EXPORT_WS=/home/jordatech/hermes-portable-export         # workspace with DB snapshots + exporter
CONVO_EXPORTER="$EXPORT_WS/scripts/export_conversations.py"
# ------------------------------------------------------------------------------

DEST="$REPO/instances/$INSTANCE"
LOCK="$EXPORT_WS/.portable-brain-sync.lock"
LOG="$EXPORT_WS/portable-brain-sync.log"
log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$LOG"; }

{
  flock -n 9 || { log "another sync running; exit"; exit 0; }
  log "=== portable-brain sync start ==="

  mkdir -p "$DEST/brain" "$DEST/skills" "$DEST/skills_profile" \
           "$DEST/knowledge" "$DEST/conversation_exports" "$DEST/metadata"

  # SOUL (both variants)
  cp -f "$HERMES/SOUL.md" "$DEST/brain/SOUL-global.md"
  cp -f "$PROFILE/SOUL.md" "$DEST/brain/SOUL-profile.md"

  # Skills (exclude runtime curator/usage state)
  rsync -a --delete \
    --exclude='.usage.json' --exclude='.curator_state' --exclude='.curator_ledger.jsonl' \
    "$HERMES/skills/" "$DEST/skills/"
  rsync -a --delete \
    --exclude='.usage.json' --exclude='.curator_state' --exclude='.curator_ledger.jsonl' \
    "$PROFILE/skills/" "$DEST/skills_profile/"

  # Durable memories
  rsync -a --exclude='.*' --exclude='*.db' --exclude='*.lock' \
    "$PROFILE/memories/" "$DEST/knowledge/memories_profile/"
  rsync -a --exclude='.*' --exclude='*.db' --exclude='*.lock' \
    "$HERMES/memories/" "$DEST/knowledge/memories/" 2>/dev/null || true
  rsync -a --exclude='.*' --exclude='*.db' --exclude='*.lock' \
    "$HERMES/shared/" "$DEST/knowledge/shared/" 2>/dev/null || true

  # Refresh workspace DB snapshots (online .backup via Python — WAL-safe)
  python3 - <<PYEOF >> "$LOG" 2>&1 || log "WARN: DB snapshot refresh failed"
import sqlite3
jobs = [
    ("$PROFILE/state.db",                 "$EXPORT_WS/metadata/state.db"),
    ("$PROFILE/memory_store.db",          "$EXPORT_WS/metadata/memory-store.db"),
    ("$PROFILE/verification_evidence.db", "$EXPORT_WS/metadata/verification-evidence.db"),
]
for src, dst in jobs:
    s = sqlite3.connect(src); d = sqlite3.connect(dst)
    with d: s.backup(d)
    d.close(); s.close()
print("DB snapshots refreshed")
PYEOF

  # Refresh conversation archive from workspace DBs (scrubbing happens in exporter)
  if python3 "$CONVO_EXPORTER" >> "$LOG" 2>&1; then
    rsync -a "$EXPORT_WS/conversation_exports/" "$DEST/conversation_exports/"
  else
    log "WARN: conversation export failed; keeping previous archive"
  fi

  # git: switch, autostash-pull, commit only on change, push
  cd "$REPO"
  current="$(git branch --show-current)"
  if [ "$current" != "$REPO_BRANCH" ]; then
    git switch "$REPO_BRANCH" || { log "ERROR: cannot switch to $REPO_BRANCH (on $current)"; exit 1; }
  fi
  git pull --rebase --autostash origin "$REPO_BRANCH" >> "$LOG" 2>&1 || log "WARN: pull failed (offline?)"
  git add "instances/$INSTANCE"
  if git diff --cached --quiet; then
    log "no changes to commit"
  else
    git commit -m "$INSTANCE portable-brain sync $(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$LOG" 2>&1
    git push origin "$REPO_BRANCH" >> "$LOG" 2>&1 || log "WARN: push failed (offline?)"
  fi

  log "=== portable-brain sync done ==="
} 9>"$LOCK"
