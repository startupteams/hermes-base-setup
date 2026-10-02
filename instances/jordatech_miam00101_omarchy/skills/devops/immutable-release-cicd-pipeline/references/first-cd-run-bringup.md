# First-CD-run bring-up: the canonical failure chain (2026-09-27, llm-manager + runner on LXC 130)

A freshly-registered self-hosted runner + first automatic staging deploy reproduced SIX distinct
failures in sequence. Each one is small; the chain is what costs time. Use this as the bring-up
checklist — expect roughly these, in roughly this order:

## 1. Runner CT: minimal image missing `unzip` (and jq)
First staging run dies at "Unpack + checksum-verify artifact": `unzip: command not found`, exit 127.
Fix: `apt-get install -y unzip jq` on the runner CT. Log this in the handoff — fresh images will keep
needing it.

## 2. workflow_dispatch path crashes where workflow_run works
Artifact download step does `context.payload.workflow_run.id` — undefined on a manual dispatch event
→ `TypeError: Cannot read properties of undefined (reading 'id')`. Fix: resolve the source CI run from
the event when present, else fall back to the latest successful `ci.yml` run on main
(`listWorkflowRuns(workflow_id, status=success, head_branch=main, per_page=1)`).

## 3. Workflow scripts piped over ssh need a checkout
`ssh target "bash -s" < deploy/preflight.sh` runs the LOCAL runner's copy — without
`actions/checkout@v4` the file doesn't exist (`deploy/preflight.sh: No such file or directory`).
Deploy workflows that pipe repo scripts over ssh MUST check out main first.

## 4. Relative ARTIFACT paths break after checkout
`ARTIFACT=$ART` captured in the unpack step is relative to `$RUNNER_TEMP`; later steps run from the
repo root after checkout → `scp: stat local ...: No such file`. Fix: `ARTIFACT=$(readlink -f "$ART")`.
(Caused BOTH a staging failure and a production failure.)

## 5. Step order: transfer BEFORE preflight
preflight verifies the tarball ON THE TARGET (`/tmp/<name>`); running it before scp verifies a
missing/stale file → guaranteed FAIL, or worse, it validates yesterday's artifact. Order:
download → checksum → scp → preflight (against `/tmp/$(basename "$ARTIFACT")`) → deploy.
And never mask preflight failures with `|| true` — that hid the wrong-order bug for a run.

## 6. The target picks the WRONG artifact from /tmp
The transaction script's `ls /tmp/llm-manager-*.tar.gz | head -1` is ALPHABETICAL — with several
artifacts in /tmp it deployed an older tarball while CI built the right one (symptom: CD run green but
`release_manifest.json` on the target shows an old SHA). Fix: clean `/tmp/<svc>-*.tar.gz*` right before
scp + `ls -t`. Verify the deployed SHA from the manifest, never from the workflow's green check.

## 7. Workflow-shape fixes only reach the next run via a merge
A workflow change does not affect runs dispatched from an old SHA (dispatch defaults to new main tip
after merge — pass `sha` explicitly when required). Pattern used throughout: find bug → tiny branch →
PR → CI green → merge → re-dispatch. Budget ~4-7 of these micro-PRs for a first bring-up; that is
NORMAL, not a failed approach.

## 8. Sudo + env_reset eats workflow-set env vars
`sudo ENV=value wrapper.sh` does not survive sudoers env_reset (deploy wrapper silently lost its
flag). Fix: set the variable INSIDE the transaction script itself (self-detection), not from the
workflow. Also prefer `ls -t` + explicit variables over env-var flags for tooling invoked under sudo.

## Also applies (from the production side, same session)
- **pg_hba scoped per role**: a new DB role needs its own `host <db> <role> <ip>/32 scram-sha-256`
  lines + reload; scoped to that role's DBs only (least privilege, and mirrors how the existing role's
  lines look).
- **Fresh PG role + DB**: create role with password → `createdb -O <role>` → `GRANT ALL ON SCHEMA
  public` → verify with `PGPASSWORD=<pw> psql -h 127.0.0.1 -U <role>` from INSIDE the CT (perl locale
  warnings are noise; the trailing `1` is the proof).
- **Protected-environment approvals**: `pending_deployments` GET shows `current_user_can_approve` +
  environment id; POST with the JSON-file body. Runs show `waiting` (not failed) while pending.

## Bring-up gate (definition of done)
green CI on main → staging CD run green → `/healthz` on staging reports the CURRENT main-tip SHA →
one production deploy accepted → one manual rollback proven (healthcheck + ledger
`manual_rollback_complete`) → roll forward. All four recorded in the release ledger.