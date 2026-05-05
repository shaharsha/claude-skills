# Transparent backgrounds

`gpt-image-2` does not support `background=transparent`. `gpt-image-1.5` did — the skill no longer uses it. This file describes the two-step pipeline that replaces native transparent output.

**The pipeline:** generate on a clean monochrome backdrop → run `rembg` → done. Empirically (see [../examples.md](../examples.md)), this produces cleaner edges than native transparent mode ever did, especially for fine line art.

## The decision tree

```
Is the asset pure 2-color line art (black-on-white, single-color-on-white)?
  ├── YES → color-key transparency (ImageMagick, one command, zero AI)
  │         → mathematically perfect alpha, no halos, instantaneous
  └── NO  → rembg (AI-based segmentation)
            ├── Default:  birefnet-general (MIT-licensed, ~90% SOTA, commercial OK)
            ├── Personal: bria-rmbg       (+a hair better on complex bg, non-commercial)
            └── Hard mode (wispy hair / translucent glass / multi-subject):
                  → remove.bg API (paid, premium) or Clipdrop
```

## Step 1 — generate with an isolation-friendly prompt

Regardless of approach, **generate against a flat backdrop with no shadow**. Add this block to any prompt where a transparent output is the final goal:

```
CONSTRAINTS:
- Isolated on flat #FFFFFF (pure white) background.
- No drop shadow beneath the subject.
- No reflection, no contact shadow, no background gradient.
- No text, no borders, no watermark.
- Generous even padding on all four sides.
```

Why pure white specifically: it gives the cleanest contrast with most subjects, gives `rembg` an easy segmentation boundary, and composites the most predictably. Use a different flat color only if the subject itself is white (then use pure black or a saturated non-brand color like `#FF00C8`).

**Why no shadow:** soft shadows confuse segmentation models — they get partially cut, leaving a ghost halo. Always ask for zero shadow at generation time.

## Step 2 — remove the background

### Option A: `rembg` (default — works on anything)

```bash
./scripts/rembg.sh \
  --input  ./generated-images/logo-v1.png \
  --output ./generated-images/logo-v1-transparent.png
```

Models supported (pass via `--model`):

| Model | License | Best for | Speed |
|---|---|---|---|
| `birefnet-general` *(default)* | MIT | All commercial work, general subjects, logos, icons, products | ~10s CPU |
| `bria-rmbg` | Non-commercial only | Complex backgrounds, slightly cleaner edges on photos | ~10s CPU |
| `birefnet-portrait` | MIT | Human subjects (hair, skin edges) | ~10s CPU |
| `isnet-anime` | MIT | 2D anime / illustrated characters | ~8s CPU |
| `u2net` | Apache 2.0 | Legacy / fallback / fastest | ~4s CPU |

The first run of each model downloads weights (~200-400MB) to `~/.u2net/`. Subsequent runs are cache hits.

### Option B: ImageMagick color-key — pure line art only

For logos / icons that are purely black strokes on pure white (no gradients, no anti-aliased edges touching a color), this is mathematically superior to any AI segmentation:

```bash
magick in.png -fuzz 5% -transparent white out.png
```

`-fuzz 5%` accepts anti-aliased off-white pixels as "white enough." Adjust up to `10%` if you see a residual white halo; adjust down if colored interiors start getting keyed out.

For ImageMagick 6 (older default `/usr/bin/convert`):
```bash
convert in.png -fuzz 5% -transparent white out.png
```

**Install on macOS:** `brew install imagemagick` (provides `magick` CLI).

**When to use this over rembg:** pure line art logos, single-color marks, anything where the "background" is literally the white pixels and not "whatever is not the subject." Example: the `NORTHWIND COFFEE` test case — mountain line art + wordmark on white. Color-key produces perfect alpha with zero AI guesswork.

**When NOT to use this:** photos, color illustrations, anything with shadows or gradients that bleed into the backdrop.

### Option C: `remove.bg` API — premium fallback

For commercial hero assets where every pixel of the edge matters (wispy hair against busy backgrounds, glass, fur, translucent fabric), `rembg` can leave subtle artifacts that `remove.bg` handles better. ~$0.20/image, ~3.5s/call.

Not bundled by default — if you need it, the skill will prompt for an API key at runtime.

## Verification — always inspect before shipping

After removing the background, **read the output with the multimodal Read tool** and compose it onto at least two non-white backdrops to catch halos that white-on-white hides:

1. **Checkerboard** — reveals partial-alpha ghosting.
2. **Hot pink `#FF00C8`** — saturated contrast exposes any white fringe around strokes.
3. **Dark navy `#0F172A`** — matches real dark-mode use, exposes light halos.

A 20-line Python script with Pillow does this in seconds:

```python
from PIL import Image
rgba = Image.open("logo-v1-transparent.png").convert("RGBA")
for name, bg in [("pink", (255, 0, 200)), ("navy", (15, 23, 42))]:
    base = Image.new("RGB", rgba.size, bg)
    base.paste(rgba, (0, 0), rgba)
    base.save(f"_view_{name}.png")
```

If you see a halo, the fix is almost always at the *generation* step, not the removal step:
- Regenerate with stronger `CONSTRAINTS` (emphasize "NO drop shadow, NO gradient, NO contact shadow").
- If still bad, try a different backdrop color in the prompt (`#FF00C8` works well — subjects with natural shadows get cleaner edges against saturated colors).
- If the subject is line art, abandon rembg and use ImageMagick color-key.

## Edge cases

- **Long hair / fur:** `bria-rmbg` edges out `birefnet-general` here. For final hero shots, consider `remove.bg`.
- **Glass / translucent objects:** AI segmentation collapses transparency into binary alpha. No rembg model handles this well. Manual touch-up in Figma or Photoshop is the pragmatic path.
- **Subjects touching the edge of the canvas:** regenerate with more padding — the model cuts everything that reaches the frame.
- **Subject color matches backdrop:** regenerate against a contrasting backdrop (white subject → black backdrop and vice versa).
- **Multi-subject scenes:** rembg treats the whole foreground as one subject. To cut per-object, use the SAM family via `ComfyUI-RMBG` (out of scope for this skill).

## Pricing

- `rembg` (any model): free, runs locally. One-time ~200-400MB download per model.
- `ImageMagick`: free, runs locally. Instant.
- `remove.bg`: ~$0.20/image. Budget only for premium finals.
