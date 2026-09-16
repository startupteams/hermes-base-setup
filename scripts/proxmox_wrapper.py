#!/usr/bin/env python3

"""Simple Proxmox guest wrapper.

Usage:
  proxmox_wrapper.py status <vmid>
  proxmox_wrapper.py start <vmid>
  proxmox_wrapper.py shutdown <vmid>
  proxmox_wrapper.py stop <vmid>
  proxmox_wrapper.py reboot <vmid>
"""

import sys

sys.path.insert(0, "/opt/hermes/scripts")

from pve_api import api


def find_guest(vmid):
    status, data = api(
        "GET",
        "/api2/json/cluster/resources?type=vm",
    )

    if status != 200:
        return None

    for guest in data.get("data", []):
        if int(guest.get("vmid", -1)) == int(vmid):
            return guest

    return None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    action = sys.argv[1]
    vmid = int(sys.argv[2])

    guest = find_guest(vmid)

    if not guest:
        print("Guest not found.")
        return 1

    node = guest["node"]
    guest_type = guest["type"]

    if action == "status":
        path = (
            "/api2/json/nodes/%s/%s/%s/status/current"
            % (node, guest_type, vmid)
        )

        status, data = api("GET", path)

    elif action in (
        "start",
        "shutdown",
        "stop",
        "reboot",
    ):
        path = (
            "/api2/json/nodes/%s/%s/%s/status/%s"
            % (
                node,
                guest_type,
                vmid,
                action,
            )
        )

        status, data = api(
            "POST",
            path,
        )

    else:
        print("Unsupported action.")
        return 1

    print(
        __import__("json").dumps(
            {
                "status": status,
                "data": data.get("data"),
            },
            indent=2,
            default=str,
        )
    )

    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
