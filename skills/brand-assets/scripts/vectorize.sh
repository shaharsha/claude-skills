#!/usr/bin/env bash
# vectorize.sh — PNG logo → multi-color SVG via split-by-color-mask + potrace.
#
# Usage:
#   vectorize.sh --input logo.png --output logo.svg \
#     --colors '#0E1320' '#F3EAD3' '#B85A3A' \
#     [--fuzz 20] [--turdsize 2] [--alphamax 1.0] [--opttolerance 0.2]
#
# See reference/vectorize.md for the pipeline.

set -euo pipefail

INPUT=""
OUTPUT=""
COLORS=()
FUZZ=20
TURDSIZE=2
ALPHAMAX=1.0
OPTTOLERANCE=0.2
REMBG_IF_OPAQUE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)         INPUT="$2"; shift 2 ;;
    --output)        OUTPUT="$2"; shift 2 ;;
    --colors)
      shift
      while [[ $# -gt 0 && "$1" =~ ^# ]]; do
        COLORS+=("$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')")
        shift
      done ;;
    --fuzz)          FUZZ="$2"; shift 2 ;;
    --turdsize)      TURDSIZE="$2"; shift 2 ;;
    --alphamax)      ALPHAMAX="$2"; shift 2 ;;
    --opttolerance)  OPTTOLERANCE="$2"; shift 2 ;;
    --rembg)         REMBG_IF_OPAQUE=1; shift ;;
    --help|-h)       sed -n '1,10p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$INPUT" && -n "$OUTPUT" && ${#COLORS[@]} -gt 0 ]] \
  || { echo "--input, --output, and --colors are required" >&2; exit 1; }
[[ -f "$INPUT" ]] || { echo "input not found: $INPUT" >&2; exit 1; }

command -v magick  >/dev/null || { echo "magick (ImageMagick v7) not found" >&2; exit 1; }
command -v potrace >/dev/null || { echo "potrace not found — brew install potrace" >&2; exit 1; }

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# ── Step 1: background removal (optional) ─────────────────────
SRC="$INPUT"
if [[ "$REMBG_IF_OPAQUE" -eq 1 ]]; then
  command -v rembg >/dev/null || { echo "rembg not found — pipx install rembg[cpu]" >&2; exit 1; }
  rembg i "$INPUT" "$TMPDIR/nobg.png"
  SRC="$TMPDIR/nobg.png"
fi

# Get dimensions for the combined viewBox
read -r WIDTH HEIGHT < <(magick "$SRC" -format "%w %h" info:)

# ── Step 2: per-color mask + trace ────────────────────────────
declare -a TRACES
declare -a COLORS_ORDERED
for COLOR in "${COLORS[@]}"; do
  safe="${COLOR#\#}"
  mask="$TMPDIR/mask-$safe.pbm"
  svg_one="$TMPDIR/trace-$safe.svg"

  # Build binary mask: target color → black, everything else → white
  magick "$SRC" \
    -fuzz "${FUZZ}%" \
    -fill white +opaque "$COLOR" \
    -fill black -opaque "$COLOR" \
    -alpha off \
    "$mask"

  # Trace the mask with potrace
  potrace "$mask" --svg --output "$svg_one" \
    --turdsize "$TURDSIZE" \
    --alphamax "$ALPHAMAX" \
    --opttolerance "$OPTTOLERANCE"

  TRACES+=("$svg_one")
  COLORS_ORDERED+=("$COLOR")
done

# ── Step 3: combine into one SVG ──────────────────────────────
python3 - "$OUTPUT" "$WIDTH" "$HEIGHT" "${COLORS_ORDERED[@]}" "--" "${TRACES[@]}" <<'PY'
import sys, re, xml.etree.ElementTree as ET
args = sys.argv[1:]
output, width, height, *rest = args
sep = rest.index("--")
colors = rest[:sep]
traces = rest[sep + 1:]
assert len(colors) == len(traces)

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)

out = ET.Element(f"{{{SVG}}}svg", {
    "xmlns": SVG,
    "viewBox": f"0 0 {width} {height}",
})

# potrace emits an implicit upside-down mapping via a transform. We'll extract paths as-is.
PATH_RE = re.compile(r'<path[^/]*d="([^"]+)"', re.DOTALL)
TRANSFORM_RE = re.compile(r'transform="([^"]+)"')

for color, trace_path in zip(colors, traces):
    txt = open(trace_path).read()
    # Extract the transform from the <g> wrapping paths (potrace puts it there)
    g_transform = None
    m = re.search(r'<g[^>]*transform="([^"]+)"', txt)
    if m:
        g_transform = m.group(1)
    g = ET.SubElement(out, f"{{{SVG}}}g", {"fill": color})
    if g_transform:
        g.set("transform", g_transform)
    for m in PATH_RE.finditer(txt):
        ET.SubElement(g, f"{{{SVG}}}path", {"d": m.group(1)})

tree = ET.ElementTree(out)
ET.indent(tree, space="")
tree.write(output, encoding="utf-8", xml_declaration=False)
print(f"wrote {output}")
PY

echo "vectorize done: ${#COLORS[@]} color group(s) in $OUTPUT"
echo "next step: run finalize-svg.py to snap fills and filter paths"
