---
name: brand-system
description: Author a production-grade brand book + design system for a web product — a long-form BRAND.md (20 sections covering the core idea, logo system, color, typography, spacing, surfaces, motion, voice, accessibility, components, and Tailwind v4 @theme tokens), a printable BRAND.html + PDF sibling, and a matched tokens.css / tokens.json with primitive/semantic/component tiering. Use when the user asks to create, draft, author, scaffold, or update a brand book, brand guidelines, design system, design tokens, style guide, visual identity, or BRAND.md; or when a new product needs its first documented identity.
allowed-tools: Read, Write, Bash, Edit, Glob, Grep
---

# Brand System

Scaffolds a brand book + design system that sits at the root of a web
product's repo — long-form `BRAND.md` (the working reference, 20
sections) paired with `BRAND.html` (the printable stakeholder
distillation, ~7 A4 pages, rendered to `BRAND.pdf` via Chrome
headless) and a matched `tokens.css` for Tailwind v4 `@theme`.

This skill **authors the document**. Its sibling
[brand-assets](../brand-assets/SKILL.md) **produces the pixels** (SVG
favicons, PWA pack, apple-touch-icon). Call both in sequence for a
complete brand rollout.

## The five artifacts

| Artifact | What | How |
|---|---|---|
| `BRAND.md` | Long-form 20-section working reference | [templates/BRAND.md.tmpl](templates/BRAND.md.tmpl) via [scripts/new-brand-book.sh](scripts/new-brand-book.sh) |
| `BRAND.html` | 7-page A4 printable distillation | [templates/BRAND.html.tmpl](templates/BRAND.html.tmpl) via same script |
| `BRAND.pdf` | Rendered via Chrome headless | [scripts/render-pdf.sh](scripts/render-pdf.sh) |
| `tokens.css` | Tailwind v4 `@theme` + `:root` + `[data-theme="dark"]` | [templates/tokens.css.tmpl](templates/tokens.css.tmpl) + [scripts/extract-tokens.py](scripts/extract-tokens.py) |
| `tokens.json` | W3C DTCG format for Style Dictionary / Tokens Studio | `scripts/extract-tokens.py --format dtcg` |

## Workflow (decision tree)

1. **Starting fresh?** — run the signature-moves interview first:
   copy [templates/signature-interview.md.tmpl](templates/signature-interview.md.tmpl)
   into the repo and answer every question **before** scaffolding.
   See [reference/signature-moves.md](reference/signature-moves.md)
   for why each question matters. Without this, the output is a
   template; with it, it's a brand.

2. **Scaffolding a new book?** — run
   [scripts/new-brand-book.sh](scripts/new-brand-book.sh) with the
   interview answers as flags. Emits `BRAND.md`, `BRAND.html`,
   `tokens.css`, `signature-interview.md` into the output dir.

3. **Drafting a specific chapter?** — load the matching reference:
   - §0 the idea / §2 primitive / §3 signature moves → [reference/signature-moves.md](reference/signature-moves.md)
   - §5 logo + favicon pack → [reference/favicon-pack.md](reference/favicon-pack.md)
   - §6 colour → [reference/color.md](reference/color.md) + [reference/tokens.md](reference/tokens.md)
   - §7 typography → [reference/typography.md](reference/typography.md)
   - §10 surfaces & materials → [reference/surfaces.md](reference/surfaces.md)
   - §11 motion → [reference/motion.md](reference/motion.md)
   - §13 voice & tone → [reference/voice-and-tone.md](reference/voice-and-tone.md)
   - §14 accessibility → [reference/accessibility.md](reference/accessibility.md)
   - §17 Tailwind v4 `@theme` → [reference/tailwind-v4.md](reference/tailwind-v4.md)
   - Hebrew / Arabic / RTL → [reference/rtl.md](reference/rtl.md)

4. **Favicon + PWA pack?** — **do not generate assets in this skill.**
   [reference/favicon-pack.md](reference/favicon-pack.md) specs the
   requirements (system-aware SVG favicon, opaque apple-touch-icon,
   maskable PWA, OG light+dark pair). Hand the spec + a source SVG to
   the [brand-assets](../brand-assets/SKILL.md) skill's
   `icon-pack.sh`.

5. **Contrast audit before shipping** →
   [scripts/audit-contrast.py](scripts/audit-contrast.py). WCAG 2.2 AA
   on body (4.5:1), 3:1 on large / UI / focus rings. Runs per theme
   (light + dark). Paste the matrix into §14.

6. **Rendering the PDF** →
   [scripts/render-pdf.sh](scripts/render-pdf.sh). Chrome headless.
   Produces `BRAND.pdf` from `BRAND.html`.

7. **Auditing an existing book** →
   [scripts/audit-outline.py](scripts/audit-outline.py). Validates the
   20-section outline, flags missing decision log entries, warns if §2
   signature primitive has <8 use-sites documented.

8. **Catching drift between BRAND.md and production CSS** →
   [scripts/check-consistency.py](scripts/check-consistency.py). Brand
   books fail when code silently diverges from them. Diffs colour
   tokens in BRAND.md against one or more target CSS files and exits
   non-zero on hex drift. Wire into CI.

9. **Enforcing the interview before scaffolding** → pass
   `--require-interview path/to/signature-interview.md` to
   [scripts/new-brand-book.sh](scripts/new-brand-book.sh). Refuses to
   scaffold if the interview still has unfilled `{{PLACEHOLDER}}`,
   `{{TODO}}`, or `> …` answer lines. Strongly recommended.

## House rules

1. **Require the anti-template moves before scaffolding.** The
   interview is not optional. One invented proper noun, three
   falsifiable principles, three real don'ts from past mistakes, a
   150-word voice sample in the brand's voice, and one signature move
   that deliberately breaks a best practice. Without these, the book
   is a template. See [reference/signature-moves.md](reference/signature-moves.md).

2. **Accent constant across light/dark.** Only surface and text
   semantic tokens swap between themes. The one saturated brand colour
   is identical in both modes — that's what lets a signature primitive
   mean the same thing regardless of system preference. Encoded in
   [templates/tokens.css.tmpl](templates/tokens.css.tmpl).

3. **Three-tier tokens per Nathan Curtis taxonomy.** Primitive
   (`--color-cream: #F3EAD3`) → semantic (`--bg: var(--color-cream)`)
   → component (`--btn-bg: var(--bg-elevated)`). Primitives go in
   `@theme`, semantics in `:root`, dark-mode overrides in
   `[data-theme="dark"]`. See [reference/tokens.md](reference/tokens.md).

4. **WCAG 2.2 AA is the legal floor in 2026.** Not APCA — APCA was
   pulled from WCAG 3 in July 2023 and has not returned. AA means
   4.5:1 body, 3:1 large/UI/focus, 24×24 target-size-minimum. Audited
   with [scripts/audit-contrast.py](scripts/audit-contrast.py); see
   [reference/accessibility.md](reference/accessibility.md).

5. **RTL is a foundation, not an appendix.** If the product ships in
   Hebrew or Arabic, use CSS logical properties (`margin-inline-start`,
   not `margin-left`) from day one; the retrofit cost is 10–50×
   designing-for-it upfront. See [reference/rtl.md](reference/rtl.md).

6. **The brand book is itself an instance of the brand.** The
   `BRAND.html` template uses the product's own palette + type — so
   the document looks like the brand on page 1. If the brand book's
   own styling doesn't pass the rules it preaches, it's wrong.

7. **System-first, toggle-second for dark mode.** Respect
   `prefers-color-scheme` by default; persist explicit user overrides
   in `localStorage`. A visible dark-mode toggle in the nav is an
   anti-pattern. The system-aware SVG favicon rule in
   [reference/favicon-pack.md](reference/favicon-pack.md) follows the
   same logic.

## Non-goals

- **Generating logo artwork** — that's [image-generation](../image-generation/SKILL.md).
- **Mechanical asset pipelines** (vectorize PNG → SVG, icon-pack
  generation, rasterize at size) — that's [brand-assets](../brand-assets/SKILL.md).
- **Building the actual components** — §18 of `BRAND.md` documents the
  specs; [react-components](../react-components/SKILL.md) and
  [frontend-design](../frontend-design/SKILL.md) implement them.
- **Brand storytelling / marketing copywriting** — §13 governs *how* to
  write, not *what*.
- **Translating copy** — the skill scaffolds RTL-aware *structure* but
  doesn't translate.
- **Versioning the brand book as a product** — update in place, commit
  with a clear message, one source of truth at the repo root.

## Canonical 20-section outline (what BRAND.md.tmpl emits)

| # | Section | Core must-have |
|---|---|---|
| 0 | The idea | One-sentence core idea + the "strip everything but X" test |
| 1 | Reading the mark | 3–5 simultaneous readings of the logo |
| 2 | Signature primitive | The semantic token that appears across every surface — 8+ use sites |
| 3 | Signature moves | 5–7 things that identify the brand without the logo |
| 4 | Brand essence | What we are / are not / tone / positioning sentence |
| 5 | Logo system | Variants, clear space, min size, don'ts, favicon + PWA pack requirements |
| 6 | Colour system | Core + extended + neutrals + semantic tokens, 62/30/8 ratio, light/dark parity |
| 7 | Typography | Face, tabular nums, scale, measure, RTL moves, wordmark treatment |
| 8 | Iconography | Style, colour rules (accent never used), size tokens, RTL flipping |
| 9 | Spacing & layout | 8-point grid, containers, radii + concentric-radii rule |
| 10 | Surfaces & materials | Default + floating material, grain overlay, hero backgrounds |
| 11 | Motion | Principle, tokens, the signature animation, reduced-motion behaviour |
| 12 | Imagery & illustration | Photography rules, illustration style, anti-patterns |
| 13 | Voice & tone | Rules, tone matrix by emotional state, 3-levels-of-same-thought, RTL specifics |
| 14 | Accessibility | WCAG 2.2 AA contrast matrix, focus rings, reduced motion, RTL equivalence |
| 15 | Reference set | What shelf the brand sits on + what it's not |
| 16 | Anti-patterns | Specific "don't do this" list — concrete bad habits banned |
| 17 | Implementation — Tailwind v4 @theme | Full block, :root + [data-theme="dark"], body rules |
| 18 | Components | Buttons, links, inputs, cards, badges, nav, alerts, dialogs, prose, landing primitives |
| 19 | Migration plan | What's being retired; ✅/⚠️/❌ per token/pattern; dates |
| 20 | What this is not + Decision log | Non-goals + dated table of decisions with rationale |

## Quick invocation

```bash
# Scaffold a new brand book at the repo root
~/.claude/skills/brand-system/scripts/new-brand-book.sh \
  --product "Agentiko" \
  --positioning "A real worker who lives inside WhatsApp." \
  --palette-bg '#F3EAD3' \
  --palette-fg '#0E1320' \
  --palette-accent '#B85A3A' \
  --signature-primitive "voice dot" \
  --primary-font "Rubik" \
  --locale "he" \
  --output-dir .

# Audit contrast
~/.claude/skills/brand-system/scripts/audit-contrast.py \
  --bg '#F3EAD3' --fg '#0E1320' --accent '#B85A3A'

# Render the printable
~/.claude/skills/brand-system/scripts/render-pdf.sh BRAND.html BRAND.pdf

# Later: check an existing book against the outline
~/.claude/skills/brand-system/scripts/audit-outline.py BRAND.md
```

## Related skills

- [brand-assets](../brand-assets/SKILL.md) — mechanical SVG/PNG pipelines; run after this skill to produce the favicon pack.
- [image-generation](../image-generation/SKILL.md) — design logo/hero imagery before this skill runs.
- [frontend-design](../frontend-design/SKILL.md) — implement §18 components in production code.
- [react-components](../react-components/SKILL.md) — build component primitives once §18 is authored.
