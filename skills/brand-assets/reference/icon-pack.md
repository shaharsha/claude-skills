# Icon pack: full favicon + apple-touch-icon + PWA set from one SVG

Runs `scripts/icon-pack.sh`. Produces the modern minimum-viable icon set:

| File | Size | Purpose |
|---|---|---|
| `favicon.svg` | vector | Modern browsers (Chrome, Firefox, Edge). Derived from the source SVG with a square viewBox. |
| `favicon-32x32.png` | 32×32 | Fallback for browsers that ignore SVG favicons. |
| `favicon-16x16.png` | 16×16 | Optional; most browsers auto-scale from 32 so usually not needed. |
| `apple-touch-icon.png` | 180×180 | iOS home screen / Safari pinned tab. **MUST have filled bg — iOS auto-rounds corners.** |
| `icon-192.png` | 192×192 | PWA manifest minimum. |
| `icon-512.png` | 512×512 | PWA manifest maskable / high-density. |
| `manifest.json` (optional) | — | PWA manifest stub referencing the above. |

## Usage

```bash
scripts/icon-pack.sh \
  --input logo-icon.svg \
  --output-dir public/ \
  --bg '#F3EAD3' \
  --brand-name 'Agentiko'
```

Options:
- `--input PATH` — source SVG (required)
- `--output-dir DIR` — where to write all the files (required, created if missing)
- `--bg COLOR` — background for apple-touch-icon and PWA icons (required; `transparent` forbidden for these two)
- `--brand-name NAME` — writes to the generated manifest.json `name` and `short_name` fields (optional)
- `--no-manifest` — skip manifest.json generation
- `--maskable` — also emit `icon-512-maskable.png` with extra 20% safe-area padding per PWA maskable-icon spec

## What the script does (in order)

1. Read source SVG. Compute the square-viewBox SVG (`favicon.svg`).
2. Rasterize the SVG into PNGs at each target size (via `rsvg-convert`).
3. For apple-touch-icon and PWA icons: composite the rasterized glyph onto a solid-bg canvas at ~80% content size (leaving ~10% safe area on all sides).
4. Optionally emit `manifest.json` with conventional PWA fields.

## Wiring into your HTML

Paste into `<head>`:

```html
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
<link rel="manifest" href="/manifest.json" />
```

Order matters — browsers pick the first `<link rel="icon">` they can parse. SVG first gives modern browsers the crisp version.

## Gotchas

- **apple-touch-icon MUST be opaque.** iOS adds rounded corners and a subtle shine overlay. A transparent PNG produces a jagged-edge icon. Always pass `--bg` as a filled color.
- **Rectangular logos don't fit square icon slots.** If your source SVG isn't square, `icon-pack.sh` will center it on a square canvas. For brand reasons, consider providing a dedicated square-cropped source (e.g., just the bubble-"a" icon, not the full wordmark) for this pipeline. Use the wordmark separately for og-image / social-share assets.
- **PWA maskable icons need extra safe area.** Android's launcher may crop up to 20% off the edges into a "mask" shape (circle, squircle, drop, etc.). Pass `--maskable` to bake a 20% padding into a dedicated 512 variant; reference it in manifest.json as `"purpose": "maskable"`.
- **Don't ship favicon.ico.** The `.ico` format is 1999 Windows relic. All browsers since 2015 accept PNG and SVG favicons. Skip it unless you're targeting literal Internet Explorer.

## Regenerate when

- Brand colors change → re-run with the same flags
- Logo geometry changes → re-run
- New platform target (e.g., adding Windows Tile icons) → extend the script or run sizes manually

## Windows Tile / Safari Mask-Icon / Legacy

Not in the default pack. Add manually if needed:

```html
<!-- Safari 10+ pinned tab (monochrome SVG) -->
<link rel="mask-icon" href="/safari-pinned-tab.svg" color="#B85A3A" />

<!-- Microsoft Edge / Windows -->
<meta name="msapplication-TileColor" content="#F3EAD3" />
<meta name="msapplication-TileImage" content="/mstile-144x144.png" />
```

These are mostly cruft in 2026. Add only if analytics show meaningful Windows/Safari-pinned-tab usage.
