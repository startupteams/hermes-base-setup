# SM facility-power route (PR #74, 2026-10-01, prod fce5ba7)

## Contract
`GET /api/v1/facility/power` on Server Manager (:8300), scope `usage:read`.
Purpose: ACMS ingests facility power WITHOUT Emporia credentials or the
llmmanager DSN (STEA-004 plan §17 — LLM Manager stays collector/provider).

Response shape (mirrors service/app/power_view.py semantics):
- `channels[]`: channel_num 1-4, label (PDU MIAM-00151/152/153, "36k 3 Ton
  mini split (cooling)"), avg_watts_1h, kwh_24h/30d, cost_usd_24h/30d,
  last_sample_ts, last_sample_age_seconds, stale
- `totals`: TOTAL MARION_IA_USA = ch1+2+3+4; **any stale channel → fields
  NULL + `incomplete_reason` (never zero-filled)**
- `collector`: samples_1h/total, last_sample_ts/age, healthy, stale,
  stale_policy string
- `rate`: effective_per_kwh (electricity_rates components override
  built-in plan v0.2.1: SUMMER_BASE .13234 / WINTER_BASE .10257 / FEES .04540,
  summer = Jun-Aug)

## Implementation notes
- STALE_SAMPLE_SECONDS = 600 (matches web app).
- Per-channel staleness judged from EACH channel's own last sample.
- SQL over `get_session_factory("llm")` (llmmanager DB on CT115 @10.0.20.116);
  `to_regclass('facility_power_samples')` existence check → honest "not
  deployed" error.
- Rate query mirrors main.effective_rate: season + effective_from<=CURRENT_DATE
  + (effective_to IS NULL OR >=), ORDER BY rate_id DESC.

## Deployment reality (re-hit live)
deploy-release.sh restarts web/collector/emporia/recovery but NOT
server-manager-api. After any server_manager/ change:
`sudo systemctl restart server-manager-api` then verify
`curl -s http://127.0.0.1:8300/openapi.json | python3 -c "import json,sys; print([p for p in json.load(sys.stdin)['paths'] if 'facil' in p])"`.

## Test patterns (tests/server_manager/test_facility_power_route.py)
- Stub: `monkeypatch.setattr(fp, "get_session_factory", lambda *a, **k: (lambda: _FakeSession()))`
  — factory returns a CALLABLE returning the fake session (routes do
  `Session = get_session_factory("llm")` then `with Session() as s:`).
- `_FakeSession`: `__enter__`/`__exit__`, scripted `execute()` matching on SQL
  fragments (to_regclass / electricity_rates / count(*), max(ts) / AVG(watts) /
  interval '24 hours' / interval '30 days' / max(ts) WHERE channel / EXTRACT(epoch).
  Timestamps returned as datetime objects (route calls .isoformat()).
- Token file fixture pattern: tmp file + `SERVER_MANAGER_SERVICE_TOKENS_FILE`
  env + `time.sleep(0.01); os.utime(tf)` (mtime-keyed cache), save/restore env
  around the test. svc-acms=tok:ALL for the 200 case, a health:read-only
  identity for the 403 case.

## ACMS pairing (acms/power_ingest.py)
`FacilityPowerClient` (urllib, `server_manager_base_url` + `server_manager_token`
settings) → `ingest_power_snapshot` → `power_cost_snapshot` (migration 0016).
`current_watts` = channel sum ONLY when no channel stale. `/power/summary?refresh=1`
ingests + returns; `/usage/summary?hours=` rolls cost_attribution (cloud ACTUAL,
local ESTIMATE-labeled). Live proof 2026-10-01: 2,335.7W total, 24h
11.174 kWh/$1.80, 30d 215.225 kWh/$34.62, 4 channels fresh (41s age).