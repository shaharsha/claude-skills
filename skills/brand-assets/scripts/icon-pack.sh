#!/usr/bin/env bash
# icon-pack.sh — generate favicon.svg + PNGs + apple-touch-icon + manifest.json
# from a single SVG source.
#
# Usage:
#   icon-pack.sh --input logo-icon.svg --output-dir public/ \
#     --bg '#F3EAD3' --brand-name 'Agentiko'
#
# Produces:
#   favicon.svg              (square-viewBox derivative of input)
#   favicon-32x32.png        (PNG fallback)
#   apple-touch-icon.png     (180x180 on --bg)
#   icon-192.png, icon-512.png  (PWA manifest icons)
#   manifest.json            (unless --no-manifest)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

INPUT=""
OUT=""
BG=""
BRAND_NAME=""
NO_MANIFEST=0
MASKABLE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)       INPUT="$2"; shift 2 ;;
    --output-dir)  OUT="$2"; shift 2 ;;
    --bg)          BG="$2"; shift 2 ;;
    --brand-name)  BRAND_NAME="$2"; shift 2 ;;
    --no-manifest) NO_MANIFEST=1; shift ;;
    --maskable)    MASKABLE=1; shift ;;
    --help|-h)     sed -n '1,14p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$INPUT" && -n "$OUT" && -n "$BG" ]] \
  || { echo "--input, --output-dir, and --bg are required" >&2; exit 1; }
[[ -f "$INPUT" ]] || { echo "input not found: $INPUT" >&2; exit 1; }
[[ "$BG" != "transparent" ]] \
  || { echo "apple-touch-icon and PWA icons REQUIRE a filled bg — pass --bg '#HEX'" >&2; exit 1; }

mkdir -p "$OUT"

# ── 1. favicon.svg (square viewBox) ───────────────────────────
# Find existing viewBox, square it by centering.
python3 - "$INPUT" "$OUT/favicon.svg" <<'PY'
import re, sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
m = re.search(r'viewBox="([^"]+)"', s)
if not m:
    raise SystemExit("source SVG has no viewBox; can't square it")
parts = [float(x) for x in m.group(1).replace(",", " ").split()]
if len(parts) != 4:
    raise SystemExit(f"weird viewBox: {m.group(1)}")
x, y, w, h = parts
side = max(w, h)
nx = x - (side - w) / 2
ny = y - (side - h) / 2
new_vb = f"viewBox=\"{nx:g} {ny:g} {side:g} {side:g}\""
out = re.sub(r'viewBox="[^"]+"', new_vb, s, count=1)
open(dst, "w").write(out)
print(f"wrote {dst}")
PY

# ── 2. Rasterize the favicon SVG to PNG fallback ──────────────
bash "$HERE/rasterize.sh" --input "$OUT/favicon.svg" --output "$OUT/favicon-32x32.png" --width 32
bash "$HERE/rasterize.sh" --input "$OUT/favicon.svg" --output "$OUT/favicon-16x16.png" --width 16

# ── 3. apple-touch-icon (180x180 on filled bg) ────────────────
bash "$HERE/rasterize.sh" --input "$OUT/favicon.svg" --output "$OUT/apple-touch-icon.png" \
  --canvas 180x180 --content-width 120 --bg "$BG"

# ── 4. PWA icons ──────────────────────────────────────────────
bash "$HERE/rasterize.sh" --input "$OUT/favicon.svg" --output "$OUT/icon-192.png" \
  --canvas 192x192 --content-width 150 --bg "$BG"
bash "$HERE/rasterize.sh" --input "$OUT/favicon.svg" --output "$OUT/icon-512.png" \
  --canvas 512x512 --content-width 410 --bg "$BG"

if [[ "$MASKABLE" -eq 1 ]]; then
  # Maskable icons need 20% safe area per PWA spec — shrink content to ~60% of canvas.
  bash "$HERE/rasterize.sh" --input "$OUT/favicon.svg" --output "$OUT/icon-512-maskable.png" \
    --canvas 512x512 --content-width 310 --bg "$BG"
fi

# ── 5. manifest.json ──────────────────────────────────────────
if [[ "$NO_MANIFEST" -eq 0 ]]; then
  NAME="${BRAND_NAME:-App}"
  MASKABLE_ENTRY=""
  if [[ "$MASKABLE" -eq 1 ]]; then
    MASKABLE_ENTRY=',
    { "src": "/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }'
  fi
  cat > "$OUT/manifest.json" <<EOF
{
  "name": "$NAME",
  "short_name": "$NAME",
  "background_color": "$BG",
  "theme_color": "$BG",
  "display": "standalone",
  "start_url": "/",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }$MASKABLE_ENTRY
  ]
}
EOF
fi

echo
echo "icon pack written to $OUT/"
echo "wire into your HTML:"
cat <<'HTML'
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
  <link rel="manifest" href="/manifest.json" />
HTML
