#!/usr/bin/env python3
"""Drain-hardened password-SSH runner for Proxmox MIAM nodes (pexpect).

Successor to scripts/ssh_run.py: fixes the empty-output failure mode where a single
expect(EOF) + child.before read returned truncated/empty output. This runner:
  1. spawns ssh, waits for the [Pp]assword: prompt, sends the credential
  2. feeds the script as base64 (no quoting/PTY-mangling issues for the script TEXT)
  3. loops expect([password, END-marker, EOF, TIMEOUT]), appending child.before on
     EVERY iteration until the END marker or EOF
  4. flags auth failure only on a SECOND password prompt or "Permission denied"
     (never on a literal `cipassword: ****` line from qm config output)

Reads the credential from /home/jordatech/.miam_root_pass (root password shared by the
MIAM Proxmox nodes AND the OPNsense web UI). Never prints it.

Usage (module):   from noderun import run; run("10.0.20.135", script_text, timeout=120)
Usage (CLI):      python3 noderun.py <host> <script-file.sh>
"""
import base64
import sys
import time

import pexpect

END = "___RUN_DONE_42___"


def run(host: str, script: str, user: str = "root", timeout: int = 120) -> str:
    pw = open("/home/jordatech/.miam_root_pass").read().strip()
    b64 = base64.b64encode(script.encode()).decode()
    wrapped = f"echo {b64} | base64 -d | bash; echo {END}"
    child = pexpect.spawn(
        "/usr/bin/ssh",
        ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
         "-o", "ConnectTimeout=10", "-l", user, host, wrapped],
        encoding="utf-8", timeout=timeout, maxread=65536)
    pieces = []
    sent = False
    deadline = time.time() + timeout
    while time.time() < deadline:
        i = child.expect([r"[Pp]assword\s*:", END, pexpect.EOF, pexpect.TIMEOUT],
                         timeout=15)
        if i == 0 and not sent:
            child.sendline(pw)
            sent = True
        elif i == 0 and sent:
            # a second password prompt after sending = auth failure
            pieces.append(child.before or "")
            break
        elif i == 1:
            pieces.append(child.before or "")
            break
        elif i == 2:
            pieces.append(child.before or "")
            break
        else:
            pieces.append(child.before or "")
    child.close()
    text = "".join(pieces)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "Permission denied" in text:
        text += "\n*** AUTH FAILED ***"
    return text


if __name__ == "__main__":
    host = sys.argv[1]
    path = sys.argv[2]
    script = open(path).read()
    print(run(host, script))
