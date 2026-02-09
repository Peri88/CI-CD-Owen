#!/usr/bin/env bash
set -euo pipefail

WATCH_DIR="/home/owen"
WATCH_FILE="Export1.xlsx"
RUNNER="/root/workspace/my-codex-repo/scripts/run_from_export1.sh"
LOCKFILE="/tmp/export1_watch.lock"
LOGFILE="/home/owen/export1_watch.log"
WIN_ERROR_DIR="/mnt/c/Users/goust/OneDrive/바탕 화면/22/OneDrive/owen_잡/4. 벽산"

# Watch for close_write or moved_to (atomic upload + rename)
/usr/bin/inotifywait -m -e close_write,moved_to,create --format '%f' "$WATCH_DIR" | while read -r fname; do
  if [[ "$fname" != "$WATCH_FILE" ]]; then
    continue
  fi

  # debounce + ensure only one run at a time
  if command -v flock >/dev/null 2>&1; then
    (
      flock -n 9 || exit 0
      sleep 5
      {
        echo "[INFO] $(date -Is) start"
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
    sleep 5
    {
      echo "[INFO] $(date -Is) start"
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

done
