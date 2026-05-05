---
name: brand-assets
description: Professional logo/brand asset pipelines — vectorize a PNG logo into a multi-color SVG, finalize an SVG (clamp fills to exact brand hexes, filter extraneous counters, square a viewBox), rasterize SVG back to pristine PNG at target size/padding, and generate a full favicon + apple-touch-icon + PWA icon pack from a single SVG source. Use when the user asks to vectorize a raster logo, clean up an SVG, re-render a logo at a specific size, produce favicons, build an icon pack, or audit brand color fidelity.
allowed-tools: Read, Write, Bash, Edit
---

# Brand Assets

Four mechanical jobs that sit between a designer's raster source and production-ready assets. Get these wrong and the brand is off by 5° for years.

## The four jobs

| Job | Input | Output | Script |
|---|---|---|---|
| **Vectorize** | PNG of a logo using ≤3 solid brand colors | clean multi-color SVG | [scripts/vectorize.sh](scripts/vectorize.sh) |
| **Finalize** | Any SVG with approximate colors or extra paths | SVG with exact brand hexes + filtered counters + square viewBox | [scripts/finalize-svg.py](scripts/finalize-svg.py) |
| **Rasterize** | SVG | PNG at specific size with tight-trim or centered-on-canvas padding | [scripts/rasterize.sh](scripts/rasterize.sh) |
| **Icon pack** | One SVG | `favicon.svg` + `favicon-32x32.png` + `apple-touch-icon.png` + manifest icons | [scripts/icon-pack.sh](scripts/icon-pack.sh) |

Plus a verification helper:

| **Color audit** | PNG | histogram of opaque pixels per hex — proves the raster only uses brand colors | [scripts/color-audit.sh](scripts/color-audit.sh) |

## When to use this skill

- "Vectorize this logo PNG" / "turn this into an SVG"
- "Clean up this SVG — the colors are slightly off"
- "Re-render the logo at 2048×2048 with 10% padding"
- "Generate a favicon pack from this logo"
- "Add apple-touch-icon" / "iOS home-screen icon is missing"
- "The PNG looks fuzzy at small sizes — can we redo it crisper?"
- "Audit which colors are in this PNG" / "is this on-brand?"
- Any refresh where brand colors changed and production PNGs need re-rendering from the SVG source.

## Workflow

1. **Read the reference for the job**:
   - [reference/vectorize.md](reference/vectorize.md) — PNG → multi-color SVG (the non-obvious part is split-by-color-mask + combine, not one-shot trace)
   - [reference/finalize.md](reference/finalize.md) — the "keep only the counter whose bbox contains the focal dot" rule, plus viewBox tricks
   - [reference/rasterize.md](reference/rasterize.md) — tight-trim vs centered-on-canvas; when to pre-bake clear space vs ship tight
   - [reference/icon-pack.md](reference/icon-pack.md) — favicon quirks, apple-touch-icon bg requirement (iOS auto-rounds corners, so NO transparent bg)
   - [reference/tools.md](reference/tools.md) — `rsvg-convert`, `vtracer`, `potrace`, `rembg`, `magick`, install + quirks

2. **Run the script** with the documented flags. Each script prints its usage with `--help`.

3. **Verify** visually and with `color-audit.sh` — does the output use exactly the brand hexes and nothing else?

4. **Iterate** if needed. Most jobs are one-shot; vectorize sometimes needs 2-3 iterations on the color mask thresholds.

## House rules

- **Never one-shot vectorize a multi-color logo.** VTracer's `color` mode produces plausible output but muddies the palette (antialiased edges introduce 50+ intermediate hexes). Always split by color first.
- **Always run finalize after vectorize.** Raw trace output never matches brand hexes exactly and often has dead sub-paths.
- **Tight-crop rasters as the default.** Let consumers add their own clear space. Bake padding in only for iOS/Android app icons (apple-touch-icon, PWA icons) where the launcher has no padding of its own.
- **Verify with `color-audit.sh` before shipping.** A 2-second check catches colors that shouldn't be there.
- **SVG over PNG when possible.** Ship the SVG as primary, PNG as fallback. The PNG is a render OF the SVG — they should never drift.

## Non-goals

- Designing a logo from scratch — use [image-generation](../image-generation/SKILL.md).
- Authoring a brand book / pitch deck — that's design work, not mechanical.
- Icon design (outline systems, multi-glyph consistency) — different discipline; use a dedicated icon designer.
- Animation / Lottie / motion — out of scope.
