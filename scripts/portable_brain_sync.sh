#!/usr/bin/env bash
# =============================================================================
# MIAM-00101 (Omen/Omarchy) portable-brain exporter (Phase R).
# Exports ONLY portable content to instances/jordatech_miam00101_omarchy in
# startupteams/hermes-base-setup, branch jordatech_miam00101_omarchy.
# Never touches: .env, auth.json, config.yaml, install_id, state.db, WAL/SHM.
# =============================================================================
set -Eeuo pipefail

export HOME=/home/jordatech
H=/home/jordatech/.hermes
REPO=/home/jordatech/Work/hermes-base-setup
DEST="$REPO/instances/jordatech_miam00101_omarchy"
LOCK="$REPO/.git/portable-brain-sync.lock"
LOG="$REPO/.git/portable-brain-sync.log"

log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$LOG"; }

{
  flock -n 9 || { log "another sync running; exit"; exit 0; }
  log "=== omen portable-brain sync start ==="

  mkdir -p "$DEST/brain" "$DEST/memories" "$DEST/skills" "$DEST/metadata"

  # ---- SOUL (current) ----
  cp -f "$H/SOUL.md" "$DEST/brain/SOUL.md"
  # ---- Skills (exclude runtime curator state) ----
  rsync -a --delete --exclude='.usage.json' --exclude='.curator_state' \
    --exclude='.curator_ledger.jsonl' --exclude='.archive' \
    "$H/skills/" "$DEST/skills/"
  # ---- Durable memories (current MEMORY/USER) ----
  cp -f "$H/memories/MEMORY.md" "$DEST/memories/" 2>/dev/null || true
  cp -f "$H/memories/USER.md" "$DEST/memories/" 2>/dev/null || true
  # ---- git sync ----
  cd "$REPO"
  current="$(git branch --show-current)"
  [ "$current" = "jordatech_miam00101_omarchy" ] || git switch jordatech_miam00101_omarchy
  git pull --rebase --autostash origin jordatech_miam00101_omarchy >> "$LOG" 2>&1 || log "WARN: pull failed"
  git add instances/jordatech_miam00101_omarchy
  if git diff --cached --quiet; then log "no changes"; else
    git commit -m "Omen portable-brain sync $(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> "$LOG" 2>&1
    git push origin jordatech_miam00101_omarchy >> "$LOG" 2>&1 || log "WARN: push failed"
  fi
  log "=== done ==="
} 9>"$LOCK"
