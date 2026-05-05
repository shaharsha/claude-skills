#!/usr/bin/env bash
# color-audit.sh — histogram of opaque pixels per hex color.
#
# Usage:
#   color-audit.sh path/to/image.png [--brand '#F3EAD3' '#0E1320' '#B85A3A']
#
# With --brand, fails (exit 1) if any non-brand hex accounts for >1% of opaque pixels.
# Without --brand, just prints the histogram.

set -euo pipefail

FILE=""
BRAND=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brand)
      shift
      while [[ $# -gt 0 && "$1" =~ ^# ]]; do
        BRAND+=("$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')")
        shift
      done ;;
    --help|-h) sed -n '1,9p' "$0"; exit 0 ;;
    *)
      FILE="$1"; shift ;;
  esac
done

[[ -f "$FILE" ]] || { echo "file not found: $FILE" >&2; exit 1; }

# Get all fully-opaque pixel colors, sorted by count
histo=$(magick "$FILE" -channel A -threshold 99% +channel \
  -depth 8 -format "%c" histogram:info:- 2>/dev/null \
  | grep -oE '[0-9]+.*#[0-9A-Fa-f]{6,8}' \
  | awk '{
    n=$1; sub(":","",n);
    h=$NF;
    # normalize: RRGGBBAA -> RRGGBB if alpha is FF
    if (length(h) == 9) { h=substr(h,1,7); }
    print n, toupper(h);
  }' \
  | sort -rn \
  | head -30)

total_opaque=$(echo "$histo" | awk '{s+=$1} END {print s}')

echo "$FILE  ($total_opaque opaque pixels)"
echo "$histo" | awk -v total="$total_opaque" '
  {
    pct=($1/total)*100;
    printf "  %10d  %s  %5.2f%%\n", $1, $2, pct;
  }'

# If brand palette was given, fail on non-brand drift
if [[ ${#BRAND[@]} -gt 0 ]]; then
  # Build a brand-contains check
  brand_regex=$(IFS='|'; echo "${BRAND[*]}")
  drift_pct=$(echo "$histo" \
    | awk -v brand="$brand_regex" -v total="$total_opaque" '
      BEGIN { split(brand, b, "|"); for (k in b) bmap[b[k]]=1; }
      !($NF in bmap) { s+=$1 }
      END { if (total > 0) printf "%.2f", (s/total)*100; else print "0.00"; }
    ')
  echo "brand drift: ${drift_pct}% non-brand opaque pixels"
  if awk "BEGIN { exit !($drift_pct > 1.0) }"; then
    echo "FAIL: brand drift exceeds 1% threshold" >&2
    exit 1
  fi
  echo "OK: brand drift within threshold"
fi
