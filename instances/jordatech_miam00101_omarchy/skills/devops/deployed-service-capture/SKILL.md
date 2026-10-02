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

- **QGA channel wedges on large/long execs** — multi-KB heredoc payloads or a 130 KB chunked push can wedge the qemu-guest-agent channel entirely (`QEMU guest agent is not running`); a VM reset clears it (services survive). Alternate, more reliable path discovered 2026-09-27: run `python3 -m http.server 8899` on the workstation and `curl` files DOWN from the VMs — one tiny exec (the downloader script) fetches unlimited content without stressing the agent channel. Kill the server when done.
- **QGA pipes/argv quirks on this fleet**: stdin pipes through `echo | python` arrive EMPTY (file ends up 0 bytes); argv b64 has the same failure. What WORKS: (a) single-exec heredoc per file (≤ ~5 KB), (b) the HTTP-server fetch path above. VM114's agent additionally wedges after a handful of execs regardless of size — interleave resets and keep per-exec payloads small.
- **HTTP-transfer path detail**: serve from the DIRECTORY containing the files (a server rooted at the parent yields 404s that look like transfer bugs); guest-side fetch must curl by exact filename. Staging-serve dir needs refreshing after local file edits — a stale served copy made one deploy run twice against an old script.

## Phase-1 audit extension (when the capture feeds a CI/CD plan, 2026-09-27 pattern)

After capture, before building deployment automation, run a **parity audit** live-vs-repo and save the evidence:

- **md5 the live files and the repo copies** — byte-identity is the strongest possible capture-verdict and takes one command per side (`md5sum /opt/<svc>/.../*.py` vs `md5sum repo/.../*.py`). A 10/10 byte-identical result converts the audit from "probably complete" to "proven".
- **Probe behavioral state the repo can't show**: `systemctl is-active` per unit, listening ports (`ss -tlnp`), DB table inventory, DB row state for the facts a plan corrects (e.g. hosts/registry rows, preset scope_keys), live generated configs (values redacted), whether a migration ledger exists.
- **Enumerate the secret-file contract by NAME only**: `ls /etc/<svc>/secrets/` — names and perms, never values. This becomes the bootstrap contract for the deploy tooling.
- **Identify the uncaptured component** (there's usually one — in the reference case it was `/opt/agent-manager`): anything running on the VM but absent from the repo. Capture it during the audit pass, not as an afterthought.
- Redaction gap in *transit*: a sed redacting `key: value` lines MISSES `database_url: postgresql://user:pass@host` URL-format DSNs — scrub that separately (`s#(database_url: postgresql://[^:]+:)[^@]+(@)#\1REDACTED\2#`). If a secret value reaches session output anyway, scrub the capture file immediately and log exposure + rotation recommendation in agents.md.
- Write the completeness table (item / in_repo / reproducible / action) into the repo as `deploy/production-manifest.yaml` — non-secret machine-readable manifest with secret NAMES, external dependencies, and active-placement state.

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
