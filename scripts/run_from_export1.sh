#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$DIR/.venv"
EXPORT1="/home/owen/Export1.xlsx"
DATE_TAG="$(date +%Y%m%d)"
PARSED="/home/owen/Export(가공)_${DATE_TAG}.xlsx"
REPORT="/home/owen/벽산 리포트_백업상태(양식)_${DATE_TAG}.xlsx"
WIN_DEST_DIR="/mnt/c/Users/goust/OneDrive/바탕 화면/22/OneDrive/owen_잡/4. 벽산"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip -q install pandas openpyxl

# copy base report template to dated output
cp "/home/owen/벽산 리포트_백업상태(양식).xlsx" "$REPORT"

python3 "$DIR/export1_to_report.py" \
  --export1 "$EXPORT1" \
  --parsed "$PARSED" \
  --report "$REPORT"

mkdir -p "$WIN_DEST_DIR"
# Safety check: only copy the dated report, never the template
if [[ -f "$REPORT" && "$REPORT" == *"벽산 리포트_백업상태(양식)_"*.xlsx ]]; then
  if ! cp -f "$REPORT" "$WIN_DEST_DIR/"; then
    # If overwrite fails (e.g., file in use), write a timestamped copy instead
    ts="$(date +%H%M%S)"
    fallback="$WIN_DEST_DIR/벽산 리포트_백업상태(양식)_${DATE_TAG}_${ts}.xlsx"
    if cp -f "$REPORT" "$fallback"; then
      echo "[WARN] Overwrite failed; copied to $fallback"
    else
      echo "[ERROR] Failed to copy report to Windows path"
      exit 2
    fi
  fi
else
  echo "[WARN] Report missing or unexpected filename: $REPORT"
fi

echo "DONE"
