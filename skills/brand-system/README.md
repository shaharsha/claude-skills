# brand-system — a Claude Code skill

Scaffolds a production-grade brand book + design system for a web product.
Pairs a long-form working reference with a printable stakeholder distillation,
and ties everything back to code via Tailwind v4 `@theme` and W3C DTCG tokens.

The skill authors the **document**. Its sibling
[brand-assets](https://github.com/shaharsha/claude-skill-brand-assets) produces
the **pixels** (favicons, PWA pack, apple-touch-icon). Run both for a complete
brand rollout.

## Why this exists

Every new product hits the same wall between "we have a logo and three colors"
and "we have a brand." The typical result is a slide deck that dies the day
it ships, a Figma file that drifts from production, or a README paragraph
that everyone ignores.

The skill codifies the pattern that actually survives:

- **One document**, not a slide deck. `BRAND.md` at repo root, diffable,
  versioned with git, next to `README.md` and `CLAUDE.md` where engineers
  actually look.
- **A printable sibling** for stakeholders who need a PDF. `BRAND.html`
  uses the brand's own palette + type, so the document looks like the brand
  on page 1. Rendered by Chrome headless to `BRAND.pdf`.
- **Tokens tied to code**, in two formats: `tokens.css` (Tailwind v4
  `@theme` + `:root` semantics + `[data-theme="dark"]` overrides) and
  `tokens.json` (W3C DTCG — so Style Dictionary, Tokens Studio, and any
  other system-of-record can consume the same source of truth).
- **An anti-template interview** that refuses to finalize a book without
  the five moves every great brand book has and every template skips: one
  invented proper noun, three falsifiable principles, three real don'ts,
  a voice passage written AS the brand, one signature-move that breaks a
  best-practice rule.
- **WCAG 2.2 AA audited at authoring time.** Every palette pair runs
  through `audit-contrast.py` before the book is considered done.

## Install as a Claude Code skill

```bash
# Into your global skills directory
git clone https://github.com/shaharsha/claude-skill-brand-system.git \
  ~/.claude/skills/brand-system
chmod +x ~/.claude/skills/brand-system/scripts/*.sh \
         ~/.claude/skills/brand-system/scripts/*.py
```

Claude Code auto-discovers the skill. Trigger with phrases like:

- *"let's draft a brand book for X"*
- *"create a BRAND.md for this project"*
- *"author a design system for our product"*
- *"scaffold brand tokens with light and dark mode"*

## Use the scripts directly

No Claude required. Bash + Python stdlib + Chrome.

```bash
# End-to-end scaffold
scripts/new-brand-book.sh \
  --product "Agentiko" \
  --positioning "A real worker who lives inside WhatsApp." \
  --palette-bg '#F3EAD3' --palette-fg '#0E1320' --palette-accent '#B85A3A' \
  --signature-primitive "voice dot" \
  --primary-font "Rubik" \
  --locale "he" \
  --output-dir .

# Audit contrast against WCAG 2.2 AA
scripts/audit-contrast.py \
  --bg '#F3EAD3' --fg '#0E1320' --accent '#B85A3A'

# Render printable to PDF
scripts/render-pdf.sh BRAND.html BRAND.pdf

# Extract tokens from a hand-edited BRAND.md
scripts/extract-tokens.py --input BRAND.md --format tailwind-v4 > theme.css
scripts/extract-tokens.py --input BRAND.md --format dtcg > tokens.json

# Validate an existing book hits the 20-section outline
scripts/audit-outline.py BRAND.md
```

## Prerequisites

- **Python 3.9+** — stdlib only, no pip install required.
- **Bash** — standard on macOS/Linux.
- **Google Chrome** — for PDF rendering via `--headless --print-to-pdf`.
  Path auto-detected on macOS (`/Applications/Google Chrome.app`),
  Linux (`google-chrome`, `chromium`), and Windows (via `start`).

Optional for the `tokens.json` DTCG output to round-trip into a real token
pipeline:

- [Style Dictionary](https://styledictionary.com/) or
  [Tokens Studio](https://tokens.studio/) — consume the DTCG JSON.

## How the skill is structured

```
brand-system/
├── SKILL.md                          # Claude entry point (router, <300 lines)
├── README.md                         # This file — human-facing
├── LICENSE                           # MIT
├── reference/                        # Deep-dives, loaded on demand
│   ├── signature-moves.md            # The anti-template interview
│   ├── canonical-outline.md          # Per-section must-haves for all 20 sections
│   ├── tokens.md                     # 3-tier architecture, DTCG, naming taxonomy
│   ├── color.md                      # Palette construction, 62/30/8, dark parity
│   ├── typography.md                 # Scale, measure, pairing, tabular nums
│   ├── surfaces.md                   # Paper vs Glass, grain overlays, hero bgs
│   ├── motion.md                     # Principles, tokens, signature animation
│   ├── voice-and-tone.md             # Mailchimp tone matrix, 3-levels exercise
│   ├── accessibility.md              # WCAG 2.2 AA, focus, reduced motion, forced-colors
│   ├── rtl.md                        # Hebrew/Arabic logical properties + type moves
│   ├── favicon-pack.md               # System-aware SVG favicon, PWA maskable, OG pair
│   ├── tailwind-v4.md                # @theme mapping, :root + [data-theme="dark"]
│   └── exemplars.md                  # 10 reference brand books + what each does well
├── templates/                        # Scaffolding sources
│   ├── BRAND.md.tmpl                 # 20-section skeleton
│   ├── BRAND.html.tmpl               # 7-page A4 printable
│   ├── tokens.css.tmpl               # @theme + :root + dark
│   └── signature-interview.md.tmpl   # The interview prompts
└── scripts/                          # Runnable pipelines
    ├── new-brand-book.sh             # Scaffold from templates
    ├── render-pdf.sh                 # HTML → PDF via Chrome headless
    ├── extract-tokens.py             # BRAND.md → tokens.css / tokens.json
    ├── audit-contrast.py             # WCAG 2.2 AA/AAA matrix
    ├── audit-outline.py              # Validate 20-section outline
    └── README.md                     # Per-script usage
```

Per Anthropic's [skill best practices](https://code.claude.com/docs/en/skills):
`SKILL.md` is under 500 lines and acts as a router to deep-dive `reference/`
files, loaded only when the relevant chapter is being drafted. Scripts handle
deterministic ops so they don't burn context tokens on every invocation.

## House rules baked in

1. **Anti-template moves required.** The interview enforces one invented
   proper noun, three falsifiable principles, three real don'ts, a 150-word
   voice sample, and one rule the brand deliberately breaks.
2. **Accent colour is constant across light and dark.** Only surface and
   text semantics swap. Encoded in `tokens.css.tmpl`.
3. **Three-tier tokens** — primitive (`@theme`) → semantic (`:root`) →
   component. Per Nathan Curtis's naming taxonomy.
4. **WCAG 2.2 AA** is the legal floor; APCA is a spot-check only.
5. **System-first dark mode.** Respect `prefers-color-scheme` by default.
   Even the SVG favicon swaps via embedded `<style>@media`.
6. **RTL as a foundation.** CSS logical properties from day one for
   Hebrew/Arabic products.

## What this skill is NOT

- A logo designer. Use `image-generation`.
- A mechanical asset pipeline. Use `brand-assets` (the sibling skill).
- A React/Vue component library. Use `react-components` / `frontend-design`
  to implement §18 specs.
- A Figma plugin. `tokens.json` is DTCG-compatible — import it into
  Tokens Studio if you want Figma sync.
- A copywriter. §13 governs *how* to write, not *what*.
- A translation service.

## License

MIT. See [LICENSE](LICENSE).
