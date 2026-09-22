#!/usr/bin/env python3
"""RDMA verbs qualification matrix — per-leg ib_send_bw RC/RoCEv2, both directions.

Proven 2026-09-12 post-cable validation (MARION 111/143/144 ring). Encodes the hard-won
ops rules:
- ib_send_bw server binds via RDMA CM: `ss -ltn` NEVER shows it — readiness = pgrep.
- Server is SINGLE-CONNECTION: run the client exactly ONCE (redirect to a log, parse after).
- `BW average` is the header row; values are the NEXT line: `65536 <iters> <peak> <avg>`.
- Bring both ends to MTU 9000 and `ip link up` first (cold-port gotcha; MTU mismatch makes
  QPs connect but transfers fail, masquerading as a GPU-direct failure).
- GID index 1 = RoCE v2 on this fleet (verify per host:
  /sys/class/infiniband/*/ports/1/gid_attrs/types/1).

Usage:  python3 rdma_qual_matrix.py          # runs every leg in LEGS
Requires: password-SSH root access (reads /home/jordatech/.miam_root_pass, never prints)
and the 172.31.0.x qualification IPs already assigned per the reference runbook.
"""
import base64
import sys
import time

import pexpect

END = "___RUN_DONE_42___"
PW_FILE = "/home/jordatech/.miam_root_pass"

# (server_ip, server_dev, client_ip, client_dev, peer_ip_of_client, label)
LEGS = [
    ("10.0.20.143", "mlx5_0",     "10.0.20.111", "rocep4s0f0",  "172.31.0.2", "legA 111->143"),
    ("10.0.20.111", "rocep4s0f0", "10.0.20.143", "mlx5_0",      "172.31.0.1", "legA 143->111"),
    ("10.0.20.143", "mlx5_1",     "10.0.20.144", "rocep4s0f1",  "172.31.0.5", "legB 144->143"),
    ("10.0.20.144", "rocep4s0f1", "10.0.20.143", "mlx5_1",      "172.31.0.6", "legB 143->144"),
]


def ssh_run(host: str, script: str, timeout: int = 120) -> str:
    pw = open(PW_FILE).read().strip()
    b64 = base64.b64encode(script.encode()).decode()
    import pexpect
    child = pexpect.spawn(
        "/usr/bin/ssh",
        ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
         "-l", "root", host, f"echo {b64} | base64 -d | bash; echo {END}"],
        encoding="utf-8", timeout=timeout, maxread=65536)
    pieces, sent = [], False
    deadline = time.time() + timeout
    while time.time() < deadline:
        i = child.expect([r"[Pp]assword\s*:", END, pexpect.EOF, pexpect.TIMEOUT], timeout=15)
        if i == 0 and not sent:
            child.sendline(pw)
            sent = True
        else:
            pieces.append(child.before or "")
            break
    child.close()
    return "".join(pieces).replace("\r\n", "\n")


SRV = ("pkill -f 'ib_send_bw -d' 2>/dev/null; sleep 1; "
       "setsid bash -c 'ib_send_bw -d {dev} -R' </dev/null >/tmp/ib_srv.log 2>&1 & "
       "for i in $(seq 1 12); do pgrep -f 'ib_send_bw -d' >/dev/null && break; sleep 0.5; done; "
       "pgrep -f 'ib_send_bw -d' >/dev/null && echo SRV_UP || echo SRV_FAIL; echo " + END)

CLI = ("ib_send_bw -c RC -d {dev} -R -x 1 -m 4096 -s 65536 {peer} > /tmp/ib_cli.log 2>&1; "
       "grep -A1 'BW average' /tmp/ib_cli.log | tail -1; echo " + END)

SRV_GRAB = "grep -A1 'BW average' /tmp/ib_srv.log | tail -1; echo " + END


def parse_avg_mbps(blob: str):
    """Values line: 65536 <iters> <peak> <avg> — avg is column index 3."""
    for line in blob.splitlines():
        parts = line.split()
        if parts and parts[0] == "65536" and len(parts) >= 4:
            try:
                return float(parts[3])
            except ValueError:
                continue
    return None


def main() -> None:
    results = []
    for sip, sdev, cip, cdev, peer, label in LEGS:
        r1 = ssh_run(sip, SRV.format(dev=sdev), timeout=60)
        up = "SRV_UP" in r1
        time.sleep(1)
        r2 = ssh_run(cip, CLI.format(dev=cdev, peer=peer), timeout=150)
        val = parse_avg_mbps(r2)
        if val is None:
            # client log failed to parse -> server-side number is authoritative
            r3 = ssh_run(sip, SRV_GRAB, timeout=60)
            val = parse_avg_mbps(r3)
        gbps = val * 8 / 1000 if val else 0.0
        verdict = "PASS" if gbps >= 80 else ("MARGINAL" if gbps >= 60 else "FAIL/MISSING")
        print(f"{label}: srv={'UP' if up else 'FAIL'} | "
              f"{val if val else '-'} MB/s ~= {gbps:.1f} Gb/s -> {verdict}", flush=True)
        results.append((label, gbps))
        time.sleep(2)
    print("\nSUMMARY:", ", ".join(f"{l}={g:.1f}Gb/s" for l, g in results))


if __name__ == "__main__":
    sys.exit(main())