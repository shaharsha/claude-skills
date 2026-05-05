# Colour system — construction & rules

## Start from a story, not a vibe

Every durable palette has a source that isn't a mood board. Agentleh's
palette comes from a Hubble photograph of the Antennae Galaxies. Stripe
draws colours from sunset observation. Patagonia pulls from specific
mountain ranges. *The source constrains the palette.*

Without a source you get committee-driven drift: someone says "warmer,"
someone else says "cooler," and six months later the brand is nothing.

## Core + accent + neutrals

A complete palette needs:

- **1 primary surface** (`--color-bg`) — the default background, 62% of any screen
- **1 primary ink** (`--color-fg`) — default type colour on the surface
- **1 accent** (`--color-accent`) — the *one* saturated colour, ≤ 8% of any screen
- **A neutral ramp** (5 steps of the bg colour, 4 steps of the fg colour) — borders, dividers, muted text, elevated surfaces
- **4 semantic colours** — success, warning, danger, info, tuned *inside* the palette (not bootstrapped from Bootstrap blue/red/green)

That's 13–15 tokens at the primitive tier. More than that is usually
noise; less is usually missing surface or semantic tokens.

## The 62/30/8 rule

Every screen breaks down roughly:

- **~62% surface** (bg or fg, depending on theme)
- **~30% neutrals** (text, borders, secondary surfaces)
- **~8% accent** (CTAs, brand moments, signature primitives)

When a screen feels "too branded," the accent is over 8%. Pull back.

## The light/dark parity rule

**The accent colour stays identical across light and dark modes.** Only
surface and text semantic tokens swap. The brand's one saturated
pigment is its one saturated pigment regardless of theme.

This is what makes the signature primitive *mean the same thing*
regardless of system preference. Without it, the accent becomes two
different brand marks — one per theme.

```css
:root {
  --bg: var(--color-cream);
  --text: var(--color-navy);
  --accent: var(--color-terracotta);  /* ← */
}
[data-theme="dark"] {
  --bg: var(--color-navy-900);
  --text: var(--color-cream);
  --accent: var(--color-terracotta);  /* ← same */
}
```

## Dark mode as narrative, not inversion

Dark mode isn't `filter: invert()`. The story changes:

- Agentleh dark-mode narrative: *"the agent works overnight."*
- Linear dark-mode narrative: same product, less visual noise.
- Stripe dark-mode narrative: a different material on the same shelf.

Re-render hero imagery per theme, don't flip. Inverting destroys
warmth: navy-in-light should be `#0E1320`, cream-in-dark should be
`#F3EAD3` — not the inverse of the other.

## System preference, not a toggle

Follow `prefers-color-scheme` by default; persist an explicit user
override in `localStorage`. A visible dark-mode toggle in the nav is an
anti-pattern — it suggests both modes are equally valid landing
experiences. One is the default per user preference; the other is the
fallback.

```js
const stored = localStorage.getItem('theme');
if (stored) document.documentElement.dataset.theme = stored;
// else: rely on @media (prefers-color-scheme: dark) in CSS
```

## Semantic colours — tuned inside the palette

Don't use Bootstrap green/red/blue. They won't match the warmth (or
coolness) of the brand palette. Derive semantic colours by mixing toward
the accent:

- Agentleh `--success = #6B8E5A` (moss, not Bootstrap green) — sits next
  to terracotta naturally
- Agentleh `--warning = #D4A24A` (warm amber, not Bootstrap yellow)
- Agentleh `--danger = #A83E2E` (deeper terracotta, not Bootstrap red)
- Agentleh `--info = #6D8BA6` (muted starlight blue)

`scripts/new-brand-book.sh` auto-derives a semantic ramp for new brands
by mixing Bootstrap-ish base hues toward the accent.

## Contrast — audit before shipping

`scripts/audit-contrast.py` runs every palette pair through WCAG 2.2
AA / AAA math. See [accessibility.md](accessibility.md).

Common finding: **accent-on-bg fails body-text AA** (below 4.5:1).
That's usually correct — the accent is used for CTA *fills* (text on
accent) and for the signature primitive (a shape, not text). Prose text
should always be fg-on-bg, which almost always hits AAA. The auditor
warns but doesn't fail for accent-on-bg pairs.

## Anti-patterns

- **Rainbow semantic tokens.** If your brand has 8 named colours, it has
  no palette.
- **Bootstrap-ish green/red/blue for semantic.** Tune inside your
  palette instead.
- **Two accents.** The "single saturated colour" rule exists because
  two accents compete. If you have two, one is decoration.
- **Colour that shifts across themes.** Breaks the parity rule.
- **Pure white as a brand colour.** White is for input fields and
  inline `code`. Use `--color-bg-50` for the "lightest surface" slot.
