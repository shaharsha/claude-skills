#!/usr/bin/env bash
# rasterize.sh — render SVG → PNG/JPG cleanly.
#
# Usage:
#   rasterize.sh --input foo.svg --output foo.png --width 2400
#   rasterize.sh --input icon.svg --output icon.png --canvas 1024x1024 --content-width 820 --bg '#F3EAD3'
#
# See reference/rasterize.md for the full option table.

set -euo pipefail

INPUT=""
OUTPUT=""
WIDTH=""
HEIGHT=""
CANVAS=""
CONTENT_WIDTH=""
BG="transparent"
QUALITY=85
TRIM=0
VERIFY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)         INPUT="$2"; shift 2 ;;
    --output)        OUTPUT="$2"; shift 2 ;;
    --width)         WIDTH="$2"; shift 2 ;;
    --height)        HEIGHT="$2"; shift 2 ;;
    --canvas)        CANVAS="$2"; shift 2 ;;
    --content-width) CONTENT_WIDTH="$2"; shift 2 ;;
    --bg)            BG="$2"; shift 2 ;;
    --quality)       QUALITY="$2"; shift 2 ;;
    --trim)          TRIM=1; shift ;;
    --verify)        VERIFY=1; shift ;;
    --help|-h)       sed -n '1,10p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$INPUT" && -n "$OUTPUT" ]] || { echo "--input and --output are required" >&2; exit 1; }
[[ -f "$INPUT" ]] || { echo "input not found: $INPUT" >&2; exit 1; }

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# ── Mode A: tight-crop (--width or --height only) ─────────────
if [[ -z "$CANVAS" ]]; then
  [[ -n "$WIDTH" || -n "$HEIGHT" ]] || { echo "provide --width, --height, or --canvas" >&2; exit 1; }
  args=()
  [[ -n "$WIDTH" ]]  && args+=(-w "$WIDTH")
  [[ -n "$HEIGHT" ]] && args+=(-h "$HEIGHT")
  rsvg-convert -a "${args[@]}" "$INPUT" -o "$TMPDIR/raw.png"

  if [[ "$TRIM" -eq 1 ]]; then
    magick "$TMPDIR/raw.png" -trim +repage "$TMPDIR/trimmed.png"
    mv "$TMPDIR/trimmed.png" "$TMPDIR/raw.png"
  fi

  # Apply bg if requested (non-transparent)
  if [[ "$BG" != "transparent" ]]; then
    magick "$TMPDIR/raw.png" -background "$BG" -alpha remove "$TMPDIR/raw.png"
  fi

# ── Mode B: centered-on-canvas (--canvas) ─────────────────────
else
  [[ "$CANVAS" =~ ^([0-9]+)x([0-9]+)$ ]] || { echo "--canvas must be WIDTHxHEIGHT" >&2; exit 1; }
  CW="${BASH_REMATCH[1]}"
  CH="${BASH_REMATCH[2]}"
  : "${CONTENT_WIDTH:=$((CW * 80 / 100))}"
  rsvg-convert -a -w "$CONTENT_WIDTH" "$INPUT" -o "$TMPDIR/glyph.png"
  if [[ "$TRIM" -eq 1 ]]; then
    magick "$TMPDIR/glyph.png" -trim +repage "$TMPDIR/glyph.png"
  fi
  magick -size "${CW}x${CH}" "xc:${BG}" "$TMPDIR/glyph.png" \
    -gravity center -composite "$TMPDIR/raw.png"
fi

# ── Output ────────────────────────────────────────────────────
OUTPUT_LC=$(printf '%s' "$OUTPUT" | tr '[:upper:]' '[:lower:]')
case "$OUTPUT_LC" in
  *.jpg|*.jpeg)
    magick "$TMPDIR/raw.png" -background "${BG:-white}" -alpha remove -quality "$QUALITY" "$OUTPUT" ;;
  *.png)
    cp "$TMPDIR/raw.png" "$OUTPUT" ;;
  *)
    echo "unknown output extension: $OUTPUT" >&2; exit 1 ;;
esac

ls -la "$OUTPUT"

if [[ "$VERIFY" -eq 1 ]]; then
  here=$(dirname "$0")
  bash "$here/color-audit.sh" "$OUTPUT" || { echo "verify failed" >&2; exit 1; }
fi
