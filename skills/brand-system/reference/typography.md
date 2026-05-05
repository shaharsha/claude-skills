# Typography — scale, measure, pairing

## Editorial, not SaaS

The default web type scale (especially anything defaulting to Inter at
16px / 1.5) reads as "dashboard." A brand-first product earns presence
from typography that looks composed, not configured.

- **Measure 45–75ch** for body prose (narrower than Tailwind's default
  prose). Wide measures feel dashboard-y; narrow measures feel
  considered.
- **Line-height 1.75** for Latin body; **1.8** for Hebrew/Arabic
  (heavier descenders need air).
- **Tabular numerals** for prices, stats, data tables:
  `font-variant-numeric: tabular-nums`.
- **Semantic scale roles**, not just sizes — `mega / display / h1 / h2 /
  h3 / lead / body / ui / micro`. Uber Base's "Go Big / Less is More /
  Simple Semantics" is the clearest public model.

## The scale

```
--text-mega    = clamp(3rem, 12vw, 12rem)          / LH 0.95 / 700   — hero, once per page max
--text-display = clamp(2.5rem, 5vw + 1rem, 4.5rem) / LH 1.05 / 700   — section heroes
--text-h1      = clamp(2rem, 3vw + 1rem, 3rem)     / LH 1.10 / 700   — page titles
--text-h2      = clamp(1.5rem, 2vw + .75rem, 2.25rem) / LH 1.15 / 600
--text-h3      = clamp(1.25rem, 1vw + 1rem, 1.5rem)   / LH 1.20 / 600
--text-lead    = clamp(1.125rem, .5vw + 1rem, 1.375rem) / LH 1.55 / 400
--text-body    = 1rem                              / LH 1.75 / 400
--text-body-sm = .875rem                           / LH 1.55 / 400
--text-ui      = .9375rem                          / LH 1.40 / 500
--text-micro   = .75rem                            / LH 1.30 / 500
```

`--text-mega` fires exactly once per page — the landing hero — and
nowhere else. Using it on an interior page shouts.

## Font smoothing (non-negotiable)

```css
body { -webkit-font-smoothing: auto; }
```

**Never** `antialiased`. It renders heavier scripts (Hebrew, Arabic,
Devanagari) unreadably thin on low-DPI Android Chrome. This isn't a
preference, it's an accessibility floor on cheap devices.

## Mobile minimum font size (iOS Safari)

**16px minimum** on mobile form inputs. Anything smaller triggers iOS
Safari auto-zoom on focus, which jumps the layout. Non-negotiable on
any input field.

## Pair a display face with a body face — carefully

Default: one face across display and body. Rubik, Inter, Source Serif,
Söhne all handle both. One family = one brand voice = less drift.

Two-face pairing (display serif + body sans, or display sans + body
serif) works when the brand wants editorial feeling. Examples:

- New York Times Magazine: Cheltenham + Franklin Gothic
- Stripe: Söhne + something else subtle
- Agentleh: Rubik for both (one family, wide weight range, Hebrew+Latin parity)

**Red flag**: three or more faces. That's decoration, not typography.

## RTL typography

See [rtl.md](rtl.md) for the full list. The type-specific moves:

- Looser line-height (1.8 vs 1.75).
- **No letter-spacing** — Hebrew/Arabic lose legibility fast.
- No italics — neither script has an italic tradition; use weight or
  colour instead.
- Numbers stay LTR inside RTL prose. Wrap in `<bdi>` for ambiguous
  edge cases.
- Drop caps in Hebrew look great and have historical precedent; in
  Arabic they look weird (ligature/shaping rules). Know the script.

## The wordmark treatment

When the brand name appears inline in running text, treat it as one
object:

```css
.wordmark {
  font-weight: 700;
  letter-spacing: -0.015em;
  white-space: nowrap;
  font-feature-settings: "kern" 1;
}
```

Never all-caps. Never title-case. Set the rule in §5 of BRAND.md and
never relitigate it.

## Font-loading strategy

`font-display: swap`. FOUT is better than FOIT for perceived performance
and for accessibility (unstyled text is still readable).

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
```

Self-host if contract size allows — cuts a third-party DNS hop and
makes the font part of your CDN cache policy.

## Anti-patterns

- Three or more type families.
- `-webkit-font-smoothing: antialiased` on body (unreadable Hebrew on Android).
- Letter-spacing on Hebrew or Arabic (legibility destroyer).
- Below 16px on mobile form inputs (triggers iOS zoom).
- `--text-mega` on more than one surface per site.
- All-caps wordmark.
- Italicising Hebrew or Arabic.
