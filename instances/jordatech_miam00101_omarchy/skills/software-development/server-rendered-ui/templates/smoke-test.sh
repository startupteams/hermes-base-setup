#!/usr/bin/env bash
# Post-deployment smoke checks for an internal single-VM UI deployment
# (backend direct IN-CONTAINER + via reverse proxy). Live-proven pattern
# (ACMS PRs #2/#9, drills 1-3; 12/12 exit 0 on CT122).
#
# Usage: deploy/smoke-test.sh [https://10.0.20.x.y]
#
# HARD RULES baked in (each was a real production bug once):
# 1. Backend probes run IN-CONTAINER via compose exec + urllib. The app
#    publishes NO host ports by design (reverse proxy is the sole ingress) —
#    host-side `curl http://127.0.0.1:8000` can never pass such a deployment.
# 2. The script EXITS 1 on any failure. A check script that counts failures
#    but always exits 0 gates nothing.
# 3. Exact status-code asserts (401/303), not just "request failed".
# 4. `-k` on all proxy-side curls (self-signed internal TLS).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACMS_ENV_FILE="${ACMS_ENV_FILE:-/opt/acms/.env}"
BASE_URL="${1:-https://10.0.20.122}"
FAILURES=0

CY=(docker compose -f "$SCRIPT_DIR/compose.yaml" --env-file "$ACMS_ENV_FILE")

check() { # name, condition-command
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  [ok]   $name"
  else
    echo "  [FAIL] $name"
    FAILURES=$((FAILURES + 1))
  fi
}

# probe <path> — GET http://127.0.0.1:8000<path> from inside the app
# container (urllib; the image ships no curl). Prints the HTTP status.
probe() {
  "${CY[@]}" exec -T acms-app python - "$1" <<'PY' 2>/dev/null
import sys, urllib.request, urllib.error
try:
    r = urllib.request.urlopen("http://127.0.0.1:8000" + sys.argv[1], timeout=5)
    print(r.status)
except urllib.error.HTTPError as e:
    print(e.code)
except Exception:
    print("ERR")
PY
}

# probe_ok <path> <expected-status> — exit 0 iff status matches exactly.
probe_ok() {
  [ "$(probe "$1")" = "$2" ]
}

echo "==> Backend (direct, in-container — no host ports by design)"
check "/health responds (200)"                 probe_ok /health 200
check "/version reports build identity (200)"  probe_ok /version 200
check "unauthenticated registry denied (401)"  probe_ok /api/v1/agents 401

echo "==> HTTPS UI (via reverse proxy: $BASE_URL)"
check "HTTPS reachable (self-signed ok)" curl -kfsS --max-time 8 "$BASE_URL/ui/login"
BASE_HOST="$(echo "$BASE_URL" | sed -E 's|^https?://||')"
check "HTTP redirects to HTTPS" bash -c "curl -s -o /dev/null -w '%{http_code}' --max-time 8 \"http://$BASE_HOST/ui/login\" | grep -q 301"
check "login page served over TLS" bash -c "curl -kfsS --max-time 8 '$BASE_URL/ui/login' | grep -qi 'sign in'"
check "UI redirects unauthenticated users" bash -c "curl -k -o /dev/null -w '%{http_code}' --max-time 8 '$BASE_URL/ui/' | grep -q 303"
check "registry API not exposed via proxy" bash -c '! curl -kfsS --max-time 8 "$BASE_URL/api/v1/agents"'

echo "==> Build identity (deployed-code truth)"
check "/version exposes git_sha" bash -c "curl -kfsS --max-time 8 '$BASE_URL/version' | grep -q 'git_sha'"
GIT_SHA="$(curl -kfsS --max-time 8 "$BASE_URL/version" | sed -n 's/.*"git_sha"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
if [ -n "$GIT_SHA" ] && [ "$GIT_SHA" != "unknown" ]; then
  echo "  [ok]   git_sha: $GIT_SHA"
else
  echo "  [FAIL] git_sha missing/unknown in /version"
  FAILURES=$((FAILURES + 1))
fi

echo "==> Docker health"
check "app container healthy" bash -c "docker inspect acms-acms-app-1 --format '{{.State.Health.Status}}' | grep -q healthy"

if [ "$FAILURES" -eq 0 ]; then
  echo "SMOKE TEST PASSED"
  exit 0
fi
echo "SMOKE TEST FAILED: $FAILURES check(s)"
exit 1