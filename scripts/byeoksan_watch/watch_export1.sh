#!/usr/bin/env bash
set -euo pipefail

WATCH_FILE="/home/owen/Export1.xlsx"
RUNNER="$(cd "$(dirname "$0")" && pwd)/run_from_export1.sh"
LOCKFILE="/tmp/export1_watch.lock"
LOGFILE="/home/owen/export1_watch.log"
WIN_ERROR_DIR="/mnt/c/Users/goust/OneDrive/바탕 화면/22/OneDrive/owen_잡/4. 벽산"

# Polling watcher (WSL + Windows writes can miss inotify events)
# Checks mtime/size every 5s and triggers when stable for two checks.
INTERVAL=5
last_sig=""

while true; do
  if [[ -f "$WATCH_FILE" ]]; then
    mtime=$(stat -c %Y "$WATCH_FILE" 2>/dev/null || echo 0)
    size=$(stat -c %s "$WATCH_FILE" 2>/dev/null || echo 0)
    sig="${mtime}:${size}"

    if [[ "$sig" != "$last_sig" ]]; then
      # Wait for file to settle
      sleep "$INTERVAL"
      mtime2=$(stat -c %Y "$WATCH_FILE" 2>/dev/null || echo 0)
      size2=$(stat -c %s "$WATCH_FILE" 2>/dev/null || echo 0)
      sig2="${mtime2}:${size2}"
      if [[ "$sig" == "$sig2" ]]; then
        if command -v flock >/dev/null 2>&1; then
          (
            flock -n 9 || exit 0
            {
              echo "[INFO] $(date -Is) start (poll)"
              bash "$RUNNER"
              rc=$?
              if [[ $rc -ne 0 ]]; then
                echo "[ERROR] $(date -Is) run failed rc=$rc"
              else
                echo "[INFO] $(date -Is) done"
              fi
              exit $rc
            } >>"$LOGFILE" 2>&1
            rc=$?
            if [[ $rc -ne 0 ]]; then
              mkdir -p "$WIN_ERROR_DIR"
              ts="$(date +%Y%m%d_%H%M%S)"
              cp -f "$LOGFILE" "$WIN_ERROR_DIR/ERROR_export1_watch_${ts}.log" || true
            fi
          ) 9>"$LOCKFILE"
        else
          {
            echo "[INFO] $(date -Is) start (poll)"
            bash "$RUNNER"
            rc=$?
            if [[ $rc -ne 0 ]]; then
              echo "[ERROR] $(date -Is) run failed rc=$rc"
            else
              echo "[INFO] $(date -Is) done"
            fi
            exit $rc
          } >>"$LOGFILE" 2>&1
          rc=$?
          if [[ $rc -ne 0 ]]; then
            mkdir -p "$WIN_ERROR_DIR"
            ts="$(date +%Y%m%d_%H%M%S)"
            cp -f "$LOGFILE" "$WIN_ERROR_DIR/ERROR_export1_watch_${ts}.log" || true
          fi
        fi
        last_sig="$sig"
      fi
    fi
  fi
  sleep "$INTERVAL"
done
