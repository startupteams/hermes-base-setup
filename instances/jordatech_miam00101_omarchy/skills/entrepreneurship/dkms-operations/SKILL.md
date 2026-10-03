---
name: dkms-operations
description: "Operate DKMS (Durable Knowledge Management Service): repo, dedicated VM117 + K3s deployment, REST/MCP surface, registry-free build-init deploys, verification playbook, P2-P8 roadmap state."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [dkms, kubernetes, k3s, knowledge-service, jordan-workflow]
---

# DKMS (Durable Knowledge Management Service) Operations

DKMS is the durable knowledge layer for AI-agent operations (plans, handoffs,
ADRs, failure learning, lessons, training candidates). It is a NEW dedicated
service — NOT inside the ACMS container, NOT a Work-statistics DB. Canonical
decisions live in the repo docs (`docs/SERVICE_BOUNDARY.md`, ADR-0001/0002)
and the plan `2026-10-03-agentifyme-dkms-ai-agent-implementation-plan-v2.md`
(Jordan-authored, V2 — its §0.1 user decisions are authoritative; the
`commented-agentifyme-architecture-workbook.md` source file was never found —
do not keep hunting for it, its decision content was re-supplied in the plan).

## Identity map (live 2026-10-03)

| Item | Value |
|---|---|
| Repo | `startupteams/dkms-project-framework` (private; local `~/work/dkms-project-framework`) |
| Service VM | **VM117 `dkms-service-001`** on node `miam00111`, DHCP 10.0.20.190, provisioned via SM/ARM (runtime_class `dkms_service`) |
| Kubernetes | K3s v1.36.5 on VM117; namespace `dkms`; kubectl via `k3s kubectl` (KUBECONFIG `/etc/rancher/k3s/k3s.yaml`) |
| Pods | `dkms` (FastAPI app), `dkms-postgres-0` (PG16 StatefulSet + PVC `dkms-postgres-pvc`), `dkms-migrate` Job (Completed) |
| Endpoint | K8s ClusterIP `dkms.dkms.svc:8000` inside pod net; **host-reachable via NodePort `10.0.20.190:30800`** (from VM114/gateway: 200) |
| Auth | Bearer `DKMS_API_TOKEN` — stored ONLY in k8s secret `dkms-secrets` (also holds `DKMS_DATABASE_URL`, `GITHUB_TOKEN` for the build-init clone). Rotate-pair: the gateway env `MCP_GATEWAY_DKMS_TOKEN` on VM114 (`/etc/miam-mcp-gateway/env`) must equal the k8s secret value; on rotation update BOTH + rollout-restart the deployment. Never echo. Unset token ⇒ 503 fail-closed; wrong token ⇒ 401. VM117 side-staged copy: `/root/.dkms_api_token` (0600). |
| Access path | qga via `~/bin/pve_qga.py` (node `miam00111`, vmid 117). NO ssh as stagent (template key not staged). qga wedge risk — see pitfalls |
| Work/Jira | ACMS-WORK-000020-20261003_082241 / STNA-91 (Epic clone of STNA-86, id 10997, TO START) |

## Deploy pattern (registry-free build-init)

No Docker/registry exists for this stack. The Deployment overlay
`deploy/k8s/overlays/vm117/dkms-deployment-buildinit.yaml` uses an initContainer
that clones the pinned commit, builds a wheel, and the app container installs
it and runs uvicorn. Since PR #9 the pin is **fail-closed** and the clone
authenticates from `dkms-secrets` (GITHUB_TOKEN → x-access-token URL) — both
wired in the overlay itself; do not hand-edit them back out. Deploy loop:

1. `sed "s/DKMS_COMMIT_SHA/<main-sha>/g"` the overlay. **The pin must be the
   origin/main TIP** — a depth-1 clone cannot fetch older SHAs
   (`upload-pack: not our ref`), and pre-#9 the `|| true` fallback silently
   built the clone tip instead, deploying WRONG-but-plausible code (live
   incident: pod ran pre-P3 code for its whole life while "P3 merged" was
   true in git). Fail-closed now FATALs on unsubstituted/unfetchable pins —
   that error is the guard working, not a bug to work around.
   **Sed self-substitution trap:** the deploy sed rewrites EVERY
   `DKMS_COMMIT_SHA` occurrence, including the guard's own comparison
   literal, which turns the unsubstituted-check into an always-true
   equality (FATAL forever, even with a correct pin). That is why the
   sentinel in the overlay is split (`"DKMS_COMMIT""_SHA"`) — keep it split;
   never "fix" it back to a whole literal.
2. `python3 ~/bin/pve_qga.py write miam00111 117 <local.yaml> /root/...yaml`
   (sha-verified), `chmod 600`, then
   `k3s kubectl -n dkms delete deployment dkms --ignore-not-found` +
   `apply -f` + `rollout status --timeout=240s`.
3. After rollout, **prove the pod runs the pinned code**: init logs must
   show `BUILD_PIN=<sha>`, and `curl http://10.0.20.190:30800/openapi.json`
   (from workstation/VM114) must list the routes you expect. Do NOT trust
   "merged in git" or an in-pod python route-print — an `kubectl exec` shell
   has no DKMS_DATABASE_URL, so the app import fails closed there and the
   route list comes back empty/misleading. The external openapi.json check
   is authoritative.
4. Migrations run as the `dkms-migrate` Job (clones repo into shared `src`
   emptyDir, runs `alembic upgrade head` there — alembic.ini is NOT packaged
   in the wheel, so migration MUST run from the source tree).
5. Re-apply `namespace.yaml` only for infra changes (it intentionally does NOT
   contain the app Deployment anymore).

Rollback = redeploy any prior main SHA through the same overlay (pin the SHA
in the overlay; the pinned-commit pattern makes rollback exact).

## Verification playbook (each deploy)

**Deploy path for the VM114 gateway is RSYNC, not a release transaction** —
`/opt/mcp-gateway/repo` has NO `.git` (rsync-staged from the workstation).
Rsync `mcp_gateway/` (+ changed tests) → run the dkms test suite ON VM114
(`.venv-acms/bin/python -m pytest tests/test_mcp_gateway_dkms.py`) →
sha-verify against `origin/main` → restart `miam-mcp-gateway` → healthz
must list `dkms` in `"domains"`. Details + full live-evidence ledger:
`references/p2-p3-window-evidence-2026-10-03.md`.

**Every fix to the DKMS pod is verified against the NEW pod, not the old
one.** Stale file-surgery across pod restarts silently reverts; delete the
pod and re-apply into the fresh one. Restart the python app inside the
container with `python3 -c 'import os; os.kill(1, 15)'` (python:3.12-slim
has no `kill` binary). The app lives at
`/usr/local/lib/python3.12/site-packages/dkms/` (wheel install — there is
NO `/app`).

```bash
# from VM117 via qga exec:
TOKEN=$(k3s kubectl -n dkms get secret dkms-secrets -o jsonpath='{.data.DKMS_API_TOKEN}' | base64 -d)
PODIP=$(k3s kubectl -n dkms get pod -l app=dkms -o jsonpath='{.items[0].status.podIP}')
curl -s http://$PODIP:8000/health                                   # {"status":"ok"}
curl -s -o /dev/null -w '%{http_code}' http://$PODIP:8000/api/v1/records          # 401 unauth
curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" .../records  # 200
# secret rejection (MUST be 422, was live-found returning 201 before the fix):
curl -s -o /dev/null -w '%{http_code}' -X POST -H auth... -d '{"record_type":"plan","title":"sec","body_markdown":"api_key = sk-proj-AAAAAAAAAAAAAAAAAAAAAAAAAAAA"}' .../records
# clean write (201) — valid record_type set: plan|decision|handoff-summary|handoff-source|lesson_learned|implementation|playbook|evaluation_finding etc.
```

- **POST /records is idempotent since PR #6 (`3d57449`, 2026-10-03):** same
  `(source_uid, content_sha256)` on an active record returns **200 + the
  original uid** (not 201, no duplicate). Before that fix live replays
  duplicated — the smoke history on VM117 contains superseded dupes (kept,
  marked `status=superseded` + `supersedes_uid`, per the never-delete rule).
- The record_type enum on the deployed service was implemented with slightly
  different names than the plan's suggestion list — query the 400 error
  message for the live valid set instead of trusting the plan text. Current
  set includes: `plan, decision, handoff-summary, summary, lesson_learned,
  implementation, review, playbook, architecture, raw-transcript, raw-log,
  raw-event, source-file, source-artifact, test-result`. Mapping note:
  plan §7.1's `handoff_summary` → `handoff-summary`,
  `architecture_decision` → `decision`/`architecture`.

## Pitfalls (live-found)

- **DKMS NodePort 30800 is PLAIN HTTP, not TLS.** `https://…:30800` probes
  return HTTP:000 (TLS handshake against a plain-HTTP listener — even from
  inside the VM against 127.0.0.1). This masqueraded as a total outage
  during the close-out sweep while the service was healthy the whole time.
  The gateway config (`MCP_GATEWAY_DKMS_BASE_URL=http://10.0.20.190:30800`)
  is correct as-is. Rule: an HTTP:000 on this endpoint means "wrong scheme",
  not "down" — probe `http://` first, then check pods.
- **Changed SSH host key on .190 = VMID reuse, not impostor — verify via PVE
  task log first.** VMID 117 was destroyed 2026-10-02 13:24 (by a W4.1
  sandbox tenant) and recreated 2026-10-03 08:35 for DKMS, so the host-key
  change was EXPECTED. Discriminate impostor vs rebuild by reading
  `/nodes/<node>/tasks?vmid=<id>` (qmdestroy/qmstart timestamps) — the
  VM108 .203 netplan-collision impostor had no destroy/recreate trail.
  Same class as the .203 trap but with the OPPOSITE conclusion.
- **Gateway token store is hash-only by design** (VM114
  `/var/lib/miam-mcp-gateway/tokens.sqlite3`, sha256 of the raw token).
  You CANNOT recover an exec/agent token from the DB — only mint new ones.
  Don't burn time brute-forcing candidate values against hashes; the MCP
  dkms path was already proven end-to-end (`dkms_record_lesson` → record).
- **`kubectl exec` shells lack pod env vars:** running
  `python -c 'from dkms.app import app; …'` inside an exec shell fails
  closed (no DKMS_DATABASE_URL) and prints an empty/misleading route list.
  Route-truth comes from the external `openapi.json` check.
- **Transcript-exposed credentials → rotation list:** the dkms-secrets
  GITHUB_TOKEN (`gho_…`) and svc-server-manager token have both appeared in
  terminal output across windows. Rotate both at the next credential window
  (k8s secret + rollout-restart; VM114 env + gateway restart).

- **MCP resources/read with query-string URI templates = "Unknown resource"
  until PR #94:** the FastMCP SDK's `ResourceTemplate.matches()` regex-
  converts templates naively — a bare `?` in `dkms://search?q={query}` becomes
  an optional-quantifier, so those templates never match ANY uri. Fixed
  gateway-wide via `GatewayServer._patch_template_matching()` (ACMS PR #94,
  idempotent monkeypatch in `__init__`). Live gate after any gateway deploy:
  read all 5 dkms param'd resources with REAL values (search?q=…,
  records/recent?limit=…, export/markdown?work_uid=…, record/{uid},
  record/{uid}/related) — 5/5 expected. `export/markdown` without any param
  stays "Unknown resource" (template requires the var).
- **DKMS failure/attempts REST contract:** `symptoms`/`evidence`/
  `side_effects` are DICT fields (strings → 422 dict_type); `attempt_number`
  is server-assigned (do not send); failure lookup for `/attempts` uses the
  FULL 32-hex uid (truncated → 404 "Failure not found"); link UIDs must be
  full-length too (FK → 500 IntegrityError on truncated).
- **K3s local-path PVs pin nodeAffinity to hostname — IMMUTABLE:** after the
  stale node (`acms-worker-template`) was force-deleted, the postgres PV kept
  `kubernetes.io/hostname In [acms-worker-template]` → pod Pending forever,
  and patching the PV's affinity 422s (field immutable). Fix chain: delete
  pod → delete PVC → `rm -rf /var/lib/rancher/k3s/storage/pvc-*_<pvc-name>` →
  re-create the PVC (local-path re-provisions on the live node) → statefulset
  rebinds. Postgres durability across pod restart: PROVEN (18 records before
  = 18 after).
- **Rotation-pair trap:** gateway env token and k8s secret MUST be the same
  64-hex value — a 48-vs-64 mismatch produced 401 "Invalid token" with a
  perfectly healthy service. Update BOTH (k8s secret + rollout-restart
  deployment, VM114 env + restart gateway) and probe 200 before proceeding.
- **ARM placement vs node-local template storage:** the golden template VM135
  root disk is on node-local `testthin` (miam00111). Placement preferred
  miam-00100 → provisioning failed with `template storage 'testthin' not
  active on placed node`. Fix = LLM-Mgr PR #91 `TEMPLATE_PINNED_CLASSES`
  (`sandbox`, `dkms_service` pin to the template node). Any NEW runtime class
  cloning from that template must be added to that frozenset. ✅ Done
  2026-10-03: the 3 failed ARM rows (dkms-service-0001/0002) are SUPERSEDED
  via `POST :8300/api/v1/agent-runtimes/{id}/supersede` with
  `{"superseded_by_runtime_id": "<live-runtime-uuid>", "reason": ...}` (the
  field is REQUIRED; requests without it 422). Jobs stay RUNNING in
  provisioning_jobs — job state and runtime state are separate columns;
  the reconciler ignores superseded runtimes (W3 precedent).
- **SM service-token format (live-found):** lines are `svc-name=token:scopes`;
  the bearer token EXCLUDES the `:ALL` scope suffix (48 chars, not 52). Both
  credential files needed: `service_tokens` (API bearer) + `arm_db_creds`
  (PG as user `arm`, db `agent_runtime_manager` — the `llmmanager` PG user
  CANNOT read ARM tables; separate DB + creds by design).
- **qga wedge on VM117 (hard class):** four wedge episodes 2026-10-03
  (~09:15, ~10:45, ~11:05, ~11:20 UTC), each after long execs (heredocs, big
  curl payloads through exec, rm -rf loops). Recovery =
  `POST /nodes/miam00111/qemu/117/status/reset` (see
  `vm114-qga-ssh-recovery` for the verb + diagnostics). k3s pods restart
  from PVCs cleanly each time. Aggravator to avoid: long-running qga exec
  commands (>60s) — chunk operations; if a wedge hits mid-`kubectl apply`,
  RE-RUN the apply after reset rather than resuming mid-flow (apply is
  idempotent). Large JSON payloads → `pve_qga.py write` a file, then
  `curl -d @file` inside the guest.
- **Provisioning service VMs through ARM:** `POST :8300/api/v1/agent-runtimes`
  requires `acms_agent_id` (min 8 chars) even for non-agent VMs — used
  `dkms-service-000N` as a durable pseudo-identity; `harness:"none"`,
  `runtime_class:"dkms_service"`. Job polling via
  `GET /api/v1/provisioning-jobs/{job_id}` (UUID, not request_id). Idempotent
  on request_id — new attempt needs a NEW request_id.
- **qga wedge on VM117:** the guest agent died mid-window (500 "QEMU guest
  agent is not running") after long execs (big heredocs, pip installs during
  provisioning). Same class as VM114. Recover per `vm114-qga-ssh-recovery`
  (wait/self-recover, file-write nudge); keep execs SHORT — write files via
  `pve_qga.py write` (sha-verified), exec only short commands.
- **First deploy hit ImagePullBackOff** on `dkms:latest` from the placeholder
  manifests — the build-init overlay exists precisely to avoid registry
  dependence; don't reintroduce `image: dkms:latest`.
- **CI secret-scan vs test fixtures:** `tests/test_secrets.py` contains
  documentation-example keys (AKIA…EXAMPLE); the CI scan excludes that file
  via `git grep … -- ':!tests/test_secrets.py'`. Keep the exclusion when
  adding example-key tests.
- **PBS coverage:** `marion-pbs-daily-all` (all=1) covers VM117 automatically.
  Logical PG backup script (`/usr/local/bin/dkms-pg-backup.sh`, nightly
  pg_dump → gzip → sha256, keep 14) was STAGED but not yet installed+verified
  when qga wedged — finish that before claiming DKM-18.

## Roadmap state (plan §15)

P0 ✅ (discovery, STNA-91 + WORK-000020) · P1 ✅ (repo+VM+K3s+schema live,
56 tests; PVC durability proven 2026-10-03: PG pod deleted→recreated, 18
records before = after) · **P2 ✅ MERGED** (ACMS PRs
#93+#94, live on VM114, 5/5 resources + 8 tools + quarantine verified
through real MCP) · **P3 ✅ MERGED + LIVE on VM117** (DKMS PR #8 `a6a06af`
— `/ingest/plan`, `/ingest/handoff` w/ source+summary+summarizes-link,
`/ingest/timeline`, all idempotent; live proof: replay → 201 then 200, same
uid; BUILD_PIN=a6a06af; written autonomously by background
Claude Code per Jordan's steering: autonomous background runs +
markdown-handoff-on-completion, Hermes supervises/merges only) ·
**Deploy-hardening PR #9 CI-green, awaiting Jordan merge** (fail-closed
SHA pin + committed GITHUB_TOKEN wiring — merge before next deploy) ·
P4 seeded (failure+attempt+validated lessons+links LIVE; lifecycle
UI/playbook promotion remain) · P5 retrieval/context_pack · P6 ACMS
artifact pointer model · P7 retention purge + training export + restore
proof (PG backup script staged, NOT installed) · P8 golden workflow with
one intentional safe failure event.

Session-state checkpoint: `~/dkms-build-20261003/SESSION-STATE.md`;
window handoff: `~/dkms-build-20261003/HANDOFF-20261003-DKMS-WINDOW.md`.
Close-out sweep incident (plain-HTTP false alarm, VMID-reuse host key,
pre-P3 silent fallback deploy, sed self-substitution trap, PR #9 chain):
`references/closeout-2026-10-03-p3-deploy-incident.md`.

### Reference: full P0/P1 evidence + P2 dispatch packet

See `references/p0-p1-execution-evidence-2026-10-03.md` for the complete
live-evidence ledger of the first window (ARM failures→PR #91 fix chain,
K3s bring-up transcript, secret-detector live-found fix PR #4, the STNA-91
Jira→Work→artifact golden-loop identifiers, the 56-test scaffold inventory,
and the standing P2+ session pointers), and
`references/p2-p3-window-evidence-2026-10-03.md` for the second window
(P2/P3 completion, MCP live gate results, token rotation-pair, K3s PV/
hot-fix-deploy/secret-wiring lessons, P4 seed records, plan §15 checkpoint).

Claude Code dispatch pattern that worked: `cat <packet>.md | claude -p
--allowedTools "…" --max-turns 120 --effort medium --output-format json` in a
background terminal (the `$(cat …)` argv-expansion form failed with "Input
must be provided either through stdin or as a prompt argument" — stdin pipe
is the reliable shape for multi-KB packets; verify the packet file exists
before dispatch). The packet MUST: (a) allowlist BOTH `python` and
`python3` variants plus every tool the packet demands, (b) pre-authorize the
verify command verbatim ("run: python3 -m pytest tests/X -q"), (c) mandate
a markdown handoff file written EARLY and updated, and (d) demand a final
`P<n>-DONE pr=<number>` line. The successful P3 run (34 turns, $1.89 vs the
failed P2 run's 81 turns/$6.67) followed all four.
