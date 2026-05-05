#!/usr/bin/env bash
# rembg.sh — remove the background from a PNG/JPEG, producing an RGBA PNG.
#
# Usage:
#   ./rembg.sh --input path.png --output path-transparent.png [options]
#
# Options:
#   --input  path.png           (required) input image path (png/jpeg/webp)
#   --output path.png           (required) output path (always written as PNG with alpha)
#   --model MODEL               default: birefnet-general
#                               Supported models:
#                                 birefnet-general   MIT license, ~90% SOTA, commercial OK (DEFAULT)
#                                 bria-rmbg          Non-commercial only, slightly better on complex bg
#                                 birefnet-portrait  Best for human subjects (hair, skin edges)
#                                 isnet-anime        2D anime / illustrated characters
#                                 u2net              Legacy / fallback / fastest
#
# Install (one-time):
#   pip install "rembg[cli]" onnxruntime
#   # First run of each model downloads weights (~200-400MB) to ~/.u2net/
#
# See ../reference/transparent-backgrounds.md for the full decision tree
# (including the ImageMagick color-key fast-path for pure line art).

set -euo pipefail

INPUT=""
OUTPUT=""
MODEL="birefnet-general"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)  INPUT="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --model)  MODEL="$2"; shift 2 ;;
    -h|--help) sed -n '1,25p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$INPUT" ]]  && { echo "Error: --input is required" >&2; exit 1; }
[[ -z "$OUTPUT" ]] && { echo "Error: --output is required" >&2; exit 1; }
[[ -f "$INPUT" ]]  || { echo "Error: input not found: $INPUT" >&2; exit 1; }

# Locate rembg: prefer the CLI on PATH, fall back to `python3 -m rembg`
# so the script works regardless of pyenv shim state.
REMBG_CMD=()
if command -v rembg >/dev/null 2>&1; then
  REMBG_CMD=(rembg)
elif command -v python3 >/dev/null 2>&1 && python3 -c "import rembg" >/dev/null 2>&1; then
  REMBG_CMD=(python3 -m rembg)
else
  cat >&2 <<EOF
Error: 'rembg' not found.

Install it once:
  pip install "rembg[cli]" onnxruntime

Then re-run this script. If you just installed it under pyenv and still see
this error, run: pyenv rehash
EOF
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

echo "▸ rembg (model=$MODEL) $INPUT → $OUTPUT" >&2
"${REMBG_CMD[@]}" i -m "$MODEL" "$INPUT" "$OUTPUT"

echo "✓ saved: $OUTPUT" >&2
echo "$OUTPUT"
