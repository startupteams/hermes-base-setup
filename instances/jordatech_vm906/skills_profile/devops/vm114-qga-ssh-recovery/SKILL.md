---
name: vm114-qga-ssh-recovery
description: "VM114 (10.0.20.108) management access: dedicated SSH key (ssh vm114), QGA channel quirks (file-write base64 literal, ping≠liveness, exec self-recovery), artifact staging + release transaction recipe."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [vm114, qga, ssh, llm-manager, pve]
---

# VM114 QGA + SSH access recovery (proven 2026-09-28)

VM114 = prod LLM Manager + Server Manager + ARM (10.0.20.108, node miam-00135).
qga exec channel has a **recurring wedge** (500 "no such file" / qgastatus None).
Recovery WITHOUT reset is usually possible — try in this order:

## 1. Diagnose which channels still work (different QEMU request paths!)

```bash
cd ~/work
python3 qga_exec.py ping miam-00135 114     # guest-ping — may 500 even when healthy
python3 pve_api.py raw GET "/api2/json/nodes/miam-00135/qemu/114/agent/get-osinfo"  # file-based
python3 qga_exec.py exec miam-00135 114 "echo alive"
```

- **`guest-ping` 500 is NOT a reliable liveness test on this PVE build.** exec,
  file-write, get-osinfo can all work while ping 500s (seen 2026-09-28, persists).
- A wedged exec channel may **self-recover within minutes** (known pattern from
  09-14). The file-write RPC (a different chardev path) sometimes nudges it back.

## 2. SSH path (provisioned 2026-09-28, Jordan-authorized)

- Keypair: `~/.ssh/vm114_ops/id_ed25519` → root@10.0.20.108. Alias `ssh vm114`
  via `~/.ssh/config.d/vm114.conf` (`Include` set in ~/.ssh/config).
- Least-privilege sudoers only for non-root accounts; for root no sudo needed.
- Key install recipe when exec is dead: stage script via `agent/file-write`
  (base64), decode in-guest, **sha256-verify before running**.

### ⚠️ qga file-write stores content LITERALLY base64

`POST .../agent/file-write` with `encode:1` (JSON int, not bool) writes the
base64 string as-is — it does NOT decode. Always:
`base64 -d <file> > <file>.dec && sha256sum -c` before executing.

## 3. Exec helper

`~/work/qga_exec.py` (ping|exec|script|stage; JSON body — urlencoded 500s on
this build). Keep each exec minimal; nohup + log-poll for long operations.

## 4. If everything is wedged

`qm reset 114` is last-resort (disrupts prod LLM Manager + SM + ARM) and
requires explicit human authorization. SSH provisioned 2026-09-28 makes this
almost never necessary.

## Post-restart hygiene

- `systemctl status qemu-guest-agent` "Memory: 3.9G" is cgroup page-cache from
  exec children, NOT a daemon leak (real RSS ~4.5 MB — check `ps -o rss=`).
- After restarting the guest agent, verify from PVE side with **exec**, not ping.
