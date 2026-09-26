#!/usr/bin/env bash
# update-hermes.sh - git-install Hermes updater (host-side wrapper).
# Order: lock -> backup -> update -> config check -> restart gateway -> health -> rollback.
# Proven live on MIAM-00101. NOTE: the gateway restart kills agent sessions on that gateway.
set -uo pipefail
H=/home/jordatech/.hermes
SRC=$H/hermes-agent
LOGD=$H/logs/local_update_receipts
mkdir -p "$LOGD"
LOG=$LOGD/receipt-$(date +%Y%m%d-%H%M%S).md
exec 9>/tmp/update-hermes.lock
if ! flock -n 9; then echo "update already running"; exit 0; fi

old_rev=$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo unknown)
old_ver=$("$H/hermes-agent/venv/bin/python" -m hermes_cli.main --version 2>/dev/null | head -1)
{
  echo "# Hermes update receipt $(date -Is)"
  echo "old_rev=$old_rev"
  echo "old_ver=$old_ver"
} > "$LOG"

# 1. mandatory pre-update backup
if ! "$H/scripts/backup-hermes.sh" >> "$LOG" 2>&1; then
  echo "ABORT: pre-update backup failed" >> "$LOG"; exit 1
fi
bk=$(cat /home/jordatech/Work/hermes-backups/.latest 2>/dev/null)
[ -f "$bk/BACKUP-COMPLETE" ] || { echo "ABORT: backup incomplete" >> "$LOG"; exit 1; }
echo "backup=$bk" >> "$LOG"

# 2. update
git -C "$SRC" fetch origin >> "$LOG" 2>&1 || { echo "ABORT: fetch failed" >> "$LOG"; exit 1; }
if ! git -C "$SRC" pull --ff-only origin main >> "$LOG" 2>&1; then
  echo "ABORT: pull failed (local changes?); manual review needed" >> "$LOG"; exit 1
fi
new_rev=$(git -C "$SRC" rev-parse HEAD)
echo "new_rev=$new_rev" >> "$LOG"

# 3. deps
"$H/hermes-agent/venv/bin/python" -m pip install -q -e "$SRC" >> "$LOG" 2>&1 \
  || echo "WARN: pip install -e failed (deps may be unchanged)" >> "$LOG"

# 4. config migration
"$H/hermes-agent/venv/bin/python" -m hermes_cli.main config check >> "$LOG" 2>&1 \
  || echo "WARN: config check rc!=0" >> "$LOG"
grep -E '^  default:' "$H/config.yaml" | head -1 >> "$LOG"

# 5. restart gateway
systemctl --user restart hermes-gateway.service && echo "restart=ok" >> "$LOG" || { echo "restart=FAILED" >> "$LOG"; exit 1; }

# 6. health check
sleep 10
if systemctl --user is-active --quiet hermes-gateway.service; then
  echo "health=gateway-active" >> "$LOG"
  echo "update=SUCCESS" >> "$LOG"
else
  echo "health=gateway-INACTIVE - rolling back" >> "$LOG"
  git -C "$SRC" reset --hard "$old_rev" >> "$LOG" 2>&1
  "$H/hermes-agent/venv/bin/python" -m pip install -q -e "$SRC" >> "$LOG" 2>&1
  systemctl --user restart hermes-gateway.service >> "$LOG" 2>&1
  echo "rollback=DONE update=ROLLED_BACK" >> "$LOG"
fi
new_ver=$("$H/hermes-agent/venv/bin/python" -m hermes_cli.main --version 2>/dev/null | head -1)
echo "new_ver=$new_ver" >> "$LOG"
cat "$LOG"
exit 0
