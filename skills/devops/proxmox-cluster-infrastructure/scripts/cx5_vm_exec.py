#!/usr/bin/env python3
"""Run a bash script inside a Proxmox VM via node-side `qm guest exec` (base64 pattern).

Import form:  from cx5_vm_exec import vm_exec ; vm_exec("miam00143", "109", SCRIPT)
CLI form:     echo SCRIPT | python3 cx5_vm_exec.py NODE VMID

Requires miam_ssh.run_script (same directory) for node access. On PVE 9.2 the CLI
`qm guest exec` BLOCKS and returns the full result JSON synchronously.
"""
import base64
import json


def vm_exec(node: str, vmid: str, script: str, timeout: int = 420) -> dict:
    from miam_ssh import run_script
    b64 = base64.b64encode(script.encode()).decode()
    out, err, rc = run_script(
        node, f"qm guest exec {vmid} -- bash -c 'echo {b64} | base64 -d | bash'",
        timeout=max(timeout + 30, 60))
    txt = (out or "").strip()
    if not txt:
        return {"error": f"no output rc={rc}: {err[-200:]}", "out-data": "",
                "err-data": "", "exitcode": rc or 1}
    start = txt.find("{")  # skip motd/profile noise before the JSON
    try:
        return json.loads(txt[start:])
    except Exception:
        return {"error": f"parse failed: {txt[-200:]}", "out-data": "",
                "err-data": "", "exitcode": 1}


if __name__ == "__main__":
    import sys
    node, vmid = sys.argv[1], sys.argv[2]
    r = vm_exec(node, vmid, sys.stdin.read())
    print(r.get("out-data", ""))
    if r.get("err-data"):
        print("STDERR:", r["err-data"])
    print(f"[exit={r.get('exitcode')}] {r.get('error', '')}")
    sys.exit(r.get("exitcode", 1) or 0)
