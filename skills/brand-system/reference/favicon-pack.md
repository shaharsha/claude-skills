# Favicon + PWA icon pack — system-aware

This reference specs the **requirements** for the full icon pack that
lives alongside a brand book. Actual generation is handled by
[brand-assets](../../brand-assets/SKILL.md) (`icon-pack.sh`).

## The full manifest

| File | Size | Bg | Dark-aware | Notes |
|---|---|---|---|---|
| `favicon.svg` | vector | transparent | **yes — via embedded `<style>@media`** | Modern browsers (Chrome 111+, Firefox, Safari) |
| `favicon.ico` | 32×32 + 16×16 | transparent | no | IE/legacy fallback |
| `favicon-32x32.png` | 32×32 | transparent | no | Browsers that don't render SVG favicons |
| `apple-touch-icon.png` | 180×180 | **opaque** brand surface | no | iOS auto-rounds corners, refuses transparency |
| `icon-192.png` | 192×192 | transparent | no | PWA home-screen |
| `icon-512.png` | 512×512 | transparent | no | PWA splash + large surfaces |
| `icon-192-maskable.png` | 192×192 | opaque, 20% safe-area padding | no | Android may mask to any shape |
| `icon-512-maskable.png` | 512×512 | opaque, 20% safe-area padding | no | Same, larger |
| `og-image.png` (light) | 1200×630 | opaque brand surface | — | Social card for light-mode platforms |
| `og-image-dark.png` | 1200×630 | opaque dark brand surface | — | Discord, dark-mode Twitter/LinkedIn |
| `manifest.json` | — | — | — | Lists the above; `theme_color` and `background_color` |

## The system-aware SVG favicon (2026 move)

A single SVG favicon renders differently per system preference via an
embedded `<style>` block. Most brand books miss this.

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <style>
    .fg     { fill: #0E1320; }  /* navy in light mode */
    .accent { fill: #B85A3A; }  /* terracotta — theme-constant */
    @media (prefers-color-scheme: dark) {
      .fg   { fill: #F3EAD3; }  /* swap to cream on dark system */
    }
  </style>
  <path class="fg" d="…mark geometry…"/>
  <circle class="accent" cx="40" cy="24" r="4"/>
</svg>
```

**The accent stays constant** — that's the parity rule from
[color.md](color.md). Only the fg-ish fills swap. One SVG file, two
renders, zero JavaScript.

Refuse static-only favicons for brands that have both a dark and light
primary surface. It's a small detail that separates finished from
unfinished.

## iOS apple-touch-icon — opaque only

iOS auto-rounds corners and **refuses transparent backgrounds**. If the
icon has transparency, iOS fills it with black. Use an opaque brand
surface (`--color-bg` on light, `--color-fg` on dark doesn't matter —
pick one and commit).

- **Size**: 180×180.
- **Safe area**: 10% margin inside the 180px square (the mark should
  occupy the inner 162×162).
- **Corners**: iOS rounds to ~18% corner radius. Don't pre-round.
- **No transparency anywhere.**

## PWA maskable icons — 20% safe-area padding

Android's "maskable" icon spec lets the OS crop the icon to any shape
(circle, squircle, rounded rectangle, teardrop). Without safe-area
padding, the mark gets clipped.

```
┌─────────────────────────────┐
│     ░░░░ safe area ░░░░░    │
│   ┌───────────────────────┐ │   outer 20% = safe area
│   │                       │ │   inner 80% = mark lives here
│   │      [mark]           │ │
│   │                       │ │
│   └───────────────────────┘ │
│     ░░░░░░░░░░░░░░░░░░░░    │
└─────────────────────────────┘
```

Both `icon-192-maskable.png` and `icon-512-maskable.png` need this
padding. `purpose: "maskable"` in `manifest.json` tells Android it's
safe to crop.

## Theme-color meta tags

Browser chrome (Safari address bar, Chrome Android bar, PWA title bar)
tints from these:

```html
<meta name="theme-color" content="#F3EAD3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0E1320" media="(prefers-color-scheme: dark)">
```

Without the `media` variants, one of the two system themes gets a
clashing chrome colour. Ship both.

## OG image — light + dark pair

Social platforms increasingly respect dark mode. Ship two OG cards:

- `og-image.png` — light brand surface, wordmark + positioning. Used on
  LinkedIn, Twitter light-mode, most email clients.
- `og-image-dark.png` — dark brand surface, same content. Used on Discord
  (always dark), Slack dark-mode, Twitter dark-mode where supported.

Serve via `<meta property="og:image">` + `<meta name="twitter:image">`.
Some platforms don't yet respect `prefers-color-scheme` in OG — you may
have to pick one as default and serve the other via `<meta name="og:image" media="(prefers-color-scheme: dark)">`. Test per-platform.

## manifest.json minimal

```json
{
  "name": "{{PRODUCT}}",
  "short_name": "{{PRODUCT_SHORT}}",
  "theme_color": "#F3EAD3",
  "background_color": "#F3EAD3",
  "display": "standalone",
  "scope": "/",
  "start_url": "/",
  "icons": [
    { "src": "/icon-192.png",          "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/icon-512.png",          "sizes": "512x512", "type": "image/png", "purpose": "any" },
    { "src": "/icon-192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

## HTML head snippet (full)

```html
<!-- Light/dark SVG favicon -->
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<!-- PNG fallback -->
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<!-- Legacy ICO fallback -->
<link rel="shortcut icon" href="/favicon.ico">
<!-- iOS home-screen -->
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<!-- PWA -->
<link rel="manifest" href="/manifest.json">
<!-- Browser chrome tint -->
<meta name="theme-color" content="#F3EAD3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0E1320" media="(prefers-color-scheme: dark)">
<!-- OG -->
<meta property="og:image" content="/og-image.png">
<meta name="twitter:image" content="/og-image.png">
```

## Checklist

- [ ] `favicon.svg` with `prefers-color-scheme` dark-mode swap.
- [ ] `apple-touch-icon.png` opaque, 180×180, no transparency.
- [ ] `icon-192.png` and `icon-512.png` with transparent bg.
- [ ] `icon-192-maskable.png` and `icon-512-maskable.png` with 20%
      safe-area padding.
- [ ] `og-image.png` and `og-image-dark.png` at 1200×630.
- [ ] `manifest.json` lists all icons with correct `purpose`.
- [ ] Both `theme-color` meta tags.
- [ ] Ran `scripts/color-audit.sh` (from brand-assets) to confirm PNGs
      use only brand hexes.
