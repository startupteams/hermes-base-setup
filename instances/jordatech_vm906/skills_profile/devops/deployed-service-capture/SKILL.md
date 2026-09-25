---
name: deployed-service-capture
description: "Capture, sanitize, and commit the deployed state of a service (source, systemd/nginx/proxy configs, DB schema-only dump) from a remote VM into a preservation Git repo. Two-pass secret sanitation, chunked base64 transfer over PVE guest-exec, validation battery, PR + agents.md log."
---

# Deployed Service Capture → Git Preservation Repo

Use when asked to "capture / preserve / snapshot the deployed service on VMxxx into a repo" — e.g. LLM Manager v0.11 on VM114 → `llm-manager-project-framework`. The captured tree mirrors the deployed layout *as-running* (no refactor), so the repo doubles as a redeploy blueprint.

## Workflow

1. **Inventory (read-only).** On the target VM: app source dirs, `/etc/systemd/system/*.service` (+ drop-ins), nginx sites, service config dirs (`/etc/<svc>/`), venv freeze (`pip freeze`), `python3 --version`, DB schema via `pg_dump --schema-only` (never data).
2. **Archive with in-stream sanitization** on the VM (`tar` piped through `sed`), so raw secrets minimize transit. But treat pass 1 as *advisory only* — pass 2 below is the real gate.
3. **Transfer**: if SSH isn't available and QGA `guest-file-read` is unimplemented, use chunked `base64 -w7000` chunks via PVE guest-exec (`pve.py exec` with arg[] + poll), reassemble + verify MD5 locally. Recipe: `references/chunked-base64-guestexec-transfer.md`.
4. **Destination second-pass secret scan BEFORE first commit** — this has caught real leaks the stream pass missed. Patterns + ready-to-run scan command: `references/secret-scan-patterns.md`.
5. **Redact in-repo** any hits. sed pitfall: YAML keys are indented — `^(master_key:)` won't match; use indent-tolerant `s#(master_key:) *sk-[A-Za-z0-9]+#\1 [REDACTED]#`.
6. **Validation battery**: `python3 -m py_compile` on all captured `.py`; run any self-contained gate tests (e.g. `v011_cost_tests.py`); re-run secret scan until clean.
7. **Docs parity**: verify doc claims against captured source before committing (grep the source for every behavioral claim, e.g. recovery flags like `STOPPED_INTENTIONAL`); update IMPLEMENTATION_STATUS/OPERATIONS docs and README index; add DEVELOPER_SETUP with repo-to-deployment path map.
8. **Commit + PR** in repo format (`... (#<issue>)`), push branch, open PR with evidence/risk/checks/limits sections. Log milestone + security findings in `~/agents.md` for downstream agents.

## Pitfalls

- **Sanitizer miss pattern class**: naive sed lists miss LiteLLM-style `master_key: sk-…` and `database_url: postgres://user:pass@host` embedded in YAML config. Rule: scan patterns must include `sk-[A-Za-z0-9_-]{16,}` and `<scheme>://[^ ]+@` DSNs; a destination-side rescan pre-commit is mandatory, not optional.
- **The transit archive is sensitive**: even "sanitized" archives can carry raw secrets. Note it in agents.md, recommend key/password rotation, and schedule deletion of both copies after merge.
- **`py_compile` litters `__pycache__/` inside the repo** — `find . -name __pycache__ -exec rm -rf` *before* `git add -A`, and ensure `.gitignore` covers it.
- **Never `write_file` a `.gitignore`/README to "append" a rule** — it clobbers existing entries. Read + merge, or use `patch`.
- **Duplicate capture artifacts** (same freeze file at root and under `config/examples/`): diff before committing, keep one canonical location.
- **Runtime facts from the VM beat assumptions**: capture `python3 --version` and freeze pins into `config/examples/` and quote them in dev docs instead of guessing the distro Python.
- GitHub issue trackers on preservation repos may be disabled — issue needed for commit format? Re-enable with Jordan's gh token (`repo` scope).

## Related

- `self-hosted-llm-gateway` — operating the LLM Manager/LiteLLM stack being captured.
- `proxmox-cluster-infrastructure` — guest-exec/PVE API plumbing used by the transfer step.
