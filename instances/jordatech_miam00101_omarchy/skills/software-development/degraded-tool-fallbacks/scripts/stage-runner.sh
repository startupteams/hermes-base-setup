#!/usr/bin/env bash
# Generic host stage-runner for degraded-sandbox operation via cron no_agent jobs.
# Usage: stage-runner.sh <stage>
# Writes output+rc of every command to ~/.hermes/scripts/out_<stage>.log
# ALWAYS exits 0 — diagnose from the log, never from cron job status.
set -u
stage="${1:-help}"
out="$HOME/.hermes/scripts/out_${stage}.log"
run(){ echo "\$ $1" >> "$out" 2>&1; eval "$1" >> "$out" 2>&1; echo "rc=$?" >> "$out"; }
: > "$out"
echo "=== STAGE $stage $(date -Is) ===" >> "$out"
case "$stage" in
  discovery)
    run "hostname; uname -a; whoami"
    run "lscpu | grep -E 'Model name|^CPU\\(s\\)'"
    run "free -h"
    run "nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv 2>&1"
    run "df -hT -x tmpfs -x devtmpfs -x efivarfs 2>/dev/null; df -h \$HOME | tail -1"
    run "command -v hermes llama-server llama-cli nvcc"
    run "ss -lntp 2>/dev/null | grep :8080 || echo port8080-free"
    run "systemctl --user list-units --type=service --state=running --no-pager 2>/dev/null | head -20"
    run "crontab -l 2>/dev/null | head -40; true"
    run "systemctl status docker --no-pager 2>&1 | head -15; true"
    ;;
  *)  # define your own stages by copying the case pattern
    echo "unknown stage: $stage" >> "$out" ;;
esac
echo "=== END $(date -Is) ===" >> "$out"
exit 0
