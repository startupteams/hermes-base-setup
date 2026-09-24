#!/usr/bin/env python3
"""PVE API helper for the MARION homelab - authenticates via the LLDAP bot
account (creds staged in a 0600 file: line 1 username, line 2 password).
Never prints credentials. Verified working 2026-09-11 for login, node/guest
enumeration, vm config/status, and guest-agent exec dispatch/polling.

Usage:
  pve_api.py login
  pve_api.py realms|nodes|resources|permissions
  pve_api.py vmconfig <node> <vmid>
  pve_api.py vmstatus <node> <vmid>
  pve_api.py raw <METHOD> <path> [body-string]

Also importable for scripts:
  from pve_api import api, load_creds
  status, data = api("POST", "/api2/json/nodes/<node>/qemu/<vmid>/agent/exec",
                     body={"command": ["bash", "-lc", "echo <b64> | base64 -d | bash"]})
"""
import sys, json, ssl, urllib.request, urllib.parse, os

BASE = "https://10.0.20.100:8006"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
CREDS = os.path.expanduser("~/.pve_ldap_bot")


def load_creds():
    with open(CREDS) as f:
        lines = [l.rstrip("\n") for l in f if l.strip()]
    return lines[0], lines[1]


def login():
    user, pw = load_creds()
    data = urllib.parse.urlencode({"username": user + "@LLDAP-Domain", "password": pw}).encode()
    req = urllib.request.Request(BASE + "/api2/json/access/ticket", data=data)
    with urllib.request.urlopen(req, context=CTX, timeout=10) as r:
        d = json.load(r)["data"]
    return d["ticket"], d["CSRFPreventionToken"], user + "@LLDAP-Domain"


def api(method, path, body=None):
    ticket, csrf, _ = login()
    return raw_req(method, path, ticket, csrf, body)


def raw_req(method, path, ticket, csrf, body=None):
    data = None
    if isinstance(body, dict):
        # doseq=True is CRITICAL: list-valued params (e.g. agent/exec "command"
        # array) are silently DROPPED by plain urlencode -> the POST succeeds
        # but the exec never runs.
        data = urllib.parse.urlencode(body, doseq=True).encode()
    elif isinstance(body, str):
        data = body.encode()
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if ticket:
        r.add_header("Cookie", "PVEAuthCookie=" + ticket)
    if csrf and method not in ("GET",):
        r.add_header("CSRFPreventionToken", csrf)
    try:
        with urllib.request.urlopen(r, context=CTX, timeout=20) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {"raw": "http error %d" % e.code}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "login"
    if cmd == "login":
        _, _, user = login()
        print(json.dumps({"login": "ok", "user": user}))
        return
    if cmd in ("realms", "nodes", "resources", "permissions"):
        paths = {
            "realms": "/api2/json/access/domains",
            "nodes": "/api2/json/nodes",
            "resources": "/api2/json/cluster/resources",
            "permissions": "/api2/json/access/permissions",
        }
        user, _ = load_creds()
        if cmd == "permissions":
            paths["permissions"] += "?userid=" + urllib.parse.quote(user + "@LLDAP-Domain")
        st, d = api("GET", paths[cmd])
        print(json.dumps({"status": st, "data": d.get("data")}, indent=1, default=str))
        return
    if cmd == "vmconfig" and len(sys.argv) >= 4:
        st, d = api("GET", "/api2/json/nodes/%s/qemu/%s/config" % (sys.argv[2], sys.argv[3]))
        print(json.dumps({"status": st, "data": d.get("data")}, indent=1, default=str))
        return
    if cmd == "vmstatus" and len(sys.argv) >= 4:
        st, d = api("GET", "/api2/json/nodes/%s/qemu/%s/status/current" % (sys.argv[2], sys.argv[3]))
        print(json.dumps({"status": st, "data": d.get("data")}, indent=1, default=str))
        return
    if cmd == "raw" and len(sys.argv) >= 3:
        method, path = sys.argv[2], sys.argv[3]
        body = sys.argv[4] if len(sys.argv) > 4 else None
        ticket, csrf, _ = login()
        st, d = raw_req(method, path, ticket, csrf, body)
        print(json.dumps({"status": st, "data": d}, indent=1, default=str))
        return
    print(__doc__)


if __name__ == "__main__":
    main()
