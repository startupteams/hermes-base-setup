#!/usr/bin/env python3
"""Allowlisted Proxmox VM ops for the LLM Manager (plan §12.1) — proven 2026-09-10.

Reads the PVE token from /etc/llm-manager/secrets/pve_token (or env PVE_TOKEN).
Allowlist ONLY: vm-status(list), vm-start, vm-shutdown, vm-reboot.
NO host shell, NO qm set, NO force-stop (plan §12.1/§23 fail-closed rules).

Token setup (cluster node, once):
    pveum user add llm-manager@pve
    pveum acl modify /vms/<vmid> --users llm-manager@pve --roles PVEVMUser   # per VM
    pveum acl modify /vms/<vmid> --users llm-manager@pve --roles PVEAuditor # status read
    pveum user token add llm-manager@pve manager-control --privsep 0   # privsep=1 breaks status!

Usage:
    pve_ops.py list | status <guest-ip> | start|shutdown|reboot <guest-ip>
"""
import json, os, sys, urllib.request, ssl

NODE_MAP = {
    "10.0.20.161": ("miam00111", "103"),
    "10.0.20.162": ("miam00112", "401"),
    "10.0.20.163": ("miam00143", "109"),
    "10.0.20.164": ("miam00144", "111"),
}
PVE_HOST = os.environ.get("PVE_HOST", "10.0.20.135")


def _token():
    tok = os.environ.get("PVE_TOKEN")
    if not tok:
        with open("/etc/llm-manager/secrets/pve_token") as f:
            tok = f.read().strip()
    return tok


def api(path, method="GET", payload=None):
    tok = _token()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f"https://{PVE_HOST}:8006/api2/json{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"PVEAPIToken=llm-manager@pve!manager-control={tok}",
                 "Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    return json.loads(resp.read())


def vm_status(ip):
    node, vmid = NODE_MAP[ip]
    d = (api(f"/nodes/{node}/qemu/{vmid}/status/current").get("data") or {})
    return {"ip": ip, "vmid": vmid, "node": node, "status": d.get("status"), "name": d.get("name"),
            "uptime_s": d.get("uptime"), "cpu_pct": d.get("cpu"), "mem": d.get("mem")}


def vm_action(ip, action):
    assert action in ("start", "shutdown", "reboot"), f"action {action} not allowlisted"
    node, vmid = NODE_MAP[ip]
    d = api(f"/nodes/{node}/qemu/{vmid}/status/{action}", method="POST")
    return {"ip": ip, "vmid": vmid, "node": node, "action": action, "ok": True,
            "upid": (d or {}).get("data")}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for ip in NODE_MAP:
            print(json.dumps(vm_status(ip)))
    elif cmd == "status":
        print(json.dumps(vm_status(sys.argv[2])))
    elif cmd in ("start", "shutdown", "reboot"):
        print(json.dumps(vm_action(sys.argv[2], cmd)))
    else:
        raise SystemExit(f"unknown command {cmd}")
