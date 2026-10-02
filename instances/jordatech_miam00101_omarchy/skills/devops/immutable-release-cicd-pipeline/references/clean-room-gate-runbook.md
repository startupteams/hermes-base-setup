# Clean-Room Staging Gate Runbook (VM120 / llm-manager reference, 2026-09-27)

End-to-end sequence with the commands that actually worked. Adapt names/paths per target service.

## 1. Provision staging VM (PVE)

- Clone prod VM for OS parity: `POST /nodes/<node>/qemu/<prod-vmid>/clone` (full, target storage). If the target VMID conf already exists but the VM isn't in cluster resources → orphan conf from an interrupted request: `DELETE /nodes/<node>/qemu/<vmid>` (destroy); if lock timeout, retry after ~5s.
- qmclone task polling: task-status returns `exitcode: None` on success for some PVE versions — verify via the task log tail ("TASK OK") and `qemu/<vmid>/config` existence.
- Check target IP is free first (`ping -c1 -W1 <ip>` rc=1 = free; rc=2 = also fine/free on some nets — cross-check cluster resources).

## 2. Renumber identity IMMEDIATELY (before service reconfig)

The clone boots with prod's netplan (prod IP!) and prod services auto-starting. In order:

```bash
systemctl stop nginx <svc>-web <svc>-recovery <svc>-collectors litellm agent-manager ...
# rewrite netplan to staging IP (match block may reference the OLD prod MAC — the clone's NIC
# MAC differs; drop the match block entirely or read the real MAC from `ip link` first)
cat > /etc/netplan/50-cloud-init.yaml <<'NP'
network:
  version: 2
  ethernets:
    eth0:
      addresses: ["<STG_IP>/24"]
      nameservers: {addresses: [<dns>]}
      routes: [{to: default, via: <gw>}]
NP
netplan apply          # may bounce the interface/VM — expect a reboot
hostnamectl set-hostname <svc>-staging
rm -f /etc/machine-id /var/lib/dbus/machine-id && systemd-machine-id-setup
```

Netplan gotchas: `search: []` key is invalid in some netplan versions ("unknown key 'search'"); a stale `match: macaddress:` referencing the prod MAC makes eth0 fail to come up ("Cannot find unique matching interface") — remove the match.

## 3. Wipe to clean room

```bash
systemctl disable --now <all svc units>
rm -f /etc/systemd/system/<svc>-*.service /etc/nginx/sites-enabled/<svc>
rm -rf /opt/<svc> /opt/<other-svc-components>
rm -rf /etc/<svc>/secrets/* /etc/<svc>/tls/* /etc/<svc>/backups/* /etc/<svc>/*.yaml /etc/<svc>/*.env
```

Verify: `ls /opt` has no service trees; `/etc/<svc>` has only empty `secrets/ tls/` dirs.

## 4. Get the artifact + deploy scripts onto the staging VM

SSH usually unavailable on these VMs (key not authorized). Two proven paths:

**Path A — workstation HTTP server (RECOMMENDED, handles big files):**
```bash
# on workstation:
mkdir serve && cp artifact.tar.gz* deploy-scripts... serve/
cd serve && python3 -m http.server 8899 --bind 0.0.0.0   # serve THIS dir, not the parent!
# on VM (via small qga exec):
curl -sf http://<ws-ip>:8899/<file> -o <dest> && sha256sum -c <dest>.sha256
```
Kill the server when done. Classic mistake: starting the server in the parent dir → every script 404s.

**Path B — qga chunked push:** works for ≤~3KB payloads; larger/longer execs wedge the agent channel. If `agent/ping` or `guest-exec` returns "QEMU guest agent is not running": `qm reset <vmid>`, wait for agent, retry. Heredoc-with-quoted-delimiter single exec (`cat > file <<'EOF'`) is the most byte-faithful small-payload method; stdin-piping through `echo | python3` does NOT work over qga (stdin doesn't flow).

## 5. Bootstrap + secrets + DB

```bash
/opt/llm-manager-deploy/bootstrap-vm.sh /tmp/<artifact>.tar.gz --staging
# staging-local secret files (fresh values, never prod copies):
printf '<staging-value>' > /etc/<svc>/secrets/<name>   # per the secret-file contract
# systemd drop-in for DB endpoint override:
printf '[Service]\nEnvironment=LLM_MANAGER_PG_HOST=127.0.0.1\n' > /etc/systemd/system/<unit>.service.d/staging-pg.conf
systemctl daemon-reload
```

Local PostgreSQL on the staging VM (isolated, no shared prod DB):
```bash
apt-get install -y postgresql
sudo -u postgres psql -c "CREATE ROLE <user> LOGIN PASSWORD '<staging-pw>' CREATEDB"
sudo -u postgres createdb -O <user> <db>           # + a second db if the gateway needs one
sudo -u postgres psql -d <db> -f /opt/<svc>/current/db/schema/schema.sql
# migrations via the release venv + env vars, then seed UNMANAGED/mock rows so
# staging recovery can never act on real infrastructure
```

## 6. Gate + proofs

```bash
/opt/<svc>-deploy/healthcheck.sh --staging        # all PASS incl. release manifest observability
# §switching proof (DB-only promotion, no Python edits):
cd /opt/<svc>/current/app && LLM_MANAGER_PG_HOST=127.0.0.1 <venv>/python - <<'PY'
import active_deployments as ad
ad.set_active("<host>", "<ip-A>", "proof"); ad.active_ip_for("<host>")
ad.set_active("<host>", "<ip-B>", "proof"); ad.active_ip_for("<host>")
PY
# rollback proof:
/opt/<svc>-deploy/rollback.sh <previous-sha>      # expect PASS on compatible releases
/opt/<svc>-deploy/rollback.sh <good-sha>          # roll forward again
```

Then REBOOT the VM and re-run healthcheck — persistence counts for the gate.

## Known staging-state quirks from the reference run

- A qmclone interrupted mid-request leaves an orphan conf; destroy before retrying clone.
- Bootstrap unit 203/EXEC = compat symlinks missing (app→service/app, venv→.venv) — fixed in bootstrap-vm.sh §5b; on already-bootstrapped VMs create them by hand per release dir.
- `pgrep -f deploy-release` in a poll loop matches itself — check `tail <log>` plus a marker echo instead.
- qga exec heredoc with quoted delimiter preserves `$()` and quotes exactly; argv-passed base64 gets mangled by the guest shell; stdin does not flow.
- **`netplan apply` after replacing the config can reboot or bounce the guest** — expect the qga channel to drop mid-sequence and re-verify with `echo alive` before the next exec. The MAC-match failure mode: the clone's netplan `match: macaddress:` references the SOURCE VM's MAC, so the clone's NIC stays DOWN with "Cannot find unique matching interface for eth0" until the match block is removed — the VM is unreachable at the new IP and this looks like a networking bug rather than a netplan bug.
- **Migration runner on a transaction deploy needs DB env inline**: `LLM_MANAGER_PG_HOST=… LLM_MANAGER_PG_DB=… LLM_MANAGER_PG_USER=… LLM_MANAGER_PG_PASSWORD=… ./deploy-release.sh <artifact> --staging` — without credentials the migration step fails ("no password supplied") and the transaction auto-rolls back the candidate install.
- **Deploying the deploy scripts**: the staging VM's copy of `deploy-release.sh`/`healthcheck.sh` must be REFRESHED after each repo fix before re-running the transaction — three staging deploys ran against a stale healthcheck and produced three false rollbacks before this was noticed. Verify `md5sum` of the staged script vs the repo file.
- **Rollback across an env-fix boundary fails healthcheck BY DESIGN** (old release lacks the new env override): execute the rollback to prove mechanics, then immediately roll forward to the good release; document the limitation rather than softening the healthcheck.
