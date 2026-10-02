# Phase C operator UI (Release 5, 2026-10-02, prod 7daad53 → PRs #72/#73/#74)

Session record for STEA-004 Phase C (plan §18–§29). Class-level guidance lives
in SKILL.md; this file holds the release chain, the two live-found bugs and
their exact failure signatures, and the acceptance-proof recipes.

## Release chain

| Release | SHA | PR | Content |
|---|---|---|---|
| baseline | `11a39de` | — | Phase B end state (alembic 0016) |
| R5 operator UI | `16a7312` | #72 | Phase C §18–§29 (29 files, +2,448/−277) |
| live-fix | `419ffe7` | #73 | facility-payload persistence + legacy handoff type |
| migration | `7daad53` | #74 | migration 0017: payload_json varchar(512) → Text (alembic 0017) |

## Architecture decisions worth keeping

- **`acms/ui/operator_data.py` = the shared UI data layer.** Home zones,
  kanban, usage page all read this ONE module — API and UI cannot drift. New
  operator pages must add their loader here, not inline in the route.
- **Old `acms/work_board.py` `board_data` superseded** by
  `operator_data.kanban_data` (§12 six columns incl. dispatching/running/
  attention). `work_prs` (§6.5 PR rows) stayed in work_board.py as the single
  source for work detail.
- **Kanban columns** derive from durable state: `execution_tasks.transport_state`
  (RUNNING/DISPATCHING), `work_items.status='blocked'` OR un-cleared hold OR
  `jira_eligibility='LOCAL_HOLD'` → attention column; terminal task status →
  terminal column. Jira state renders as a SEPARATE badge per card (§11).
- **Agent chat** (`acms/ui/chat_routes.py` + `templates/agent_chat.html`):
  transcript sanitized in `bridge.HermesBridge.fetch_messages` (only
  role/content/tool_name/timestamp survive — reasoning fields NEVER leave the
  bridge layer). Slash commands come from `bridge.slash_commands()` which probes
  `/v1/capabilities` first; unreachable bridge → /help only (honest). Tool
  cards collapse by default; safe-args redacts anything matching
  key/token/secret/password/auth, caps 120 chars.

## Live-found bug 1: facility payload divergence (PR #73)

Symptom: `/ui/usage` rendered totals-only while `/power/summary?refresh=1`
showed all 4 channel cards. Root cause: `ingest_power_snapshot` persisted a
500-byte `payload_json` WITHOUT the channels array, but
`latest_power_summary` (the no-refresh path the UI uses) rebuilds the §17 view
from the STORED payload. Fix: persist the full payload (channels + rate +
collector detail, 4KB app cap). Lesson: **any route that has both a
"fresh fetch" and a "read stored snapshot" path must persist everything the
stored-path reconstruction needs** — the divergence only shows on the UI page,
not the API that just fetched.

Also in #73: the work-detail HANDOFF card matched only
`artifact_type == 'work_handoff'`, but prod artifacts created before Release 2
are typed `handoff`. Use `HANDOFF_TYPES = ("work_handoff", "handoff")`
(`acms/ui/work_routes.py`). Legacy-type compatibility must be checked against
REAL prod data, not the new code's vocabulary.

## Live-found bug 2: varchar overflow (PR #74, migration 0017)

The #73 fix then 500'd on the first real refresh:
`asyncpg.exceptions.StringDataRightTruncationError: value too long for type
character varying(512)` — the full channels payload is ~2–3KB and
`power_cost_snapshot.payload_json` was `String(512)` in both migration 0016
and the ORM model. SQLite unit tests CANNOT see this class (no length
enforcement). Migration 0017 widens to Text; chain test
`tests/test_power_payload_migration.py` runs the full SQLite
upgrade→downgrade cycle on a SCRATCH DB (the shared unit DB is create_all-
managed and collides with alembic) plus a >512-char round-trip. The
migration-vs-model parity test now imports `acms.power_ingest` too. Lesson
re-earned: **every column you widen in the model needs a migration + a
length-exceeding round-trip test before release.**

## Test-infra notes (new this session)

- Alembic chain tests need a tmp_path scratch DB with `monkeypatch.setenv`
  BEFORE building the Config; and after `command.upgrade`, read columns back
  via a SYNC engine on the raw sqlite FILE PATH — `alembic_env.get_main_option
  ("sqlalchemy.url")` returns the ASYNC form (`sqlite+aiosqlite://`) rewritten
  by migrations/env.py, and a sync engine on an async URL fails with
  `MissingGreenlet`.
- `get_settings()` fixture mutation: `cache_clear()` must run on ENTRY (before
  the first `get_settings()` in the test), not only on exit — otherwise the
  first route call re-reads stale env (hit live: empty commands list).
- Direct-route-function probes outside pytest need EVERY models module
  imported before `SessionLocal()` use, else
  `NoReferencedTableError: ... could not find table 'work_items'` — in a demo
  script prefer the HTTP API over direct DB.
- urllib follows 303 redirects silently — to assert a redirect LOCATION
  (e.g. inbox `?archive_warn=1`), build an opener with a NoRedirect handler:
  `class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self, *a): return None`.
- `docker cp` into the acms-app container lands root-owned 0600; the app runs
  as uid 10001 — `docker exec -u root <ctr> chmod 644 <file>` before
  `compose exec ... python3 /app/<script>`.

## Acceptance-proof recipes (re-runnable on CT122)

Demo scripts staged at CT122 `/tmp` (`demo_44.py`, `demo_42.py`), copied to
container `/app`, run via `docker compose -f repo/deploy/compose.yaml
--env-file .env exec -T acms-app python3 /app/demo_44.py`. Session tokens are
minted in-process via `acms.ui.session_auth.issue_token` (secret never
printed). §44 covers 45 checks (home zones/kanban/facility cards/artifact
chain by sha-prefix/HANDOFF card/search/chat honesty/inbox/responsive CSS/no
bearer leak). §42 creates controlled FYI + ACTION_REQUIRED items, verifies
17 behaviors, and archives both afterward so the inbox returns to its prior
state. §41 (chat, 7/7) is folded into the same scripts' pattern: bridge
against the REAL worker fleet, assert sanitized roles and
capability-sourced commands.

## Post-release regression sweep

After any UI release, re-run `bash deploy/smoke-test.sh` ON CT122, then probe
the new pages in-container with a minted token (see above). Two prods-relevant
checks that saved the session: `/power/summary` vs `/power/summary?refresh=1`
channel count must match (stored-path integrity), and a truncated artifact
UID must 303 to the list page (safe failure, no error leak).