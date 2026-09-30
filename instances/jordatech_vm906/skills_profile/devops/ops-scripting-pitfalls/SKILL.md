---
name: ops-scripting-pitfalls
description: "Writing and debugging operational bash tooling (deploy/release/rollback/backup scripts) — stdout purity in command substitution, false-failure patterns under pipefail, docker-compose and nginx reload traps, git-in-scripts, verification discipline."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [bash, docker-compose, nginx, git, release-engineering, pitfalls, devops]
---

# Operational Scripting Pitfalls

**Trigger this skill when:** writing or reviewing bash scripts that drive deploys, releases, rollbacks, backups, or container/nginx ops; debugging a script that failed when everything actually worked (or exited 4 while the physical operation succeeded); maintaining a safe-release/deploy pipeline.

Every pitfall below was produced by a real production drill (twice, at cost). They are failure modes that survive review because each one *looks* correct.

## 1. Command substitution captures EVERYTHING on stdout

`VAR="$(func)"` captures **all** of func's stdout — including the function's own log lines.

- Rule for any function whose output is captured: **nothing on stdout except the return value.** Every log line goes `>&2`, including your own `info()` calls.
- External tool output (e.g. `docker compose build`) is human log text — redirect it `>&2` too. Its stdout is not your return value.
- `die` / `exit` inside a command-substituted function only kills the **subshell**; the parent continues with a polluted or empty value and no error signal. Use `return 1` and handle at the call site: `VAR="$(func)" || handle_failure`.
- Symptom when violated: `invalid tag "app:[2026-09-26T..] INFO Building…"` — the log text becomes part of the value.

## 2. False-failure patterns under `set -euo pipefail`

These make a passing system report failure:

- `grep -c PATTERN` exits **1 when the count is 0** — so a "logs must contain no errors" check fails exactly when logs are clean (under pipefail). Capture the count, compare numerically: `count=$(... | grep -cE PAT || true); [ "$count" -eq 0 ]`.
- `[ cond ] && cmd` as the **last statement** of a loop/function returns 1 when `cond` is false on the final iteration — even when every iteration before succeeded. Classic case: `[ "$i" -lt 3 ] && sleep 2` inside a 3-iteration health-check loop. Use explicit `if`; end the function with an explicit `return 0`.
- Audit pattern: any check function whose success path ends with a conditional short-circuit is suspect.
- `$?` after a pipeline is the LAST command's status, not the pipeline head's: `bash script.sh 2>&1 | tee log | tail -60; echo $?` reports `tail`'s status. A drill verdict was once read as PASS off `tail`'s exit code. Use `"${PIPESTATUS[0]}"` for the first stage, or make the script print its own explicit final verdict line and match on that text.

## 3. git inside scripts

- `git checkout --detach <sha>` fails with `fatal: git checkout: --detach does not take a path argument '<sha>'` when the SHA is **not in the local object store**. The error looks like a syntax mistake but is a missing-fetch problem. Always `git fetch origin main` before resolving a target SHA.
- A dirty tracked file (e.g. a config overlaid for maintenance mode) makes checkout refuse. Restore the tracked file (`git checkout -- <file>`) before moving HEAD, then re-apply the overlay afterward.
- Mirror case: a failed stage BETWEEN "overlay maintenance conf" and "restore normal conf" leaves the tracked file holding maintenance content. Restore with `git checkout -- <file>` BEFORE retrying the overlay sequence — otherwise the retry copies onto an already-switched file and maintenance on/off bookkeeping desyncs from what the container serves.

## 4. docker compose operational traps

- `compose up -d <service>` also recreates `depends_on` services. Always pin the app image tag on every compose invocation (e.g. `ACMS_APP_IMAGE_TAG=<sha>`), or a recreation silently reverts the app to the default `:local` image.
- Detect wrong-image states fast via a build-identity endpoint: `/version` should echo the deployed git SHA — check it after any container recreation.
- A compose **spec change** (e.g. volume mount type) is recreate-requiring: a container created under the old spec keeps the old mount topology; no reload fixes it. `up -d` recreates only when the resolved spec differs — for depends_on services, recreate explicitly and re-pin the image.
- Recovery from a stuck state: recreate the affected container explicitly (`up -d --force-recreate <svc>`), then re-verify the app image tag.
- Compose v2 container names are `<project>-<service>-1` and depend on the project name — never hard-code them for `docker exec` (a bootstrap hop died on `No such container: acms-reverse-proxy`). Use `docker compose exec <service>`, which resolves by service name under any naming scheme.

## 5. nginx config reload + bind mounts

- A **single-file bind mount** (`./nginx.conf:/etc/nginx/conf.d/default.conf`) pins the inode: replacing the file on the host is invisible to the container, and `kill -s HUP` then reloads the **stale** config forever. Symptom: a maintenance 503 page persists after maintenance-off even though the host file is correct.
- Mount the **directory** instead and edit files in place (same inode). Keep non-active variants as `*.template` so the include glob never loads them.
- Guard every reload with `nginx -t` first; fall back to single-container `compose restart`, never bare `up -d` (depends_on recreation risk).
- After any config surgery, verify what the **container** sees — `docker exec <proxy> grep -c MARKER /etc/nginx/conf.d/<file>` — not just the host file. Container and host can disagree after mount-topology or inode changes.

## 6. Verification discipline (writes lie)

- Never treat a file-write tool's success echo as ground truth; content can corrupt mid-write with injected text.
- Ground truth, in order of authority: `git diff` (tracked files) → `python -m py_compile` / `bash -n` (syntax) → `python ast.parse` (content sanity).
- Repair corrupted files via scripted rewrite with assertion pre-checks (assert exact expected lines before writing), then re-verify with diff/lint. After one failed full-file write, prefer small patch-tool edits over another full write.

## 7. Smoke / check scripts must be runnable truth

- A check script that counts failures but always exits 0 gates nothing. End with an explicit `exit 1` on any failure (the ACMS standalone smoke-test.sh counted `FAILURES` yet always exited 0 until PR #9; `validate-release.sh` got it right from the start).
- Write probes against the service's ACTUAL reachability. A smoke script that curls `127.0.0.1:8000` from the VM host silently fails forever once the service stops publishing host ports — reverse-proxy-as-sole-ingress hardening produces exactly this. With no host ports, probe in-container: `docker compose exec -T <svc> python -c "import urllib.request, …"` (many images ship no curl; assert exact status codes, e.g. unauth API = 401).
- When hardening changes topology (published ports removed, allowlists added, mount types changed), audit every existing check script in the same change — stale probes become permanent false-fails that train operators to ignore the whole suite.

## 8. Deploy-transaction healthchecks: false-failure classes (llm-manager staging, 2026-09-27)

Three smoke/healthcheck bugs in a row produced the same symptom — a correct deploy auto-rollback on false evidence:

- **Restart-backoff false-negative**: the transaction restarts units then healthchecks immediately; a unit still in `Restart=on-failure` backoff (RestartSec=5–15) reads "not active". Healthcheck needs a bounded wait per unit: `for _ in $(seq 1 10); do systemctl is-active --quiet $u && return 0; sleep 3; done`.
- **Route-inventory 404**: a 404 on an optional API route (`/api/benchmarks` absent in older releases) is a release difference, not a deploy failure — tolerate 404 in the route-alive check. But tolerance MASKS phantom probes: verify each probed path against the app's real route inventory before trusting it (live case 2026-09-27: the check probed `/api/benchmarks`, which never existed — the real route was `/api/history/benchmarks`; the 404-tolerance then hid the bogus probe indefinitely).
- **Auth-gate responses are PASSes**: a gated endpoint answering its auth error (`invalid or missing API key` on `/v1/models`) proves the route is alive with its gate enforced — don't fail on it; staging environments legitimately have no keys seeded.
- **Post-rollback identity confusion**: when the candidate fails smoke and the transaction auto-rolls back, the post-rollback healthcheck correctly reports the PREVIOUS release's manifest. Read the log sequence (smoke FAILED → rollback started → healthcheck on old release) before diagnosing.
- The rollback chain itself worked correctly every time — the bug was always in the acceptance criteria, never in the transaction mechanics.

## 9. Scripts that silently operate on empty inputs

A runner/discovery script that finds ZERO input items must hard-fail, not succeed emptily. Real case (2026-09-27): a DB migration runner computed its migrations dir as `os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")` while the script itself lived inside `db/migrations/` — resolving to `db/migrations/migrations`. Every downstream consumer (`apply`, `status`, `verify`) then exited 0 over an empty set: `apply` printed nothing, `verify` printed "verified 0 applied migrations". The silent zero was only caught when a live test tried to SELECT a table the scratch migration should have created.

### 9b. Sync/reconciler success logs that count INPUTS, not outcomes (2026-09-30, cost a session)

A registry→Kuma reconciler logged `kuma: monitors ensured (34)` where 34 = `len(services)` — the count of
DESIRED inputs — while the target system actually held **zero** monitors (its auth had never worked; every
write silently failed). An operator session trusted the log and shipped a false "34 monitors reconciled"
claim in a handoff. The audit trail even had thousands of these "success" events.

Rules for ANY sync/reconcile/ensure tool:
- Log `created=X updated=Y unchanged=Z errors=E` derived from PER-ITEM ACK/RESULT checks — never a bare
  count of inputs, and never `len(desired)` in place of an outcome.
- After the write phase, READ BACK the target's actual state and diff against desired; report the diff.
- A success log whose number always equals the input count (identical across runs, regardless of target
  state) is a red flag, not evidence.
- Silent failures inside client libs (a socket.io emit whose callback never fires) produce NO exception —
  the only defense is ack timeouts + per-item ok checks + read-back verification.

Rules:

- Self-referencing directory = `os.path.dirname(os.path.abspath(__file__))` itself — appending `/<dirname>/` again double-nests.
- `apply`-style commands must print EVERY action taken; an `apply` run with no output lines is suspicious by default.
- Add an explicit guard: `items = discover(); if not items: die("no <inputs> found in <dir>")` for anything that later writes state.
- Same class: "verified 0 X", "applied 0 migrations", "0 files processed" on a supposedly-populated tree = treat as failure, not success.

## 10. Sibling-script paths break under absolute invocation

`./"$(dirname "$0")/preflight.sh"` — prefixing the dirname with `./` — works only when the caller uses a RELATIVE path. Invoked by absolute path (`sudo /opt/svc/current/deploy/deploy-release.sh <tarball>` — exactly what CD wrappers and operators do), `dirname` yields `/opt/svc/current/deploy` and bash resolves the sibling as `.//opt/svc/current/deploy/preflight.sh`: `No such file or directory` → FATAL preflight. Three call sites shipped in a release transaction before the first absolute-path invocation caught all of them (2026-09-27, staging re-deploy).

- Rule: sibling scripts are invoked as `"$(dirname "$0")/sibling.sh"` — never with a `./` prefix gluing an absolute dirname back together.
- `"$0"`-relative paths differ by invocation style (relative cwd, absolute, via sudo/wrapper). Test deploy tooling BOTH ways before shipping; the documented usage of transaction scripts is an absolute path, so that is the case that must pass.

## References

- `references/acms-release-drill-evidence.md` — session evidence: exact error strings, drill timeline, recovery commands, ACMS release-record layout.
- Verdict-reading recipe for piped drivers (2026-09-26 first through-the-pipeline deploy of merged PR @137a008): run `bash deploy/x.sh … 2>&1 | tee log | grep -E "INFO|ERROR|ACCEPTED|ROLLBACK"` and capture `"${PIPESTATUS[0]}"` immediately; ALSO match the script's own printed verdict line (`Release ACCEPTED` / `SMOKE TEST PASSED`) in the tee'd log; finish with the standalone smoke test for operator truth.
