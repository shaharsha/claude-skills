#!/usr/bin/env bash
# render-pdf.sh — assemble slide PNGs + deck plan into a 16:9 PDF deck via Chrome headless.
#
# Usage:
#   render-pdf.sh --plan deck-plan.json --slides-dir ./slides/ --output ./output/deck.pdf
#
# How it works:
#   1. Reads deck-plan.json to know slide order.
#   2. Builds a self-contained HTML file with one full-bleed <img> per slide in 16:9.
#   3. Chrome headless renders to PDF at exactly the slide aspect ratio (no margins).

set -euo pipefail

PLAN=""
SLIDES_DIR=""
OUTPUT=""
KEEP_HTML=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan) PLAN="$2"; shift 2 ;;
    --slides-dir) SLIDES_DIR="$2"; shift 2 ;;
    --output|-o) OUTPUT="$2"; shift 2 ;;
    --keep-html) KEEP_HTML=1; shift ;;
    -h|--help)
      sed -n '1,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -z "$PLAN" ]]       && { echo "ERROR: --plan required" >&2; exit 2; }
[[ -z "$SLIDES_DIR" ]] && { echo "ERROR: --slides-dir required" >&2; exit 2; }
[[ -z "$OUTPUT" ]]     && { echo "ERROR: --output required" >&2; exit 2; }
[[ ! -f "$PLAN" ]]     && { echo "ERROR: plan not found: $PLAN" >&2; exit 2; }
[[ ! -d "$SLIDES_DIR" ]] && { echo "ERROR: slides dir not found: $SLIDES_DIR" >&2; exit 2; }

# Resolve absolute paths
PLAN_ABS="$(cd "$(dirname "$PLAN")" && pwd)/$(basename "$PLAN")"
SLIDES_ABS="$(cd "$SLIDES_DIR" && pwd)"
OUT_DIR="$(dirname "$OUTPUT")"
mkdir -p "$OUT_DIR"
OUT_ABS="$(cd "$OUT_DIR" && pwd)/$(basename "$OUTPUT")"

# Find Chrome
CHROME=""
for candidate in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "$(command -v google-chrome 2>/dev/null || true)" \
  "$(command -v google-chrome-stable 2>/dev/null || true)" \
  "$(command -v chromium 2>/dev/null || true)" \
  "$(command -v chromium-browser 2>/dev/null || true)" \
  "$(command -v chrome 2>/dev/null || true)"
do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    CHROME="$candidate"
    break
  fi
done
if [[ -z "$CHROME" ]]; then
  echo "ERROR: Chrome/Chromium not found. Install Google Chrome." >&2
  exit 1
fi

# Build the HTML deck via Python (one-off — keeps this script self-contained)
HTML_TMP="$(mktemp -t deck-XXXXXX).html"
python3 - "$PLAN_ABS" "$SLIDES_ABS" "$HTML_TMP" <<'PY'
import json, sys, os, glob, re
plan_path, slides_dir, out_html = sys.argv[1], sys.argv[2], sys.argv[3]

with open(plan_path) as f:
    plan = json.load(f)

slides = plan.get("slides", [])
title = plan.get("title", "Presentation")

# For each slide, find its PNG by id prefix in slides_dir
def find_slide_png(slide_id):
    sid = str(slide_id)
    pattern = os.path.join(slides_dir, f"slide-{sid}-*.png")
    matches = sorted(glob.glob(pattern))
    if not matches:
        # Fall back to any file starting with slide-<id>
        pattern2 = os.path.join(slides_dir, f"slide-{sid}*.png")
        matches = sorted(glob.glob(pattern2))
    return matches[0] if matches else None

sections = []
for s in slides:
    sid = str(s["id"])
    png = find_slide_png(sid)
    if not png:
        # Render a placeholder slide so the deck's order is preserved
        sections.append(f'''<section class="slide missing"><div class="placeholder">
          <div class="placeholder-id">Slide {sid}</div>
          <div class="placeholder-msg">image missing</div>
        </div></section>''')
        continue
    file_uri = "file://" + os.path.abspath(png)
    sections.append(f'<section class="slide"><img src="{file_uri}" alt="slide {sid}" /></section>')

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{
    size: 13.333in 7.5in;
    margin: 0;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0;
    background: #000;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  .slide {{
    width: 13.333in;
    height: 7.5in;
    page-break-after: always;
    break-after: page;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #000;
  }}
  .slide:last-child {{
    page-break-after: auto;
    break-after: auto;
  }}
  .slide img {{
    width: 100%;
    height: 100%;
    object-fit: cover;  /* fill the 16:9 frame; PNGs are already 16:9 so no crop */
    display: block;
  }}
  .slide.missing {{
    background: #1a1a1a;
    color: #eee;
  }}
  .placeholder {{
    text-align: center;
  }}
  .placeholder-id {{
    font-size: 72pt; font-weight: 700; opacity: 0.7;
  }}
  .placeholder-msg {{
    font-size: 18pt; opacity: 0.5; margin-top: 12pt;
  }}
</style>
</head>
<body>
{chr(10).join(sections)}
</body>
</html>
"""

with open(out_html, "w") as f:
    f.write(html)
print(f"Wrote HTML deck: {out_html} ({len(sections)} slides)", file=sys.stderr)
PY

echo "Rendering $HTML_TMP → $OUT_ABS via $CHROME..." >&2

"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-pdf-header-footer \
  --hide-scrollbars \
  --run-all-compositor-stages-before-draw \
  --virtual-time-budget=10000 \
  --print-to-pdf="$OUT_ABS" \
  "file://$HTML_TMP" 2>&1 | grep -v 'DevTools listening' || true

if [[ ! -f "$OUT_ABS" ]]; then
  echo "ERROR: Chrome did not produce $OUT_ABS" >&2
  exit 1
fi

if [[ "$KEEP_HTML" -eq 1 ]]; then
  HTML_KEEP="${OUT_ABS%.pdf}.html"
  cp "$HTML_TMP" "$HTML_KEEP"
  echo "Kept HTML: $HTML_KEEP" >&2
fi
rm -f "$HTML_TMP"

echo "✓ Wrote $OUT_ABS ($(wc -c < "$OUT_ABS" | tr -d ' ') bytes)" >&2
echo "$OUT_ABS"
