# Worker fleet provisioning from golden template 121 — 2026-10-01 session

Multi-worker clone → re-identify → bootstrap → register recipe as executed for
acms-worker-002..005 (STEA-004 A2A production path, Phase 6). Extends
`references/hermes-worker-bringup.md` (single-worker bring-up on VM124) with the
multi-clone path and the traps that only show up at fleet scale. Facts below are
limited to what the session verified via live tool output (PVE API, qga exec,
HTTP probes).

## Placement policy (Jordan, 2026-10-01 — authoritative)

- **acms-worker-001 (VM124) STAYS on miam00111.** CPUs differ across MARION
  nodes; `cpu=host` VMs must never live- or cold-migrate across CPU-different
  nodes. One worker per inference node is explicitly OK.
- New workers: 002→miam00112 (VM125), 003→miam00143 (VM126), 004→miam00144
  (VM127), 005→miam-00100 (VM128 — primary test worker, cloud+local inference).
- MIAM00100 = default-preferred host for NEW general AI-agent workers;
  MIAM00133/MIAM00147 excluded (critical services/backup).
- MIAM-00112 has a known failing DIMM (channel#7, ECC errors persist across
  reboot) — Jordan chose to proceed for modest worker load; on record for
  hardware service.
- **Node-name format trap:** PVE API uses `miam00111`, `miam00112`,
  `miam00143`, `miam00144` (no dash) but `miam-00100` (dash). Always list nodes
  from `/api2/json/nodes` first — name-format assumptions 500.

## CRITICAL: template 121 bakes a STATIC netplan (.203) and NO Hermes runtime

- PVE config shows `ipconfig0: ip=dhcp`, but that is cosmetic — cloud-init is
  disabled in the image (`/etc/cloud/cloud-init.disabled`) and `/etc/netplan`
  pins `10.0.20.203/24` (worker-001's live IP).
- **Every clone of 121 boots into an instant IP collision with the live
  worker-001.** Observed 2026-10-01: four fresh clones all claimed .203 and ARP
  resolved .203 to one of the CLONES' MACs (bc:24:11:10:80:fe = VM127) — the
  exact impostor-IP failure class of the 2026-09-29 VM108 case, at 4× scale.
- Template also carries NO Hermes runtime: no `/home/hermes`, no
  `/opt/hermes-venv`, no systemd units — only legacy `st-agentd` (port 8765,
  ignored by the ACMS path). VM124's Hermes was installed manually 2026-09-27
  via the pip bootstrap (see hermes-worker-bringup.md).
- Template hostname lineage (`miam00111-vllm-vm103`) is baked in too.

## PVE provisioning sequence (offline = cross-CPU-safe)

1. **Clone:** `POST /nodes/{src}/qemu/121/clone {newid, full: 1, target,
   storage: testthin, format: raw}` — 4 clones in parallel OK (~2.5 min total).
2. **Offline storage-migrate while STOPPED:** `POST
   /nodes/{src}/qemu/{id}/migrate {target, targetstorage: local-lvm}` — pass
   `targetstorage` when the source storage (testthin) is absent/empty on the
   destination. A 200G thin clone copies allocated blocks only (~5–15 min).
   `cpu=host` is safe here because the VM boots on the DESTINATION's CPU.
   The qmigrate preflight is the real CPU/compat check — there is no
   reliable cpu-models endpoint (501 on this PVE build).
3. **Start:** `POST /nodes/{dst}/qemu/{id}/status/start`. First boot ~60–90 s;
   `agent/get-osinfo` answering = qga ready.
4. **Task polling correctness:** check
   `/nodes/{src}/tasks/{upid}/status` until `status == "stopped"`;
   `exitstatus == "OK"` means success. A naive poller that treats
   `stopped` as failure misreads every finished task (hit live).

## Clone re-identification recipe (run on EVERY clone after first boot)

```bash
systemctl stop hermes-bridge 2>/dev/null || true   # not present on fresh clones
rm -f /etc/machine-id /var/lib/dbus/machine-id && systemd-machine-id-setup
rm -f /etc/ssh/ssh_host_* && dpkg-reconfigure -f noninteractive openssh-server  # or: ssh-keygen -A
hostnamectl set-hostname <worker-name>
# netplan rewrite (below), chmod 600, netplan apply
```

- `systemd-machine-id-setup` stderr "Initializing machine ID from VM UUID" is
  normal (derives from the per-VM UUID, so clones still diverge).
- **Free-IP verification BEFORE assigning:** ping sweep from a LAN host (ssh
  root@10.0.20.122 works; the workstation's ICMP is firewalled and will report
  false "free") + `ip neigh` ARP on that host — STALE `bc:24:11:*` entries mean
  a Proxmox VM holds the IP; match ARP MACs against each clone's real `net0`
  MAC from PVE config. Assigned 2026-10-01: .206/.207/.208/.209 (verified free).

## Hermes bootstrap per clone (proven pattern)

Stage `/tmp/bootstrap.sh` via qga base64, run under **nohup** (qga wedges on
long execs), log `/tmp/worker-bootstrap.log`:

```bash
id hermes 2>/dev/null || useradd -m -s /bin/bash hermes
python3 -m venv /opt/hermes-venv
/opt/hermes-venv/bin/pip install --quiet --upgrade pip
/opt/hermes-venv/bin/pip install --quiet hermes-agent
```

~2 min/VM when all four run in parallel. Verify with
`/opt/hermes-venv/bin/hermes --version` (0.19.0 on 2026-10-01).

## Per-worker Hermes config (after bootstrap — the still-pending part on the clones)

- **Agent naming convention (Jordan directive, 2026-10-01):**
  `acms-hermes-worker-uid-###` — harness prefix (`hermes` today, e.g.
  `acms-codex-worker-uid-###` for a different harness later); **the UID is THE
  unique identifier** used to distinguish agents regardless of harness.
- Profile: `~/.hermes/profiles/<name>/config.yaml` — custom_providers[0]
  (`llm-manager` → `http://10.0.20.108:8080/v1`, plain-LAN nginx surface; the
  :443 self-signed TLS breaks OpenAI clients) with
  `models: [fast, qwen3.6-35b-a3b, code, gemma4-26b-a4b, qwen3.8-flash-next]`;
  `model.default: qwen3.8-flash-next`; `context_length: 70000`,
  `max_tokens: 8192`, `tools.tool_search.enabled: "on"`.
- **Changing a worker's effective model live** (done on VM124 this session):
  edit the profile config (append alias to custom_providers.models + set
  model.default), keep a `.bak-pre-*` copy, `systemctl restart hermes-bridge`.
  Unmatched request-model aliases are silently ignored (model_routes caveat) —
  the worker config owns the mapping.
- Systemd unit (created manually on VM124, template has none):
  `hermes-bridge.service` — User=hermes,
  `EnvironmentFile=/etc/llm-manager-agent.env` (LLM_MANAGER_AGENT_KEY +
  API_SERVER_KEY), `ExecStart=/opt/hermes-venv/bin/hermes gateway run --profile
  <name> --replace`. Gateway run takes NO --host/--port — those live in the
  profile under `platforms.api_server.extra.{host,port,key}` (0.0.0.0:8402).
  A drop-in alone does NOT change the ExecStart profile arg.
- Each worker needs its OWN LLM Manager virtual key (per-agent keys are the
  auth layer; VM124 uses `agent_key_acms_worker_001` 0600 on VM114). Issue
  siblings via SM `POST /api/service/agents/provision` (idempotent) or LiteLLM
  `/key/generate`.
- Verify: plain `GET :8402/health` → `{"status":"ok","version":"0.19.0"}` +
  `/health/detailed` with bearer API_SERVER_KEY (readiness: state_db / config /
  model / gateway all ok).

## ACMS registration + bridge wiring (per new worker)

- **Register:** `POST https://10.0.20.122/api/v1/agents/register` (NOT
  `/api/v1/agents` — that 405s) with `{external_registration_id: "arm-<name>",
  display_name: <final name>, trust_class: "internal", harness: "hermes",
  bridge_version: "0.19.0", protocol_version: "1"}` → 201 + agent_id. Bearer =
  ACMS_ADMIN_TOKEN from /opt/acms/.env (never echo it).
- **Set the final display name AT REGISTRATION — there is NO display-name
  PATCH endpoint** (404 on `/api/v1/agents/{id}`, hit live). The 4 agents were
  registered as `acms-worker-00N` before the naming directive arrived; they
  need re-registration or a new rename endpoint.
- **Bridge resolution** (`acms/bridge_discovery.py`): SM
  `/api/v1/agent-runtimes` (bearer ACMS_SERVER_MANAGER_TOKEN on CT122) carries
  identity (acms_agent_id ↔ runtime_id, node/vmid, state_sync_health) but
  `bridge_base_url` is NULL → the manual fallback `ACMS_BRIDGE_TARGETS_JSON`
  supplies base_url + api_key. New workers = append entries to that JSON in
  `/opt/acms/.env` + **container RECREATE** (compose env resolves at create
  time; a restart is NOT enough — the credential-activation trap).
- Model policy: migration 0012 seeds the system default
  (local-preferred / qwen3.8-flash-next / cloud allowed); per-agent or
  per-work-item overrides are optional rows in `model_policies`.

## 2026-10-01 Phase A2 UPDATE: golden template REBUILT (VM135) + auto re-identification

- **The NEW golden template is VM 135 `acms-golden-worker-template`** (testthin, template=1,
  miam00111). VM 121 renamed `am-golden-test-v2-wip-RETIRED`; VM 131 (repaired runtime, NO
  re-identify unit) renamed `acms-golden-worker-template-v1-no-reidentify` — both kept as
  rollback. Template 135 adds to everything above: Hermes v0.19.0 venv, aiohttp 3.14.3,
  `hermes-bridge.service` unit (inactive; env injected at clone time), secret-free `*.TEMPLATE`
  placeholder files, DHCP netplan, st-agentd disabled, and **`acms-clone-reidentify.service`**
  (enabled, oneshot, Before=network.target+ssh.service) running
  `/usr/local/sbin/acms-clone-reidentify.sh`.
- **NEW defect class proven live:** clones inherit the parent machine-id → systemd-networkd
  derives an IDENTICAL DHCP client DUID on every clone → **Kea leases the SAME IP to multiple
  clones simultaneously** (two test clones both held 10.0.20.225; the Kea lease table showed one
  row while both guests bound the address). This is the automated root cause behind this file's
  manual re-identification recipe. The unit fixes it at first boot: when machine-id == the
  reference in `/etc/acms-template-identity`, it chmods+removes `/etc/machine-id` (the file is
  **444 read-only — systemd-machine-id-setup SILENTLY no-ops otherwise**), regenerates, copies to
  `/var/lib/dbus/machine-id`, regenerates ALL SSH host keys, writes the new id back to the
  reference file, and RESTARTS systemd-networkd (required for the DUID to change). Idempotent:
  second boot is a no-op (ids differ). Clone-proven: VM136 from 135 booted with a unique
  machine-id, new host-key fingerprint, and its own lease (.227).
- **Clone-time contract** (the only remaining manual step): inject `/etc/llm-manager-agent.env`
  (unique LLM_MANAGER_AGENT_KEY + API_SERVER_KEY), fill `/etc/acms-worker-meta.TEMPLATE`,
  rename/point the Hermes profile, enable+start hermes-bridge, ACMS register +
  ACMS_BRIDGE_TARGETS_JSON append + container recreate.
- **VMID collision trap:** `qm clone` fails "config file already exists" when the VMID is taken
  by a guest on ANOTHER node (VMID 130 = CT130 CI runner on miam-00133; 3 failed attempts before
  the cluster-wide check). ALWAYS allocate via `/api2/json/cluster/nextid` + cluster resources.
- **Templates cannot be booted** — repair runtime in a working-copy VM first, then `qm template`.

## State: FLEET COMPLETE (2026-10-01, second session)

- ALL PENDING ITEMS DONE: profiles + bridge units + env files on VM125-128;
  per-worker LLM Manager keys `agent_key_acms_worker_002..005` (0600 on VM114,
  each proven against LiteLLM); ARM runtime records via direct DB insert
  (adopted-VM semantics w/ honest ownership_meta — no adopt API exists);
  ACMS_BRIDGE_TARGETS_JSON 1→5 entries + container RECREATE (pinned image).
- **aiohttp TRAP (hit on every clone):** the pip bootstrap installs hermes-agent
  ONLY; the api_server platform needs `pip install aiohttp` + bridge restart or
  the gateway logs "No adapter available for api_server" and :8402 never
  listens while systemd shows active. Add to the pre-clone checklist.
- Naming RESOLVED: ACMS PR #60 added migration 0013 (`legacy_name` + `worker_uid`
  columns, backfill legacy_name=display_name) + admin-gated
  `PATCH /api/v1/agents/{agent_id}` (display-only; UUID/external id IMMUTABLE).
  All 5 renamed live to `acms-hermes-worker-uid-00N`; UUIDs preserved.
- Final handoff: `~/acms-a2a-20261001/2026-10-01-ACMS-A2A-PRODUCTION-PATH-FINAL-HANDOFF.md`
  (+ PLAN-OF-RECORD/STEER-LOG/CHECKPOINT-1..3/ROLLBACK/VM123-DISPOSITION).
- VM123 (stopped duplicate acms-worker-001, miam00111): disposition documented,
  NOT destroyed — holds static .203 netplan; NEVER start while VM124 owns .203.
