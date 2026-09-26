---
name: acms-project-framework
description: "ACMS (startupteams/acms-project-framework) — AI workforce control plane on MARION CT122. Governance model (no self-merge, PR gates, REQ traceability), §12 production sync check, repo validation commands, PR conventions, startupteams org quirks (REST PR edit, push protection), vertical-slice feature delivery workflow."
version: 1.0.0
author: Hermes Agent
license: MIT
---

# ACMS Project Framework (startupteams/acms-project-framework)

Class-level workflow for any task touching ACMS: feature slices, deployment
tooling, UI work, requirement updates, or production sync checks.

## Fixed facts

- **Repo:** `startupteams/acms-project-framework` · clone `~/work/acms-project-framework`
- **Venv:** `.venv-acms` (Python 3.12; system python3 is 3.11 but pyproject requires >=3.12)
- **Live:** LXC CT122 "acms" on MIAM-00135 @ `10.0.20.122` (root SSH key works; jordatech user does not)
- **Docs log:** `/home/jordatech/agents.md` — every PR/session appends a dated entry (Surprise Protocol)
- **Plan of record:** `ACMS_FEATURE_DELIVERY_AND_AUTOMATED_ROLLBACK_PLAN_2026-09-26.md` (vertical slices; PR 0 = safe release/rollback)

## Governance model (repo AGENTS.md — binding)

- **Agents never self-merge.** Every change: feature branch → PR → human review → merge.
- **Deployment is separately human-gated** (plan §3). Rollback to the exact previous known-good on failed validation is the ONE pre-authorized autonomous action.
- Trace implementation to `ACMS-REQ-###` IDs; summarize IDs, acceptance criteria, files, assumptions, validation **before editing**.
- Out-of-scope discoveries → `FUTURE_WORK.md` with provenance (Human-Directed / Agent-Discovered / Source-Derived). Next free ID is checked via `grep -oE "^## FW-[0-9]+" FUTURE_WORK.md | sort -V | tail -1`.
- ADRs: agent-originated significant decisions stay **Proposed**; only human-explicit decisions are **Accepted**.
- Meaningful work produces a handoff in `docs/handoffs/YYYY-MM-DD-<topic>.md`: requirements, attempted/changed, believed state, validation results, blockers, next action.
- PR body must list: requirement IDs, acceptance criteria, validation (exact results), risks, ADR/TDR changes, future work, reviewer focus.

## §12 production sync check (run FIRST, before new feature work)

Never infer deployed code from the version string alone:

```bash
# Repository side
git -C ~/work/acms-project-framework fetch origin --prune
git -C ~/work/acms-project-framework rev-parse origin/main
# Production side
ssh root@10.0.20.122 'cd /opt/acms/repo && git rev-parse HEAD && git status --porcelain | head -3'
ssh root@10.0.20.122 'docker exec acms-postgres-1 psql -U acms -d acms -tAc "SELECT version_num FROM alembic_version"'
```

If production != origin/main: the sync deploy goes FIRST (human-authorized), then feature work. If equal: proceed directly. Record the exact live SHA in the PR body and agents.md.

## Validation battery (before every PR)

```bash
cd ~/work/acms-project-framework && source .venv-acms/bin/activate
python -m pytest -q                                   # full suite
bash -n deploy/*.sh                                   # shell syntax
python3 -c "import yaml; yaml.safe_load(open('deploy/compose.yaml'))"
git diff | grep -iE 'sk-[a-zA-Z0-9]|gho_|vck_|vcp_|GOCSPX|BEGIN.*PRIVATE' || echo CLEAN   # secret scan
```

Docker is NOT available on the workstation — deploy scripts validate as
syntax+logic only; live drills happen on CT122 after merge + authorization.

## startupteams org quirks (GitHub)

- **PR body edits must use REST, not `gh pr edit`** — the GraphQL path errors (projects-classic deprecation): `gh api -X PATCH repos/startupteams/<repo>/pulls/<n> -f body=@file.md`
- Issue trackers may be disabled on some repos — re-enable via settings with the jordatech gh token (`repo` scope) if an issue must be filed.
- **Push protection scans ancestor commits.** If a push is rejected for a secret, rebuilding only the tip is not enough — rebuild branch history from main and re-push.

## PR numbering state (as of 2026-09-26)

PR #1–#4 merged (scaffold, async stack, LLDAP fix, work orchestration).
PR #5 OPEN (`ops/ACMS-safe-release-rollback`): safe release transaction +
automated rollback — awaiting human review. Do not assume; run
`gh pr list` to confirm current state.

## Pitfalls

- The maintenance-mode nginx conf overlays the tracked `nginx.conf`; any `git checkout` on the VM must restore that file first or checkout is refused. `deploy/common.sh` handles this — keep the pattern if touching release tooling.
- Never run `alembic downgrade` automatically (plan §29); destructive migrations need human approval + restore testing.
- Level-2 DB restore is only authorized inside an open release transaction (`transaction.json`); standalone rollback is app-only by design.
- Live CT122 layout facts (repo path, container names, allowlist, DNS reality) → see `references/ct122-live-layout.md` before running anything on the box.

## Related skills

- `implementation-package-execution` — for zip+plan package deliveries (overlaps on STOP gates/handoffs)
- `server-rendered-ui` — the Jinja2 UI conventions ADR-0008 builds on
- `github-pr-workflow` — generic PR lifecycle (protected; org quirks live here, not there)
