#!/usr/bin/env bash
# new-brand-book.sh — scaffold BRAND.md + BRAND.html + tokens.css + signature-interview.md
#
# Usage:
#   new-brand-book.sh \
#     --product "Agentiko" \
#     --positioning "A real worker who lives inside WhatsApp." \
#     --palette-bg '#F3EAD3' \
#     --palette-fg '#0E1320' \
#     --palette-accent '#B85A3A' \
#     --signature-primitive "voice dot" \
#     --primary-font "Rubik" \
#     --locale "he" \
#     --output-dir .

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES_DIR="$SKILL_DIR/templates"

# Defaults
export BS_PRODUCT=""
export BS_POSITIONING=""
export BS_PALETTE_BG=""
export BS_PALETTE_FG=""
export BS_PALETTE_ACCENT=""
export BS_SIGNATURE_PRIMITIVE="accent dot"
export BS_PRIMARY_FONT="Rubik"
export BS_LOCALE="en"
OUTPUT_DIR="."
FORCE=0
REQUIRE_INTERVIEW=""

usage() {
  cat <<EOF
Usage: $0 [options]

Required:
  --product NAME              Product name (e.g. "Agentiko")
  --positioning "SENTENCE"    One-line positioning (<= 12 words)
  --palette-bg HEX            Primary light surface hex (e.g. '#F3EAD3')
  --palette-fg HEX            Primary text / dark surface hex (e.g. '#0E1320')
  --palette-accent HEX        The one saturated accent hex (e.g. '#B85A3A')

Optional:
  --signature-primitive NAME  Invented proper noun (default: "accent dot")
  --primary-font NAME         Font family (default: "Rubik")
  --locale CODE               Primary locale: en, he, ar, es (default: en)
  --output-dir PATH           Where to write files (default: current dir)
  --require-interview PATH    Path to a filled-in signature-interview.md.
                              Script refuses to run if interview is unfilled
                              (template placeholders remain or ellipses present).
                              Strongly recommended — the interview is the
                              anti-template move.
  --force                     Overwrite existing files
  -h, --help                  This message

Output:
  BRAND.md, BRAND.html, tokens.css, signature-interview.md
EOF
  exit 1
}

validate_interview() {
  # Exit non-zero if the interview at $1 still contains unfilled placeholders.
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "ERROR: --require-interview path not found: $path" >&2
    return 1
  fi
  # Count unfilled markers:
  #   - {{...}} template placeholders
  #   - Lines that are exactly "> …" or "> ..." (the unfilled answer pattern)
  local placeholders
  placeholders=$(grep -c '{{[A-Z_]*}}' "$path" 2>/dev/null || echo 0)
  local ellipses
  ellipses=$(grep -cE '^\s*>\s*(…|\.\.\.)\s*$' "$path" 2>/dev/null || echo 0)
  local todos
  todos=$(grep -c '{{TODO' "$path" 2>/dev/null || echo 0)
  local total=$((placeholders + ellipses + todos))
  if [[ $total -gt 0 ]]; then
    echo "ERROR: interview at $path is not fully filled in." >&2
    echo "  $placeholders unfilled {{PLACEHOLDER}} markers" >&2
    echo "  $ellipses unfilled '> …' answer lines" >&2
    echo "  $todos {{TODO}} markers" >&2
    echo "" >&2
    echo "Fill in every question before scaffolding. The interview is the" >&2
    echo "load-bearing anti-template move — without it, the book is a form." >&2
    return 1
  fi
  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --product)             BS_PRODUCT="$2"; shift 2 ;;
    --positioning)         BS_POSITIONING="$2"; shift 2 ;;
    --palette-bg)          BS_PALETTE_BG="$2"; shift 2 ;;
    --palette-fg)          BS_PALETTE_FG="$2"; shift 2 ;;
    --palette-accent)      BS_PALETTE_ACCENT="$2"; shift 2 ;;
    --signature-primitive) BS_SIGNATURE_PRIMITIVE="$2"; shift 2 ;;
    --primary-font)        BS_PRIMARY_FONT="$2"; shift 2 ;;
    --locale)              BS_LOCALE="$2"; shift 2 ;;
    --output-dir)          OUTPUT_DIR="$2"; shift 2 ;;
    --require-interview)   REQUIRE_INTERVIEW="$2"; shift 2 ;;
    --force)               FORCE=1; shift ;;
    -h|--help)             usage ;;
    *)                     echo "Unknown arg: $1" >&2; usage ;;
  esac
done

# Validate
[[ -z "$BS_PRODUCT" ]]        && { echo "ERROR: --product required" >&2; usage; }
[[ -z "$BS_POSITIONING" ]]    && { echo "ERROR: --positioning required" >&2; usage; }
[[ -z "$BS_PALETTE_BG" ]]     && { echo "ERROR: --palette-bg required" >&2; usage; }
[[ -z "$BS_PALETTE_FG" ]]     && { echo "ERROR: --palette-fg required" >&2; usage; }
[[ -z "$BS_PALETTE_ACCENT" ]] && { echo "ERROR: --palette-accent required" >&2; usage; }

validate_hex() {
  if [[ ! "$1" =~ ^#[0-9A-Fa-f]{6}$ ]]; then
    echo "ERROR: invalid hex '$1' — must be #RRGGBB format" >&2
    exit 1
  fi
}
validate_hex "$BS_PALETTE_BG"
validate_hex "$BS_PALETTE_FG"
validate_hex "$BS_PALETTE_ACCENT"

# Enforce the interview if the caller opted in
if [[ -n "$REQUIRE_INTERVIEW" ]]; then
  if ! validate_interview "$REQUIRE_INTERVIEW"; then
    exit 1
  fi
  echo "✓ Interview at $REQUIRE_INTERVIEW is fully filled in."
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

# Export derived values for the Python substituter
export BS_PRODUCT_LOWER
export BS_YEAR
export BS_DATE
export BS_MONTH_YEAR
export BS_SIGNATURE_PRIMITIVE_CLASS
export BS_PRIMARY_FONT_URL
export BS_FORCE="$FORCE"

BS_PRODUCT_LOWER="$(echo "$BS_PRODUCT" | tr '[:upper:]' '[:lower:]')"
BS_YEAR="$(date +%Y)"
BS_DATE="$(date +%Y-%m-%d)"
BS_MONTH_YEAR="$(date '+%B %Y')"
BS_SIGNATURE_PRIMITIVE_CLASS="$(echo "$BS_SIGNATURE_PRIMITIVE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"
BS_PRIMARY_FONT_URL="$(echo "$BS_PRIMARY_FONT" | sed 's/ /+/g'):wght@300;400;500;600;700;800;900"

# Derive neutral + semantic ramps from bg/fg/accent
eval "$(python3 - <<'PY'
import os
bg = os.environ['BS_PALETTE_BG'].lstrip('#')
fg = os.environ['BS_PALETTE_FG'].lstrip('#')
ac = os.environ['BS_PALETTE_ACCENT'].lstrip('#')

def hx(s): return tuple(int(s[i:i+2], 16) for i in (0,2,4))
def rgb(t): return '#{:02X}{:02X}{:02X}'.format(*(max(0,min(255,int(round(c)))) for c in t))
def mix(a, b, t): return tuple(a[i]*(1-t) + b[i]*t for i in range(3))

BG, FG, AC = hx(bg), hx(fg), hx(ac)
pairs = {
    'BS_PALETTE_BG_50':  rgb(mix(BG, (255,255,255), 0.30)),
    'BS_PALETTE_BG_200': rgb(mix(BG, FG, 0.12)),
    'BS_PALETTE_BG_300': rgb(mix(BG, FG, 0.32)),
    'BS_PALETTE_BG_500': rgb(mix(BG, FG, 0.60)),
    'BS_PALETTE_FG_300': rgb(mix(FG, BG, 0.22)),
    'BS_PALETTE_FG_500': rgb(mix(FG, BG, 0.10)),
    'BS_PALETTE_FG_700': rgb(mix(FG, (0,0,0), 0.20)),
    'BS_SEMANTIC_SUCCESS': rgb(mix((107,142,90),  AC, 0.06)),
    'BS_SEMANTIC_WARNING': rgb(mix((212,162,74),  AC, 0.04)),
    'BS_SEMANTIC_DANGER':  rgb(mix((168,62,46),   AC, 0.20)),
    'BS_SEMANTIC_INFO':    rgb(mix((109,139,166), AC, 0.04)),
}
for k, v in pairs.items():
    print(f'export {k}="{v}"')
PY
)"

export OUTPUT_DIR FORCE_FLAG="$FORCE"

# Run the big substitution once per file
substitute() {
  local src="$1"
  local dest="$2"
  if [[ -e "$dest" && "$FORCE_FLAG" -eq 0 ]]; then
    echo "SKIP: $dest already exists (use --force to overwrite)"
    return
  fi
  export BS_SRC="$src" BS_DEST="$dest"
  python3 "$SKILL_DIR/scripts/_substitute.py"
}

echo "Scaffolding brand book for '$BS_PRODUCT' into $OUTPUT_DIR..."

substitute "$TEMPLATES_DIR/BRAND.md.tmpl"                "$OUTPUT_DIR/BRAND.md"
substitute "$TEMPLATES_DIR/BRAND.html.tmpl"              "$OUTPUT_DIR/BRAND.html"
substitute "$TEMPLATES_DIR/tokens.css.tmpl"              "$OUTPUT_DIR/tokens.css"
substitute "$TEMPLATES_DIR/signature-interview.md.tmpl"  "$OUTPUT_DIR/signature-interview.md"

echo ""
echo "✓ Scaffolded:"
for f in BRAND.md BRAND.html tokens.css signature-interview.md; do
  [[ -e "$OUTPUT_DIR/$f" ]] && echo "  $OUTPUT_DIR/$f"
done
echo ""
echo "Next steps:"
echo "  1. Fill in signature-interview.md (don't skip — it's load-bearing)"
echo "  2. Review BRAND.md and replace every {{TODO}} placeholder"
echo "  3. Run scripts/audit-contrast.py to validate the palette:"
echo "     $SKILL_DIR/scripts/audit-contrast.py \\"
echo "       --bg '$BS_PALETTE_BG' --fg '$BS_PALETTE_FG' --accent '$BS_PALETTE_ACCENT'"
echo "  4. Render the printable:"
echo "     $SKILL_DIR/scripts/render-pdf.sh $OUTPUT_DIR/BRAND.html $OUTPUT_DIR/BRAND.pdf"
