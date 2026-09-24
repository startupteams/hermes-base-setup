#!/usr/bin/env bash
# =============================================================================
# Destination-side additive import of a portable Hermes brain (class template).
# Adapted from the proven scripts/import-portable-brain.sh on branch
# jordatech_vm906 of startupteams/hermes-base-setup (2026-09-24).
#
# Copy and set the four CONFIG values. SAFETY MODEL: ADDITIVE ONLY.
#   - NEVER writes .env / auth.json / config.yaml / install_id / state.db
#   - SOUL.md untouched; source variants -> migration_sources/<instance>/
#   - skills: --ignore-existing (destination wins; conflict reports written)
#   - memories: namespaced under memories/imported_<instance>*
#   - conversation archive -> memories/imported_<instance>_history/
#   - config sha256 before/after must match or script FAILS LOUD
#
# Usage:  DRY_RUN=1 ./import-portable-brain.sh   # backup+checksums only
#         ./import-portable-brain.sh             # full additive import
# =============================================================================
set -Eeuo pipefail

# ---- CONFIG (edit these four) ----------------------------------------------
export HOME=/home/jordatech
H=/home/jordatech/.hermes                    # destination Hermes home
REPO=/home/jordatech/hermes-base-setup       # clone of the brain repo
REPO_URL=https://github.com/OWNER/hermes-base-setup.git
SRC_INSTANCE=jordatech_vm906                 # branch + instances/<id> to import from
# -----------------------------------------------------------------------------

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP=/home/jordatech/hermes-migration-backups/$STAMP
WORKTREE=/home/jordatech/hermes-import-$SRC_INSTANCE
DRY_RUN="${DRY_RUN:-0}"

fail() { echo "FATAL: $*" >&2; exit 1; }
command -v git >/dev/null || fail "git missing"
command -v rsync >/dev/null || fail "rsync missing"
command -v python3 >/dev/null || fail "python3 missing"
HAVE_SQLITE3=0; command -v sqlite3 >/dev/null && HAVE_SQLITE3=1

# ---- Backup BEFORE anything ----
mkdir -p "$BACKUP"
for f in SOUL.md .env auth.json config.yaml install_id; do
  cp -a "$H/$f" "$BACKUP/" 2>/dev/null || true
done
for d in skills memories sessions; do
  cp -a "$H/$d" "$BACKUP/" 2>/dev/null || true
done
if [ $HAVE_SQLITE3 = 1 ]; then
  sqlite3 "$H/state.db" ".backup '$BACKUP/state.db'"
else
  python3 - "$H/state.db" "$BACKUP/state.db" <<'PY'
import sqlite3, sys
s = sqlite3.connect(sys.argv[1]); d = sqlite3.connect(sys.argv[2])
with d: s.backup(d)
PY
fi

# ---- Config checksums (pre) ----
CHECKSUMS=/home/jordatech/hermes-config-before.sha256
( cd "$H" && sha256sum .env auth.json config.yaml install_id 2>/dev/null ) > "$CHECKSUMS" || true

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN: backup + checksums complete, no writes. Backup: $BACKUP"
  exit 0
fi

# ---- Repo + destination instance branch ----
[ -d "$REPO/.git" ] || git clone "$REPO_URL" "$REPO"
cd "$REPO"
git fetch --all --prune
git switch main && git pull --ff-only
DEST_INSTANCE="${DEST_INSTANCE:-$(git branch --show-current | sed 's/^/dest_/')}"
if git show-ref --verify --quiet "refs/remotes/origin/$DEST_INSTANCE"; then
  git switch -C "$DEST_INSTANCE" "origin/$DEST_INSTANCE"
else
  git switch -c "$DEST_INSTANCE"
fi
mkdir -p "instances/$DEST_INSTANCE"/{brain,memories,skills,metadata}
cat > "instances/$DEST_INSTANCE/metadata/instance.yaml" <<EOF
instance_id: $DEST_INSTANCE
hermes_home: $H
portable_sync: true
runtime_database_sync: false
credentials_sync: false
imported_from: $SRC_INSTANCE
imported_at: "$(date -Is)"
EOF

# ---- Source worktree ----
git fetch origin "$SRC_INSTANCE"
rm -rf "$WORKTREE"
git worktree add --detach "$WORKTREE" "origin/$SRC_INSTANCE"
SRC_SKILLS="$WORKTREE/instances/$SRC_INSTANCE/skills"
SRC_SKILLS_PROFILE="$WORKTREE/instances/$SRC_INSTANCE/skills_profile"
SRC_BRAIN="$WORKTREE/instances/$SRC_INSTANCE/brain"
SRC_KNOW="$WORKTREE/instances/$SRC_INSTANCE/knowledge"
SRC_CONVO="$WORKTREE/instances/$SRC_INSTANCE/conversation_exports"

# ---- N.1 skills: additive, destination wins ----
rsync -a --ignore-existing "$SRC_SKILLS/"         "$H/skills/"
rsync -a --ignore-existing "$SRC_SKILLS_PROFILE/" "$H/skills/" 2>/dev/null || true
diff -qr "$SRC_SKILLS" "$H/skills" 2>/dev/null | head -200 > /home/jordatech/hermes-skill-conflicts-global.txt || true
diff -qr "$SRC_SKILLS_PROFILE" "$H/skills" 2>/dev/null | head -200 > /home/jordatech/hermes-skill-conflicts-profile.txt || true

# ---- N.2 SOUL: comparison copies only ----
mkdir -p "$H/migration_sources/$SRC_INSTANCE"
cp -f "$SRC_BRAIN/"*.md "$H/migration_sources/$SRC_INSTANCE/"
cp -f "$SRC_BRAIN/"*.md "instances/$DEST_INSTANCE/brain/"

# ---- N.3 memories: namespaced ----
mkdir -p "$H/memories/imported_$SRC_INSTANCE" "$H/memories/imported_${SRC_INSTANCE}_shared"
rsync -a "$SRC_KNOW/memories_profile/" "$H/memories/imported_$SRC_INSTANCE/" 2>/dev/null || true
rsync -a "$SRC_KNOW/memories/"         "$H/memories/imported_${SRC_INSTANCE}_shared/" 2>/dev/null || true
rsync -a "$SRC_KNOW/shared/"           "$H/memories/imported_${SRC_INSTANCE}_shared/" 2>/dev/null || true

# ---- O conversation archive ----
mkdir -p "$H/memories/imported_${SRC_INSTANCE}_history"
rsync -a "$SRC_CONVO/" "$H/memories/imported_${SRC_INSTANCE}_history/"
mkdir -p "$H/memories/imported_${SRC_INSTANCE}_history/raw"
mv "$H/memories/imported_${SRC_INSTANCE}_history/"*.jsonl \
   "$H/memories/imported_${SRC_INSTANCE}_history/raw/" 2>/dev/null || true

# ---- Commit destination metadata ----
git add "instances/$DEST_INSTANCE"
git diff --cached --quiet || git commit -m "Seed $DEST_INSTANCE metadata (import from $SRC_INSTANCE)"
git push -u origin "$DEST_INSTANCE" || echo "WARN: push failed (offline?); local branch exists"

# ---- Checksums (post) — fail loud ----
( cd "$H" && sha256sum .env auth.json config.yaml install_id 2>/dev/null ) \
  > /home/jordatech/hermes-config-after.sha256 || true
diff -u "$CHECKSUMS" /home/jordatech/hermes-config-after.sha256 \
  || fail "CONFIG CHECKSUM CHANGED — restore from $BACKUP and investigate"

# ---- Functional verification ----
[ -f "$H/SOUL.md" ] && echo "SOUL.md present"
if [ $HAVE_SQLITE3 = 1 ]; then
  sqlite3 "$H/state.db" 'PRAGMA quick_check;'
else
  python3 -c "import sqlite3;print(sqlite3.connect('$H/state.db').execute('PRAGMA quick_check;').fetchone()[0])"
fi
echo "=== IMPORT COMPLETE $(date -Is) ==="
echo "Follow-ups: SOUL semantic merge; conflict review; start Hermes Desktop;"
echo "write migration-verification.md; set up Phase R hourly exporter."
