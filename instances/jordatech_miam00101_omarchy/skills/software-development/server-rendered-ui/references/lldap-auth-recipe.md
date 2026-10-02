# LLDAP/LDAP Auth Recipe (ldap3, FastAPI)

Session-proven flow from ACMS PR #2 (2026-09-26). Key files in that repo: `acms/ui/ldap_auth.py`, `acms/ui/roles.py`, `tests/test_ui_auth.py`.

## The flow (in `_authenticate_sync`)

```python
server = ldap3.Server(url, get_info=ldap3.NONE, connect_timeout=5)
conn = ldap3.Connection(server, user=bind_dn or None, password=bind_pw or None,
                        auto_bind=True, raise_exceptions=True, receive_timeout=10)
```

1. **Service bind** with configured bind DN (or anonymous if none). Any exception → `LdapUnavailable` → HTTP 503.
2. **User search**: filter from configurable template, e.g. `(uid={username})` — escape the username with `ldap3.utils.conv.escape_filter_chars` before substitution; attributes `["memberOf"]`; `size_limit=1`. No entries → return `role=None` (generic deny).
3. **`memberOf` extraction**: `entry.attributes.get("memberOf")` may be an attribute object or a list depending on ldap3 version — handle both (`getattr(attr, "values", None)`).
4. **Password verification by rebind**: `conn.rebind(user=entry.entry_dn, password=password)` inside the same connection context. `False` or exception → `role=None`.
5. **Role mapping** on the collected DNs. Unknown user, wrong password, and authenticated-but-unmapped all return the SAME generic 403 — never distinguish them in the response (no user enumeration).
6. Async wrapper: `await anyio.to_thread.run_sync(_authenticate_sync, username, password)`.

## Failure semantics table

| Condition | Result | HTTP |
|---|---|---|
| LDAP unreachable / bind exception | `LdapUnavailable` | 503 |
| LDAP unconfigured (`ACMS_LDAP_URL`/`USER_BASE` empty) | `LdapUnavailable` | 503 |
| Unknown user | `role=None` | 403 generic |
| Wrong password (rebind fails) | `role=None` | 403 generic |
| Authenticated, no mapped group | `role=None` | 403 "Account is not authorized for ACMS access." |
| Authenticated + mapped | session cookie issued | 303 → `/ui/` |

Import `ldap3` **lazily inside** the sync function: keeps app import light and lets tests install a fake into `sys.modules`.

## Role mapping invariants (`roles.py`)

- Configured group DNs from settings (`ACMS_LDAP_GROUP_ADMIN/WORKER/OBSERVER`); empty settings are skipped.
- Normalize: strip + lower both sides before comparison (directories emit mixed case).
- Multi-group membership: highest-privilege role wins via a rank dict — deterministic.
- Result `None` = deny.

## Fake-ldap3 test harness (no live directory needed)

Install a fake package into `sys.modules` for the test (monkeypatch.setitem):

```python
fake = types.ModuleType("ldap3"); fake.NONE = object()
class FakeServer:
    def __init__(self, *a, **k): pass
class FakeConnection:
    def __init__(self, *a, **k): pass          # raise here to test bind failure → 503
    def __enter__(self): return self
    def __exit__(self, *x): return False
    def search(self, base, filt, attributes=None, size_limit=None):
        self.entries = [...]                    # SimpleNamespace with entry_dn +
                                                # attributes.get() → SimpleNamespace(values=[...])
    def rebind(self, user, password): return True/False
fake.Server = FakeServer; fake.Connection = FakeConnection
utils = types.ModuleType("ldap3.utils"); conv = types.ModuleType("ldap3.utils.conv")
conv.escape_filter_chars = lambda s: s; utils.conv = conv; fake.utils = utils
sys.modules["ldap3"] = fake; sys.modules["ldap3.utils"] = utils; sys.modules["ldap3.utils.conv"] = conv
```

Matrix to cover: mapped admin/worker/observer → correct role; `rebind_ok=False` → role None; empty `entries` → role None; empty groups → role None; bind raises → `LdapUnavailable`; unconfigured URL → `LdapUnavailable`; empty username/password → role None without touching LDAP.

## Settings mutations in tests

The app uses `@lru_cache get_settings()` returning a live pydantic-settings object — tests mutate the instance directly and restore in teardown:

```python
s = get_settings()
saved = {k: getattr(s, k) for k in (...)}
s.session_secret = "test-secret-0123456789abcdef"   # etc.
yield s
for k, v in saved.items(): setattr(s, k, v)
```

(Env-var approaches race with the cache; instance mutation is deterministic.)
