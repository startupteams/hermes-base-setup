#!/bin/bash
# llm-control.sh — fixed-command control agent for vLLM guests (MARION-IA-USA pattern)
# Deployed INTO each inference guest by the LLM Manager. No arbitrary command execution.
# Install: base64 this script, run via owning node: qm guest exec <vmid> -- bash -c "echo <b64> | base64 -d > /tmp/x.sh && bash /tmp/x.sh"
# (qm guest exec does NOT forward stdin — never pipe the script body directly.)
# Also append the gateway host's control pubkey to /root/.ssh/authorized_keys.
set -u
ACTION="${1:-}"
UNIT=/etc/systemd/system/vllm.service
log() { logger -t llm-control "$1"; }

case "$ACTION" in
  status)
    systemctl is-active vllm
    systemctl show vllm -p NRestarts 2>/dev/null
    ;;
  get-unit)
    cat "$UNIT" 2>/dev/null || echo "NO_UNIT"
    ;;
  set-unit)
    # unit text arrives on stdin (works over real SSH, e.g. ssh root@guest /opt/llm-control/llm-control.sh set-unit < unit)
    TMP=$(mktemp)
    cat > "$TMP"
    grep -q "^\[Service\]" "$TMP" && grep -q "^ExecStart=" "$TMP" || { echo "INVALID_UNIT"; rm -f "$TMP"; exit 1; }
    cp "$UNIT" "${UNIT}.bak.$(date +%s)" 2>/dev/null
    mv "$TMP" "$UNIT"
    systemctl daemon-reload
    echo "UNIT_SAVED (not restarted)"
    ;;
  restart)
    log "restart requested"
    systemctl restart vllm
    echo "RESTART_ISSUED"
    ;;
  start)
    systemctl start vllm && echo "START_OK" || echo "START_FAIL"
    ;;
  stop)
    systemctl stop vllm && echo "STOP_OK"
    ;;
  logs)
    journalctl -u vllm --no-pager -n 200 2>/dev/null | tail -200
    ;;
  nvidia)
    nvidia-smi --query-gpu=index,utilization.gpu,memory.used,power.draw --format=csv,noheader 2>/dev/null || echo "NO_NVIDIA"
    ;;
  *)
    echo "usage: llm-control.sh {status|get-unit|set-unit|restart|start|stop|logs|nvidia}"
    exit 1
    ;;
esac
