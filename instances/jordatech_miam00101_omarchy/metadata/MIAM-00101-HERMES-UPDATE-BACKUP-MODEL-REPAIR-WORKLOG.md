# MIAM-00101 Hermes Update / Backup / Default-Model Repair - WORKLOG

## 2026-09-26 22:15-22:45 (+05:45) - Session start

### Phase A/B/C discovery (verified)
- Host: MIAM-00101, Omarchy, kernel 7.2.5-3-omarchy, user jordatech (docker/wheel groups).
- Install type: **git source install** (`~/.hermes/hermes-agent`, origin NousResearch/hermes-agent, branch main).
- Hermes v0.21.5 (2026.9.24) @ 749220ef. `hermes update --check`: 2062 commits behind origin/main.
- Runtime: single gateway, PID 1473, `systemd --user` unit `~/.config/systemd/user/hermes-gateway.service` (Restart=always). No Desktop-spawned second gateway. No hermes docker containers (only the Hermes tool sandbox container).
- `updates.check` config = true. `_config_version` = 46.
- `hermes update --plan`: git install, profile default, 1 running service (gateway) restart via systemctl.

### Egress incident (recurring, fixed again)
- Docker-backed tools blocked: iron-proxy enabled but not running on its tunnel port.
- Fixed on-host via `hermes egress start`. NOT reboot-persistent (2nd occurrence across sessions).

### Phase H/J model findings (verification BEFORE change)
- `/home/jordatech/.hermes/config.yaml`: `model.default: z-ai/glm-5.3-flash`, `model.provider: openrouter`, `base_url: https://openrouter.ai/api/v1`, `api_mode: chat_completions`. NO qwen alias in config.yaml / .env / auth.json / SOUL.md.
- => Persistent default is ALREADY GLM/OpenRouter. If `/new` still shows qwen38-27b, likely a live session override or the gateway process predating the config change (update restart addresses this). Telegram acceptance test pending.
- Local qwen endpoint VERIFIED from host: host-loopback port 8080, path `/v1/models`, returns qwen38-27b (llama.cpp-style OpenAI-compatible). Gateway runs on host => loopback URL correct. systemd user service `qwen38-27b.service` exists.

### Phase G portable sync audit
- `~/.hermes/scripts/portable_brain_sync.sh` explicitly never touches .env/auth.json/config.yaml/state.db.
- Sync last succeeded 2026-09-25 01:15 UTC; Hermes-cron hourly sync stalled => replaced by systemd `hermes-brain-sync.timer` (03:00 daily).

### Phase D/E/F backup + scheduling (created)
- `~/.hermes/scripts/backup-hermes.sh` (flock, sqlite online backup + quick_check, brain/skills/harness/private, sha256 manifest, retention 3 latest/14 daily/8 weekly/6 monthly with safety gate, BACKUP-COMPLETE marker).
- Manual run verified: `/home/jordatech/Work/hermes-backups/20260926-222033` (96M, 200 skills, state/projects/kanban quick_check=ok).
- systemd user timers enabled: hermes-backup 02:30, hermes-brain-sync 03:00, hermes-update 03:15 (Persistent=true).
- `~/.hermes/scripts/update-hermes.sh`: flock -> mandatory backup -> git fetch/pull --ff-only -> pip -e -> config check -> systemctl restart -> health -> automatic rollback to old rev on failed restart. Receipts in ~/.hermes/logs/local_update_receipts/.

### Unresolved / next
- Hermes update (2062 commits) next, backup-first wrapper.
- Telegram /new acceptance test after update restart.
