# Session model pin + cloud-only failover — implementation notes

## Where the behavior lives

- `agent/chat_completion_helpers.py` — `try_activate_fallback` is the single choke point every automatic switch funnels through. The pinned branch refuses the local chain, and (when `model.automatic_failover` is configured) performs exactly ONE bounded failover to the cloud entry by temporarily setting `_fallback_chain=[cloud_entry]` + clearing the pin for a recursive activation, restoring chain/index/pin in `finally`.
- `agent/agent_init.py` — pin is cached at init (`agent._session_model_pin`) from `model.pin_sessions`; init-time fallback raises instead of silently starting on a fallback model when pinned.
- Compression/rotation forks create the child session row with `model=agent.model` (the LIVE model). Pinning works because the pin prevents `agent.model` mutation — any new automatic model-mutation path silently breaks fork inheritance. Grep for new `agent.model =` assignments when touching failover code.

## Config shape

```yaml
model:
  pin_sessions: true
  automatic_failover:
    enabled: true
    allow_local_targets: false
    cloud:
      enabled: true
      provider: custom
      model: <cloud-model-slug>
      base_url: <llm-manager-or-provider-url>
      key_env: <ENV_VAR_NAME_ONLY — never the value>
    on_failover_failure: stop
```

## Failure classification (the rule)

Eligible for automatic cloud failover: `timeout`, `overloaded` (503/529), `server_error` (500/502), `rate_limit` (429). Everything else fails closed — notably `format_error` (malformed/empty tool-call names from the model; OpenRouter rejects the replay with 400, and a 400 BadRequest is NOT provider unavailability), `context_overflow`, auth, billing, model_not_found, policy blocks, `unknown`. When adding a new FailoverReason, add it to the eligible frozenset ONLY if it is a provider-side availability failure.

Audit: every refusal/activation/stop logs a structured `MODEL_CHANGE` line (session, old/new model+provider, source, reason, authorized flag) with no credential material — keep it that way; notifications quote model slugs and env-var NAMES only.

## Proving a runtime change didn't regress (baseline comparison)

Run the focused domain suite (e.g. `tests/run_agent`) on the modified tree, then `git stash push <changed files>` (+ move untracked tests aside) and rerun on the clean tree; restore with `git stash pop`. Compare `grep '^FAILED' | sort` outputs with `diff` — identical sets = all failures pre-existing. Use this whenever a change lands in a tree with known-failing wider suites; do not chase pre-existing failures.

## Identifying which LLM Manager credential a consumer uses (no secrets printed)

`MARION_LOCAL_API_KEY` etc. are LiteLLM virtual keys in the `litellm` DB (`"LiteLLM_VerificationToken"` — key_alias, key_name shows `sk-…<last4>`, expires, models). Match a consumer's env value to a key by comparing a 6-char prefix + 4-char suffix and length, or sha256 of the value vs `tr -d '\n' < secret_file | sha256sum`. `agent_keys` in the `llmmanager` DB is the SM-facing key table; secrets files live in `/etc/llm-manager/secrets/agent_key_*` on VM114. Check `expires` — an expiring failover key silently breaks cloud failover later; flag rotation before the date.
