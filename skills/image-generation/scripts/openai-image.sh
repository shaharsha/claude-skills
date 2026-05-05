#!/usr/bin/env bash
# openai-image.sh — generate or edit images via OpenAI gpt-image-2.
#
# Usage:
#   ./openai-image.sh --prompt "..." --output path.png [options]
#
# Options:
#   --prompt "..."              (required) prompt text
#   --output path.png           (required) output file path
#   --quality low|medium|high   default: high
#   --size WxH                  default: 1024x1024
#                               Constraints on gpt-image-2:
#                                 each edge ≤ 3840px
#                                 each edge a multiple of 16
#                                 long-to-short ratio ≤ 3:1
#                                 total pixels: 655,360–8,294,400
#                               Common sizes: 1024x1024, 1024x1536, 1536x1024,
#                                             2048x1152, 2560x1440, 3840x2160
#   --background opaque|auto    default: opaque
#                               NOTE: transparent is NOT supported on gpt-image-2.
#                               Use --background opaque + scripts/rembg.sh for
#                               transparent PNGs. See reference/transparent-backgrounds.md.
#   --output-format png|jpeg|webp   default: png
#   --moderation auto|low           default: auto
#   --n N                           default: 1 (additional images saved as path-2.png, path-3.png, ...)
#   --ref path.png                  (repeatable) reference image for /v1/images/edits.
#                                   Presence of any --ref switches to edit mode.
#                                   gpt-image-2 processes every reference at high fidelity automatically
#                                   (no input_fidelity flag needed or accepted).
#   --model gpt-image-2             default: gpt-image-2 (only supported model)
#
# Env:
#   OPENAI_IMAGE_API_KEY (required)   Get from ~/.claude/projects/-Users-shaharshavit/memory/api-keys.md
#                                     → "OpenAI (image generation)" section.

set -euo pipefail

PROMPT=""
OUTPUT=""
QUALITY="high"
SIZE="1024x1024"
BACKGROUND="opaque"
OUTPUT_FORMAT="png"
MODERATION="auto"
N=1
MODEL="gpt-image-2"
REFS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)          PROMPT="$2"; shift 2 ;;
    --output)          OUTPUT="$2"; shift 2 ;;
    --quality)         QUALITY="$2"; shift 2 ;;
    --size)            SIZE="$2"; shift 2 ;;
    --background)      BACKGROUND="$2"; shift 2 ;;
    --output-format)   OUTPUT_FORMAT="$2"; shift 2 ;;
    --moderation)      MODERATION="$2"; shift 2 ;;
    --n)               N="$2"; shift 2 ;;
    --ref)             REFS+=("$2"); shift 2 ;;
    --model)           MODEL="$2"; shift 2 ;;
    --input-fidelity)
      echo "Error: --input-fidelity is not configurable on gpt-image-2." >&2
      echo "Every reference image is processed at high fidelity automatically." >&2
      exit 1
      ;;
    -h|--help)         sed -n '1,35p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$PROMPT" ]] && { echo "Error: --prompt is required" >&2; exit 1; }
[[ -z "$OUTPUT" ]] && { echo "Error: --output is required" >&2; exit 1; }

# gpt-image-2 does not support transparent backgrounds
if [[ "$BACKGROUND" == "transparent" ]]; then
  cat >&2 <<EOF
Error: gpt-image-2 does not support background=transparent.

For transparent PNGs, generate with --background opaque and include a clean
backdrop in your prompt (e.g. "isolated on flat #FFFFFF, no shadow"), then
post-process with scripts/rembg.sh. See reference/transparent-backgrounds.md
for the full pipeline.
EOF
  exit 1
fi

# Validate size constraints (each edge ≤ 3840, multiple of 16, ratio ≤ 3:1)
if [[ "$SIZE" =~ ^([0-9]+)x([0-9]+)$ ]]; then
  W="${BASH_REMATCH[1]}"
  H="${BASH_REMATCH[2]}"
  if (( W > 3840 || H > 3840 )); then
    echo "Error: --size $SIZE violates gpt-image-2 constraint (each edge ≤ 3840px)" >&2
    exit 1
  fi
  if (( W % 16 != 0 || H % 16 != 0 )); then
    echo "Error: --size $SIZE violates gpt-image-2 constraint (both edges must be multiples of 16)" >&2
    exit 1
  fi
  LONG=$(( W > H ? W : H ))
  SHORT=$(( W < H ? W : H ))
  if (( LONG * 10 > SHORT * 30 )); then
    echo "Error: --size $SIZE violates gpt-image-2 constraint (long:short ratio must be ≤ 3:1)" >&2
    exit 1
  fi
  TOTAL=$(( W * H ))
  if (( TOTAL < 655360 || TOTAL > 8294400 )); then
    echo "Error: --size $SIZE violates gpt-image-2 constraint (total pixels 655,360–8,294,400; got $TOTAL)" >&2
    exit 1
  fi
else
  echo "Error: --size must be WxH format (e.g. 1024x1024)" >&2
  exit 1
fi

: "${OPENAI_IMAGE_API_KEY:?Set OPENAI_IMAGE_API_KEY (see ~/.claude/projects/-Users-shaharshavit/memory/api-keys.md → 'OpenAI (image generation)')}"

# Make sure output dir exists
mkdir -p "$(dirname "$OUTPUT")"

# Pick endpoint
if [[ ${#REFS[@]} -eq 0 ]]; then
  ENDPOINT="https://api.openai.com/v1/images/generations"
  BODY=$(jq -n \
    --arg model "$MODEL" \
    --arg prompt "$PROMPT" \
    --arg quality "$QUALITY" \
    --arg size "$SIZE" \
    --arg background "$BACKGROUND" \
    --arg output_format "$OUTPUT_FORMAT" \
    --arg moderation "$MODERATION" \
    --argjson n "$N" \
    '{model:$model, prompt:$prompt, quality:$quality, size:$size, background:$background, output_format:$output_format, moderation:$moderation, n:$n}')

  echo "▸ POST $ENDPOINT (generate, model=$MODEL, n=$N, quality=$QUALITY, size=$SIZE)" >&2
  RESP=$(curl -sS -X POST "$ENDPOINT" \
    -H "Authorization: Bearer $OPENAI_IMAGE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$BODY")
else
  ENDPOINT="https://api.openai.com/v1/images/edits"
  echo "▸ POST $ENDPOINT (edit, model=$MODEL, ${#REFS[@]} ref(s), quality=$QUALITY, size=$SIZE)" >&2

  CURL_ARGS=(
    -sS -X POST "$ENDPOINT"
    -H "Authorization: Bearer $OPENAI_IMAGE_API_KEY"
    -F "model=$MODEL"
    -F "prompt=$PROMPT"
    -F "quality=$QUALITY"
    -F "size=$SIZE"
    -F "background=$BACKGROUND"
    -F "output_format=$OUTPUT_FORMAT"
    -F "n=$N"
  )
  for ref in "${REFS[@]}"; do
    [[ -f "$ref" ]] || { echo "Error: ref not found: $ref" >&2; exit 1; }
    CURL_ARGS+=(-F "image[]=@$ref")
  done
  RESP=$(curl "${CURL_ARGS[@]}")
fi

# Check for error
if echo "$RESP" | jq -e '.error' >/dev/null 2>&1; then
  echo "API error:" >&2
  echo "$RESP" | jq '.error' >&2
  exit 1
fi

# Save each returned image
COUNT=$(echo "$RESP" | jq '.data | length')
[[ "$COUNT" -eq 0 ]] && { echo "Error: no images in response" >&2; exit 1; }

BASE="${OUTPUT%.*}"
EXT="${OUTPUT##*.}"

for ((i=0; i<COUNT; i++)); do
  if [[ $i -eq 0 ]]; then
    OUT="$OUTPUT"
  else
    OUT="${BASE}-$((i+1)).${EXT}"
  fi
  echo "$RESP" | jq -r ".data[$i].b64_json" | base64 --decode > "$OUT"
  echo "✓ saved: $OUT" >&2
done

# Print first output path on stdout so callers can capture it
echo "$OUTPUT"
