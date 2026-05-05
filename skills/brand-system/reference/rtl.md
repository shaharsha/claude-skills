# RTL (Hebrew / Arabic) — foundation, not appendix

Retrofitting RTL is 10–50× more expensive than designing for it upfront.
For a Hebrew-first or Arabic-first product, these rules are
non-negotiable from day one.

## CSS logical properties — the single biggest rule

Use direction-agnostic properties everywhere:

| Never | Always |
|---|---|
| `padding-left` | `padding-inline-start` |
| `padding-right` | `padding-inline-end` |
| `margin-top` | `margin-block-start` |
| `margin-bottom` | `margin-block-end` |
| `left: 0` | `inset-inline-start: 0` |
| `right: 0` | `inset-inline-end: 0` |
| `border-left` | `border-inline-start` |
| `text-align: left` | `text-align: start` |
| `float: left` | `float: inline-start` |

Logical properties flip automatically based on `dir` and `writing-mode`.
A single `<html dir="rtl">` inverts the entire layout without touching
any other CSS. This is the load-bearing move.

Enforce in code review. Anything in `padding-left` is a bug.

## Tokens stay direction-agnostic

```css
/* ✓ Good: direction-free */
--space-inline-sm: 8px;
--space-block-sm: 4px;

/* ✗ Bad: locks to LTR */
--space-left-sm: 8px;
--space-right-sm: 4px;
```

If a token name says "left" or "right", it's wrong. Use `start`/`end`
or `inline`/`block`.

## Directional icons mirror; semantic icons do not

```css
/* Mirror arrows, chevrons, send/reply, undo/redo */
[dir="rtl"] .icon-flip { transform: scaleX(-1); }
```

Flip:
- arrows (← →)
- send, reply, forward
- undo, redo
- chevrons used for "next"

Don't flip:
- search (loupe — symmetric)
- user, profile
- check, x, plus, minus
- clock (numbers stay readable)
- photo, camera

When in doubt: does flipping change its meaning? No → don't flip. Yes →
flip.

## Bidi text — handle mixed-script runs

Hebrew/Arabic sentences often contain embedded English (brand names,
numbers, URLs, code). The Unicode Bidi Algorithm handles most of it,
but edge cases bite:

- **Numbers stay LTR** inside RTL prose. This is fine by default but
  ambiguous punctuation (dates with hyphens, phone numbers) sometimes
  renders backwards. Wrap in `<bdi>`:
  ```html
  <p>הטלפון שלי הוא <bdi dir="ltr">+972-50-123-4567</bdi>.</p>
  ```
- **Quotation marks** around English inside Hebrew — use `<bdi>` or
  explicit `dir="ltr"` span.
- **Code spans** (`monospace`) — the monospace font usually has a bidi
  override, but inline code should still be wrapped in `<code dir="ltr">`
  for safety.

## Type moves Latin doesn't get

See [typography.md](typography.md) for the full list.

- Looser line-height (1.8 vs 1.75) — heavier descenders.
- **No letter-spacing** — Hebrew/Arabic lose legibility when
  letter-spaced.
- No italics — neither script has an italic tradition. Use weight
  or colour instead.
- Hebrew drop caps on long-form prose — historical precedent (medieval
  manuscript tradition). Arabic drop caps look weird because of
  shaping/ligature rules.

```css
html[lang="he"] body { line-height: 1.8; }

html[lang="he"] .longform p:first-of-type::first-letter {
  font-size: 3em;
  font-weight: 700;
  float: inline-start;
  margin-inline-end: 0.2em;
  line-height: 0.9;
}

html[lang="he"] *, html[lang="ar"] * {
  font-style: normal !important;  /* no italics */
}
```

## UI copy preferences in RTL

- **Prefer words over icons.** Israeli/Arabic-speaking users decode
  clear labels faster than abstract iconography. Icon-only nav is a
  usability regression in these locales.
- **Second-person direct** (`את`/`אתה` / `أنت`). Formal third-person
  reads cold.
- **Numerals as digits**: `3 דקות` / `3 دقائق`. Not spelled out.
- **Avoid English loan words** where a native word exists:
  `תהליך` over `וורקפלאו`; `نموذج` over `فورم`.

## Form inputs and RTL

- **Placeholder text**: inherits `dir` from input. If the input should
  accept an English URL or phone, force `dir="ltr"` on the input:
  ```html
  <input type="tel" dir="ltr" placeholder="+972-...">
  ```
- **Chevron in `<select>`**: use `inset-inline-end` for its position.
- **Number inputs**: `dir="ltr"` is almost always correct. Otherwise the
  digit order inverts.

## QA rule

Every feature gets an RTL smoke test. Same user flow, `<html dir="rtl" lang="he">`.
If it breaks, the feature is not done. Add this to the PR checklist and
enforce.

## Resources

- [SimpleLocalize — RTL Design Guide for Developers](https://simplelocalize.io/blog/posts/rtl-design-guide-developers/)
- [Workday Canvas — RTL and Bidi](https://canvas.workday.com/globalization/rtl-and-bidi/) — best public reference
- [Flowbite — Tailwind CSS RTL](https://flowbite.com/docs/customize/rtl/)

## Anti-patterns

- `padding-left` / `margin-right` anywhere in the codebase.
- A token named `--space-left-4`.
- Mirrored search-loupe icon in RTL.
- Non-mirrored arrow in RTL.
- Input field with Hebrew placeholder that should be LTR (email,
  phone, URL).
- Running text in Hebrew/Arabic with letter-spacing applied.
- Italicised Hebrew or Arabic body text.
- A "Hebrew version" as a separate codebase instead of a `dir` flip.
