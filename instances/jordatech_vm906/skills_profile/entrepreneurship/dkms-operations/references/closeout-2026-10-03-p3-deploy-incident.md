# DKMS close-out sweep — 2026-10-03 ~13:15–13:35Z

Session-close verification pass that started as "confirm the P3 background
run" and ended up catching a silently-wrong deployment. Full incident chain
recorded here; durable rules were folded into SKILL.md.

## Timeline (all UTC)

| Time | Event | Evidence |
|---|---|---|
| 12:17 | P3 Claude run completes: PR #8 opened, later MERGED (`a6a06af`); result JSON: success, 34 turns, $1.89 | `/tmp/claude-p3-result.json` |
| 13:20 | Session-close check: `https://10.0.20.190:30800/health` → HTTP:000 from workstation AND VM114 | curl |
| 13:22 | False alarm diagnosed: DKMS NodePort is PLAIN HTTP. `http://…:30800/health` → 200. Even `https://127.0.0.1:30800` INSIDE the VM → 000 (rules out network path issues entirely) | curl |
| 13:24 | VM117 host-key-changed scare: PVE task log shows `qmdestroy 117` 10-02 13:24 (W4.1 sandbox tenant) → `qmconfig+qmstart` 10-03 08:35 (DKMS provision). Rebuild, not impostor | `/nodes/miam00111/tasks?vmid=117` |
| 13:26 | REAL bug: running pod has NO `/ingest/*` routes. Init log: `fatal: remote error: upload-pack: not our ref 3d57449` — depth-1 clone couldn't fetch the pinned SHA, `|| true` fallback built the clone tip (pre-P3; pod started 11:43Z < P3 merge 12:17Z) | init-container logs |
| 13:28 | PR #9 opened: fail-closed SHA pin (FATAL on unsubstituted/unfetchable), GITHUB_TOKEN wiring committed (was on-cluster-only drift), deploy README updated | fix/buildinit-failclosed-sha |
| 13:30 | Redeploy attempt 1 fails: overlay rendered from workstation lacked GITHUB_TOKEN env → clone 401s ("could not read Username") — fail-closed logic surfaced the drift | init logs |
| 13:31 | Attempt 2 fails: variable-name mismatch (`$KUBE_BUILD_PINNED_SHA` never assigned from the substituted placeholder) | init logs |
| 13:32 | Attempt 3 fails: **sed self-substitution** — `sed s/DKMS_COMMIT_SHA/<sha>/g` rewrote the guard's own comparison literal, making the unsubstituted-check always-true. Fix: split sentinel `"DKMS_COMMIT""_SHA"` in the overlay | rendered yaml + init logs |
| 13:35 | SUCCESS: pod `1/1 Running`, `BUILD_PIN=a6a06af…` in init logs, all 4 `/ingest/*` in external openapi.json | kubectl + curl |
| 13:37 | Idempotency live-proven: identical plan ingest twice → 201 then 200, SAME uid `70f850d6606a45069f4311778c3ddefe` | REST |
| 13:38 | Gateway REST re-verified vs new pod: records/search/audit → 200/200/200 (base `http://10.0.20.190:30800`) | curl via VM114 |

## Lessons (class-level, not one-off)

1. **"Merged in git" ≠ "running in prod"** for build-from-source deploys.
   The only authoritative checks are (a) the build pin echo from the init
   logs and (b) route presence in the externally-fetched openapi.json.
   An in-pod route-print via `kubectl exec` fails closed (no DB env) and
   misleads.
2. **Deploy-time `sed` on a template rewrites the template's own guard
   literals.** Any placeholder that appears in a comparison/error string
   must be split (shell: `"X""_Y"` concat) or the sed will corrupt the
   guard. Generalizes to any sed-substituted manifest with self-checks.
3. **`|| true` + fetch-failure in a build step = silent wrong-version
   deploys.** Fail closed on pin verification; the failure mode is worse
   than the inconvenience (here: P3 features absent while everyone believed
   them live).
4. **HTTP:000 → check scheme before checking infrastructure.** Plain-HTTP
   NodePort + https probe = identical signature to a dead service.
5. **Host-key change on a recycled VMID:** discriminate rebuild vs impostor
   via the PVE task log (destroy/recreate trail) — same instinct as the
   VM108 .203 netplan impostor, opposite conclusion.
6. **Fail-closed guards earn their keep by surfacing drift:** attempt 1's
   FATAL was correct behavior exposing GITHUB_TOKEN wiring that existed
   only on-cluster and never in git.

## Token/exposure notes

- `dkms-secrets` GITHUB_TOKEN fragment (`gho_ohtV3is1…`) rendered in
  transcript during secret inspection → add to rotation list.
- Gateway tokens DB (`/var/lib/miam-mcp-gateway/tokens.sqlite3`) is
  hash-only (sha256) — raw exec token NOT recoverable; mint new if lost.
- svc-server-manager token: already on rotation list from prior window.

## PRs

- DKMS PR #9 `fix/buildinit-failclosed-sha` — 3 commits, CI green
  (secret-scan + test), MERGEABLE, awaiting Jordan merge. Merges the
  fail-closed pin + committed token wiring + README deploy procedure
  (BUILD_PIN verification step included).