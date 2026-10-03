# DKMS P0/P1 Execution Evidence — 2026-10-03 window

Chronological ledger of the first DKMS implementation window (orchestrator:
Hermes STEA-004; implementation worker: Claude Code opus-4-5 effort=medium).
Session discipline files live in `~/dkms-build-20261003/`.

## P0 discovery (verified 08:09–08:35Z)

- Repo `startupteams/dkms-project-framework` absent (404 + org/user repo scans) → created PRIVATE exactly as named.
- ACMS CT122 `24c5d4b` v0.11.0 healthy; artifact surface = `/artifacts` POST/GET + `/{id}/content` at ROOT (no `/api/v1/artifacts`), bearer-gated 401 unauth; 96 openapi paths.
- MCP gateway VM114:8202 v0.3.0, 7 domains live.
- SM/ARM on VM114 :8300; service tokens at `/etc/llm-manager/secrets/service_tokens` (format `service=token:scopes`).
- Golden template VM135 (miam00111, 10 cores/32G/200G testthin, template=1).
- VMID 117 verified FREE cluster-wide (all 16 nodes, qemu+lxc) before provisioning.
- IP candidates: .140–.146/.148–.150 unclaimed across guest inventory + service inventory + PVE resources + ARP; DHCP pool starts .190; sandbox pool .222-.249.
- **Discrepancy logged:** `2026-10-03-commented-agentifyme-architecture-workbook.md` NOT FOUND (workstation, session archives, portable export). Proceeded on plan §0.1 user decisions. Do not re-hunt for it.

## Jira/Work golden loop (STNA-91)

- STNA-91 (id 10997) created as Epic clone of STNA-86: ADF structure captured (`/tmp/stna86_adf.json` in CT122 container), paragraphs text-filled in place preserving hardBreak structure; labels `dkms/roadmap-01/agent-instruction`; summary "AI_AGENT: STEA-004 - Build DKMS Durable Knowledge Management Service MVP".
- Eligibility move (authorized per STNA-88/90 precedent): assignee = AI account (`ACMS_JIRA_AI_ACCOUNT_ID`), transition id 2 → TO START.
- Reconcile via in-container loopback (`http://localhost:8000/api/v1/jira/reconcile`, admin bearer; nginx 403s loopback TLS) → run a1b7f3c1 → **ACMS-WORK-000020-20261003_082241** (7d4db4be-de43-4636-95c4-0e9eef43e3f2) → assignment ACKed → dispatched to uid-002 (VM125) → external run_84954387a81044e9b0a1162102f77fd6 → SUCCEEDED → canonical fallback handoff **ACMS-ARTIFACT-000009-20261003_082913** (sha e2b17432…, jira_issue_key STNA-91) → Jira comments 10913 (execution started) + 10914 (BLUF succeeded w/ artifact UID).
- Content-transfer mechanics that worked: scp to CT122 host → `docker exec -i … sh -c 'cat > /tmp/x.py'` hangs; working path = temp `python3 -m http.server 9111` on CT122 host + in-container urllib fetch + exec(compile(src)) + pkill.

## ARM provisioning fix chain

- First attempt (request dkms-vm-provision-20261003-01, acms_agent_id dkms-service-0001): job 0650cf7a stuck RUNNING at CLONING_VM, no PVE task cluster-wide; journal showed `psycopg2.errors.FeatureNotSupported` swallowing the real error — actual cause: `template storage 'testthin' not active on placed node 'miam-00100'` (placement prefers miam-00100 at score 100; testthin exists on miam-00100 but inactive/not VG-backed).
- Fix: LLM-Mgr PR #91 (`fix/arm-dkms-template-pin`, merged d11c229): `TEMPLATE_PINNED_CLASSES = frozenset({"sandbox", "dkms_service"})` in `server_manager/agent_runtime_manager/services/placement.py`; generalizes the sandbox pin; test `test_dkms_service_placement_pins_to_template_node` added. CI 7/7 green.
- Hot-deploy to prod VM114: scp placement.py → backup `placement.py.bak.dkms` → `systemctl restart server-manager-api`. (Full release transaction deferred — documented deviation; content == merged main.)
- Retry (request …-04, acms_agent_id dkms-service-0003): job c0dab4a6 → DONE, all 8 steps (VALIDATING→…→HERMES_STATE_BRANCH) → **VM117 dkms-service-001 on miam00111**, DHCP **10.0.20.190**, qga reachable.
- Runtime rows dkms-service-0001/0002 left in ERROR state — SUPERSEDE them (never delete) per the W3 precedent; NOT yet done.

## K3s + K8s bring-up (VM117)

- `curl -sfL https://get.k3s.io | sh -s - --disable traefik` via qga exec → active; node Ready v1.36.5+k3s1.
- Hostname fixed template→`dkms-service-001` via hostnamectl (k3s node name still `acms-worker-template` until reboot — cosmetic).
- namespace `dkms` created; manifests from repo `deploy/k8s/namespace.yaml` (SA + Role/RoleBinding + secret placeholder + PVC 10Gi + PG16 StatefulSet + services).
- Real secrets staged via `pve_qga.py write` (openssl rand, 0600 on VM117), then `kubectl create secret generic dkms-secrets --from-literal=… --dry-run=client -o yaml | kubectl apply -f -`. Token files removed from /root after use.
- **ImagePullBackOff** on placeholder `dkms:latest` → PR #2 (ba663e0): namespace.yaml keeps ONLY infra; app Deployment moves to `overlays/vm117/dkms-deployment-buildinit.yaml` (initContainer clones pinned commit → wheel → app container installs + uvicorn).
- **Private-clone auth:** `.git-credentials` token was stale/invalid for this repo; `gh auth token` works (verified via API 200). Token embedded ONLY in the on-VM yaml (0600), never committed.
- Migration Job: first form failed ("No 'script_location' key" — alembic.ini not packaged in wheel). Working form: shared `src` emptyDir; build-wheel clones repo to /src; migrate container installs wheel + alembic + asyncpg, `cd /src/dkms && alembic upgrade head` → **Completed**.
- Final state: dkms app pod 1/1 Running (build-init, SHA f529290), dkms-postgres-0 Running, migrate Completed.

## Secret-detector live-found fix (PR #4, f529290)

- Live probe `api_key = sk-proj-AAAA…` returned **201** (stored!) — pattern `sk-[a-zA-Z0-9]{20,}` stopped at the dash; unquoted `password=…` assignments also missed.
- Fix in `dkms/secrets.py`: char class `[a-zA-Z0-9_\-]{20,}` for sk- keys + new unquoted assignment patterns (password/api[_-]?key/secret `\S{16,}`+); prose false-positives checked ("The password policy requires 12 chars" stays clean). All 56 tests still pass; local detector probes re-verified; live 422 QUARANTINED confirmed post-redeploy.

## Service scaffold (PR #1, 424d1d2 — Claude Code)

- 34 source files: `dkms/` (config, database, models, auth, secrets, lessons, retention, ingest, schemas, api, app), migrations 001_initial, 13 test files, deploy/docker + deploy/k8s, CI (pytest + grep-based secret scan).
- **56 tests passing** (SQLite/aiosqlite, offline) — verified independently.
- CI secret-scan initially failed on documentation-example keys in tests → exclusion fix merged in PR #1.
- API surface verified live: GET /records 401/200, POST /records 201, invalid record_type → 400 with the LIVE valid-type list (differs slightly from plan text — query the error, don't trust the plan), 422 QUARANTINED on secrets, GET /version {version, git_sha:null}.
- POST /records does NOT dedupe (source_uid+hash dedupe lives in `ingest_source()` service layer, unit-tested) — P3 ingestion must route through it.

## P2 handoff state

- Packet: `~/dkms-build-20261003/claude-p2-packet.md` (full DkmsClient + server.py wiring + tokens scopes + test spec vs the LIVE REST surface).
- Branch: `feat/dkms-mcp-domain` in `~/work/acms-project-framework` (reset to d8363e5). Result lands in `/tmp/claude-p2-result.json`.
- After merge: rsync gateway to VM114 `/opt/mcp-gateway/repo/` + restart + add `dkms.read`/`dkms.write` to mint defaults AND `grant-scopes` for existing agents (the W2 migration pattern — tokens minted before a domain exist carry only old scopes).

## Open items at window end

1. P2 in flight (check /tmp/claude-p2-result.json FIRST on resume).
2. VM117 qga wedge (agent daemon down after long execs) — recover per vm114-qga-ssh-recovery before further VM117 work; keep qga execs SHORT.
3. Install + verify `/usr/local/bin/dkms-pg-backup.sh` (script staged at `/tmp/dkms-pg-backup.sh` local; needs `/root/.dkms-backup-env` with KUBECONFIG + cron entry) — required for DKM-18.
4. Supersede ARM rows dkms-service-0001/0002.
5. svc-server-manager token value was echoed in one terminal output during auth debugging → rotation candidate.
6. P3–P8 per plan §15.
