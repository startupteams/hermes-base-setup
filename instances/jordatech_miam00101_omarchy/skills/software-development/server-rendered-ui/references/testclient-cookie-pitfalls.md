# TestClient Cookie & TemplateResponse Pitfalls (FastAPI/Starlette)

Both of these cost a debug cycle on 2026-09-26 (ACMS PR #2). Reproduce-proof for future UI test sessions.

## Pitfall 1: Secure cookies silently dropped against http://testserver

**Symptom:** login test passes (cookie issued), but every subsequent `client.get(path, cookies=resp.cookies)` returns **303 → /ui/login** with "assert 303 == 200" — while the same flow works in a real browser. 6 of 17 tests failed this way; no auth error anywhere.

**Cause:** passing `cookies=` per-request routes through httpx's cookie jar, which applies the cookie's `Secure` attribute and refuses to send it over plain `http://testserver`. The jar silently drops it; `current_user` finds no cookie → redirect. (Starlette even deprecation-warns that per-request cookie-jar persistence is "ambiguous".)

**Fix:** pass cookie values as a plain dict — dict cookies bypass the jar:

```python
# _login() helper returns a dict, not the Response:
return {COOKIE_NAME: resp.cookies[COOKIE_NAME]}
...
page = client.get("/ui/", cookies=resp)   # resp is now a dict
```

For tests that must inspect `Set-Cookie` headers (HttpOnly/Secure/SameSite assertions), issue the POST inside the test itself and read `resp.headers["set-cookie"]` — don't reuse the helper.

**Secondary gotcha:** the helper's return-type change breaks other callers expecting `.status_code`/`.headers` (`AttributeError: 'dict' object has no attribute 'headers'`) — search all callers when switching.

## Pitfall 2: TemplateResponse built but not returned → silent 200

**Symptom:** a denial endpoint (bad password / unmapped user) that should return **403** returns **200 OK** with an empty body. Direct call of the auth function is correct (`role=None`); only the HTTP layer is wrong.

**Cause:** helper rendered the template but didn't `return` it:

```python
def _deny_unmapped(request, username) -> None:
    templates.TemplateResponse(request, "login.html", {...}, status_code=403)  # discarded!
```

FastAPI sees a handler returning `None` → bare 200. No exception, no log. An auth failure silently becomes a success-looking response.

**Fix:**

```python
def _deny_unmapped(request, username) -> Response:
    return templates.TemplateResponse(request, "login.html", {...}, status_code=403)
```

plus `from fastapi.responses import RedirectResponse, Response`. Rule: every helper that builds a `TemplateResponse`/`RedirectResponse` returns it, with a `-> Response` annotation.

## Debug-order lesson

When a status code differs between "direct function call" and "through TestClient", suspect the HTTP-layer glue first (template return path, redirect status, cookie transport), not the auth logic. Empirically probe with:

```python
r = c.post("/ui/login", data={...})
print(r.status_code, dict(r.cookies))
```

Run the direct function and the endpoint in the same interpreter so the fake-ldap3 patch applies to both.

## Related environment quirk (not a code bug)

Integration tests that `subprocess.run(["alembic", ...])` fail with `FileNotFoundError: 'alembic'` when pytest runs via bare `.venv/bin/python -m pytest` — the venv bin dir isn't on PATH for subprocesses. Run `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest` or activate the venv. (Wrongly diagnosing this as your change wastes time: 6 passed / 2 errors was the tell.)
