#!/usr/bin/env python3
"""Batched SSH runner for Proxmox fleet nodes (password auth via pexpect).

Usage: ssh_run.py HOST SCRIPT_FILE OUT_FILE [user]
Env:   MIAM_SSH_PW must hold the password (never hardcode; source from session secret).

Batches an entire bash script into ONE ssh call (hosts rate-limit rapid reconnects),
drains ALL output via an expect-loop (single child.before read loses output), and
treats only 'Permission denied' as auth failure (qm config prints a literal
'cipassword: ****' that false-matches password prompts).

This is the reference implementation extracted from a session-proven helper.
"""
import base64
import os
import pexpect
import sys


def run(host: str, script_path: str, outfile: str, user: str = "root") -> str:
    pw = os.environ.get("MIAM_SSH_PW")
    assert pw, "MIAM_SSH_PW env var not set (do not hardcode passwords)"
    script = open(script_path).read()
    b64 = base64.b64encode(script.encode()).decode()

    child = pexpect.spawn(
        "/usr/bin/ssh",
        ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
         "-o", "ConnectTimeout=10", "-l", user, host,
         "bash", "-c", f"echo {b64} | base64 -d | bash"],
        encoding="utf-8", timeout=60, maxread=65536)

    out = []
    while True:
        i = child.expect([r"[Pp]assword:", pexpect.EOF, pexpect.TIMEOUT], timeout=30)
        if i == 0:
            child.sendline(pw)
        elif i == 1:
            out.append(child.before or "")
            break
        else:
            out.append(child.before or "")

    result = "".join(out)
    if "Permission denied" in result:
        result += "\n*** AUTH FAILED ***"
    with open(outfile, "w") as f:
        f.write(result)
    print(f"wrote {len(result)} chars to {outfile}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("usage: ssh_run.py HOST SCRIPT_FILE OUT_FILE [user]")
    run(*sys.argv[1:])
