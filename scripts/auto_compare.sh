#!/usr/bin/env bash
set -euo pipefail

REF="${1:?Usage: auto_compare.sh /path/to/ref.pdf /path/to/gen.pdf}"
GEN="${2:?Usage: auto_compare.sh /path/to/ref.pdf /path/to/gen.pdf}"
OUTDIR="${3:-/tmp/pdfdiff}"

mkdir -p "$OUTDIR/ref" "$OUTDIR/gen" "$OUTDIR/diff"

# Render both PDFs to PNG at 150 DPI
pdftoppm -png -r 150 "$REF" "$OUTDIR/ref/page"
pdftoppm -png -r 150 "$GEN" "$OUTDIR/gen/page"

# Compare page by page
rm -f "$OUTDIR/diff/compare.txt"
for ref_img in "$OUTDIR/ref"/*.png; do
  base=$(basename "$ref_img")
  gen_img="$OUTDIR/gen/$base"
  if [[ ! -f "$gen_img" ]]; then
    echo "$base missing in generated" >> "$OUTDIR/diff/compare.txt"
    continue
  fi
  # Generate diff image and metric
  diff_img="$OUTDIR/diff/$base"
  # compare returns metric on stderr
  metric=$(compare -metric AE "$ref_img" "$gen_img" "$diff_img" 2>&1 || true)
  echo "$base $metric" >> "$OUTDIR/diff/compare.txt"

done

echo "[OK] Diff report: $OUTDIR/diff/compare.txt"
