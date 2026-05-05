# Accessibility

WCAG 2.2 AA is the 2026 legal floor. Audit at authoring time, not
review time.

## Contrast floors (WCAG 2.2)

- **Body text**: 4.5:1 (AA)
- **Large text** (≥ 24px or ≥ 19px bold): 3:1 (AA)
- **UI controls, focus rings, non-text elements**: 3:1 (AA)
- **AAA** (aspirational, not legally required): 7:1 body / 4.5:1 large

Run `scripts/audit-contrast.py --bg X --fg Y --accent Z --theme both`
on the final palette. Paste the matrix into §14 of BRAND.md. Exit code
non-zero = body-text pair fails AA = palette wrong.

Expected warnings (not failures):

- Accent-on-bg often falls below 4.5:1. The accent is for CTA *fills*
  (text on accent = contrast reversed) and for the signature primitive
  (a shape, not text). Prose should never be `--accent` on `--bg`.
- Accent-on-fg at similar luminance fails too. Same rationale.

## WCAG 2.2 additions to watch (new since 2.1)

- **2.4.11 Focus Not Obscured** (AA): the focus indicator cannot be
  fully hidden by sticky headers, overlays, toasts. QA with keyboard-
  only navigation on every sticky pattern.
- **2.4.13 Focus Appearance** (AAA): focus ring ≥ 2 CSS px thick
  *around the full perimeter* with ≥ 3:1 contrast.
- **2.5.8 Target Size Minimum** (AA): 24×24 CSS px for any interactive
  target, except inline text links and user-agent defaults. Most
  `.btn-sm` specs are already at 36×36; checkbox/radio at 20×20 fail —
  bump to 24×24 or bind a larger invisible hit area.

## APCA? WCAG 3? Short answer

Use WCAG 2.2. APCA was pulled from WCAG 3 in July 2023 and hasn't
returned. WCAG 3 won't ship before 2030 and will use a Bronze/Silver/
Gold rating, not A/AA/AAA. APCA is fine as a *spot-check* for dark-mode
pairings that pass 2.2 math but feel wrong — it's not legally
defensible anywhere yet. See [Adrian Roselli's 2026 summary](https://adrianroselli.com/2026/04/wcag3-contrast-as-of-april-2026.html).

## Focus rings

```css
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-radius: inherit;
}
.btn-primary:focus-visible { outline-color: var(--color-fg); }
```

Use `:focus-visible`, not `:focus`. `:focus` fires on clicks (annoying);
`:focus-visible` only when keyboard-navigated. Tie outline color to a
semantic token so it respects theming.

## Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

The signature-primitive pulse stops. Hero wash stays (static). Page-load
reveal disappears. Cursor dot still follows the cursor but stops pulsing
on hover (never leave a user cursorless; that's an accessibility
regression).

## Forced colors (Windows high-contrast)

Windows high-contrast mode overrides all colors via `@media
(forced-colors: active)`. Specifically handle borders and focus rings:

```css
@media (forced-colors: active) {
  :root {
    --accent: CanvasText;
    --border: CanvasText;
  }
  .btn-primary {
    forced-color-adjust: none;
    border: 2px solid ButtonText;
  }
}
```

`forced-color-adjust: none` preserves brand styling where meaning depends
on colour (e.g. a brand CTA). Use sparingly — default is to let the OS
win.

## RTL equivalence

Every feature must work identically in RTL and LTR. Never ship a
feature QA'd only in one direction. See [rtl.md](rtl.md) for the rules.

In audit terms:

- Logical properties everywhere (`padding-inline-start`, not `padding-left`).
- Directional icons mirrored; semantic icons not.
- Numbers stay LTR inside RTL prose.
- Screen-reader order matches visual order in both directions.

## Target-size exceptions

24×24 is the AA floor, but some exceptions apply:

- **Inline text links** in a run of prose — exempt.
- **User-agent defaults** (`<input type="radio">` at browser default) —
  exempt.
- **Essential** targets where a smaller size is required (think color
  picker pixel, chess-board square) — exempt.

For close-but-small targets (16×16 icon buttons), expand the hit area
without enlarging the visible icon:

```css
.icon-btn {
  position: relative;
  width: 16px; height: 16px;
}
.icon-btn::before {
  content: '';
  position: absolute;
  inset: -8px;   /* 32×32 effective hit area */
}
```

## Checklist before shipping

- [ ] `audit-contrast.py --theme both` exits 0.
- [ ] Every focus ring passes 3:1 against every surface it appears on.
- [ ] Keyboard-only navigation reaches every interactive element, in
      logical order.
- [ ] `prefers-reduced-motion: reduce` path tested.
- [ ] `forced-colors: active` path tested (Windows HCM or Chrome
      DevTools emulation).
- [ ] RTL QA pass if the product ships in Hebrew/Arabic.
- [ ] Target-size 24×24 audit on every `.btn-sm` / checkbox / radio.
- [ ] Focus-not-obscured test on every sticky header / toast / modal.

## Anti-patterns

- Using APCA as the primary audit. Not legally defensible; use 2.2 AA.
- `outline: none` without replacement. Banned.
- Colour alone to convey meaning (status pips without icons, form
  errors with only red text).
- `role="button"` on a non-button. Use `<button>`.
- Ignoring `forced-colors: active`. Windows HCM has ~4% penetration;
  not edge-case.
- Motion without reduced-motion fallback.
- Target sizes below 24×24 without expanded hit area.
