# Provisioning Hygiene Gate — Live Wiring Notes (2026-09-29, PR #59; Phase D)

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