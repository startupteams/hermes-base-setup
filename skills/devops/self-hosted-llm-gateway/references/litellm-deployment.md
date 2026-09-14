# LiteLLM proxy bring-up on Ubuntu 24.04 with PostgreSQL backing

Session-proven sequence (2026-09, VM114 @ MIAM-00135 → CT115 PostgreSQL @ MIAM-00147).
Order matters; each numbered fix below was a real startup failure.

## 0. Prerequisites

- Python 3.12 venv at `/opt/llm-manager/venv` (FastAPI shell shares it).
- PostgreSQL reachable, role + DB created:
  ```sql
  CREATE ROLE llmmanager LOGIN PASSWORD '<from secret file>';
  CREATE DATABASE litellm OWNER llmmanager;
  -- INSIDE the litellm DB (schema grants are per-DB):
  GRANT ALL ON SCHEMA public TO llmmanager;
  ```
- pg_hba: one line per ROLE, not per database, when the role serves multiple DBs:
  `host  all  llmmanager  10.0.20.0/24  scram-sha-256`
  (a line naming only `llmmanager` the DATABASE silently breaks the second DB later — P1010).

## 1. Install (known dependency chain)

```bash
/opt/llm-manager/venv/bin/pip install 'litellm[proxy]' prisma
apt-get install -y nodejs npm     # prisma generate needs node/npm; Ubuntu noble ships node 18
```

## 2. Generate the prisma client (three separate pitfalls)

```bash
sudo env PATH="/opt/llm-manager/venv/bin:/usr/local/bin:/usr/bin:/bin" \
  /opt/llm-manager/venv/bin/python -m prisma generate \
  --schema /opt/llm-manager/venv/lib/python3.12/site-packages/litellm/proxy/schema.prisma
```

- Without `--schema`, prisma errors "Could not find a schema" (schema lives inside the litellm package).
- Without venv `bin` on PATH, the generator fails `prisma-client-py: not found`.
- Without node/npm, engine generation fails with npm exit 127.

## 3. Create tables — `prisma db push`, not just generate

LiteLLM's proxy does NOT auto-migrate on first boot. Without tables, key/generate 500s:
`The table public.LiteLLM_VerificationToken does not exist`.

```bash
sudo env PATH="/opt/llm-manager/venv/bin:/usr/bin:/bin" \
  DATABASE_URL="postgresql://<user>:<pw>@<pg-host>:5432/litellm" \
  /opt/llm-manager/venv/bin/python -m prisma db push \
  --schema <venv>/lib/python3.12/site-packages/litellm/proxy/schema.prisma \
  --skip-generate --accept-data-loss
# expect: "Your database is now in sync with your Prisma schema"
```

## 4. Config shape

`/etc/llm-manager/litellm_config.yaml` (chmod 600; master key injected from
`/etc/llm-manager/secrets/litellm_master_key`, never inline in the repo copy):

```yaml
model_list:
  - model_name: startupteams/general     # logical alias, repeated per endpoint = load balancing
    litellm_params:
      model: openai/qwen3.6-35b-a3b      # openai/ prefix + vLLM served-model-name
      api_base: http://10.0.20.161:8000/v1
      api_key: local-00111               # vLLM ignores it; label only
  # ... repeat for each healthy endpoint (163, 164)

litellm_settings:
  drop_params: true
  num_retries: 1
  request_timeout: 600

general_settings:
  master_key: <sk-lm-...>
  database_url: postgresql://llmmanager:<pw>@10.0.20.115:5432/litellm
  store_model_in_db: true
```

## 5. systemd unit

```ini
[Service]
ExecStart=/opt/llm-manager/venv/bin/litellm --config /etc/llm-manager/litellm_config.yaml --host 127.0.0.1 --port 4000
Restart=on-failure
RestartSec=5
```

Bind to 127.0.0.1; nginx fronts it (`location /v1 { proxy_pass http://127.0.0.1:4000; proxy_read_timeout 900s; proxy_buffering off; }` — streaming needs buffering off and long read timeout).

## 6. Key lifecycle (the actual product)

```bash
MK=$(cat /etc/llm-manager/secrets/litellm_master_key)
# issue (raw key in response, shown once — save to root-only file):
curl -s -X POST http://127.0.0.1:4000/key/generate -H "Authorization: Bearer $MK" \
  -H "Content-Type: application/json" \
  -d '{"key_alias":"hermes-<agent>","models":["startupteams/general"],"max_budget":10.0,"budget_duration":"30d"}'
# update budget / rotate params:
curl -s -X POST http://127.0.0.1:4000/key/update -H "Authorization: Bearer $MK" \
  -d '{"key":"sk-...","max_budget":25.0}'
# revoke: POST /key/delete {"keys":["sk-..."]}
```

**Enforcement test (do not skip):** issue one key with `max_budget: 0` and confirm the
completion returns `429 budget_exceeded`. That single response is the proof the caps work.

## 7. End-to-end validation

```bash
KEY=$(cat /etc/llm-manager/secrets/agent_key_hermes_pilot)
curl -s http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"startupteams/general","messages":[{"role":"user","content":"Reply exactly: GATEWAY-OK"}],"max_tokens":300}'
# verify response .model == logical alias and .system_fingerprint shows the vLLM backend
```

Client contract for Hermes agents:
```
OPENAI_BASE_URL=http://<gateway-ip>/v1   (or https://llm-manager.../v1 once DNS+TLS exist)
OPENAI_API_KEY=<virtual key>
OPENAI_MODEL=startupteams/general
```

## Startup-failure triage table

| Log signature | Cause | Fix |
|---|---|---|
| `No module named 'prisma'` | dep missing | `pip install prisma` |
| `Unable to find Prisma binaries. Run 'prisma generate'` | engine not generated (or generated without node) | step 2 |
| `prisma-client-py: not found` | venv bin not on PATH during generate | `env PATH=...` |
| npm exit 127 during generate | nodejs/npm absent | `apt install nodejs npm` |
| `P1010 denied on database X.public` | missing schema grants | `GRANT ALL ON SCHEMA public TO <role>` inside X |
| `no pg_hba.conf entry for host ..., database X` | HBA line scoped to another DB name | widen to `host all <role> cidr` |
| key/generate 500 `table ... does not exist` | schema never pushed | step 3 |
| `httpx.ConnectError` loop, exit status 3 | prisma engine can't reach DB | triage table rows above; check HBA + grants first |
