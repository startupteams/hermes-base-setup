#!/usr/bin/env bash
# backup-hermes.sh - MIAM-00101 private Hermes backup (brain/skills/harness/private/db)
# Runs on the HOST. Never prints secret values.
set -uo pipefail

HERMES_HOME="${HERMES_HOME:-/home/jordatech/.hermes}"
BACKUP_ROOT="${BACKUP_ROOT:-/home/jordatech/Work/hermes-backups}"
TS="$(date +%Y%m%d-%H%M%S)"
DEST="$BACKUP_ROOT/$TS"
LOG="$BACKUP_ROOT/backup-hermes.log"
LOCK=/tmp/backup-hermes.lock

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

exec 9>"$LOCK"
if ! flock -n 9; then log "SKIP: another backup/update holds the lock"; exit 0; fi

mkdir -p "$BACKUP_ROOT"; chmod 700 "$BACKUP_ROOT"
mkdir -p "$DEST"/{brain,skills,harness,private,databases}

fail=0
note() { echo "$*" >> "$DEST/BACKUP-INFO.md"; }
note "# Hermes backup $TS (host $(hostname))"
note "generated: $(date -Is)"

# A. Brain/context
for f in SOUL.md USER.md MEMORY.md; do
  [ -f "$HERMES_HOME/$f" ] && cp -a "$HERMES_HOME/$f" "$DEST/brain/" && note "brain/$f ok"
done
[ -d "$HERMES_HOME/memories" ] && cp -a "$HERMES_HOME/memories" "$DEST/brain/" && note "brain/memories ok"
[ -d "$HERMES_HOME/sessions" ] && cp -a "$HERMES_HOME/sessions" "$DEST/brain/" && note "brain/sessions ok"

# SQLite online backups
python3 - "$HERMES_HOME" "$DEST/databases" <<'PY' || fail=1
import sqlite3, sys, os
home, dest = sys.argv[1], sys.argv[2]
ok = True
for db in ("state.db", "projects.db", "kanban.db"):
    src = os.path.join(home, db)
    if not os.path.exists(src): continue
    try:
        s = sqlite3.connect(src)
        d = sqlite3.connect(os.path.join(dest, db))
        s.backup(d); d.close()
        chk = s.execute("PRAGMA quick_check").fetchone()[0]
        s.close()
        print(f"{db}: backup ok, quick_check={chk}")
        if chk != "ok": ok = False
    except Exception as e:
        print(f"{db}: FAILED {e}"); ok = False
sys.exit(0 if ok else 1)
PY
note "databases done (rc=$fail)"

# B. Skills
if [ -d "$HERMES_HOME/skills" ]; then
  rsync -a --exclude node_modules --exclude __pycache__ "$HERMES_HOME/skills/" "$DEST/skills/"
  note "skills ok ($(find "$DEST/skills" -name SKILL.md | wc -l) skills)"
fi

# C. Harness/runtime structure
cp -a "$HERMES_HOME/config.yaml" "$DEST/harness/" 2>/dev/null && note "harness/config.yaml ok"
[ -d "$HERMES_HOME/hooks" ] && cp -a "$HERMES_HOME/hooks" "$DEST/harness/"
[ -d "$HERMES_HOME/scripts" ] && cp -a "$HERMES_HOME/scripts" "$DEST/harness/"
[ -f "$HERMES_HOME/cron/jobs.json" ] && cp -a "$HERMES_HOME/cron/jobs.json" "$DEST/harness/"
[ -d "$HERMES_HOME/proxy" ] && rsync -a "$HERMES_HOME/proxy/" "$DEST/harness/proxy/" && note "harness/proxy ok"
systemctl --user cat hermes-gateway.service > "$DEST/harness/hermes-gateway.service.txt" 2>/dev/null
systemctl --user list-timers > "$DEST/harness/systemd-user-timers.txt" 2>/dev/null
crontab -l > "$DEST/harness/crontab.txt" 2>/dev/null
( hermes --version 2>/dev/null; echo ---; git -C "$HERMES_HOME/hermes-agent" rev-parse HEAD 2>/dev/null ) > "$DEST/harness/hermes-version.txt"
docker ps -a --format '{{.Names}} {{.Image}} {{.ID}}' 2>/dev/null | grep -i hermes | while read -r n img id; do
  docker inspect "$id" > "$DEST/harness/docker-inspect-$n.json" 2>/dev/null
  echo "harness/docker-inspect-$n.json ok" >> "$DEST/BACKUP-INFO.md"
done
find "$HERMES_HOME" -maxdepth 3 ! -path '*/node_modules*' ! -path '*/venv*' ! -path '*/cache/*' ! -path '*/logs/*' \
  -printf '%M\t%u\t%g\t%s\t%TY-%Tm-%TdT%TH:%TM:%TS\t%p\n' \
  > "$DEST/harness/HERMES-STRUCTURE-MANIFEST.txt" 2>/dev/null
note "harness manifest ok"

# D. Private credentials (LOCAL ONLY, never git)
[ -f "$HERMES_HOME/.env" ] && cp -a "$HERMES_HOME/.env" "$DEST/private/" && note "private/.env ok (local only)"
[ -f "$HERMES_HOME/auth.json" ] && cp -a "$HERMES_HOME/auth.json" "$DEST/private/" && note "private/auth.json ok (local only)"

# Manifest + permissions
( cd "$DEST" && find . -type f ! -name MANIFEST.sha256 -exec sha256sum {} \; > MANIFEST.sha256 )
chmod -R go-rwx "$DEST"
echo "$DEST" > "$BACKUP_ROOT/.latest"

# Retention: 3 latest, 14 daily, 8 weekly, 6 monthly (only if newest complete + >=4 valid)
python3 - "$BACKUP_ROOT" <<'PY'
import os, sys, re, datetime, shutil
root = sys.argv[1]
pat = re.compile(r'^\d{8}-\d{6}$')
snaps = sorted([d for d in os.listdir(root) if pat.match(d) and os.path.isdir(os.path.join(root,d))], reverse=True)
if not snaps: sys.exit(0)
newest = snaps[0]
latest_ok = os.path.exists(os.path.join(root, newest, 'BACKUP-COMPLETE'))
db_ok = os.path.exists(os.path.join(root, newest, 'databases/state.db'))
valid_total = sum(1 for d in snaps if os.path.exists(os.path.join(root,d,'BACKUP-COMPLETE')))
if not (latest_ok and db_ok and valid_total >= 4):
    print("prune-skipped: safety conditions not met"); sys.exit(0)
keep = set(snaps[:3])
now = datetime.date.today()
daily, weekly, monthly = [], [], []
for d in snaps[3:]:
    date = datetime.datetime.strptime(d, "%Y%m%d-%H%M%S").date()
    daily.append(d)
    if date.weekday() == 0: weekly.append(d)
    if date.day <= 7: monthly.append(d)
for lst, n in ((daily,14),(weekly,8),(monthly,6)):
    for d in lst[:n]: keep.add(d)
removed = 0
for d in snaps:
    if d not in keep:
        shutil.rmtree(os.path.join(root,d)); removed += 1
print(f"prune: kept {len(keep)}, removed {removed}")
PY

if [ "$fail" -eq 0 ]; then
  touch "$DEST/BACKUP-COMPLETE"
  log "OK: $DEST"
else
  log "PARTIAL: $DEST (db rc=$fail, no BACKUP-COMPLETE)"
fi
log "done $TS"
exit 0
