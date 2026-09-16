#!/opt/hermes/.venv/bin/python

import asyncio
import json
import sys
import time
from urllib.parse import quote

sys.path.insert(0, "/opt/hermes/scripts")

from mcp.server.mcpserver import MCPServer
from pve_api import api


server = MCPServer(
    name="proxmox",
    title="Proxmox Cluster Management",
    description=(
        "Proxmox VE management through the authenticated LLDAP account. "
        "Proxmox ACL permissions are the authorization source of truth."
    ),
    instructions=(
        "Use discovery tools before acting on guests. "
        "Never assume a VMID, node, or guest type. "
        "Proxmox itself enforces the authenticated account's permissions. "
        "Destructive operations require an explicit confirmation string; "
        "this is a UX safeguard against malformed or accidental calls, "
        "not a substitute for tightly scoped PVE ACL permissions. "
        "Never power off, reboot, shut down, or otherwise mutate the "
        "configuration of a Proxmox cluster node itself. "
        "Guest VM/LXC lifecycle operations are allowed when authorized."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def result(success, **kwargs):
    return json.dumps(
        {
            "success": success,
            **kwargs,
        },
        default=str,
    )


def api_error(status, data):
    error = data.get("errors", data) if isinstance(data, dict) else data
    return result(
        False,
        status=status,
        error=error,
    )


def call_api(method, path, body=None):
    status, data = api(method, path, body)
    return status, data


def guest_path(node, vmid, guest_type, suffix=""):
    guest_type = guest_type.lower()

    if guest_type not in ("qemu", "lxc"):
        raise ValueError("guest_type must be 'qemu' or 'lxc'")

    return (
        f"/api2/json/nodes/{quote(str(node), safe='')}/"
        f"{guest_type}/{int(vmid)}{suffix}"
    )


def find_guest(vmid):
    status, data = call_api(
        "GET",
        "/api2/json/cluster/resources?type=vm",
    )

    if status != 200:
        return None, api_error(status, data)

    for guest in data.get("data", []):
        try:
            if int(guest.get("vmid", -1)) == int(vmid):
                return guest, None
        except (TypeError, ValueError):
            continue

    return None, result(
        False,
        status=404,
        error=f"Guest {vmid} was not found in the cluster.",
    )


def validate_guest(node, vmid):
    guest, error = find_guest(vmid)

    if error:
        return None, error

    if node and guest.get("node") != node:
        return None, result(
            False,
            status=409,
            error=(
                f"VMID {vmid} is currently on node "
                f"{guest.get('node')}, not {node}."
            ),
        )

    return guest, None


def wait_for_task(node, upid, timeout=300):
    if not upid:
        return {
            "completed": True,
            "upid": None,
            "status": "no_task",
        }

    encoded_upid = quote(str(upid), safe="")
    path = (
        f"/api2/json/nodes/{quote(str(node), safe='')}"
        f"/tasks/{encoded_upid}/status"
    )

    started = time.time()

    while time.time() - started < timeout:
        status, data = call_api("GET", path)

        if status != 200:
            return {
                "completed": False,
                "upid": upid,
                "status": "poll_error",
                "api_status": status,
                "error": data,
            }

        task = data.get("data", {})

        if task.get("status") == "stopped":
            exit_status = task.get("exitstatus")

            return {
                "completed": True,
                "upid": upid,
                "status": "stopped",
                "exitstatus": exit_status,
                "success": exit_status == "OK",
            }

        time.sleep(2)

    return {
        "completed": False,
        "upid": upid,
        "status": "timeout",
        "timeout_seconds": timeout,
    }


def execute_task(method, path, node, body=None, wait=True):
    status, data = call_api(method, path, body)

    if status not in (200, 201):
        return api_error(status, data)

    task = data.get("data")

    if not wait or not task:
        return result(
            True,
            status=status,
            data=task,
        )

    task_result = wait_for_task(node, task)

    return result(
        True,
        status=status,
        task=task_result,
    )


def destructive_confirmation(required, confirmation):
    if confirmation != required:
        return result(
            False,
            status=400,
            error="Explicit confirmation required.",
        )

    return None


# ---------------------------------------------------------------------------
# Node-level protection
#
# The generic proxmoxApi() escape hatch is intentionally restrictive for
# node-level mutations.
#
# GET/HEAD node-level requests are allowed for read-only inspection.
#
# Non-read node-level requests are blocked unless explicitly added to
# NODE_MUTATION_ALLOWLIST.
#
# Guest qemu/lxc paths are treated separately and remain available through
# the dedicated guest tools and generic API, subject to PVE ACL permissions.
# ---------------------------------------------------------------------------

NODE_MUTATION_ALLOWLIST = set()


def is_node_level_path(path):
    """Return True when path targets the Proxmox node itself."""

    prefix = "/api2/json/nodes/"

    if not path.startswith(prefix):
        return False

    remainder = path[len(prefix):]
    parts = remainder.split("/", 1)

    if len(parts) < 2:
        return True

    rest = parts[1]

    if rest.startswith("qemu/") or rest.startswith("lxc/"):
        return False

    if rest in ("qemu", "lxc"):
        return False

    return True


def node_mutation_blocked(method, path):
    """Block node-level mutations unless explicitly allowlisted."""

    if method in ("GET", "HEAD"):
        return False

    if not is_node_level_path(path):
        return False

    if (method, path) in NODE_MUTATION_ALLOWLIST:
        return False

    return True


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@server.tool(
    description=(
        "List all Proxmox cluster nodes and their current status. "
        "Use this before relying on a node name."
    )
)
def listNodes() -> str:
    status, data = call_api(
        "GET",
        "/api2/json/nodes",
    )

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        nodes=data.get("data", []),
    )


@server.tool(
    description=(
        "List all VMs and LXC containers in the cluster. "
        "Returns VMID, node, type, name, status and template state."
    )
)
def listGuests() -> str:
    status, data = call_api(
        "GET",
        "/api2/json/cluster/resources?type=vm",
    )

    if status != 200:
        return api_error(status, data)

    guests = []

    for guest in data.get("data", []):
        if guest.get("type") not in ("qemu", "lxc"):
            continue

        guests.append(
            {
                "vmid": guest.get("vmid"),
                "node": guest.get("node"),
                "type": guest.get("type"),
                "name": guest.get("name"),
                "status": guest.get("status"),
                "uptime": guest.get("uptime", 0),
                "template": guest.get("template", 0),
            }
        )

    return result(
        True,
        guests=guests,
    )


@server.tool(
    description="Get the current status of any QEMU VM or LXC container."
)
def getGuestStatus(vmid: int) -> str:
    guest, error = validate_guest(None, vmid)

    if error:
        return error

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        "/status/current",
    )

    status, data = call_api("GET", path)

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        guest={
            "vmid": vmid,
            "node": guest["node"],
            "type": guest["type"],
            "status": data.get("data"),
        },
    )


@server.tool(
    description="Get the complete configuration of a QEMU VM or LXC container."
)
def getGuestConfig(vmid: int) -> str:
    guest, error = validate_guest(None, vmid)

    if error:
        return error

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        "/config",
    )

    status, data = call_api("GET", path)

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        guest={
            "vmid": vmid,
            "node": guest["node"],
            "type": guest["type"],
            "config": data.get("data"),
        },
    )


@server.tool(
    description=(
        "List Proxmox storage available on a node. "
        "Use this before creating or cloning guests when storage is required."
    )
)
def listStorage(node: str = None) -> str:
    if node:
        path = (
            f"/api2/json/nodes/{quote(node, safe='')}/storage"
        )
    else:
        path = "/api2/json/storage"

    status, data = call_api("GET", path)

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        storage=data.get("data", []),
    )


@server.tool(
    description="List storage content on a specific node and storage."
)
def listStorageContent(node: str, storage: str) -> str:
    path = (
        f"/api2/json/nodes/{quote(node, safe='')}"
        f"/storage/{quote(storage, safe='')}/content"
    )

    status, data = call_api("GET", path)

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        content=data.get("data", []),
    )


@server.tool(
    description=(
        "List cluster resources that can be used as VM/LXC templates, "
        "including template guests."
    )
)
def listTemplates() -> str:
    status, data = call_api(
        "GET",
        "/api2/json/cluster/resources?type=vm",
    )

    if status != 200:
        return api_error(status, data)

    templates = [
        guest
        for guest in data.get("data", [])
        if guest.get("template", 0) == 1
    ]

    return result(
        True,
        templates=templates,
    )


@server.tool(
    description="Return the next available VMID according to Proxmox."
)
def getNextVmid() -> str:
    status, data = call_api(
        "GET",
        "/api2/json/cluster/nextid",
    )

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        vmid=data.get("data"),
    )


@server.tool(
    description=(
        "Return the permissions visible to the authenticated Proxmox "
        "account. Use this to understand what the account may be "
        "authorized to do."
    )
)
def getPermissions() -> str:
    status, data = call_api(
        "GET",
        "/api2/json/access/permissions",
    )

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        permissions=data.get("data", {}),
    )


# ---------------------------------------------------------------------------
# Guest lifecycle
# ---------------------------------------------------------------------------

def guest_action(vmid, action):
    guest, error = validate_guest(None, vmid)

    if error:
        return error

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        f"/status/{action}",
    )

    return execute_task(
        "POST",
        path,
        guest["node"],
    )


@server.tool(
    description="Start a QEMU VM or LXC container."
)
def startGuest(vmid: int) -> str:
    return guest_action(vmid, "start")


@server.tool(
    description="Gracefully shut down a QEMU VM or LXC container."
)
def shutdownGuest(vmid: int) -> str:
    return guest_action(vmid, "shutdown")


@server.tool(
    description=(
        "Immediately stop a QEMU VM or LXC container. "
        "Requires confirmation in the form STOP <vmid>."
    )
)
def stopGuest(
    vmid: int,
    confirmation: str = "",
) -> str:
    required = f"STOP {vmid}"

    check = destructive_confirmation(
        required,
        confirmation,
    )

    if check:
        return check

    return guest_action(vmid, "stop")


@server.tool(
    description="Reboot a QEMU VM or LXC container."
)
def rebootGuest(vmid: int) -> str:
    return guest_action(vmid, "reboot")


@server.tool(
    description=(
        "Reset a QEMU VM or LXC container. "
        "Requires confirmation in the form RESET <vmid>."
    )
)
def resetGuest(
    vmid: int,
    confirmation: str = "",
) -> str:
    required = f"RESET {vmid}"

    check = destructive_confirmation(
        required,
        confirmation,
    )

    if check:
        return check

    return guest_action(vmid, "reset")


# ---------------------------------------------------------------------------
# Guest configuration
# ---------------------------------------------------------------------------

@server.tool(
    description=(
        "Update the configuration of an existing VM or LXC. "
        "Parameters must use the Proxmox API configuration parameter names."
    )
)
def updateGuest(
    vmid: int,
    parameters: dict,
) -> str:
    guest, error = validate_guest(None, vmid)

    if error:
        return error

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        "/config",
    )

    status, data = call_api(
        "PUT",
        path,
        parameters,
    )

    if status not in (200, 201):
        return api_error(status, data)

    return result(
        True,
        vmid=vmid,
        node=guest["node"],
        type=guest["type"],
        data=data.get("data"),
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@server.tool(
    description=(
        "Create a QEMU VM using Proxmox API parameters. "
        "The LLDAP/PVE account determines whether this operation is allowed."
    )
)
def createVM(
    node: str,
    vmid: int,
    parameters: dict,
) -> str:
    parameters = dict(parameters)
    parameters["vmid"] = vmid

    path = (
        f"/api2/json/nodes/{quote(node, safe='')}/qemu"
    )

    return execute_task(
        "POST",
        path,
        node,
        parameters,
    )


@server.tool(
    description=(
        "Create an LXC container using Proxmox API parameters. "
        "The LLDAP/PVE account determines whether this operation is allowed."
    )
)
def createLXC(
    node: str,
    vmid: int,
    parameters: dict,
) -> str:
    parameters = dict(parameters)
    parameters["vmid"] = vmid

    path = (
        f"/api2/json/nodes/{quote(node, safe='')}/lxc"
    )

    return execute_task(
        "POST",
        path,
        node,
        parameters,
    )


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------

@server.tool(
    description=(
        "Clone an existing QEMU VM. "
        "Use listGuests/getGuestConfig first to verify the source."
    )
)
def cloneVM(
    vmid: int,
    newid: int,
    node: str = None,
    parameters: dict = None,
) -> str:
    guest, error = validate_guest(node, vmid)

    if error:
        return error

    if guest["type"] != "qemu":
        return result(
            False,
            status=400,
            error=f"VMID {vmid} is {guest['type']}, not qemu.",
        )

    body = dict(parameters or {})
    body["newid"] = newid

    path = guest_path(
        guest["node"],
        vmid,
        "qemu",
        "/clone",
    )

    return execute_task(
        "POST",
        path,
        guest["node"],
        body,
    )


@server.tool(
    description=(
        "Clone an existing LXC container. "
        "Use listGuests/getGuestConfig first to verify the source."
    )
)
def cloneLXC(
    vmid: int,
    newid: int,
    node: str = None,
    parameters: dict = None,
) -> str:
    guest, error = validate_guest(node, vmid)

    if error:
        return error

    if guest["type"] != "lxc":
        return result(
            False,
            status=400,
            error=f"VMID {vmid} is {guest['type']}, not lxc.",
        )

    body = dict(parameters or {})
    body["newid"] = newid

    path = guest_path(
        guest["node"],
        vmid,
        "lxc",
        "/clone",
    )

    return execute_task(
        "POST",
        path,
        guest["node"],
        body,
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@server.tool(
    description=(
        "Permanently delete a QEMU VM or LXC container. "
        "Requires confirmation in the form DELETE <vmid>. "
        "This is irreversible."
    )
)
def deleteGuest(
    vmid: int,
    confirmation: str = "",
) -> str:
    required = f"DELETE {vmid}"

    check = destructive_confirmation(
        required,
        confirmation,
    )

    if check:
        return check

    guest, error = validate_guest(None, vmid)

    if error:
        return error

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
    )

    return execute_task(
        "DELETE",
        path,
        guest["node"],
        wait=True,
    )


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

@server.tool(
    description="List snapshots for a VM or LXC container."
)
def listSnapshots(vmid: int) -> str:
    guest, error = validate_guest(None, vmid)

    if error:
        return error

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        "/snapshot",
    )

    status, data = call_api("GET", path)

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        snapshots=data.get("data", []),
    )


@server.tool(
    description="Create a snapshot of a VM or LXC container."
)
def createSnapshot(
    vmid: int,
    snapname: str,
    description: str = "",
) -> str:
    guest, error = validate_guest(None, vmid)

    if error:
        return error

    body = {
        "snapname": snapname,
    }

    if description:
        body["description"] = description

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        "/snapshot",
    )

    return execute_task(
        "POST",
        path,
        guest["node"],
        body,
    )


@server.tool(
    description=(
        "Rollback a VM/LXC to a snapshot. "
        "Requires confirmation in the form "
        "ROLLBACK <vmid> <snapshot>."
    )
)
def rollbackSnapshot(
    vmid: int,
    snapname: str,
    confirmation: str = "",
) -> str:
    required = f"ROLLBACK {vmid} {snapname}"

    check = destructive_confirmation(
        required,
        confirmation,
    )

    if check:
        return check

    guest, error = validate_guest(None, vmid)

    if error:
        return error

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        f"/snapshot/{quote(snapname, safe='')}/rollback",
    )

    return execute_task(
        "POST",
        path,
        guest["node"],
    )


@server.tool(
    description=(
        "Delete a VM/LXC snapshot. "
        "Requires confirmation in the form "
        "DELETE SNAPSHOT <vmid> <snapshot>."
    )
)
def deleteSnapshot(
    vmid: int,
    snapname: str,
    confirmation: str = "",
) -> str:
    required = f"DELETE SNAPSHOT {vmid} {snapname}"

    check = destructive_confirmation(
        required,
        confirmation,
    )

    if check:
        return check

    guest, error = validate_guest(None, vmid)

    if error:
        return error

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        f"/snapshot/{quote(snapname, safe='')}",
    )

    return execute_task(
        "DELETE",
        path,
        guest["node"],
    )


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

@server.tool(
    description=(
        "Migrate a VM or LXC to another Proxmox node. "
        "Proxmox permissions and migration preconditions are enforced by PVE."
    )
)
def migrateGuest(
    vmid: int,
    target: str,
    online: bool = False,
    parameters: dict = None,
) -> str:
    guest, error = validate_guest(None, vmid)

    if error:
        return error

    body = dict(parameters or {})
    body["target"] = target
    body["online"] = 1 if online else 0

    path = guest_path(
        guest["node"],
        vmid,
        guest["type"],
        "/migrate",
    )

    return execute_task(
        "POST",
        path,
        guest["node"],
        body,
    )


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@server.tool(
    description="Get the current status of a Proxmox task using its UPID."
)
def getTaskStatus(
    node: str,
    upid: str,
) -> str:
    path = (
        f"/api2/json/nodes/{quote(node, safe='')}"
        f"/tasks/{quote(upid, safe='')}/status"
    )

    status, data = call_api("GET", path)

    if status != 200:
        return api_error(status, data)

    return result(
        True,
        task=data.get("data"),
    )


@server.tool(
    description="Wait for a Proxmox task to finish and return its result."
)
def waitForTask(
    node: str,
    upid: str,
    timeout: int = 300,
) -> str:
    return result(
        True,
        task=wait_for_task(
            node,
            upid,
            max(1, min(timeout, 1800)),
        ),
    )


# ---------------------------------------------------------------------------
# Generic Proxmox API
# ---------------------------------------------------------------------------

@server.tool(
    description=(
        "Execute a Proxmox REST API request using the authenticated account. "
        "This is the general escape hatch for supported Proxmox operations "
        "that do not have a dedicated MCP tool. "
        "The Proxmox API remains the authorization boundary. "
        "Node-level mutations including power, services, network, execute, "
        "and node configuration are blocked by default. "
        "Only GET/HEAD requests against node-level paths are allowed through "
        "this generic hatch. "
        "Guest qemu/lxc paths are unaffected by this node-level restriction. "
        "DELETE requests require confirmation in the form DELETE <path>."
    )
)
def proxmoxApi(
    method: str,
    path: str,
    body: dict = None,
    confirmation: str = "",
) -> str:
    method = method.upper()

    if method not in (
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "DELETE",
    ):
        return result(
            False,
            status=400,
            error=f"Unsupported HTTP method: {method}",
        )

    if not path.startswith("/api2/json/"):
        return result(
            False,
            status=400,
            error="Path must start with /api2/json/.",
        )

    if ".." in path:
        return result(
            False,
            status=400,
            error="Path traversal is not allowed.",
        )

    if node_mutation_blocked(method, path):
        return result(
            False,
            status=403,
            error=(
                "Mutating Proxmox node-level state is blocked through "
                "the generic API hatch. Guest VM/LXC operations remain "
                "available through dedicated guest tools and the generic "
                "API, subject to PVE ACL permissions."
            ),
        )

    if method == "DELETE":
        required = f"DELETE {path}"

        check = destructive_confirmation(
            required,
            confirmation,
        )

        if check:
            return check

    access_mutation = (
        path.startswith("/api2/json/access/")
        and method not in ("GET", "HEAD")
    )

    if access_mutation:
        return result(
            False,
            status=403,
            error=(
                "Access-control mutations are blocked from the agent. "
                "Manage LLDAP/PVE permissions separately."
            ),
        )

    status, data = call_api(
        method,
        path,
        body,
    )

    if status not in (200, 201):
        return api_error(status, data)

    return result(
        True,
        status=status,
        data=data.get("data"),
    )


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

async def main():
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
