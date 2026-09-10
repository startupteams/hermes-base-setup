#!/usr/bin/env bash
# Hermes profile redundant-file cleanup — requires explicit profile argument
# Keeps cron/ and skills/ preserved.
# Logs to /opt/hermes/.git/hermes_cleanup.log (same dir as hermes_sync.log)

PROFILE_DIR="${1:-}"
if [ -z "$PROFILE_DIR" ]; then
    echo "ERROR: profile directory must be specified (e.g., profiles/biraj)" >&2
    exit 1
fi
PROFILE_DIR="$(realpath -m "$PROFILE_DIR")"
if [ ! -d "$PROFILE_DIR" ]; then
    echo "ERROR: profile directory not found: $PROFILE_DIR" >&2
    exit 1
fi

LOG_FILE="/opt/hermes/.git/hermes_cleanup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$LOG_FILE"
    echo "$*"
}

clean_target() {
    target="$PROFILE_DIR/$1"
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

clean_target "models_dev_cache.json"
clean_target "provider_models_cache.json"
clean_target "ollama_cloud_models_cache.json"
clean_target "cache"
clean_target "bin"
