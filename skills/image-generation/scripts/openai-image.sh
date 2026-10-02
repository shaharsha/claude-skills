#!/usr/bin/env bash
# openai-image.sh — generate or edit images via OpenAI GPT Image (2.5 Sunburst / Flare, 2).
#
# Usage:
#   ./openai-image.sh --prompt "..." --output path.png [options]
#
# Options:
#   --prompt "..."              (required) prompt text (≤ 32,000 chars)
#   --output path.png           (required) output file path
#   --model ID                  default: gpt-image-2.5-sunburst
#                                 gpt-image-2.5-sunburst  best quality; anything that may ship
#                                 gpt-image-2.5-flare     fast drafts / exploration (~2x faster)
#                                 gpt-image-2             previous generation (not deprecated)
#   --draft                     shortcut for --model gpt-image-2.5-flare --quality medium
#                               (~15 s, ~1¢ at 1024x1536). Put it AFTER any --model/--quality.
#   --quality low|medium|high|xhigh|max|auto   default: max
#                               ⚠ The 2.5 ladder is re-cut: 2.5 "high" ≈ gpt-image-2 "medium"
#                               in output tokens, and 2.5 "max" ≈ gpt-image-2 "high".
#                               xhigh/max exist only on the 2.5 models. Avoid "auto" — it lands
#                               on different budgets for identical calls.
#   --size WxH                  default: 1024x1024
#                               each edge ≤ 3840px and a multiple of 16, ratio ≤ 3:1,
#                               total pixels 655,360–8,294,400; above 2560x1440 is experimental.
#                               Common: 1024x1024, 1024x1536, 1536x1024, 2048x1152, 2560x1440, 3840x2160
#   --background opaque|transparent|auto   default: opaque
#                               transparent: native on 2.5 (needs png or webp); preview on gpt-image-2.
#   --output-format png|jpeg|webp   default: png
#   --moderation auto|low           default: auto
#   --n N                           default: 1 (1-10; extras saved as path-2.png, path-3.png, ...)
#   --ref path.png                  (repeatable, ≤ 16) reference image(s) → /v1/images/edits.
#                                   Number them in the prompt by role ("image 1 = product, image 2 = style").
#
# Prints one line to stderr per call with latency, output tokens and the token cost.
#
# Env:
#   OPENAI_IMAGE_API_KEY (required)   Get from ~/.claude/projects/-Users-shaharshavit/memory/api-keys.md
#                                     → "OpenAI (image generation)" section.

set -euo pipefail

PROMPT=""
OUTPUT=""
QUALITY="max"
SIZE="1024x1024"
BACKGROUND="opaque"
OUTPUT_FORMAT="png"
MODERATION="auto"
N=1
MODEL="gpt-image-2.5-sunburst"
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
    --draft)           MODEL="gpt-image-2.5-flare"; QUALITY="medium"; shift ;;
    --input-fidelity)
      echo "Error: don't send input_fidelity — gpt-image-2 ignores it and the 2.5 models don't list it." >&2
      echo "References are processed at high fidelity automatically." >&2
      exit 1
      ;;
    -h|--help)         sed -n '1,38p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$PROMPT" ]] && { echo "Error: --prompt is required" >&2; exit 1; }
[[ -z "$OUTPUT" ]] && { echo "Error: --output is required" >&2; exit 1; }

case "$QUALITY" in low|medium|high|xhigh|max|auto) ;; *)
  echo "Error: --quality must be low|medium|high|xhigh|max|auto" >&2; exit 1 ;; esac
if [[ "$QUALITY" == "xhigh" || "$QUALITY" == "max" ]] && [[ "$MODEL" != gpt-image-2.5-* ]]; then
  echo "Error: quality=$QUALITY exists only on the gpt-image-2.5 models (got $MODEL; its top is 'high')." >&2
  exit 1
fi

if [[ "$BACKGROUND" == "transparent" ]]; then
  if [[ "$OUTPUT_FORMAT" == "jpeg" ]]; then
    echo "Error: transparent backgrounds need --output-format png or webp" >&2; exit 1
  fi
  if [[ "$MODEL" != gpt-image-2.5-* ]]; then
    echo "Note: transparency on $MODEL is a preview feature and has been reported to fail intermittently;" >&2
    echo "      prefer a gpt-image-2.5 model, or fall back to an opaque backdrop + scripts/rembg.sh." >&2
  fi
fi

[[ ${#REFS[@]} -gt 16 ]] && { echo "Error: the edits endpoint accepts at most 16 reference images" >&2; exit 1; }

# Validate size constraints (each edge ≤ 3840, multiple of 16, ratio ≤ 3:1)
if [[ "$SIZE" =~ ^([0-9]+)x([0-9]+)$ ]]; then
  W="${BASH_REMATCH[1]}"
  H="${BASH_REMATCH[2]}"
  if (( W > 3840 || H > 3840 )); then
    echo "Error: --size $SIZE: each edge must be ≤ 3840px" >&2
    exit 1
  fi
  if (( W % 16 != 0 || H % 16 != 0 )); then
    echo "Error: --size $SIZE: both edges must be multiples of 16" >&2
    exit 1
  fi
  LONG=$(( W > H ? W : H ))
  SHORT=$(( W < H ? W : H ))
  if (( LONG * 10 > SHORT * 30 )); then
    echo "Error: --size $SIZE: long:short ratio must be ≤ 3:1" >&2
    exit 1
  fi
  TOTAL=$(( W * H ))
  if (( TOTAL < 655360 || TOTAL > 8294400 )); then
    echo "Error: --size $SIZE: total pixels must be 655,360–8,294,400 (got $TOTAL)" >&2
    exit 1
  fi
else
  echo "Error: --size must be WxH format (e.g. 1024x1024)" >&2
  exit 1
fi

: "${OPENAI_IMAGE_API_KEY:?Set OPENAI_IMAGE_API_KEY (see ~/.claude/projects/-Users-shaharshavit/memory/api-keys.md → 'OpenAI (image generation)')}"

# Make sure output dir exists
mkdir -p "$(dirname "$OUTPUT")"
START=$(date +%s)

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

  echo "▸ POST $ENDPOINT (generate, model=$MODEL, n=$N, quality=$QUALITY, size=$SIZE, background=$BACKGROUND)" >&2
  RESP=$(curl -sS -X POST "$ENDPOINT" \
    -H "Authorization: Bearer $OPENAI_IMAGE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$BODY")
else
  ENDPOINT="https://api.openai.com/v1/images/edits"
  echo "▸ POST $ENDPOINT (edit, model=$MODEL, ${#REFS[@]} ref(s), quality=$QUALITY, size=$SIZE, background=$BACKGROUND)" >&2

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

# Cost from the response's own token usage (GPT Image 2 / 2.5 rates, standard tier):
# image output $30/1M, image input $8/1M, text input $5/1M.
echo "$RESP" | jq -r --argjson secs "$(( $(date +%s) - START ))" '
  (.usage // {}) as $u
  | ($u.output_tokens // 0) as $out
  | ($u.input_tokens_details.image_tokens // 0) as $img
  | ($u.input_tokens_details.text_tokens // 0) as $txt
  | "  \($secs)s · output_tokens=\($out) · cost≈$\((($out*30 + $img*8 + $txt*5) / 1000000 * 1000 | round) / 1000)"' >&2

# Print first output path on stdout so callers can capture it
echo "$OUTPUT"
