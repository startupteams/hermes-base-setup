# Server Manager (Agent Runtime Manager) — first provisioning session record

Reference for future worker provisioning / debugging. Repo: `startupteams/llm-manager-project-framework`, package `server_manager/` (ADR-0011).

## Architecture as deployed (2026-09-27, prod e33093ae on VM114)

- `server_manager/common/` — env-first settings (no prod-IP defaults), SQLAlchemy 2.x engine factory for THREE logical DBs (`arm`, `llm`, `litellm` — LiteLLM_SpendLogs lives in the litellm DB, same PG host/role as llmmanager, matching main.py:609 dual-DSN pattern), scoped service-token auth (`SERVER_MANAGER_SERVICE_TOKENS_FILE`, 0600, format `service=token:scope1,scope2`, constant-time compare, mtime-triggered reload).
- `server_manager/agent_runtime_manager/` — greenfield ORM (5 tables: agent_runtimes, provisioning_jobs, provisioning_steps, runtime_events, bridge_registrations) + alembic (migration `0001_arm_initial_schema`, autogen'd from models via pgserver). Deploy integration: `deploy-release.sh` Phase F2 runs ARM alembic in the transaction.
- `server_manager/agent_runtime_manager/providers/proxmox_vm.py` — the §8 safety core:
  - `verify_ownership(provider, node, vmid, runtime, protected_vmids)` — refuses: protected VMID (906 always), missing VM, runtime not marked `created_by_agent_runtime_manager`, unparseable/mismatched/incomplete on-VM marker.
  - Durable marker = JSON in the VM's PVE `description` (keys: server_runtime_id, acms_agent_id, provisioning_request_id, provider, node, vmid, created_by_agent_runtime_manager, created_at, template_source).
  - `wait_clone_lock_release` — during a PVE full clone the config read 500s ("VM is locked (clone)"); a FAILED read is NOT lock-free, keep waiting. `configure_cloud_init` refuses a locked VM (a `vm_config()` failure must count as still-locked — vm_config() swallows errors and returns {}).
  - `ProxmoxVMProvider._call` — PVE API base URL MUST include `/api2/json` (`https://10.0.20.135:8006/api2/json`); token from `/etc/llm-manager/secrets/pve_token` (llm-manager@pve!manager-control).
- `server_manager/agent_runtime_manager/services/provisioning.py` — 8-step state machine (VALIDATING → RESERVING → CLONING_VM → CONFIGURING_CLOUD_INIT → BOOTING (wait_for_ip 420s) → WAITING_GUEST → INJECTING_BRIDGE_CONFIG → HERMES_STATE_BRANCH). `submit()` idempotent on request_id. Failure → job FAILED + runtime ERROR + `provision_failed` RuntimeEvent.
- `server_manager/api_app.py` — combined API (uvicorn :8300, unit `server-manager-api.service`, bind 0.0.0.0 LAN). Routes: POST/GET `/api/v1/agent-runtimes[/{id}]`, `.../desired-state`, DELETE (ownership-gated → 403 on refusal + `destroy_refused` audit), GET `/api/v1/provisioning-jobs/{job_id}`, `/api/v1/model-routes/{route}` (model_registry column is `logical_model_name`, `health` — not model_name/healthy), `/api/v1/usage` (LiteLLM_SpendLogs via the litellm DB), `/api/v1/capabilities`. Auth via FastAPI `Depends(_auth(scope))` — dependency-scoped so 401 fires BEFORE 422 body validation.
- ARM DBs on CT115 (PG 10.0.20.116): `agent_runtime_manager` (prod) + `agent_runtime_manager_staging`, role `arm` (own creds file `/etc/llm-manager/secrets/arm_db_creds`), pg_hba scoped to role arm + the two DBs from VM114 (.108) and VM120 (.131), scram-sha-256.

## Debugging playbook (from the first live provisioning run)

1. Job state + error: `provisioning_jobs` table (error column) + `provisioning_steps` (seq 1-8) + `runtime_events` (provision_failed). All on the ARM DB.
2. "unknown url type: /cluster/nextid" → provider has no API URL (settings/env).
3. PVE 500 "no such file" → missing `/api2/json` in the base URL.
4. PVE 500 "VM is locked (clone)" during CONFIGURING step → clone-lock race; check whether wait_clone_lock_release treats failed config reads as lock-free.
5. Client "timed out" but runtime LIVE → client timeout < provisioning duration; reconcile truth from SM.
6. Replay of old job_id on retry → attempt counter bug.
7. Orphaned clone (job failed, VM left on node): verify provenance via PVE task log (`qmclone` by the manager-control token) BEFORE destroying; fresh template clones carry no unique state.
8. Migration replay vs run_job: `ProvisioningService.run_job(session, job_id)` only executes QUEUED jobs — idempotent submits return the original job without re-running.

## Test suite

`tests/server_manager/` — conftest (session pgserver + alembic head + per-test savepoint rollback + mtime-cached token file fixture with `add_token` helper), 19 tests: ownership safety (8), provisioning state machine (3, fake provider), API auth (7, incl. 401-before-422). CI deps: sqlalchemy, alembic, httpx (TestClient), pgserver. pgserver URI: pin BOTH `postgres://` and `postgresql://` prefixes to `postgresql+psycopg2://` (version-dependent get_uri output).