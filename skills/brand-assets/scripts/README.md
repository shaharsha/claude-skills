# Scripts

| Script | Purpose | Reference |
|---|---|---|
| [vectorize.sh](vectorize.sh) | PNG → multi-color SVG via split-by-color-mask + potrace | [reference/vectorize.md](../reference/vectorize.md) |
| [finalize-svg.py](finalize-svg.py) | Snap fills to brand hexes, filter paths, normalize viewBox | [reference/finalize.md](../reference/finalize.md) |
| [rasterize.sh](rasterize.sh) | SVG → PNG/JPG, tight-crop or centered-on-canvas | [reference/rasterize.md](../reference/rasterize.md) |
| [icon-pack.sh](icon-pack.sh) | One SVG → favicon.svg + PNGs + apple-touch-icon + manifest.json | [reference/icon-pack.md](../reference/icon-pack.md) |
| [color-audit.sh](color-audit.sh) | Opaque-pixel histogram; fails if non-brand drift >1% | see this README |

Make them executable on first checkout:

```bash
chmod +x vectorize.sh rasterize.sh icon-pack.sh color-audit.sh finalize-svg.py
```

## End-to-end: from a designer's PNG to production assets

```bash
cd /path/to/project
SRC=/path/to/designer-source.png
BRAND=('#0E1320' '#F3EAD3' '#B85A3A')

# 1. Vectorize PNG → raw multi-color SVG
vectorize.sh \
  --input "$SRC" \
  --output raw.svg \
  --colors "${BRAND[@]}" \
  --fuzz 20 --rembg

# 2. Finalize: snap fills, keep only the bubble counter that contains the terra dot,
#    drop speckle under 20px², leave viewBox as-is.
finalize-svg.py \
  --input raw.svg --output logo-icon.svg \
  --brand "${BRAND[@]}" \
  --require-contains '#F3EAD3:#B85A3A' \
  --min-area 20

# 3. Rasterize to production PNGs
rasterize.sh --input logo-icon.svg --output logo-icon.png --canvas 1024x1024 --content-width 820
rasterize.sh --input logo-icon.svg --output logo-icon@2x.png --width 2048

# 4. Icon pack (favicon + apple-touch-icon + PWA)
icon-pack.sh --input logo-icon.svg --output-dir public/ --bg '#F3EAD3' --brand-name 'Agentiko'

# 5. Verify brand fidelity
color-audit.sh logo-icon.png --brand "${BRAND[@]}"
color-audit.sh public/apple-touch-icon.png --brand "${BRAND[@]}" '#F3EAD3'  # include bg
```

The whole pipeline runs in ~5-10 seconds per logo. Zero network calls after first rembg model download.
