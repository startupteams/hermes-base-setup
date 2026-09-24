#!/usr/bin/env python3
"""Password-SSH batched runner for MIAM Proxmox ring nodes (paramiko).

Import form:  from cx5_miam_ssh import run_script ; run_script("miam00143", SCRIPT)
CLI form:     python3 cx5_miam_ssh.py miam00143 /path/to/script.sh

Reads the root password from the profile's staged 0600 creds file
(cache/secrets/miam_pve_creds.json, key "pve_root") — never hardcode or echo it.
Batch an entire phase into ONE script per node (hosts pace reconnects).
"""
import json
import os

import paramiko

CREDS = os.path.expanduser(
    "~/.hermes/profiles/agent_stea004_entrepreneur/cache/secrets/miam_pve_creds.json")
NODE_IPS = {  # MIAM-00XXX -> 10.0.20.XXX convention; nodes own these as statics
    "miam00111": "10.0.20.111",
    "miam00143": "10.0.20.143",
    "miam00144": "10.0.20.144",
    "miam00112": "10.0.20.112",
}


def run_script(host: str, script: str, timeout: int = 240):
    pw = json.load(open(CREDS))["pve_root"]["password"]
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(NODE_IPS.get(host, host), username="root", password=pw,
                look_for_keys=False, allow_agent=False, timeout=15)
    try:
        stdin, stdout, stderr = cli.exec_command("bash -s", timeout=timeout)
        stdin.write(script)
        stdin.channel.shutdown_write()
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        return out, err, stdout.channel.recv_exit_status()
    finally:
        cli.close()


if __name__ == "__main__":
    import sys
    out, err, rc = run_script(sys.argv[1], open(sys.argv[2]).read())
    print(out)
    if err:
        print("STDERR:\n" + err)
    sys.exit(rc)
