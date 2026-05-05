# Tools — install + quirks

All scripts assume these are on `$PATH`. macOS / Homebrew recommended.

## Required

| Tool | Install | What it does | Notes |
|---|---|---|---|
| `rsvg-convert` (librsvg) | `brew install librsvg` | SVG → PNG renderer | Only SVG renderer that respects fill-rule correctly. ImageMagick's built-in SVG is NOT acceptable for brand work. |
| `magick` / ImageMagick | `brew install imagemagick` | Mask ops, composite, trim, color audits | v7+ required. Commands use `magick`, not legacy `convert`. |
| `potrace` | `brew install potrace` | 1-color raster → SVG tracer | Rock-solid since 2001. Outputs `fill-rule: nonzero` by default. |
| Python 3.10+ | usually pre-installed | finalize-svg.py + combine-traces.py | No deps beyond stdlib. |

## Optional

| Tool | Install | What it does | When to use |
|---|---|---|---|
| `vtracer` | `brew install vtracer` or `cargo install vtracer` | Multi-color raster → SVG tracer | Fallback for complex illustrative rasters. Always run output through finalize-svg.py. |
| `rembg` | `pipx install rembg[cpu]` (or `pip install`) | Background removal | Only if source PNG has a non-transparent background. First-run downloads ~170 MB model. |
| Google Chrome headless | macOS ships with Chrome in `/Applications` | HTML → PDF (for brand books) | Only for the one-off brand book use case; not wired into the core skill. |

## Version quirks

- **ImageMagick v6 vs v7**: scripts target v7 (`magick ...`). If a user has v6 (`convert ...`), scripts will fail. Check with `magick --version`; upgrade via `brew upgrade imagemagick` if needed.
- **rsvg-convert** version differences: behavior is stable across 2.40+. If text isn't rendering in embedded `<text>` elements, the Homebrew build may lack Pango — try `brew reinstall librsvg` or check `rsvg-convert --version` output for "Pango" support. For our brand pipelines, we don't use SVG `<text>` elements, so Pango is optional.
- **potrace** input limits: potrace reads PBM (binary bitmap) only. ImageMagick handles the PNG→PBM conversion in `vectorize.sh`. If you pipe a PNG directly you'll get cryptic errors.
- **rembg** model variants: default is `u2net` (general-purpose). For logos on plain backgrounds, `u2netp` (lighter, smaller model) is often enough and is 3-5× faster. Pass `-m u2netp` to `rembg i`.

## Smoke-test (run once after install)

```bash
rsvg-convert --version
magick --version | head -1
potrace --version | head -1
python3 --version
# Optional:
vtracer --help 2>&1 | head -1 || echo 'vtracer: not installed (optional)'
rembg --version 2>&1 | head -1 || echo 'rembg: not installed (optional)'
```

If any Required line fails, stop and install before running pipelines.

## What we DON'T need

- Inkscape / Illustrator / Figma CLI — SVGs are plain XML, we manipulate them directly.
- Node/npm — no JS tooling in the scripts.
- Docker — all tools run native.
- Ghostscript — only needed if you're reading PDFs (use `pdftoppm` from `poppler` instead).
