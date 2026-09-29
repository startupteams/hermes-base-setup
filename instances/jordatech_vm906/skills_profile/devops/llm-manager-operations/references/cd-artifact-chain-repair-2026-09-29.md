# CD Artifact Chain Repair — 2026-09-29 (PRs #61–#66)

Symptom: `deploy-staging` runs went green while staging VM120 sat ~2 days
behind main (healthz 32a905e while main was 8b05afb).

## Failure chain (three stacked causes, each masked the next)

1. **RUNNER_TEMP reuse on self-hosted runners.** The runner (CT130,
   machine name `pdu-deploy-runner`, runner name `llm-manager-deploy`) does
   NOT reliably clean `$RUNNER_TEMP` between jobs. A stale
   `llm-manager-32a905e7af97.tar.gz` survived; the unpack step's
   `find . -maxdepth 2 -name 'llm-manager-*.tar.gz' | head -1` picked it.
   Fix (PR #61): `rm -f llm-manager-*.tar.gz llm-manager-*.tar.gz.sha256`
   first, then select by EXACT expected name.
2. **Self-inflicted rm-order bug** (PR #62): the first fix added
   `artifact.zip` to the rm list — but the DOWNLOAD step writes
   `$RUNNER_TEMP/artifact.zip` fresh, so the unpack step deleted its own
   input (`unzip: cannot find or open artifact.zip`). rm covers only stale
   tarballs.
3. **`dist/` was tracked in the repo** (PR #63): the repo had historical
   committed tarballs and no `.gitignore` entry, so the CI `artifact` job
   (which packs `dist/llm-manager-*.tar.gz*`) uploaded MULTIPLE artifacts
   per run; the zip contained old tarballs regardless of the run's sha.
   Fixed: `git rm -r --cached dist`, `dist/` gitignored, CI asserts exactly
   ONE tarball pair (`N=$(ls dist/llm-manager-*.tar.gz | wc -l); [ "$N" = "1" ]`).
4. **Short-sha vs full-sha naming** (PR #64): `build-release.sh` names
   tarballs `llm-manager-<short12>.tar.gz` but the workflow matched
   `llm-manager-${github.sha}` (40-char). Zip inflated
   `llm-manager-477af7b0c495.tar.gz` while WANT wanted the full sha →
   "artifact missing". Match: `cut -c1-12` of the resolved sha.

## Detection rule

A green `deploy-staging` run proves NOTHING. Always verify the DEPLOYED
state afterward:

```bash
curl -sk https://10.0.20.131/healthz | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["git_sha"][:12])'
```

and compare with `git rev-parse --short origin/main`. The deployed sha is
also readable on the staging host:
`/opt/llm-manager/current/release_manifest.json` → `git_sha`.

## Debug technique that worked

`gh run view <id> --log-failed` + grep for the step name showed the exact
bash lines with expanded variables (`WANT="..."`, the `inflating:` lines
from unzip) — this is how the short-sha mismatch and the missing zip were
diagnosed without shell access to the runner.

## Staging access reality (blocks alternative fixes)

- No root ssh to VM120 from workstation or VM114.
- CT130 runner holds `llm-manager-deploy@10.0.20.131`; its sudo is
  wrapper-only (bootstrap-wrapper / deploy-wrapper / healthcheck-wrapper) —
  arbitrary sudo asks for a password ("a terminal is required to read the
  password").
- One-shot env toggles: `.github/workflows/staging-orm-cutover-toggle.yml`
  (workflow_dispatch, `value` input; writes systemd drop-ins + daemon-reload
  + restart + verifies via `systemctl show`).
- There is NO `/opt/llm-manager/.env` on staging — env flows through systemd
  unit Environment/drop-ins (the toggle's first attempt did `touch "$F"` with
  an empty var → `touch: cannot touch ''`).