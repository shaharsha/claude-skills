# brand-assets

Professional logo/brand asset pipelines that run locally, in seconds.

Part of [shaharsha/claude-skills](../..). MIT.

---

- **vectorize** — turn a raster logo (PNG/JPG) into a multi-color SVG using split-by-color-mask + potrace (not one-shot vtracer, which muddies the palette).
- **finalize-svg** — snap fills to exact brand hexes, filter extraneous paths (*"keep only the counter whose bbox contains the focal dot"*), normalize viewBox (square, trim, pad).
- **rasterize** — SVG → pristine PNG/JPG at target size with tight-crop or centered-on-canvas padding.
- **icon-pack** — one SVG → `favicon.svg` + `favicon-32x32.png` + `apple-touch-icon.png` + PWA `icon-192/512.png` + `manifest.json` wired correctly (iOS-opaque background, maskable safe area).
- **color-audit** — histogram opaque pixels per hex; fails if non-brand drift > 1%.

## Why this exists

Every brand refresh hits the same four mechanical problems between the designer's PSD/Figma output and the production-ready SVG/PNG set. Each one is easy to botch in a way that ships a 5°-off brand for years:
- One-shot vtracer outputs 200 near-hexes along antialiased edges. "Tan" becomes `#F2E9D2, #F1E8D0, #EFE5CC, …`.
- Potrace output doesn't match the brand hex and has dead sub-paths.
- ImageMagick's built-in SVG renderer is approximate and ignores `fill-rule` — you'll get filled letter counters.
- Favicon + apple-touch-icon + PWA icons have non-obvious requirements (iOS needs opaque bg, PWA maskable needs 20% safe area). Skip one, your brand looks unfinished on someone's phone.

The scripts here encapsulate what actually works. Each is runnable standalone — you don't need an agent to use them.

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install brand-and-visuals@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/brand-assets" ~/.claude/skills/brand-assets
chmod +x ~/.claude/skills/brand-assets/scripts/*.sh \
         ~/.claude/skills/brand-assets/scripts/*.py
```

Trigger it by saying things like *"vectorize this logo,"* *"generate a favicon pack,"* *"re-render the icon at 2048px with cream bg."*

## Use the scripts directly

No agent required. Plain bash + Python (stdlib only).

```bash
# End-to-end: PNG → production SVG + PNG pack
SRC=path/to/designer-source.png
BRAND=('#0E1320' '#F3EAD3' '#B85A3A')

scripts/vectorize.sh --input "$SRC" --output raw.svg --colors "${BRAND[@]}"
scripts/finalize-svg.py --input raw.svg --output logo.svg \
  --brand "${BRAND[@]}" --min-area 20
scripts/icon-pack.sh --input logo.svg --output-dir public/ \
  --bg '#F3EAD3' --brand-name 'YourBrand'
scripts/color-audit.sh public/apple-touch-icon.png --brand "${BRAND[@]}" '#F3EAD3'
```

Full option tables: [scripts/README.md](scripts/README.md).

## Prerequisites

All via Homebrew on macOS (apt / linuxbrew on Linux):

```bash
brew install librsvg imagemagick potrace
# Optional:
brew install vtracer                    # fallback for complex rasters
pipx install 'rembg[cpu]'               # background removal
```

See [reference/tools.md](reference/tools.md) for version notes.

## How the skill is structured

```
brand-assets/
├── SKILL.md              # agent entry point
├── README.md             # this file
├── reference/            # deep-dives, loaded on demand
│   ├── vectorize.md
│   ├── finalize.md
│   ├── rasterize.md
│   ├── icon-pack.md
│   └── tools.md
└── scripts/              # Runnable pipelines
    ├── vectorize.sh
    ├── finalize-svg.py
    ├── rasterize.sh
    ├── icon-pack.sh
    ├── color-audit.sh
    └── README.md
```

Per Anthropic's [skill best practices](https://code.claude.com/docs/en/skills.md): `SKILL.md` stays under 500 lines, references are one level deep, scripts handle deterministic ops (so they don't burn context tokens on every invocation).

## House rules baked in

- **Never one-shot vectorize a multi-color logo.** Always split by color mask first.
- **Always finalize after vectorize.** Raw trace output never matches brand hexes exactly.
- **Tight-crop rasters as the default.** Let consumers add their own clear space. Only bake padding in for app icons (apple-touch-icon, PWA).
- **Verify with `color-audit.sh` before shipping.** Catches drift in two seconds.

## What this skill is NOT

- A logo designer. Use [image-generation](../image-generation) for that.
- A brand book authoring tool. That's [brand-system](../brand-system).
- An Illustrator/Figma replacement. SVG is XML — if you need to edit a path, open it in Illustrator.
- A raster editor. Don't paint over a vectorized output; re-generate from the source.

## Related skills

- [brand-system](../brand-system) — the sibling that authors the brand *document*; this one produces the pixels. Run both for a complete rollout.
- [image-generation](../image-generation) — designs the logo artwork this pipeline then cleans up.

## License

MIT — see [LICENSE](../../LICENSE).

