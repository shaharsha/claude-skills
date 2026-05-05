#!/usr/bin/env bash
# gemini-image.sh — generate or edit images via Google Gemini Nano Banana
#
# Usage:
#   ./gemini-image.sh --prompt "..." --output path.png [options]
#
# Options:
#   --prompt "..."             (required) prompt text
#   --output path.png          (required) output file path
#   --model flash|pro|<full-id> default: flash
#                              flash = gemini-3.1-flash-image-preview
#                              pro   = gemini-3-pro-image-preview
#   --aspect 1:1|16:9|9:16|4:5|5:4|4:3|3:4|3:2|2:3|21:9|1:4|4:1|1:8|8:1
#                              default: 1:1
#   --size 0.5K|1K|2K|4K       default: 1K (Pro doesn't support 0.5K)
#   --thinking minimal|high    default: minimal (Flash only; Pro thinks by default)
#   --include-thoughts         (flag) include reasoning trace in response
#   --search                   (flag) enable Google Search grounding
#   --ref path.png             (repeatable, up to 14)
#
# Env:
#   GEMINI_IMAGE_API_KEY (required)  Get from ~/.claude/projects/-Users-shaharshavit/memory/api-keys.md
#                                    → "Google AI Studio (image generation)" section.

set -euo pipefail

PROMPT=""
OUTPUT=""
MODEL_ALIAS="flash"
ASPECT="1:1"
SIZE="1K"
THINKING="minimal"
INCLUDE_THOUGHTS=false
SEARCH=false
REFS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)            PROMPT="$2"; shift 2 ;;
    --output)            OUTPUT="$2"; shift 2 ;;
    --model)             MODEL_ALIAS="$2"; shift 2 ;;
    --aspect)            ASPECT="$2"; shift 2 ;;
    --size)              SIZE="$2"; shift 2 ;;
    --thinking)          THINKING="$2"; shift 2 ;;
    --include-thoughts)  INCLUDE_THOUGHTS=true; shift ;;
    --search)            SEARCH=true; shift ;;
    --ref)               REFS+=("$2"); shift 2 ;;
    -h|--help)           sed -n '1,25p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$PROMPT" ]] && { echo "Error: --prompt is required" >&2; exit 1; }
[[ -z "$OUTPUT" ]] && { echo "Error: --output is required" >&2; exit 1; }
: "${GEMINI_IMAGE_API_KEY:?Set GEMINI_IMAGE_API_KEY (see ~/.claude/projects/-Users-shaharshavit/memory/api-keys.md → 'Google AI Studio (image generation)')}"
[[ ${#REFS[@]} -gt 14 ]] && { echo "Error: max 14 reference images" >&2; exit 1; }

# Resolve model alias
case "$MODEL_ALIAS" in
  flash) MODEL="gemini-3.1-flash-image-preview" ;;
  pro)   MODEL="gemini-3-pro-image-preview" ;;
  *)     MODEL="$MODEL_ALIAS" ;;
esac

mkdir -p "$(dirname "$OUTPUT")"

# All intermediate JSON / base64 lives on disk to avoid argv limits with
# large reference images (a 4K JPEG base64-encoded is several MB).
TMPDIR_REQ=$(mktemp -d)
trap 'rm -rf "$TMPDIR_REQ"' EXIT
PARTS_FILE="$TMPDIR_REQ/parts.json"
BODY_FILE="$TMPDIR_REQ/body.json"

# Step 1: parts = [text]
jq -n --arg t "$PROMPT" '[{text: $t}]' > "$PARTS_FILE"

# Step 2: append each ref as inline_data via --rawfile (no argv crossing)
if [[ ${#REFS[@]} -gt 0 ]]; then
  for ref in "${REFS[@]}"; do
    [[ -f "$ref" ]] || { echo "Error: ref not found: $ref" >&2; exit 1; }
    MIME=$(file --mime-type -b "$ref")
    REFB64="$TMPDIR_REQ/$(basename "$ref").b64"
    base64 < "$ref" | tr -d '\n' > "$REFB64"
    NEW_PARTS="$TMPDIR_REQ/parts.next.json"
    jq --arg mt "$MIME" --rawfile d "$REFB64" \
      '. + [{inline_data: {mime_type: $mt, data: $d}}]' \
      < "$PARTS_FILE" > "$NEW_PARTS"
    mv "$NEW_PARTS" "$PARTS_FILE"
  done
fi

# Step 3: generationConfig (small, fits in argv)
GEN_CONFIG=$(jq -n \
  --arg aspect "$ASPECT" \
  --arg size "$SIZE" \
  '{responseModalities: ["IMAGE"], imageConfig: {aspectRatio: $aspect, imageSize: $size}}')

if [[ "$MODEL" == "gemini-3.1-flash-image-preview" ]]; then
  GEN_CONFIG=$(jq \
    --arg level "$THINKING" \
    --argjson include "$INCLUDE_THOUGHTS" \
    '. + {thinkingConfig: {thinkingLevel: $level, includeThoughts: $include}}' <<<"$GEN_CONFIG")
fi

# Step 4: assemble body. --slurpfile loads the parts array from disk.
jq -n \
  --slurpfile parts "$PARTS_FILE" \
  --argjson genCfg "$GEN_CONFIG" \
  '{contents: [{parts: $parts[0]}], generationConfig: $genCfg}' \
  > "$BODY_FILE"

# Step 5: optional grounding tool
if [[ "$SEARCH" == "true" ]]; then
  NEW_BODY="$TMPDIR_REQ/body.next.json"
  jq '. + {tools: [{google_search: {}}]}' < "$BODY_FILE" > "$NEW_BODY"
  mv "$NEW_BODY" "$BODY_FILE"
fi

ENDPOINT="https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent"

echo "▸ POST $ENDPOINT" >&2
echo "  model=$MODEL aspect=$ASPECT size=$SIZE refs=${#REFS[@]} thinking=$THINKING search=$SEARCH" >&2

RESP=$(curl -sS -X POST "$ENDPOINT" \
  -H "x-goog-api-key: $GEMINI_IMAGE_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary "@$BODY_FILE")

# Check for error
if echo "$RESP" | jq -e '.error' >/dev/null 2>&1; then
  echo "API error:" >&2
  echo "$RESP" | jq '.error' >&2
  exit 1
fi

# Extract first image part. REST returns camelCase (inlineData/mimeType);
# the SDK uses snake_case. Accept both.
IMG_PART=$(echo "$RESP" | jq -c '
  [ .candidates[0].content.parts[]?
    | (.inlineData // .inline_data) as $d
    | select($d != null)
    | { mime: ($d.mimeType // $d.mime_type), data: $d.data }
    | select(.mime | startswith("image/"))
  ] | .[0]
')

if [[ -z "$IMG_PART" || "$IMG_PART" == "null" ]]; then
  echo "Error: no image in response" >&2
  echo "$RESP" | jq '.candidates[0] // .' >&2
  exit 1
fi

MIME_OUT=$(echo "$IMG_PART" | jq -r '.mime')
B64=$(echo "$IMG_PART" | jq -r '.data')

# Auto-correct extension if it doesn't match the returned MIME
case "$MIME_OUT" in
  image/png)  EXT_WANT=png  ;;
  image/jpeg) EXT_WANT=jpg  ;;
  image/webp) EXT_WANT=webp ;;
  *)          EXT_WANT=""   ;;
esac
EXT_HAVE="${OUTPUT##*.}"
if [[ -n "$EXT_WANT" && "$EXT_HAVE" != "$EXT_WANT" ]]; then
  CORRECTED="${OUTPUT%.*}.${EXT_WANT}"
  echo "ℹ API returned $MIME_OUT; saving as $CORRECTED instead of $OUTPUT" >&2
  OUTPUT="$CORRECTED"
fi

echo "$B64" | base64 --decode > "$OUTPUT"
echo "✓ saved: $OUTPUT ($MIME_OUT)" >&2

# Print thoughts if requested
if [[ "$INCLUDE_THOUGHTS" == "true" ]]; then
  THOUGHTS=$(echo "$RESP" | jq -r '.candidates[0].content.parts[] | select(.text? and .thought? == true) | .text' 2>/dev/null || true)
  if [[ -n "$THOUGHTS" ]]; then
    echo "─── thoughts ───" >&2
    echo "$THOUGHTS" >&2
    echo "────────────────" >&2
  fi
fi

echo "$OUTPUT"