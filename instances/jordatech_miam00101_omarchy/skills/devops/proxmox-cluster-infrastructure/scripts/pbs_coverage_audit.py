#!/usr/bin/env python3
"""Read-only PBS backup-coverage audit across the PVE cluster.

Collects, in one pass (no writes anywhere):
  - cluster resources + per-guest config (onboot, bind mounts mp0..N)
  - PVE vzdump backup jobs (scope: all+exclude vs fixed include)
  - PBS datastore snapshots (via token API on :8007) + datastore status/GC stats
  - per-guest newest backup age + verify state

Usage:
  python3 pbs_coverage_audit.py > coverage_raw.json
  (writes nothing to the cluster; stdout is the JSON evidence blob)

Env/paths expected (MARION-IA-USA defaults, override via env):
  PVE_HOST   (default 10.0.20.147)   any cluster node for the PVE API
  PBS_HOST   (default 10.0.20.147)   the PBS host
  PBS_DATASTORE (default marion-pbs)
  creds: ~/.pve_ldap_bot (two lines: user, password — realm @LLDAP-Domain)
  PBS token secret is fetched read-only from /etc/pve/priv/storage/<storage>.pw
  on the PBS host via scripts/noderun.py root SSH — never printed.

Reuse the skill's pve_api.py/noderun.py; they live in the same scripts/ dir.
"""
import base64
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PVE_HOST = os.environ.get("PVE_HOST", "10.0.20.147")
PBS_HOST = os.environ.get("PBS_HOST", PVE_HOST)
PBS_DS = os.environ.get("PBS_DATASTORE", "marion-pbs")
PBS_STORAGE_ID = os.environ.get("PBS_STORAGE_ID", "pbs-marion")
PBS_PORT = int(os.environ.get("PBS_PORT", "8007"))
RECENT_H = float(os.environ.get("RECENT_H", "30"))

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def pve(method, path, body=None):
    from pve_api import login, raw_req
    t, c, _ = login()
    st, d = raw_req(method, "/api2/json" + path, t, c, body)
    if isinstance(d, dict) and "data" in d:
        d = d["data"]
    if isinstance(d, str):
        d = json.loads(d)
    return st, d


def pbs_token_secret():
    from noderun import run
    out = run(PBS_HOST, f"cat /etc/pve/priv/storage/{PBS_STORAGE_ID}.pw", timeout=60)
    return out.strip().splitlines()[-1].strip()


def pbs_get(path, secret):
    req = urllib.request.Request(f"https://{PBS_HOST}:{PBS_PORT}/api2/json{path}")
    req.add_header("Authorization", f"PBSAPIToken=pve-backup@pbs!marion-cluster:{secret}")
    with urllib.request.urlopen(req, context=CTX, timeout=180) as r:
        return json.load(r).get("data")


def main():
    now = time.time()
    st, res = pve("GET", "/cluster/resources")
    guests = sorted(
        (g for g in res if g.get("type") in ("qemu", "lxc")),
        key=lambda g: (g["node"], g["vmid"]))

    configs = {}
    for g in guests:
        typ = "qemu" if g["type"] == "qemu" else "lxc"
        configs[f'{g["node"]}/{typ}/{g["vmid"]}'] = pve(
            "GET", f'/nodes/{g["node"]}/{typ}/{g["vmid"]}/config')[1]

    st, jobs = pve("GET", "/cluster/backup")

    secret = pbs_token_secret()
    snaps = pbs_get(f"/admin/datastore/{PBS_DS}/snapshots", secret)
    ds_status = pbs_get(f"/admin/datastore/{PBS_DS}/status", secret)
    gc_status = pbs_get(f"/admin/datastore/{PBS_DS}/gc", secret)
    try:
        prune_jobs = pbs_get("/admin/prune", secret)
    except Exception as e:
        prune_jobs = [{"error": str(e)}]

    by_id = {}
    for sn in snaps:
        by_id.setdefault((sn["backup-type"], sn["backup-id"]), []).append(sn)

    out = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "datastore_status": ds_status,
           "gc_status": gc_status, "prune_jobs": prune_jobs, "jobs": jobs, "guests": []}
    for g in guests:
        typ = "qemu" if g["type"] == "qemu" else "ct"
        cfg = configs.get(f'{g["node"]}/{typ}/{g["vmid"]}', {}) or {}
        lst = sorted(by_id.get((typ, str(g["vmid"])), []),
                     key=lambda x: x["backup-time"], reverse=True)
        newest = lst[0] if lst else None
        out["guests"].append({
            "vmid": g["vmid"], "node": g["node"], "type": g["type"],
            "name": g.get("name"), "status": g.get("status"),
            "onboot": cfg.get("onboot", "0"),
            "bind_mounts": {k: v for k, v in cfg.items() if k.startswith("mp")},
            "pbs_group_size": len(lst),
            "newest_backup": (time.strftime("%Y-%m-%d %H:%M", time.localtime(
                newest["backup-time"])) if newest else None),
            "age_h": (round((now - newest["backup-time"]) / 3600, 1) if newest else None),
            "recent_enough": bool(newest and (now - newest["backup-time"]) / 3600 <= RECENT_H),
            "verify": (newest or {}).get("verification", {}).get("state") if newest else None,
            "size_gb": (round(newest["size"] / 1e9, 2) if newest else None),
        })
    json.dump(out, sys.stdout, indent=1)
    print(file=sys.stderr)
    print(f"guests={len(out['guests'])} pbs_snapshots={len(snaps)}", file=sys.stderr)


if __name__ == "__main__":
    main()
