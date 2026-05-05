#!/usr/bin/env bash
# render-pdf.sh — render a BRAND.html file to BRAND.pdf via Chrome headless.
#
# Usage:
#   render-pdf.sh BRAND.html BRAND.pdf
#   render-pdf.sh --input BRAND.html --output BRAND.pdf

set -euo pipefail

INPUT=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input)  INPUT="$2";  shift 2 ;;
    -o|--output) OUTPUT="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 <input.html> <output.pdf>"
      echo "       $0 --input input.html --output output.pdf"
      exit 0
      ;;
    *)
      # Positional: first arg = input, second = output
      if [[ -z "$INPUT" ]]; then
        INPUT="$1"
      elif [[ -z "$OUTPUT" ]]; then
        OUTPUT="$1"
      else
        echo "Unexpected arg: $1" >&2; exit 1
      fi
      shift
      ;;
  esac
done

[[ -z "$INPUT" ]]  && { echo "ERROR: input HTML required" >&2; exit 1; }
[[ -z "$OUTPUT" ]] && { echo "ERROR: output PDF path required" >&2; exit 1; }
[[ ! -f "$INPUT" ]] && { echo "ERROR: $INPUT not found" >&2; exit 1; }

# Resolve to absolute paths so Chrome gets a clean file:// URL
INPUT_ABS="$(cd "$(dirname "$INPUT")" && pwd)/$(basename "$INPUT")"
OUTPUT_ABS="$(cd "$(dirname "$OUTPUT")" 2>/dev/null || mkdir -p "$(dirname "$OUTPUT")" && cd "$(dirname "$OUTPUT")" && pwd)/$(basename "$OUTPUT")"

# Find Chrome. Try common binaries on macOS/Linux/Windows (Git Bash).
CHROME=""
for candidate in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "$(command -v google-chrome || true)" \
  "$(command -v google-chrome-stable || true)" \
  "$(command -v chromium || true)" \
  "$(command -v chromium-browser || true)" \
  "$(command -v chrome || true)"
do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    CHROME="$candidate"
    break
  fi
done

if [[ -z "$CHROME" ]]; then
  echo "ERROR: Chrome not found. Install Google Chrome or Chromium." >&2
  echo "  macOS:  https://www.google.com/chrome/" >&2
  echo "  Linux:  apt install google-chrome-stable   (or chromium-browser)" >&2
  exit 1
fi

echo "Rendering $INPUT_ABS → $OUTPUT_ABS via $CHROME..."

"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-pdf-header-footer \
  --hide-scrollbars \
  --run-all-compositor-stages-before-draw \
  --virtual-time-budget=5000 \
  --print-to-pdf="$OUTPUT_ABS" \
  "file://$INPUT_ABS" 2>&1 | grep -v 'DevTools listening' || true

if [[ -f "$OUTPUT_ABS" ]]; then
  echo "✓ Wrote $OUTPUT_ABS ($(wc -c < "$OUTPUT_ABS" | tr -d ' ') bytes)"
else
  echo "ERROR: Chrome did not produce $OUTPUT_ABS" >&2
  exit 1
fi
