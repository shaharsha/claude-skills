# Finalize: clean up an SVG

The last mile between a raw trace and production. Runs `scripts/finalize-svg.py`.

## What finalize does

1. **Snap fills to exact brand hexes.** Near-matches like `#0D1320`, `#0F1421`, `#101522` collapse to `#0E1320`. Uses Euclidean RGB distance against the provided brand palette; pixels beyond a configurable threshold (default 15 RGB-units) raise an error rather than silently mapping to something arbitrary.
2. **Filter extraneous paths.** Three modes:
   - `--min-area N` — drop paths whose bounding-box area is under N (kills speckle the tracer missed).
   - `--require-contains FOCAL_HEX` — keep a given color group's paths ONLY if their bbox contains the bounding box of any path in the FOCAL_HEX group. This is the rule we used for the Agentiko bubble-"a": keep only the cream counter whose bbox contains the terracotta voice dot. All other counters (`e`, `o` in "agentiko") get dropped.
   - `--drop-group HEX` — remove a color group entirely (useful when you want a 2-color variant).
3. **Normalize the viewBox.** Options:
   - `--square` — pad height to equal width (or vice versa) by shifting the viewBox origin, content stays centered. Use for favicons.
   - `--trim` — shrink viewBox to content bbox (no padding).
   - `--pad-percent N` — add N% padding on all sides.
4. **Sort group order** — background color first, foreground last. Matters for fill-rule and visual stacking.

## Usage

```bash
python3 scripts/finalize-svg.py \
  --input raw-traced.svg \
  --output clean.svg \
  --brand '#0E1320' '#F3EAD3' '#B85A3A' \
  --require-contains '#F3EAD3:#B85A3A' \
  --min-area 50 \
  --square \
  --tolerance 15
```

The `--require-contains 'A:B'` syntax reads as *"keep only color-A paths whose bbox contains any color-B bbox"*.

## Reading the output

The script prints a one-line summary per operation:
```
vt-wordmark-light.svg: navy=9 counters=1 terra=1 → 22394 bytes
```

If you expected `counters=1` (just the bubble-"a") and see `counters=4`, the contains-check filter missed — inspect the raw SVG's paths and widen the tolerance or add a manual `--keep-index N` for the path you want.

## Gotchas

- **Bbox containment is literal.** If the counter's bbox is just barely off (1-2 pixel shy of enclosing the dot), the filter drops it. Set `--contains-slack 5` to add padding to the containment check.
- **Tolerance too tight → error.** Pragmatic default is 15 RGB-units. Vectorize-then-finalize pipelines rarely drift more than 3. Hand-drawn SVGs from Illustrator may drift 20+ because of "web color" optimization (e.g., `#0E1320` gets saved as `#0D1220`). Raise tolerance to 30 in those cases; beyond 50 you're lying to yourself about brand fidelity.
- **Fill-rule preservation.** If the input SVG has `fill-rule="evenodd"` on a group, the finalize output keeps it. If you need to switch, pass `--fill-rule nonzero|evenodd`.
- **Transforms flatten.** Any `transform="translate(x,y)"` on groups gets baked into the paths by default (via `--flatten-transforms`, on by default). Disable with `--preserve-transforms` only when the downstream consumer expects them.
- **Paths not in a colored group.** Some tracers emit top-level paths without a `<g fill>` wrapper. Finalize treats those as "black" by default; pass `--default-fill HEX` to override.

## Typical workflows

**Pristine vectorize output:**
```
raw-trace.svg → finalize --brand ... --min-area 2 → clean.svg
```

**Two-color wordmark (drop the terracotta dot for a minimal mark):**
```
clean.svg → finalize --drop-group '#B85A3A' → wordmark-2color.svg
```

**Square favicon from a rectangular icon:**
```
clean.svg → finalize --square → favicon-source.svg
```

**2-color dark variant (invert light-to-dark):**
There's no automatic inversion — that's a design decision. Produce the dark variant by re-running `vectorize.md` on a dark source PNG, OR by hand-editing fills in the SVG. Finalize will snap the manual fills to exact brand hexes.
