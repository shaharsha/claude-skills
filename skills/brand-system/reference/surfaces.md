# Surfaces & materials

A web product has (almost always) two materials: a **default** for
content and a **floating** material for chrome. Every surface is one
or the other. Never mix within a single composition without reason.

## The two materials

### Paper (default)

Flat surface + hairline borders + subtle grain overlay. The default for
prose, forms, lists, dashboards, editorial content.

**Why Paper matters**: a 1–2% grain overlay on the base surface makes
it read as actual paper, not a flat Pantone. This is the
Pentagram/Shinola craft detail that separates a brand from every
generic warm-SaaS clone. One texture, applied globally, unmistakably
yours.

```css
body::before {
  content: '';
  position: fixed; inset: 0;
  pointer-events: none;
  z-index: 1;
  opacity: 0.025;
  background-image: url('/noise.png');   /* tileable 200×200 PNG */
  mix-blend-mode: multiply;
}
```

**Elevation tiers**:

| Tier | Background | Border | Shadow |
|---|---|---|---|
| Ground | `--bg` | — | — |
| Resting | `--bg-elevated` | 1px solid `--border` | none |
| Hover | `--bg-elevated` | 1px solid `--border-strong` | `0 2px 8px rgb(0 0 0 / 0.06)` |
| Modal | `--bg` | — | `0 12px 48px rgb(0 0 0 / 0.18)` |

### Liquid Glass (floating)

Apple's Liquid Glass (WWDC 2025) is the state-of-the-art material
language for floating chrome. Use it for:

- Top nav bar
- Floating buttons on hero backgrounds
- Modal overlays
- Dropdowns
- Tooltips
- Popovers

**Tune for the palette.** Standard Liquid Glass is calibrated for cool
whites. On a warm palette, apply less saturation boost and a warm tint:

```css
.glass {
  background: rgba(243, 234, 211, 0.55);   /* warm tint, not white */
  backdrop-filter: blur(24px) saturate(140%) brightness(1.06);
  -webkit-backdrop-filter: blur(24px) saturate(140%) brightness(1.06);
  border: 1px solid rgba(255, 255, 255, 0.28);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.45),   /* specular top */
    inset 0 -1px 0 rgba(14, 19, 32, 0.05),     /* contact bottom */
    0 4px 24px rgba(14, 19, 32, 0.08);         /* drop */
}
```

**Glass intensities** (Apple nomenclature):

| Class | Blur | Saturate | Use |
|---|---|---|---|
| `.glass-thin` | 12px | 130% | Toolbars over photography |
| `.glass` | 24px | 140% | Nav, dropdowns, floating CTAs |
| `.glass-thick` | 40px | 150% | Modal sheets, command palette |

### Where each material goes

| Surface | Material |
|---|---|
| Top nav bar | Glass |
| Floating CTA over photo | Glass (thin) |
| Editorial body text | Paper (ground) |
| Pricing tiles | Paper (resting) |
| Dashboard cards | Paper (resting) |
| Forms | Paper (ground + resting for sections) |
| Modals | Glass (thick) |
| Tooltips | Glass |
| Dropdowns | Glass |
| Toast | Glass |
| Command palette (⌘K) | Glass (thick) |

**Rule of thumb**: if the surface *floats over* content or needs to feel
*separate from* the page, it's glass. If the surface *is* the page,
it's paper.

## Hero backgrounds

The landing hero — and only the landing hero — is allowed a background
treatment beyond plain paper. One use per site. Never on interior
pages.

**Two canonical options**, each tuned to the brand:

1. **Colour-field wash** (pure CSS, 0KB):
   ```css
   .hero-wash {
     background:
       radial-gradient(ellipse at 10% 20%, var(--accent-translucent-hi), transparent 50%),
       radial-gradient(ellipse at 90% 80%, var(--accent-translucent-lo), transparent 50%),
       var(--bg);
   }
   ```
   Peak opacity ≤ 8%. Never literal (stars, galaxies, etc.).

2. **Atmosphere image** — a heavily blurred photographic source. Keep
   only the palette warmth; blur out all structure. See Agentleh's
   "dust field" treatment for an example.

**Hero rules**:

- One treatment per site. Not both, not rotated.
- **Theme-symmetric** pair: light version + dark version. Not `filter: invert()` — re-rendered.
- **Scrim overlay** for contrast control so typography hits WCAG AA
  regardless of which region sits behind it.
- **Mark-safe zone**: the wordmark sits in the quietest image region.

## Motion on surfaces

Paper doesn't animate (§11 motion). Glass can optionally have a
specular-highlight shift tied to cursor proximity (Apple Liquid Glass
behaviour) — up to 4° of shift, 300ms damped, desktop only, gated on
`prefers-reduced-motion`.

## Anti-patterns

- Flat frosted-glass nav bar without the specular edges (just a blurred
  bg with a border). Half of Liquid Glass, none of the depth.
- Mixing paper and glass in one card (a "glass card" with a hairline
  border *and* a drop shadow *and* a blur).
- Paper everywhere, glass nowhere — nav will feel stuck.
- Glass everywhere, paper nowhere — content will feel weightless.
- Hero background repeated on interior pages.
- Hero colour-wash with peak opacity > 10%. Reads as a gradient-mesh SaaS
  aesthetic.
