# Secret scan patterns for captured configs (destination-side, pre-commit)

Run from the repo root **before the first commit** of any capture. Pass-1 stream sanitization on the source VM has already missed real secrets; this pass is the actual gate.

## The scan

```bash
grep -rnEI "(postgres(ql)?://[^ ]+@|mysql://[^ ]+@|mongodb(\+srv)?://[^ ]+@|sk-[A-Za-z0-9_-]{16,}|ghp_|gho_|github_pat_|vck_|vcp_|xox[bap]-|AIza[0-9A-Za-z_-]{30,}|AKIA[0-9A]{16}|GOCSPX-|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY)" . --exclude-dir=.git | grep -v REDACTED
```

Then a second pass for secret *names* to manually adjudicate:

```bash
grep -rniE "password|passwd|secret|token" ops/ db/ service/ config/ \
  | grep -viE "REDACTED|CHANGE_ME|token_|_token\b"
```

Accept only code that reads env vars at runtime (`password=pw`, `PG_PW` lookups) and schema column names (`prompt_tokens`). Anything with a literal value is a leak. Binary hits (`__pycache__/*.pyc`) count — they embed string constants from source; delete them before staging.

## Known-miss class (why pass 2 is mandatory)

LiteLLM-style YAML configs embed:
- `master_key: sk-…` — **indented**, so `^(master_key:)` anchored seds silently don't match
- `database_url: postgresql://user:pass@host:5432/db`

Redact with indent-tolerant sed:

```bash
sed -i -E \
 's#(master_key:) *sk-[A-Za-z0-9]+#\1 [REDACTED:litellm-master-key]#;
  s#(database_url:) *postgres(ql)?://[^ ]+#\1 postgresql://[REDACTED-user]:[REDACTED-pw]@host:5432/db#' \
  ops/litellm/litellm_config.yaml
```

Verify the redaction by grepping the key names again — a sed that doesn't match exits 0.

## Post-scan duties

- `pg_dump` must be `--schema-only`; grep the dump for `CREATE ROLE ... PASSWORD`.
- If pass 2 found anything: the transit archive is sensitive → log in `~/agents.md`, recommend credential rotation, plan deletion of both copies (source VM + local) post-merge.
