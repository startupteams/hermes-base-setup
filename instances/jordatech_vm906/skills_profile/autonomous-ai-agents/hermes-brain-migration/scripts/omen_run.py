#!/usr/bin/env python3
"""Omen SSH relay runner via CT100 tailscale-ssh bridge (miam-00133).

The HP Omen (MIAM-00101, Omarchy) is only reachable over the tailnet, and its
Tailscale SSH requires a one-time browser approval per session. This runner
streams bash scripts over `tailscale ssh` from CT100 (tailscale-router on
miam-00133). First run of the day needs Jordan to approve the URL printed by:
  ssh miam00133 'pct exec 100 -- tailscale ssh jordatech@100.69.169.125 "echo ok"'

Usage:
    from omen_run import run
    out, err, rc = run("hostname; ls ~/.hermes | head", timeout=120)

No passwords are printed or stored; the relay is identity-based (tailscale ssh).
NOTE: the target hostname/IP is Omen-specific; generalize by parameterizing if
another tailnet desktop becomes a Hermes host.
"""
import importlib.util
import os

BRIDGE_HOST = "10.0.20.133"          # miam-00133 (tailscale-router CT100 lives here)
OMEN_TS_IP = "100.69.169.125"        # miam-00101-1-omarchy
OMEN_USER = "jordatech"


def _load_bridge():
    spec = importlib.util.spec_from_file_location(
        "miam_ssh", os.path.expanduser(
            "~/.hermes/profiles/agent_stea004_entrepreneur/scripts/miam_ssh.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(script: str, timeout: int = 240):
    b = _load_bridge()
    cmd = (
        "timeout " + str(timeout) + " pct exec 100 -- tailscale ssh "
        + OMEN_USER + "@" + OMEN_TS_IP + " 'bash -s' <<'INNEREOF'\n"
        + script +
        "\nINNEREOF"
    )
    out, err, rc = b.run_script(BRIDGE_HOST, cmd)
    return out, err, rc


if __name__ == "__main__":
    import sys
    s = sys.stdin.read()
    o, e, r = run(s)
    print(o)
    if e:
        print("STDERR:", e, file=sys.stderr)
    sys.exit(r)
