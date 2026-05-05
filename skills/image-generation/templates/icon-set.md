# Icon set prompt template

**Default model:** `gpt-image-2` at `quality=high` for finals (prompt adherence + reasoning keep all icons stylistically locked in a single grid call). Gemini Flash for exploration only.

## Required inputs

- List of icons (subjects) — e.g., home, user, settings, search, bell, cart
- Style: line / filled / duotone
- Stroke weight (if line): "1.5px stroke" / "2px stroke" / "3px bold stroke"
- Color: monochrome black / brand color / two-tone palette
- Output: single grid, or one PNG per icon (post-slice)
- Background: transparent / pure white

## Strategy A — single-call grid (recommended)

Generate the entire set in one image as a grid, then slice client-side.

### gpt-image-2 variant

```
BACKGROUND: Plain white background, no texture, no shadow.

SUBJECT: A set of [N] UI icons arranged in a [ROWS]×[COLS] grid, evenly spaced.

DETAILS: Icons in reading order (left-to-right, top-to-bottom):
1. [ICON 1]
2. [ICON 2]
3. [ICON 3]
[...]

Style for ALL icons: [STROKE DESCRIPTION — e.g., "2px black stroke, rounded
stroke caps, no fill"], same optical weight across all icons, centered in
each tile at consistent scale, [PADDING — e.g., "30% padding around each
icon"]. Flat 2D vector aesthetic, suitable for a design system.

CONSTRAINTS: No overlap between tiles. No text labels. No extra decorative
elements. Monochrome [COLOR] on plain white. No watermark.
```

**Run with:** `--quality high --size 1024x1024` (for ≤6 icons) or `--size 2048x1152` (for a wider grid).

### Gemini Flash variant (exploration only)

```
Generate a set of [N] UI icons arranged in a [ROWS]×[COLS] grid on pure
white background. Icons (in reading order): [LIST]. All icons share 2px
black stroke, rounded caps, no fill, 30% padding, centered, consistent
optical weight. Flat 2D vector aesthetic.
```

**Run with:** `--model gemini-3.1-flash-image-preview --aspect 1:1 --size 1K`.

## Strategy B — multi-turn, one icon per image

Use when you need clean isolated PNGs (e.g., for an iOS app icon set).

1. Generate the **first icon** with the full style description (gpt-image-2 high).
2. For each subsequent icon, attach the first as a reference via `/edits`:
   ```
   In the exact same style as the attached reference icon (same stroke
   weight, same corner radius, same visual weight, same color), draw a
   [NEXT SUBJECT]. Isolated on pure white background, centered, 30% padding.
   No text, no watermark.
   ```
3. gpt-image-2 processes every reference at high fidelity automatically — no flag needed.

**Run with:** `--ref path/to/first-icon.png` for each follow-up call.

## Strategy C — transparent PNGs (post-process)

Generate with Strategy A or B on white background, then transparency-process each icon:

**For pure monochrome line art (recommended):** ImageMagick color-key — mathematically perfect alpha, instantaneous.
```bash
magick icon.png -fuzz 5% -transparent white icon-transparent.png
```

**For colored or textured icons:** `scripts/rembg.sh`.
```bash
./scripts/rembg.sh --input icon.png --output icon-transparent.png
```

See [../reference/transparent-backgrounds.md](../reference/transparent-backgrounds.md) for the decision tree.

## Filled example — 6 UI icons, line style, monochrome

**Brief:** Home, user, settings, search, bell, cart. 2px black stroke, rounded caps, 3×2 grid.

**gpt-image-2 prompt:**
```
BACKGROUND: Plain white background, no texture, no shadow.

SUBJECT: A set of 6 UI icons arranged in a 3×2 grid, evenly spaced.

DETAILS: Icons in reading order (left-to-right, top-to-bottom):
1. home (house outline)
2. user (head and shoulders)
3. settings (gear)
4. search (magnifying glass)
5. bell (notification)
6. cart (shopping basket)

Style for ALL icons: 2px black stroke (#000000), rounded stroke caps, no
fill, same optical weight across all icons, centered in each tile at
consistent scale, 30% padding around each icon. Flat 2D vector aesthetic,
suitable for a design system.

CONSTRAINTS: No overlap between tiles. No text labels. No extra decorative
elements. Monochrome black on plain white. No watermark.
```

**Run with:** `--quality high --size 1024x1024`.

## Tips

- For more than 12 icons, split into multiple grid calls of 6-8 icons each. Density above ~12 icons per grid degrades individual icon quality even on gpt-image-2.
- For final delivery, vectorize the raster output via the `brand-assets` skill (or Illustrator Image Trace, VectorizerAI) — these models output rasters, "vector-like" is aesthetic only.
- Slice grids client-side with ImageMagick or Pillow:
  ```bash
  magick grid.png -crop 3x2@ +repage +adjoin tile-%d.png
  ```
