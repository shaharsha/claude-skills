# brand-system scripts

All scripts are stdlib-only (bash + Python 3.9+). No `pip install` required.

| Script | Purpose |
|---|---|
| [new-brand-book.sh](new-brand-book.sh) | Scaffold BRAND.md + BRAND.html + tokens.css + signature-interview.md from the templates/ |
| [render-pdf.sh](render-pdf.sh) | Render BRAND.html to BRAND.pdf via Chrome headless |
| [extract-tokens.py](extract-tokens.py) | Parse BRAND.md color/spacing/radii tables → emit tokens.css / tokens.json |
| [audit-contrast.py](audit-contrast.py) | WCAG 2.2 AA/AAA contrast matrix for a palette |
| [audit-outline.py](audit-outline.py) | Validate a BRAND.md against the canonical 20-section outline |
| [check-consistency.py](check-consistency.py) | Diff BRAND.md tokens against production CSS files to catch drift |
| `_substitute.py` | Internal: template variable substituter (called by new-brand-book.sh) |

## new-brand-book.sh

```bash
./new-brand-book.sh \
  --product "Agentiko" \
  --positioning "A real worker who lives inside WhatsApp." \
  --palette-bg '#F3EAD3' \
  --palette-fg '#0E1320' \
  --palette-accent '#B85A3A' \
  --signature-primitive "voice dot" \
  --primary-font "Rubik" \
  --locale "he" \
  --output-dir .
```

Emits `BRAND.md`, `BRAND.html`, `tokens.css`, `signature-interview.md`
into `--output-dir`. Derives a warm neutral ramp (`--color-bg-50`,
`--color-bg-200`, etc.) and in-palette semantic status colours
(success/warning/danger/info) from the three inputs. Respects
RTL-aware defaults when `--locale` contains `he` or `ar`.

**`--force`** overwrites existing files. Without it, existing files are
skipped (safe to re-run).

## render-pdf.sh

```bash
./render-pdf.sh BRAND.html BRAND.pdf
# or
./render-pdf.sh --input BRAND.html --output BRAND.pdf
```

Auto-detects Chrome/Chromium on macOS, Linux, and Windows (via Git Bash).
Uses `--headless=new` (Chrome 112+). No external dependencies.

## extract-tokens.py

```bash
# Tailwind v4 @theme + :root + [data-theme="dark"]
./extract-tokens.py --input BRAND.md --format tailwind-v4 > tokens.css

# W3C DTCG JSON (for Style Dictionary / Tokens Studio)
./extract-tokens.py --input BRAND.md --format dtcg > tokens.json

# Plain :root CSS variables
./extract-tokens.py --input BRAND.md --format css-vars > vars.css
```

Parses the markdown tables in §6 (colour), §9 (spacing, radii), and
emits the tokens in the requested format. Handy for keeping `tokens.css`
in sync with the source-of-truth BRAND.md.

## audit-contrast.py

```bash
# Light theme only (default)
./audit-contrast.py --bg '#F3EAD3' --fg '#0E1320' --accent '#B85A3A'

# Also check the dark theme (bg ↔ fg swap, accent constant)
./audit-contrast.py --bg '#F3EAD3' --fg '#0E1320' --accent '#B85A3A' --theme both

# Include elevated / muted variants
./audit-contrast.py --bg '#F3EAD3' --fg '#0E1320' --accent '#B85A3A' \
  --bg-elevated '#FAF5E8' --fg-muted '#8A7860'
```

Emits a markdown contrast matrix for every fg/bg pair, grading each by
WCAG 2.2 AA (4.5:1 body, 3:1 large/UI) and AAA (7:1 body, 4.5:1 large).

Exit codes:

- **0** — all required body-text pairs pass AA.
- **1** — a required body-text pair fails AA (the script tells you which).
- **2** — invalid arguments.

Accent-on-bg is expected to fail body AA — that's why the accent is
used for CTA *fills* (text on accent), not prose. The script warns
without failing in those cases.

## audit-outline.py

```bash
./audit-outline.py BRAND.md           # informational
./audit-outline.py BRAND.md --strict  # also fail on unresolved {{TODO}}s
```

Validates a BRAND.md against the canonical 20-section outline. Checks:

- All 20 canonical section headings present.
- §2 signature primitive lists ≥8 use-sites in its table.
- §3 has ≥3 numbered signature moves.
- §14 contains a contrast matrix (ratios or WCAG reference).
- Decision log has ≥1 dated entry.
- With `--strict`, fails on any remaining `{{TODO}}` placeholders.

Exit codes:

- **0** — outline complete.
- **1** — one or more structural checks failed.
- **2** — invalid input path.

## check-consistency.py

```bash
# Diff BRAND.md tokens against one or more production CSS files
./check-consistency.py BRAND.md landing/src/index.css
./check-consistency.py BRAND.md landing/src/index.css app/frontend/src/index.css tokens.css

# --target (repeatable) is equivalent to positional
./check-consistency.py BRAND.md \
  --target landing/src/index.css \
  --target app/frontend/src/index.css

# --strict also fails on missing or extra tokens
./check-consistency.py --strict BRAND.md landing/src/index.css
```

Parses `--name: #hex` declarations from target CSS files and compares
them against colour tokens in BRAND.md (markdown tables + any `@theme`
code blocks). Reports **matches**, **drifts** (same name, different
hex), **missing** (in BRAND.md but not CSS), and **extra** (in CSS but
not BRAND.md).

Exit codes:

- **0** — no hex drift (ignoring missing/extra unless `--strict`).
- **1** — at least one token hex drifted between BRAND.md and a CSS file.
- **2** — invalid input path.

Intended for CI: run after every PR that touches `BRAND.md` or any
tracked CSS file. Catches the "we updated the hex in BRAND.md but not
production" class of drift — the most common way brand books silently
rot.

## new-brand-book.sh — interview enforcement

To refuse scaffolding unless the interview has been filled in:

```bash
./new-brand-book.sh \
  --product "Agentiko" --positioning "..." \
  --palette-bg '#F3EAD3' --palette-fg '#0E1320' --palette-accent '#B85A3A' \
  --require-interview signature-interview.md
```

The script counts unfilled `{{PLACEHOLDER}}`, `{{TODO}}`, and `> …`
answer lines. Any non-zero count → exit 1 with a count per category.
Strongly recommended for first-time scaffolding; skip for quick
iteration.
