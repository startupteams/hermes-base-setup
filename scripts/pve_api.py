#!/usr/bin/env python3
"""Proxmox API helper using the LLDAP bot account.

Credentials:
  ~/.pve_ldap_bot
  line 1: username
  line 2: password

Never prints credentials.
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://10.0.20.135:8006"
CREDS = os.path.expanduser("~/.pve_ldap_bot")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def load_creds():
    with open(CREDS) as f:
        lines = [line.rstrip("\n") for line in f if line.strip()]

    if len(lines) < 2:
        raise RuntimeError("Invalid credential file.")

    return lines[0], lines[1]


def login():
    user, password = load_creds()

    data = urllib.parse.urlencode({
        "username": user + "@LLDAP-Domain",
        "password": password,
    }).encode()

    req = urllib.request.Request(
        BASE + "/api2/json/access/ticket",
        data=data,
        method="POST",
    )

    with urllib.request.urlopen(req, context=CTX, timeout=10) as response:
        data = json.load(response)["data"]

    return (
        data["ticket"],
        data["CSRFPreventionToken"],
        user + "@LLDAP-Domain",
    )


def raw_req(method, path, ticket, csrf, body=None):
    data = None

    if isinstance(body, dict):
        data = urllib.parse.urlencode(body, doseq=True).encode()
    elif isinstance(body, str):
        data = body.encode()

    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
    )

    if ticket:
        req.add_header("Cookie", "PVEAuthCookie=" + ticket)

    if csrf and method.upper() not in ("GET", "HEAD"):
        req.add_header("CSRFPreventionToken", csrf)

    try:
        with urllib.request.urlopen(req, context=CTX, timeout=20) as response:
            return response.status, json.load(response)

    except urllib.error.HTTPError as error:
        try:
            return error.code, json.load(error)
        except Exception:
            return error.code, {
                "data": None,
                "errors": {
                    "http": "HTTP error %d" % error.code
                },
            }


def api(method, path, body=None):
    ticket, csrf, _ = login()
    return raw_req(method, path, ticket, csrf, body)


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "login"

    if command == "login":
        _, _, user = login()
        print(json.dumps({
            "login": "ok",
            "user": user,
        }))
        return

    if command in ("realms", "nodes", "resources", "permissions"):
        paths = {
            "realms": "/api2/json/access/domains",
            "nodes": "/api2/json/nodes",
            "resources": "/api2/json/cluster/resources",
            "permissions": "/api2/json/access/permissions",
        }

        user, _ = load_creds()

        if command == "permissions":
            paths["permissions"] += "?userid=" + urllib.parse.quote(
                user + "@LLDAP-Domain"
            )

        status, data = api("GET", paths[command])

        print(json.dumps({
            "status": status,
            "data": data.get("data"),
        }, indent=1, default=str))
        return

    if command == "vmconfig" and len(sys.argv) >= 4:
        node = sys.argv[2]
        vmid = sys.argv[3]

        status, data = api(
            "GET",
            "/api2/json/nodes/%s/qemu/%s/config" % (node, vmid),
        )

        print(json.dumps({
            "status": status,
            "data": data.get("data"),
        }, indent=1, default=str))
        return

    if command == "vmstatus" and len(sys.argv) >= 4:
        node = sys.argv[2]
        vmid = sys.argv[3]

        status, data = api(
            "GET",
            "/api2/json/nodes/%s/qemu/%s/status/current" % (node, vmid),
        )

        print(json.dumps({
            "status": status,
            "data": data.get("data"),
        }, indent=1, default=str))
        return

    if command == "raw" and len(sys.argv) >= 3:
        method = sys.argv[2]
        path = sys.argv[3]
        body = sys.argv[4] if len(sys.argv) > 4 else None

        ticket, csrf, _ = login()
        status, data = raw_req(
            method,
            path,
            ticket,
            csrf,
            body,
        )

        print(json.dumps({
            "status": status,
            "data": data,
        }, indent=1, default=str))
        return

    print(__doc__)


if __name__ == "__main__":
    main()
