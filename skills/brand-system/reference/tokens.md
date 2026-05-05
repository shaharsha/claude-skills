# Design token architecture

The 2026 canonical stack: three-tier tokens expressed in W3C DTCG JSON,
compiled by Style Dictionary, consumed in Tailwind v4 via `@theme`.

## Three tiers (Nathan Curtis taxonomy)

| Tier | Purpose | Example | Consumed by |
|---|---|---|---|
| **1. Primitive** | Raw values, no semantics | `color.navy.900 = #0E1320`, `space.8 = 32px` | Nobody directly — always routed through tier 2 |
| **2. Semantic / alias** | Purpose-driven, themeable | `color.bg.default → color.navy.900` (dark) / `color.cream.50` (light) | Components, patterns |
| **3. Component** | Component-scoped overrides (optional) | `button.primary.bg = color.action.primary` | The component only |

**Only tier 2 changes between themes.** Tier 1 is fixed. Tier 3 inherits.
That's the invariant that makes theming work. See Nathan Curtis's
[Naming Tokens in Design Systems](https://medium.com/eightshapes-llc/naming-tokens-in-design-systems-9e86c7444676)
for the full taxonomy.

## In this skill

- `@theme { --color-*: ... }` in `tokens.css` → tier 1 primitives.
- `:root { --bg: var(--color-cream); ... }` → tier 2 light semantics.
- `[data-theme="dark"] { --bg: var(--color-navy-900); ... }` → tier 2 dark semantics.
- Components consume `var(--bg)`, not `var(--color-cream)`. Always.
- The accent token in tier 2 is **identical** across both themes. Parity rule.

## W3C DTCG format (stable 2025-10-28)

```json
{
  "color": {
    "cream":      { "$value": "#F3EAD3", "$type": "color", "$description": "Primary light surface" },
    "navy":       { "$value": "#0E1320", "$type": "color" },
    "terracotta": { "$value": "#B85A3A", "$type": "color", "$description": "Accent — only saturated colour; constant across themes" }
  },
  "spacing": {
    "4": { "$value": "16px", "$type": "dimension" }
  }
}
```

`$value` is required. `$type` required unless inherited from a parent
group. `$description` optional but recommended. Aliases use curly-brace
syntax: `"{color.cream}"`.

`scripts/extract-tokens.py --format dtcg` emits this format from a
BRAND.md so you can round-trip into Tokens Studio or Style Dictionary.

## Naming conventions (Curtis axes)

`[namespace]-[category]-[concept]-[property]-[variant]-[state]-[scale]-[mode]`

Use only the axes you need — "purposeful incompleteness" is a feature.

- **Namespace** prepended (e.g. `agl-color-bg-default`). Skip if
  single-tenant.
- **Category**: `color`, `space`, `radius`, `font`, `duration`.
- **Concept**: `bg`, `fg`, `border`, `accent`, `text`.
- **Property**: `default`, `hover`, `active`, `disabled`.
- **State**: `focus-visible`, `pressed`.
- **Scale**: `50, 100, 200, ..., 900` for ramps.
- **Mode**: `light`, `dark` — prefer routing through semantic tier
  instead of token name.

Promote a component-scoped token (tier 3) to semantic (tier 2) **only
when ≥3 components need it**. Before that, keep it local.

## Anti-patterns

- **Skipping tiers.** `button.primary.bg = #B85A3A` (component →
  primitive, no semantic layer) locks you out of theming. Always route
  through tier 2.
- **Primitives with semantic names.** `--color-brand = #B85A3A` sounds
  semantic but isn't — what does "brand" mean when the brand has three
  colours? Use `--color-terracotta` (primitive, named by what it *is*)
  and `--accent` (semantic, named by what it *does*).
- **Mixing modes in token names.** `--color-bg-light = #F3EAD3` and
  `--color-bg-dark = #0E1320` as separate tokens means components must
  know which mode they're in. Instead, have one `--bg` semantic token
  that swaps primitives per `[data-theme]`.
- **Missing `$description` for primitives with ambient meaning.** If a
  colour has a story (the Antennae palette), put it in `$description`
  so it survives the round-trip through Style Dictionary.

## Pipeline (2026 canonical)

```
Figma variables (Tokens Studio)
      ↓ GitHub sync
tokens.json (DTCG format)
      ↓ Style Dictionary transforms
      ├─→ CSS custom properties
      ├─→ Tailwind v4 @theme block
      └─→ iOS/Android native (xcassets / xml)
```

Tailwind v4's `@theme` block consumes CSS custom properties directly
and generates utility classes from them — no `tailwind.config.js`
round-trip needed. See [tailwind-v4.md](tailwind-v4.md) for details.

## References

- [Nathan Curtis — Naming Tokens in Design Systems](https://medium.com/eightshapes-llc/naming-tokens-in-design-systems-9e86c7444676)
- [W3C DTCG Format Module](https://tr.designtokens.org/format/)
- [Style Dictionary — DTCG support](https://styledictionary.com/info/dtcg/)
- [Tailwind v4 theme docs](https://tailwindcss.com/docs/theme)
