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

## 5. QGA wedge is NOT VM114-specific (generalize)

The wedge class recurred on **VM117 (2026-10-03)** mid-window: after a burst
of long execs (heredoc writes + pip installs during provisioning), PVE flips
to 500 "QEMU guest agent is not running" while the VM itself keeps running
(status=running, agent flag=1, memory normal). Same behavior on VM114/VM120
historically. General rules:

- **Keep exec payloads SHORT** — write files with `~/bin/pve_qga.py write`
  (sha-verified) and exec only brief commands; big heredocs through
  `guest-exec` both wedge the channel AND time out (500 timeout on long
  exec even before the wedge). **A guest-exec ending
  `guest-exec failed - got timeout` is itself a wedge precursor — the agent
  channel typically dies right after (VM117, 3× live 2026-10-03).**
- Self-recovery is NOT reliable on hard wedges: VM117 stayed wedged 25–40 min
  on three occasions; file-write nudges did NOT revive it. Re-probe with a
  1-word exec after a few minutes, but don't wait long — go to reset.
- **The working reset verb: `POST /nodes/{node}/qemu/{vmid}/status/reset`**
  (host-side, no qga needed, plain API ticket auth). The bare
  `POST .../qemu/{vmid}/reset` path is **501 Not Implemented** on this PVE
  build. Reset reboots the VM (~60–75s); services/k3s pods recover from
  persistent volumes — proven 4× on VM117 (2026-10-03) with zero data loss.
  Human-gate still applies for non-disposable production VMs, but for
  disposable/service VMs a hard wedge is a REASON to reset promptly (an
  hour of dead management access costs more than the reboot).
- Diagnostics before reset: `GET /nodes/{node}/qemu/{vmid}/agent` (the
  agent-capability index) usually still answers while every channel 500s,
  confirming qemu status=running + agent flag=1. `agent/get-osinfo` and
  siblings are 501 here (not implemented). VM117 had NO staged SSH key
  (template `stagent` key not provisioned for this profile; ssh →
  Permission denied), so reset was the only recovery — stage an SSH key at
  provision time for future VMs so a wedge never blocks management.
- Prevention for future worker/service VMs: stage an SSH key at provision
  time so qga wedges never block management access (VM124 got this via the
  worker bring-up recipe; VM117 came up without one — lesson applied).

## Post-restart hygiene

- `systemctl status qemu-guest-agent` "Memory: 3.9G" is cgroup page-cache from
  exec children, NOT a daemon leak (real RSS ~4.5 MB — check `ps -o rss=`).
- After restarting the guest agent, verify from PVE side with **exec**, not ping.
- Restarting the guest daemon does NOT clear a QEMU-side exec wedge — the
  wedge lives in the host chardev handling; only in-guest restart + file-write
  nudge / self-recovery clears it (proven 2026-09-28). `guest-ping` stayed 500
  all day while exec/file-write worked; treat ping≠liveness as permanent on
  this build.
- SSH key install order when exec is wedged: file-write the (base64-staged)
  bootstrap script → decode in-guest → sha256-verify → run → THEN use SSH for
  everything else (guest agent restart per runbook §A3, health checks,
  release transactions). File-write channel is the most reliable first move.
