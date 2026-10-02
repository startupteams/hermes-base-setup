1|# PVE qga helper (workstation) — pve_qga.py
2|
3|Reusable tool written 2026-10-02 (W1 MCP gateway window): `~/bin/pve_qga.py` —
(companion: `pve_api.py` in the proxmox-cluster-infrastructure skill — same API, LLDAP bot auth, does NOT poll exec-status; use it for login/vmconfig/raw calls).
4|login-free-to-you helper wrapping the Proxmox API for QEMU guest agent ops on
5|worker VMs (which have NO sshd — qga is the only path).
6|
7|## Proven API quirks (live, 2026-10-02, PVE on 10.0.20.100:8006)
8|
9|1. **Login:** creds file `~/.llm-manager-v011/creds/pve_root.txt` = 2 lines
10|   (user, password). User needs the `@pam` realm appended for the API:
11|   `root` → `root@pam`. POST `/api2/json/access/ticket` (urlencoded).
12|2. **CSRF:** attach `CSRFPreventionToken` header on EVERY POST/PUT/DELETE —
13|   even zero-body POSTs (`agent/ping` 401s without it).
14|3. **agent endpoints** (index via GET `/api2/json/nodes/{node}/qemu/{vmid}/agent`):
15|   - `exec` — POST; `command` MUST be sent as a **list**
16|     (`{'command': ['/bin/bash', '-c', cmd]}`); a string + `arg[]` pair 400s.
17|   - `exec-status` — GET with **query string** `?pid=N` (NOT a urlencode body;
18|     NOT `/agent/exec/get` — that path does not exist here).
19|   - `file-write` — POST, `{file, content}`; stores content **LITERALLY
20|     base64** (window-3 lesson re-confirmed) → stage b64, decode in-guest,
21|     sha256-verify before use (helper `write` op does all of this + 0600).
22|4. **out-data is PLAIN TEXT here** (not base64) — the helper decodes with a
23|   try-b64-fallback-to-plain heuristic. Verify before relying on either.
24|5. **HTTP 596 broken pipe** on rapid sequential exec POSTs — retry with backoff
25|   (helper does 4 attempts); a `file-write` nudge un-wedges a stuck channel.
26|
27|## Usage
28|
29|```bash
30|~/bin/pve_qga.py exec miam00111 124 'hostname'          # guest stdout, exit code
31|~/bin/pve_qga.py write miam00111 124 /local/file /opt/dest  # sha-verified stage
32|```
33|
34|Node map for the worker fleet: VM124 uid-001 @ miam00111, VM125 uid-002 @
35|miam00112, VM126 uid-003 @ miam00143, VM127 uid-004 @ miam00144, VM128 uid-005
36|@ miam-00100.
37|