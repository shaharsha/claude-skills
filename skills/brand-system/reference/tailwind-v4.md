# Tailwind v4 `@theme` — the 2026 token consumption layer

Tailwind v4's `@theme` block consumes CSS custom properties directly
and generates utility classes from them. No `tailwind.config.js`
round-trip. The brand's `tokens.css` is authored once and drives both
the utility classes and the runtime CSS variables.

See [Tailwind v4 theme docs](https://tailwindcss.com/docs/theme) for the
full namespace list.

## The split: `@theme` vs `:root` vs `[data-theme="dark"]`

```css
@theme {
  /* Primitives — the design tokens that become utility classes */
  --color-cream: #F3EAD3;
  --color-navy: #0E1320;
  --color-terracotta: #B85A3A;

  --font-sans: 'Rubik', system-ui, sans-serif;

  --spacing-4: 1rem;
  --spacing-8: 2rem;

  --radius-md: 10px;
  --radius-lg: 14px;

  --duration-fast: 150ms;
  --duration-base: 200ms;

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

/* Light-mode semantics — tier 2 */
:root {
  --bg:          var(--color-cream);
  --bg-elevated: var(--color-cream-50);
  --text:        var(--color-navy);
  --border:      var(--color-cream-200);
  --accent:      var(--color-terracotta);  /* ← constant across themes */
}

/* Dark-mode override — same keys, different primitives */
[data-theme="dark"] {
  --bg:          var(--color-navy-900);
  --bg-elevated: var(--color-navy-700);
  --text:        var(--color-cream);
  --border:      var(--color-navy-500);
  --accent:      var(--color-terracotta);  /* ← still the same */
}

/* System fallback when no explicit theme attribute */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:          var(--color-navy-900);
    --bg-elevated: var(--color-navy-700);
    --text:        var(--color-cream);
    --border:      var(--color-navy-500);
  }
}
```

**Rule of thumb**:

- `@theme` = things that should generate utility classes (`bg-cream`,
  `text-navy`, `rounded-md`, `p-4`). Primitives + scale values.
- `:root` = runtime/contextual values that should NOT generate a
  utility. Dark-mode overrides, user preferences.

## Namespaces Tailwind v4 auto-generates from `@theme`

- `--color-*` → `bg-*`, `text-*`, `border-*`, `ring-*`, `fill-*`, `stroke-*`, etc.
- `--font-*` → `font-*`
- `--text-*` → `text-*` sizes
- `--font-weight-*` → `font-*` weights
- `--tracking-*` → `tracking-*`
- `--leading-*` → `leading-*`
- `--spacing-*` → `p-*`, `m-*`, `gap-*`, etc.
- `--radius-*` → `rounded-*`
- `--shadow-*` → `shadow-*`
- `--ease-*` → `ease-*`
- `--duration-*` → `duration-*`
- `--blur-*` → `blur-*`
- `--breakpoint-*` → `md:`, `lg:`, custom
- `--container-*` → `container-*`

## `@theme inline` — when a theme var references another CSS var

If a `@theme` value contains `var(--another)`, use `@theme inline { }`
to avoid double-hop resolution issues:

```css
@theme inline {
  --color-accent-hover: color-mix(in oklch, var(--color-terracotta), black 10%);
}
```

Without `inline`, Tailwind inserts the var name as-is into generated
utilities; the browser then has to resolve it twice.

## The reset idiom

Wipe Tailwind's default slate/blue/green ramps to prevent them leaking
into a brand-first project:

```css
@theme {
  --color-*: initial;   /* wipe all default colors */
  --color-cream: #F3EAD3;
  --color-navy: #0E1320;
  /* ... */
}
```

Or, more aggressive:

```css
@theme {
  --*: initial;         /* nuke everything */
  /* start from scratch */
}
```

Useful when you want no Tailwind defaults at all — only your brand
tokens.

## Dark mode activation

Tell Tailwind which selector controls dark-mode utilities:

```css
@import "tailwindcss";
@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));
```

Now `dark:bg-navy` fires when `[data-theme="dark"]` is set on any
ancestor. Combine with the media-query fallback in `:root` for
system-preference-first behaviour.

## Integration with the brand-system skill

When `scripts/new-brand-book.sh` runs, it emits `tokens.css` with:

1. An `@theme` block containing primitives + scale values.
2. A `:root { }` block with light-mode semantics.
3. A `[data-theme="dark"] { }` block with dark-mode overrides.
4. The `@media (prefers-color-scheme: dark)` fallback.
5. Body defaults (`-webkit-font-smoothing: auto`, RTL line-height).
6. The signature-primitive animation keyframe.
7. `prefers-reduced-motion: reduce` guards.
8. `forced-colors: active` handling.

Drop `tokens.css` into `src/index.css` (landing + app) via
`@import './tokens.css';` at the top of the file. Everything else —
utility classes, custom CSS — composes on top.

## Anti-patterns

- Using `tailwind.config.js` with Tailwind v4. It's deprecated; use
  `@theme`.
- Putting dark-mode colour values in `@theme`. They belong in
  `[data-theme="dark"]` because they shouldn't generate utility classes.
- Referencing primitives directly in components (`class="bg-cream"`
  instead of `class="bg-bg"`). Route through semantic tokens so theming
  works.
- Forgetting the `@media (prefers-color-scheme: dark)` fallback. Without
  it, dark mode only works for explicit user overrides.
