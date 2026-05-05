# Vectorize: PNG → multi-color SVG

Turn a raster logo (PNG/JPG) into a clean SVG with ≤3 solid brand colors. Read this before running `scripts/vectorize.sh`.

## Why you cannot one-shot vectorize a brand logo

VTracer's `--colormode color` mode produces plausible output but gives you 50-200 intermediate hex values along every anti-aliased edge. You end up with an SVG that claims to be "tan + navy" but actually has `#F2E9D2`, `#F1E8D0`, `#EFE5CC`, … — dozens of near-hexes no designer will accept.

**Solution: split by color mask first.** For each brand color, build a binary black-and-white mask (that color → black, everything else → white), trace each mask separately with potrace (single-color, lossless), then combine the traces into one SVG with the exact brand fills assigned post-hoc.

## Pipeline

```
PNG (opaque on bg) ──rembg──▶ PNG (transparent)
                              │
                              ├── color mask A ──potrace──▶ SVG path A  (fill: hex A)
                              ├── color mask B ──potrace──▶ SVG path B  (fill: hex B)
                              └── color mask C ──potrace──▶ SVG path C  (fill: hex C)
                                                               │
                                                               ▼
                                                          combine.py
                                                               │
                                                               ▼
                                                         combined.svg
```

## Prerequisites

Install via Homebrew:

```bash
brew install potrace        # 1-color tracer, rock-solid since 2001
brew install imagemagick    # for mask operations
pipx install rembg[cpu]     # background removal (or just trim manually)
# Optional multi-color tracer (fallback only, not default):
brew install vtracer
```

See [tools.md](tools.md) for version notes.

## Step-by-step

### 1. Isolate the logo (remove background)

If the source PNG already has transparent background, skip. Otherwise:

```bash
rembg i input.png input-transparent.png
```

`rembg` pulls a pre-trained segmentation model on first run (~170 MB), then runs offline. Works best on logos that are opaque shapes on a contrasting background — less well on thin linework or gradients.

### 2. Identify brand colors

Sample the dominant opaque pixel colors:

```bash
magick input-transparent.png -channel A -threshold 50% +channel +dither -colors 3 -unique-colors txt:- \
  | grep -oE '#[0-9A-F]{6}' | sort -u
```

Expect 3 distinct hex values for a typical 3-color logo. These are your **trace color targets**.

If the output has > 4 values, the logo has gradients or antialiased colored detail — your logo may not be cleanly vectorizable without art changes. Escalate to design.

### 3. Build a binary mask per color

For each brand color `$COLOR` (e.g., `#0E1320`):

```bash
magick input-transparent.png \
  -fuzz 20% \
  -fill white +opaque "$COLOR" \
  -fill black -opaque "$COLOR" \
  -alpha off \
  mask-$COLOR.pbm
```

**Fuzz tolerance** is the key knob. Start at 20%. Raise if the mask misses antialiased edges (black pixels not captured). Lower if the mask bleeds into adjacent colors (black pixels where cream should be white). The right value is color-dependent — terracotta near navy needs lower fuzz than cream near white.

Inspect each mask visually before tracing. A broken mask produces a broken trace.

### 4. Trace each mask with potrace

```bash
potrace mask-$COLOR.pbm --svg --output path-$COLOR.svg \
  --turdsize 2 \
  --alphamax 1.0 \
  --opttolerance 0.2
```

Key potrace flags:
- `--turdsize N`: drop tiny noise clusters smaller than N pixels. 2 is conservative (keeps voice dots). Raise to 20 to aggressively denoise.
- `--alphamax`: corner threshold. 1.0 = default. Lower (0.5) preserves sharper corners for geometric logos.
- `--opttolerance`: curve-fitting tolerance. 0.2 default. Lower (0.1) = more faithful but more control points. Higher (0.5) = smoother but loses detail.

For a typical geometric wordmark: defaults are fine. Iterate if corners round off or the bubble tail smooths out.

### 5. Combine traces into one SVG

Use the bundled combiner (`scripts/combine-traces.py`) or the inline pattern:

```python
import xml.etree.ElementTree as ET
# Pseudocode — real impl in scripts/combine-traces.py
for color_hex, trace_path in traces:
    path_element = extract_path_from_potrace_svg(trace_path)
    path_element.set('fill', color_hex)
    combined.append(path_element)
```

Emit one `<g fill="HEX">` group per color, each containing its traced paths. Use the union of all mask viewBoxes as the combined viewBox.

### 6. Finalize

Pipe the result through `finalize-svg.py` (see [finalize.md](finalize.md)) to:
- Snap any residual near-colors to the exact brand hex
- Filter dead paths
- Normalize viewBox

## Gotchas

- **Fill rule**: potrace uses `fill-rule: nonzero` by default. If your logo has counters (holes in letterforms like `a`, `o`, `p`), verify the counter is reverse-wound so it punches a hole. If the output "fills in" a letter counter, add `fill-rule="evenodd"` to the group or re-trace with `-n` (invert) on the problematic mask.
- **Overlapping masks**: if color A and color B have touching antialiased edges, both masks may claim the edge pixels. Paint order matters — put the background color group FIRST in the SVG, foreground colors LAST.
- **Voice-dot / small features**: if the focal feature is <16px on the source, boost source resolution 2× with `magick -resize 200%` before masking. Small features disappear into `--turdsize` otherwise.
- **The tail/serif trap**: geometric logos with thin extending tails (like a bubble-"a" chat tail) can vanish if `--turdsize` is too aggressive. Start at 2; raise only if you have genuine noise.

## When to fall back to vtracer

VTracer's `color` mode is acceptable when:
- The logo is complex illustrative (50+ colors, not a brand mark)
- You need speed over precision
- You'll run the result through `finalize-svg.py` to clamp colors anyway

`vtracer --input foo.png --output foo.svg --colormode color --mode polygon --filter_speckle 4 --color_precision 6 --hierarchical cutout`

The `hierarchical cutout` mode is what preserves counter holes. Without it, VTracer flattens counters.
