---
name: dkms-operations
description: "Operate DKMS (Durable Knowledge Management Service): repo, dedicated VM117 + K3s deployment, REST/MCP surface, registry-free build-init deploys, verification playbook, P2-P8 roadmap state."
version: 1.0.0
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
| Auth | Bearer `DKMS_API_TOKEN` — stored ONLY in k8s secret `dkms-secrets` (also holds `DKMS_DATABASE_URL`). Fetch live: `k3s kubectl -n dkms get secret dkms-secrets -o jsonpath='{.data.DKMS_API_TOKEN}' | base64 -d`. Never echo. Unset token ⇒ 503 fail-closed; wrong token ⇒ 401. |
| Access path | qga via `~/bin/pve_qga.py` (node `miam00111`, vmid 117). NO ssh as stagent (template key not staged). qga wedge risk — see pitfalls |
| Work/Jira | ACMS-WORK-000020-20261003_082241 / STNA-91 (Epic clone of STNA-86, id 10997, TO START) |

## Deploy pattern (registry-free build-init)

No Docker/registry exists for this stack. The Deployment overlay
`deploy/k8s/overlays/vm117/dkms-deployment-buildinit.yaml` uses an initContainer
that clones the pinned commit, builds a wheel, and the app container installs
it and runs uvicorn. Deploy loop:

1. `sed "s/DKMS_COMMIT_SHA/<main-sha>/g"` the overlay; ALSO substitute the
   clone URL with a token form `https://jordatech:<gh auth token>@github.com/...`
   (private repo — `.git-credentials` token may be stale; **`gh auth token` is
   the working source**, verify with a 200 against
   `/repos/startupteams/dkms-project-framework` before staging).
2. `python3 ~/bin/pve_qga.py write miam00111 117 <local.yaml> /root/...yaml`
   (sha-verified), `chmod 600`, then
   `k3s kubectl -n dkms delete deployment dkms --ignore-not-found` +
   `apply -f` + `rollout status --timeout=240s`.
3. Migrations run as the `dkms-migrate` Job (clones repo into shared `src`
   emptyDir, runs `alembic upgrade head` there — alembic.ini is NOT packaged
   in the wheel, so migration MUST run from the source tree).
4. Re-apply `namespace.yaml` only for infra changes (it intentionally does NOT
   contain the app Deployment anymore).

Rollback = redeploy any prior main SHA through the same overlay (pin the SHA
in the overlay; the pinned-commit pattern makes rollback exact).

## Verification playbook (each deploy)

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

- **POST /records does NOT dedupe** by design — idempotency lives in
  `dkms.ingest.ingest_source()` (matches source_uid + content_sha256). P3
  event ingestion MUST use the ingest path, or retries duplicate records.
- The record_type enum on the deployed service was implemented with slightly
  different names than the plan's suggestion list — query the 400 error
  message for the live valid set instead of trusting the plan text.

## Pitfalls (live-found)

- **ARM placement vs node-local template storage:** the golden template VM135
  root disk is on node-local `testthin` (miam00111). Placement preferred
  miam-00100 → provisioning failed with `template storage 'testthin' not
  active on placed node`. Fix = LLM-Mgr PR #91 `TEMPLATE_PINNED_CLASSES`
  (`sandbox`, `dkms_service` pin to the template node). Any NEW runtime class
  cloning from that template must be added to that frozenset. Supersede the 2
  failed ARM rows (dkms-service-0001/0002) per the W3 SUPERSEDED precedent.
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
56 tests) · **P2 IN PROGRESS** (`dkms.*` MCP domain in mcp_gateway — Claude
Code packet at `~/dkms-build-20261003/claude-p2-packet.md`, branch
`feat/dkms-mcp-domain` in the ACMS repo) · P3 ingestion (plan-dispatch hook +
ACMS Log Lesson Learned) · P4 failure learning · P5 retrieval/context_pack ·
P6 ACMS artifact pointer model · P7 retention purge + training export +
restore proof · P8 golden workflow with one intentional safe failure event.

Session-state checkpoint: `~/dkms-build-20261003/SESSION-STATE.md`.

### Reference: full P0/P1 evidence + P2 dispatch packet

See `references/p0-p1-execution-evidence-2026-10-03.md` for the complete
live-evidence ledger of the first window (ARM failures→PR #91 fix chain,
K3s bring-up transcript, secret-detector live-found fix PR #4, the STNA-91
Jira→Work→artifact golden-loop identifiers, the 56-test scaffold inventory,
and the standing P2+ session pointers).

Claude Code dispatch pattern that worked: `cat <packet>.md | claude -p
--allowedTools "…" --max-turns 70 --effort medium --output-format json` in a
background terminal (the `$(cat …)` argv-expansion form failed with "Input
must be provided either through stdin or as a prompt argument" — stdin pipe
is the reliable shape for multi-KB packets; verify the packet file exists
before dispatch).
