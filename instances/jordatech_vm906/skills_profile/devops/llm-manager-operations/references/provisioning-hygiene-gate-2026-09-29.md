# Provisioning Hygiene Gate — Live Wiring Notes (2026-09-29, PR #59; Phase D)

> **2026-10-02 W4 UPDATE — 3 live-found clone-provisioning bugs (PRs #76/#77/#78), first-ever
> exercise of the clone path since placement-as-code (all 5 production workers were ADOPTED
> runtimes, so the clone path was never hit cross-node before):**
>
> 1. **Clone target (PR #76):** `clone_template()` pinned `target=spec.template_node` — the VM
>    LANDED ON THE TEMPLATE NODE while `wait_clone_lock_release()` polled the PLACED node's vmid
>    (which doesn't exist there) → 240s timeout → job FAILED + orphan VM on the template node.
>    Fix: `target=spec.node`. Regression: `tests/server_manager/test_clone_target.py`.
> 2. **Template-storage gate (PR #77):** cross-node full clone 500s when the template's
>    node-local storage is inactive on the target ("can't clone VM to node X (VM uses local
>    storage…)"). Golden template 121's root disk = `testthin` (lvmthin, INACTIVE on miam-00100).
>    Fix: `template_storage()` + `storage_active()` provider methods checked BEFORE the clone;
>    fail closed with an honest error. Fake providers must stub both.
> 3. **Sandbox placement pin (PR #78):** `runtime_class=sandbox` pins to the template node
>    (reason `sandbox_pinned_to_template_node`) — node-local template storage makes cross-node
>    placement impossible until testthin is active cluster-wide or the template is replicated.
>
> **🚨 CRITICAL DHCP finding (live-proven 2026-10-02):** a clone-provisioned sandbox VM's DHCP
> lease was `10.0.20.203` — worker-001's STATIC IP. Transient ARP conflict (~60s risk to
> worker-001 bridge traffic); VM powered off + destroyed; worker recovered (bridge 200 after
> ARP refresh). **Worker statics sit INSIDE the Kea lease pool** — any clone-provisioned VM
> risks grabbing them. Sandbox create paused until Jordan picks: Kea static reservations /
> sandbox DHCP class / gateway-managed static pool + `ipconfig0`.
>
> **PVE name rule (live-found):** VM names REJECT underscores ("invalid format — not a valid
> DNS name"). Sandbox naming: `sbx-<work_uid>-<agent>` with `_`→`-`, lstrip/rstrip dashes,
> start alnum, ≤63.
>
> **Sandbox TTL substrate (PR #75):** `runtime_class="sandbox"` + `sandbox_expires_at`
> (migration 0004_sandbox_ttl) + `ownership_meta={kind, ttl_hours}`; TTL sweep
> (`expire_stale_sandboxes`) runs FIRST in `reconcile_all()` → DESIRED_DESTROYED flip
> (API-only, idempotent); `POST /agent-runtimes/{id}/extend-ttl` (sandbox-only 422, bounded
> by `SERVER_MANAGER_ARM_SANDBOX_{DEFAULT,MAX}_TTL_HOURS` = 8/72, audited).
>
> **qga/wait_for_ip note:** the provider's `wait_for_ip` uses `agent/network-get-interfaces`
> (DASHED path — correct). A 501 on un-dashed `network-getinterfaces` in ad-hoc probes is a
> probe-path bug, not the guest. Also: a FAILED job's runtime row keeps `vmid=NULL` even when
> the VM was created — orphan VMs need direct PVE disposal (ownership marker lives in the VM
> description; job rows stay ERROR-honest, never fabricated to match).

## What the gate is

`server_manager/agent_runtime_manager/services/provisioning.py` step 6
`HYGIENE_GATE` (fail-closed) runs between BOOTING (IP acquired) and any
READY/bridge registration, wrapping the PR #57 module
`services/clone_hygiene.py::verify_clone_identity()`.

## Checks performed (in order)

1. `vmid_valid` — nonzero (VMID uniqueness is structural via PVE)
2. `mac_valid` — MAC format AND not template-default (`BC:24:11:00` prefix
   rejected)
3. `hostname_reidentified` — set, not `template*`
4. `ip_not_owned_by_other_runtime` — candidate IP vs OTHER runtimes'
   ownership_meta IPs (from `AgentRuntime` rows; the marker's OWN claim is fine)
5. `netplan_reidentified` — guest netplan statics via qga
   (`_guest_netplan_static_ips`) must not conflict with the intended IP
   (THE VM108/VM124 .203 impostor class)
6. `guest_identity_matches` — clone-time ownership marker's
   `acms_agent_id` == runtime's acms_agent_id

## Failure semantics (fail-closed, durable)

- `HygieneError` → job FAILED with `clone hygiene gate rejected VM <id>`
- runtime `actual_state=ERROR`, **vmid NOT promoted** (stays NULL — the VM
  exists but is never operational; the vmid lives in the failure event)
- durable `clone_hygiene_failed` RuntimeEvent (vmid/ip/policy
  `fail_closed_no_ready`) for human disposal — the failed VM is NEVER
  auto-destroyed
- verdict persisted in `runtime.ownership_meta["clone_hygiene"]`
  (`ok: false, error: …`) — durable, not just a log line
- Retry = NEW request → fresh VMID/identity allocation (attempt counter
  `|retry:N`); the failed candidate is never reused

## Guest identity source pre-bootstrap

The guest cannot report its own agent id before Hermes is bootstrapped — the
durable PVE `description` ownership marker (written at clone time, §8) IS the
identity source of truth. `vm_config()` → `net0` (MAC) + `description` (JSON
marker). Any test fake provider must return BOTH.

## Test patterns (tests/server_manager/test_provisioning_hygiene_gate.py)

- `_svc(monkeypatch, fake)` replaces the provider AND wraps `submit` so
  `fake.agent_id = req.acms_agent_id` before run — otherwise the marker's
  agent id is the class's stale `__init__` default and identity checks fail
  for the wrong reason.
- `arm_session` fixture = embedded pgserver PG16, one schema per test via
  transaction rollback. Extra `AgentRuntime` rows need
  `provisioning_request_id` (NOT NULL constraint).
- Patch `clone_hygiene._guest_netplan_static_ips` to simulate inherited
  netplans (qga not available in tests).
- Assertions must match reality: job FAILED → `runtime.vmid is None`
  (promoted only on success path); the vmid for disposal lives in the
  `clone_hygiene_failed` event detail.

## VM108/VM124 case file

See `references/ip-collision-10-0-20-203-case-2026-09-29.md` in the ACMS
operations skill for the original incident (ARP favored the most-recently-
booted impostor; every app-level check passed).