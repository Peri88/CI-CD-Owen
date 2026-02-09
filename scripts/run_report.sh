#!/usr/bin/env bash
set -euo pipefail

IN="${1:?Usage: run_report.sh /path/to/Export1.txt}"
OUTDIR="/home/owen"

TS="$(date +%Y%m%d_%H%M%S)"
OUT="${OUTDIR}/NetBackup_Report_${TS}.pdf"

python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate
pip -q install -r requirements.txt

python3 scripts/nbu_txt_to_pdf.py \
  --in "$IN" \
  --out "$OUT"

echo "DONE: $OUT"
