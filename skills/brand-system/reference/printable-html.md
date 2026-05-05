# The printable `BRAND.html` + `BRAND.pdf`

Why this artifact exists:

- **Figma files rot**; an HTML file in the repo is durable, diffable,
  reproducible in CI, and free.
- **Stakeholders need a PDF** to forward to investors, partners, designers,
  printers. A 20-page markdown file is not shareable.
- **The brand book should look like the brand** on page 1. An HTML sibling
  using the brand's own palette and typography proves the rules.

## Structure (what `BRAND.html.tmpl` emits)

7 A4 pages, in order:

| Page | Content |
|---|---|
| 1 | **Cover** — dark/atmospheric background, wordmark, one-line positioning as h1, stamp/year |
| 2 | **§0 The idea** — "Strip everything else" + positioning + the signature-primitive one-liner |
| 3 | **§1 The mark** — 2×2 grid of mark variants (light/dark × with/without wordmark) |
| 4 | **§2 The signature primitive** — hero shape on its own page + 8-use grid |
| 5 | **§6 Colors** — 3 hero swatches (core) + mini-grid (semantic) with hex values |
| 6 | **§7 Typography** — type-scale ladder with samples at each tier, in brand language |
| 7 | **Usage — Do & Don't** — two columns, green ✓ / red ✗, "source of truth" callout |

Not 20 pages — the distillation is the point. A 7-page PDF everyone
reads beats a 20-page PDF nobody does.

## How the rendering works

```bash
scripts/render-pdf.sh BRAND.html BRAND.pdf
```

Chrome headless with:

```
--headless=new
--disable-gpu
--no-pdf-header-footer
--hide-scrollbars
--run-all-compositor-stages-before-draw
--virtual-time-budget=5000
--print-to-pdf=$OUTPUT
```

`--virtual-time-budget=5000` gives fonts time to load before the PDF
snapshot. Without it, Chrome sometimes races and renders fallback
fonts.

## Critical CSS rules in the template

```css
@page { size: A4; margin: 0; }

html, body {
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

.page {
  width: 210mm;
  height: 297mm;
  padding: 22mm 24mm;
  page-break-after: always;
}
.page:last-child { page-break-after: auto; }
```

`print-color-adjust: exact` forces the browser to render brand colours
at the hex specified, not the printer-friendly desaturated version.

## Typography at print size

Point sizes, not rem. Print units behave differently:

```
h1        48pt
h2        28pt
h3        13pt
body      10.5pt
lead      14pt
eyebrow   10pt (uppercase, letter-spacing)
muted     9pt
footer    8.5pt
```

Line-height 1.55 for body, 1.1 for display. Tight tracking on h1/h2
(`letter-spacing: -0.01em`) makes print headlines cohere.

## Assets in the printable

**Images**: reference with **relative paths**, not absolute. The
rendered HTML expects assets at `public/brand/…` relative to the HTML
file's location. Chrome headless follows `file://` relative refs fine
if the paths resolve.

**Fonts**: Google Fonts via `<link>` works in headless Chrome. If you
need self-hosted fonts, place them at the same path structure you'd
use in production and the same URLs will resolve.

## Light-to-dark signature on the cover

The cover page should use the brand's dark surface to immediately
establish the product has a dark-mode identity (§10 dark-mode narrative).
The `BRAND.html.tmpl` template ships with a cosmic-gradient cover
using the brand accent as highlights:

```css
.cover {
  background-image:
    radial-gradient(ellipse at 15% 70%, <accent>22 0%, transparent 45%),
    radial-gradient(ellipse at 85% 80%, <accent>14 0%, transparent 40%),
    linear-gradient(180deg, <fg> 0%, <fg-700> 100%);
}
```

Cream/light brands can invert this; the principle is "cover looks
distinctly different from interior pages, using the brand's palette."

## Regeneration workflow

When the brand changes:

1. Update `BRAND.md` tokens and prose first.
2. Re-run `scripts/extract-tokens.py --input BRAND.md --format tailwind-v4 > tokens.css`.
3. Update `BRAND.html` directly (it has its own inline styles — the
   tokens are copied from `tokens.css`; keep them in sync).
4. `scripts/render-pdf.sh BRAND.html BRAND.pdf` to regenerate the PDF.
5. Commit all four: `BRAND.md`, `BRAND.html`, `tokens.css`, `BRAND.pdf`.

## Anti-patterns

- Editing `BRAND.html` and forgetting `BRAND.md` — the long-form doc
  is source of truth, the printable distills.
- Using absolute URLs for assets; breaks offline PDF rendering.
- 20-page printable. Nobody reads it. 6–7 pages is the ceiling.
- Generic cover (black + white + "Brand Book" in Helvetica). The cover
  is the first proof the book walks the talk.
- Shipping only the PDF, not the HTML. The HTML is diffable; the PDF is
  rendered output.
