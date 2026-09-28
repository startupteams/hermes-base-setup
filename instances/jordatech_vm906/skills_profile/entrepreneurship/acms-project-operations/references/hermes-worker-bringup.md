# Hermes worker runtime bring-up recipe (as executed on acms-worker-001 / VM 124, 2026-09-27)

Step-by-step for booting a fresh Hermes worker on a Proxmox VM clone, wired to the LLM Manager gateway
and controllable by ACMS via the api-server platform. Companion to `pdu-manager-vm154`/`acms-project-operations`
JINT-001 sections.

## 0. Prerequisites

- VM cloned from a working template (template VM 121 on miam00111 = VM103-lineage Ubuntu 24.04; qga enabled).
- ARM runtime row exists (or create one via the Server Manager API) so the §8 ownership marker is written at provision time.
- A LiteLLM virtual key for the agent (`POST /key/generate` with the master key on VM114; store 0600 as `/etc/llm-manager/secrets/agent_key_<alias>`).

## 1. Install Hermes on the VM (qga path)

```bash
# from the owning node (root ssh), via qm guest exec; LONG installs go under nohup
qm guest exec <vmid> -- bash -c "echo <b64-script> | base64 -d > /tmp/bootstrap.sh && nohup /tmp/bootstrap.sh & echo LAUNCHED"
```

Bootstrap script contents (b64-embed): `useradd hermes` → `python3 -m venv /opt/hermes-venv` →
`pip install hermes-agent aiohttp` (aiohttp is REQUIRED for the api-server platform — without it the
gateway logs "No adapter available" and starts cron-only) → `hermes profile init <name>`.
Log to `/tmp/worker-bootstrap.log`; poll via `qm guest exec ... tail`.

## 2. Wire the LLM backend (profile config)

```yaml
# ~/.hermes/profiles/<name>/config.yaml
custom_providers:
  - name: llm-manager
    base_url: http://10.0.20.108:8080/v1   # nginx plain-LAN surface; TLS :443 breaks OpenAI clients (self-signed)
    api_mode: chat
    key_env: LLM_MANAGER_AGENT_KEY
    models: [fast, qwen3.6-35b-a3b, code, gemma4-26b-a4b]
model:
  provider: llm-manager
  default: fast
  context_length: 70000     # REQUIRED — without it Hermes requests ctx-minus-prompt output tokens
  max_tokens: 8192          # and litellm 400s ContextWindowExceededError (2026-09-20 playbook)
tools:
  tool_search: {enabled: "on"}
```

Deliver the key as `/etc/llm-manager-agent.env` (0600, `LLM_MANAGER_AGENT_KEY=...`) referenced by the
systemd unit's `EnvironmentFile=`.

## 3. Enable the api-server platform (ACMS bridge endpoint)

Config keys live INSIDE `extra` (top-level host/port are IGNORED → defaults to loopback:8642):

```yaml
platforms:
  api_server:
    enabled: true
    extra:
      key: <bridge-key>       # required; API_SERVER_KEY env var also accepted
      host: 0.0.0.0           # loopback-only is unreachable cross-host
      port: 8402
```

Generate the bridge key with `secrets.token_urlsafe(32)`; stage it where ACMS will read it
(`ACMS_BRIDGE_TARGETS_JSON` on CT122: `[{"agent_id": ..., "base_url": "http://<vm>:8402", "api_key": ..., "harness": "hermes"}]`).

## 4. Systemd unit

```ini
[Service]
Type=simple
User=hermes
EnvironmentFile=/etc/llm-manager-agent.env
WorkingDirectory=/home/hermes
ExecStart=/opt/hermes-venv/bin/hermes gateway run --profile <name> --replace
# gateway run takes NO --host/--port (config-driven). --replace for systemd supervision.
Restart=on-failure
RestartSec=5
```

`systemctl enable --now` — the unit auto-starts on VM boot (proven: full VM stop/start → bridge back →
same ACMS identity reconnects with session history intact).

## 5. Verify

1. `ss -ltn | grep 8402` on the VM.
2. From ACMS host: `curl -H "Authorization: Bearer <key>" http://<vm>:8402/api/sessions` → `{"object": "list", "data": []}`.
3. From the ACMS container: `HermesBridge(target).fetch_status()` → `acms-heartbeat-v1` (raises "no sessions reported" on a fresh worker — send work first).
4. `send_work(...)` → run_id → `GET /v1/runs/{run_id}` → status completed + output.

## Known traps

- Gateway start failure loop: check `journalctl -u hermes-bridge` for (a) missing aiohttp → "No adapter available",
  (b) missing API key → "Refusing to start: API_SERVER_KEY is required", (c) wrong config shape → silently defaults to loopback:8642.
- Worker sends tools unconditionally → model must have tool-caller parsing on the serving side (see self-hosted-llm-gateway skill).
- `hermes profile list` Gateway column shows "running" for a cron-only gateway with NO platform — verify the LISTENER, not the profile status.