#!/usr/bin/env bash
# =============================================================================
# import-portable-brain.sh — Omen-side (MIAM-00101 / Omarchy) import of the
# VM906 portable brain from startupteams/hermes-base-setup branch jordatech_vm906.
#
# Implements migration plan Phases L, M, N, O, P, Q (scriptable parts).
# SAFETY MODEL: ADDITIVE ONLY.
#   - NEVER writes .env / auth.json / config.yaml / install_id / state.db
#   - SOUL.md is NOT overwritten; VM906 variants land in ~/.hermes/migration_sources/vm906/
#   - skills imported with --ignore-existing (Omen versions win conflicts; a
#     conflict report is written for later semantic merge)
#   - memories land in namespaced dirs (imported_vm906*)
#   - conversation history is a searchable archive, no DB merge
#   - config checksum before/after must match or the script FAILS LOUD
#
# Usage:
#   ./import-portable-brain.sh            # full run
#   DRY_RUN=1 ./import-portable-brain.sh  # backup+verify only, no writes
# Idempotent: safe to re-run.
# =============================================================================
set -Eeuo pipefail

export HOME=/home/jordatech
H=/home/jordatech/.hermes
REPO=/home/jordatech/hermes-base-setup
REPO_URL=https://github.com/startupteams/hermes-base-setup.git
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP=/home/jordatech/hermes-migration-backups/$STAMP
WORKTREE=/home/jordatech/hermes-import-vm906
LOG=/home/jordatech/hermes-import-vm906-$STAMP.log
DRY_RUN="${DRY_RUN:-0}"

exec > >(tee -a "$LOG") 2>&1

echo "=== VM906 portable-brain import — $(date -Is) (DRY_RUN=$DRY_RUN) ==="

fail() { echo "FATAL: $*" >&2; exit 1; }

# ---------- 0. Preflight ----------
command -v git   >/dev/null || fail "git missing (Arch: sudo pacman -S git)"
command -v rsync >/dev/null || fail "rsync missing (Arch: sudo pacman -S rsync)"
HAVE_SQLITE3=0; command -v sqlite3 >/dev/null && HAVE_SQLITE3=1
echo "sqlite3 CLI: $([ $HAVE_SQLITE3 = 1 ] && echo present || echo absent — python3 fallback will be used)"
command -v python3 >/dev/null || fail "python3 missing"

# ---------- Phase L: backup BEFORE anything ----------
mkdir -p "$BACKUP"
echo "--- Phase L: backups to $BACKUP"
cp -a "$H/SOUL.md"  "$BACKUP/" 2>/dev/null || true
cp -a "$H/skills"   "$BACKUP/" 2>/dev/null || true
cp -a "$H/memories" "$BACKUP/" 2>/dev/null || true
cp -a "$H/sessions" "$BACKUP/" 2>/dev/null || true
# config rollback copies (never modified, backed up anyway)
for f in .env auth.json config.yaml install_id; do
  cp -a "$H/$f" "$BACKUP/" 2>/dev/null || true
done
# consistent state.db backup
if [ $HAVE_SQLITE3 = 1 ]; then
  sqlite3 "$H/state.db" ".backup '$BACKUP/state.db'"
else
  python3 - "$H/state.db" "$BACKUP/state.db" <<'PY'
import sqlite3, sys
s = sqlite3.connect(sys.argv[1]); d = sqlite3.connect(sys.argv[2])
with d: s.backup(d)
print("state.db online backup OK (python)")
PY
fi
echo "backup done: $(du -sh "$BACKUP" | cut -f1)"

# ---------- Phase P(pre): config checksums ----------
CHECKSUMS=/home/jordatech/hermes-config-before.sha256
( cd "$H" && sha256sum .env auth.json config.yaml install_id 2>/dev/null ) > "$CHECKSUMS" || true
echo "--- config checksums captured: $CHECKSUMS"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN: stopping before any writes. Backup + checksums complete."
  exit 0
fi

# ---------- Phase M: ensure repo + Omen branch ----------
if [ ! -d "$REPO/.git" ]; then
  git clone "$REPO_URL" "$REPO"
fi
cd "$REPO"
git fetch --all --prune
git switch main
git pull --ff-only
if git show-ref --verify --quiet refs/remotes/origin/jordatech_miam00101_omarchy; then
  git switch -C jordatech_miam00101_omarchy origin/jordatech_miam00101_omarchy
else
  # Branch from the jordatech_vm906 branch (not main) so the .gitignore with the
  # instances/ whitelist is in effect for the git add below. Full fetch first so
  # the remote-tracking ref is current (git fetch <url> <branch> only sets FETCH_HEAD).
  git fetch origin '+refs/heads/jordatech_vm906:refs/remotes/origin/jordatech_vm906'
  git switch -c jordatech_miam00101_omarchy origin/jordatech_vm906
fi
mkdir -p instances/jordatech_miam00101_omarchy/{brain,memories,skills,metadata}
cat > instances/jordatech_miam00101_omarchy/metadata/instance.yaml <<EOF
instance_id: jordatech_miam00101_omarchy
hostname: MIAM-00101 (HP Omen, Omarchy)
role: desktop
hermes_home: /home/jordatech/.hermes
portable_sync: true
runtime_database_sync: false
credentials_sync: false
imported_from: jordatech_vm906
imported_at: "$(date -Is)"
EOF
git add instances/jordatech_miam00101_omarchy
if ! git diff --cached --quiet; then
  git commit -m "Seed Omen instance metadata (import from jordatech_vm906)"
fi
git push -u origin jordatech_miam00101_omarchy || echo "WARN: push failed (offline?); local branch exists, retry later"

# ---------- Phase N: fetch VM906 branch into worktree ----------
git fetch origin jordatech_vm906
rm -rf "$WORKTREE"
git worktree add --detach "$WORKTREE" origin/jordatech_vm906
SRC_SKILLS="$WORKTREE/instances/jordatech_vm906/skills"
SRC_SKILLS_PROFILE="$WORKTREE/instances/jordatech_vm906/skills_profile"
SRC_BRAIN="$WORKTREE/instances/jordatech_vm906/brain"
SRC_KNOW="$WORKTREE/instances/jordatech_vm906/knowledge"
SRC_CONVO="$WORKTREE/instances/jordatech_vm906/conversation_exports"

echo "--- Phase N.1: skills (additive, --ignore-existing)"
mkdir -p "$H/skills"
echo "dry-run preview of NEW files (first 40):"
rsync -rni "$SRC_SKILLS/"        "$H/skills/" | head -40 || true
rsync -rni "$SRC_SKILLS_PROFILE/" "$H/skills/" | head -40 || true
rsync -a --ignore-existing "$SRC_SKILLS/"         "$H/skills/"
rsync -a --ignore-existing "$SRC_SKILLS_PROFILE/" "$H/skills/"
# conflict report (files that differ where both exist)
diff -qr "$SRC_SKILLS" "$H/skills" 2>/dev/null | head -200 > /home/jordatech/hermes-skill-conflicts-global.txt || true
diff -qr "$SRC_SKILLS_PROFILE" "$H/skills" 2>/dev/null | head -200 > /home/jordatech/hermes-skill-conflicts-profile.txt || true
echo "conflict reports: /home/jordatech/hermes-skill-conflicts-{global,profile}.txt (semantic merge = follow-up agent task, NOT automatic)"

echo "--- Phase N.2: SOUL comparison copies (Omen SOUL.md untouched)"
mkdir -p "$H/migration_sources/vm906"
cp -f "$SRC_BRAIN/SOUL-global-vm906.md"  "$H/migration_sources/vm906/"
cp -f "$SRC_BRAIN/SOUL-profile-vm906.md" "$H/migration_sources/vm906/"
cp -f "$SRC_BRAIN/SOUL-global-vm906.md"  "$REPO/instances/jordatech_miam00101_omarchy/brain/"
cp -f "$SRC_BRAIN/SOUL-profile-vm906.md" "$REPO/instances/jordatech_miam00101_omarchy/brain/"
echo "NEXT STEP (agent, not script): read current $H/SOUL.md + both migration_sources/vm906/*.md and propose a semantic merge. Backup SOUL first."

echo "--- Phase N.3: durable memories (namespaced, additive)"
mkdir -p "$H/memories/imported_vm906" "$H/memories/imported_vm906_shared"
rsync -a "$SRC_KNOW/memories_profile/" "$H/memories/imported_vm906/" 2>/dev/null || true
rsync -a "$SRC_KNOW/memories/"         "$H/memories/imported_vm906_shared/" 2>/dev/null || true
rsync -a "$SRC_KNOW/shared/"           "$H/memories/imported_vm906_shared/" 2>/dev/null || true
cp -a "$H/memories/imported_vm906" "$REPO/instances/jordatech_miam00101_omarchy/memories/" 2>/dev/null || true

# ---------- Phase O: conversation archive ----------
echo "--- Phase O: VM906 history archive"
mkdir -p "$H/memories/imported_vm906_history"
rsync -a "$SRC_CONVO/" "$H/memories/imported_vm906_history/"
mkdir -p "$H/memories/imported_vm906_history/raw"
mv "$H/memories/imported_vm906_history/sessions.jsonl" "$H/memories/imported_vm906_history/raw/" 2>/dev/null || true
mv "$H/memories/imported_vm906_history/messages.jsonl" "$H/memories/imported_vm906_history/raw/" 2>/dev/null || true
echo "archive: $H/memories/imported_vm906_history (INDEX.md + sessions/*.md + raw/*.jsonl)"

# ---------- Phase P(post): verify config untouched ----------
( cd "$H" && sha256sum .env auth.json config.yaml install_id 2>/dev/null ) > /home/jordatech/hermes-config-after.sha256 || true
if ! diff -u "$CHECKSUMS" /home/jordatech/hermes-config-after.sha256; then
  fail "CONFIG CHECKSUM CHANGED — restore from $BACKUP and investigate"
fi
echo "config checksums UNCHANGED ✔"

# ---------- Phase Q: functional verification ----------
[ -f "$H/SOUL.md" ] && echo "SOUL.md present ✔"
[ -d "$H/skills" ] && echo "skills dir present ✔"
[ -d "$H/memories" ] && echo "memories dir present ✔"
if [ $HAVE_SQLITE3 = 1 ]; then
  echo -n "state.db quick_check: "; sqlite3 "$H/state.db" 'PRAGMA quick_check;'
else
  python3 -c "import sqlite3; print('state.db quick_check:', sqlite3.connect('$H/state.db').execute('PRAGMA quick_check;').fetchone()[0])"
fi
echo "=== IMPORT COMPLETE $(date -Is) ==="
echo "Remaining manual steps: (1) SOUL semantic merge, (2) skill-conflict review, (3) verify Hermes Desktop starts, (4) answer the 7 verification questions (plan §19) into instances/jordatech_miam00101_omarchy/metadata/migration-verification.md, (5) set up the Omen's own hourly exporter (Phase R)."
