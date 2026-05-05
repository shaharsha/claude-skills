# Rasterize: SVG → pristine PNG

Goal: produce a PNG that uses exactly the brand hex colors with clean edge anti-aliasing, at a target size, with a predictable padding rule.

Runs `scripts/rasterize.sh`.

## Why not just `convert foo.svg foo.png`?

ImageMagick's native SVG renderer is approximate — it ignores `fill-rule`, misrenders nested transforms, and can drift colors on gradient edges. Always use `rsvg-convert` (librsvg) for the actual SVG → bitmap step, then use ImageMagick ONLY for compositing, padding, and trim operations.

## Two padding strategies

### Tight-crop (default, for flexible delivery)

The content fills the entire canvas. Downstream consumers (web, print, CSS) add their own clear space. Best for wordmarks and assets used in layouts.

```bash
scripts/rasterize.sh --input logo-wordmark.svg --output logo-wordmark.png --width 2400
# Content width = 2400, height auto via aspect ratio, no padding.
```

### Centered-on-square (for app icons / favicons)

Glyph centered on a square canvas with the brand background filled (or transparent). Use for iOS/Android app icons, favicons, PWA manifest icons.

```bash
scripts/rasterize.sh --input logo-icon.svg --output icon-1024.png \
  --canvas 1024x1024 \
  --content-width 820 \
  --bg '#F3EAD3'
# Glyph rendered at 820 wide, centered on 1024×1024 cream canvas.
```

Use `--bg transparent` for an alpha PNG. iOS apple-touch-icon REQUIRES a filled bg (the OS adds its own rounded corners).

## Flags

| Flag | Default | Notes |
|---|---|---|
| `--input PATH` | (required) | SVG source |
| `--output PATH` | (required) | PNG destination. Use `.jpg` to output JPEG (q=85). |
| `--width N` | — | Content width in px (height auto). Tight-crop. |
| `--height N` | — | Content height in px (width auto). Tight-crop. |
| `--canvas WxH` | — | Canvas size for centered-on-canvas mode. |
| `--content-width N` | 80% of canvas width | Glyph width inside canvas. Only valid with `--canvas`. |
| `--bg COLOR` | `transparent` | Canvas bg. Hex or `transparent`. |
| `--quality N` | 85 | JPEG quality (ignored for PNG). |
| `--trim` | off | Tight-trim alpha edges before composite. Use when source SVG has sub-pixel padding. |
| `--verify` | off | Run color-audit on the output, fail if non-brand hex >1% of opaque pixels. |

## Multi-size rendering

Render one SVG into a pack of sizes:

```bash
for w in 256 512 1024 2048; do
  scripts/rasterize.sh --input logo-icon.svg --output icon-$w.png --width $w
done
```

Or use the icon-pack script (see [icon-pack.md](icon-pack.md)) if you want web-standard sizes baked in.

## Quality expectations

A crisp rasterize from a 3-color SVG at 2400px wide should produce:
- **3 dominant opaque colors** matching the brand hexes exactly (verify with `color-audit.sh`)
- **<2% edge anti-aliasing pixels** (the intermediate-hex pixels along edges)
- **Filesize ~50-100 KB** for PNG, <30 KB for JPEG q=85

If you see filesize >500 KB or >10% AA pixels, the source SVG probably has gradients or transforms that aren't flattening. Clean the SVG first.

## When to ship JPG vs PNG

- **JPG** for large hero/photographic assets (20 KB-300 KB range). Always q=85 or higher; q<80 introduces visible blocking around brand color edges.
- **PNG** for logos, icons, anything with sharp geometry or transparency. Alpha channel is the tiebreaker.

Never deliver both — pick one. Hero JPG + logo PNG is fine; same asset in both formats is a maintenance smell.
