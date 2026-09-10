#!/usr/bin/env bash
# Hermes profile redundant-file cleanup script (shell version)
# Keeps cron/ and skills/ per user instruction.
# Logs to /opt/hermes/.git/hermes_cleanup.log (same dir as hermes_sync.log)

PROFILE_DIR="${1:-profiles/biraj}"
PROFILE_DIR="$(realpath -m "$PROFILE_DIR")"
LOG_FILE="/opt/hermes/.git/hermes_cleanup.log"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$LOG_FILE"
    echo "$*"
}

clean_target() {
    target="$1"
    if [ -e "$target" ]; then
        if [ -d "$target" ]; then
            rm -rf "$target"
            log "Cleaned dir: $target"
        else
            rm -f "$target"
            log "Cleaned file: $target"
        fi
    fi
}

clean_target "$PROFILE_DIR/models_dev_cache.json"
clean_target "$PROFILE_DIR/provider_models_cache.json"
clean_target "$PROFILE_DIR/ollama_cloud_models_cache.json"
clean_target "$PROFILE_DIR/cache"
clean_target "$PROFILE_DIR/bin"
