# claude-skills

Agent skills by [@shaharsha](https://github.com/shaharsha) - 14 production-grade [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills) that work in Claude Code, claude.ai, Codex, Cursor, and any other harness that reads the SKILL.md format.

MIT licensed. Built day-to-day; battle-tested in real projects.

---

## Install

### Claude Code (recommended)

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install shaharsha-skills@shaharsha-skills
```

This installs all 14 skills as one plugin. Or pick a subset:

```bash
/plugin install documents-and-decks@shaharsha-skills    # gdoc-sync + gslides-sync + gsheets + presentation-generator
/plugin install brand-and-visuals@shaharsha-skills      # brand-system + brand-assets + image-generation
/plugin install engineering-decisions@shaharsha-skills  # tech-design-doc
/plugin install building-agents@shaharsha-skills        # prompt-engineer + writing-project-instructions
/plugin install utilities@shaharsha-skills              # namecheap-domains + office-render + viewing-videos + proton-pass
```

### Manual (any other harness)

```bash
git clone https://github.com/shaharsha/claude-skills.git ~/shaharsha-skills
ln -s ~/shaharsha-skills/skills/<skill-name> ~/.claude/skills/<skill-name>
# repeat per skill, or symlink the whole skills/ dir
```

For Codex, Cursor, Gemini CLI, OpenClaw, etc., follow the same shape - point your harness at `skills/<name>/SKILL.md`.

---

## Skills

### Documents & decks

#### [gdoc-sync](skills/gdoc-sync)

Push a local `.md` to an existing Google Doc, then fix the four things Google's converter breaks: `#anchor` links arriving as broken URL strings, `other.md#anchor` cross-doc refs, inline images at 1500pt+ wrecking layout, and missing RTL for Hebrew/Arabic. One Python script, stdlib + `google-auth`.

#### [gslides-sync](skills/gslides-sync)

Sister to `gdoc-sync` for `.pptx` -> existing Google Slides. Rewrites broken slide-anchor and cross-presentation links into native `pageObjectId` references, scales oversized images, applies RTL per text shape. Same service-account setup works for both.

#### [gsheets](skills/gsheets)

Comprehensive Sheets API v4 CLI - the Sheets-shaped sibling to `gdoc-sync` and `gslides-sync`. Read / write / append / clear cells; create / rename / duplicate / delete tabs; freeze rows, set column widths, merge ranges; style headers (bold + colored bg + frozen + filter as one atomic batch); apply borders, banding (zebra stripes), and conditional formatting; sort and filter; or drop to a `batch-update` escape hatch for charts, pivots, data-validation dropdowns, protected ranges, and gradient color scales. Same service-account auth as the other Google skills.

#### [presentation-generator](skills/presentation-generator)

Generate 16:9 PDF + PPTX decks where every slide is a custom AI-rendered image - not a templated layout with stock photos. Style locks globally via a reference image; composition varies per slide (full-bleed photo, infographic, architecture flowchart, big-number callout, timeline, quote card, etc.). Research -> narrative arc (SCQA / Duarte / Kawasaki) -> style lock -> parallel generation at concurrency 4 -> QA -> assemble. ~$3-5 in image-API spend for a 10-slide deck.

### Brand & visuals

#### [brand-system](skills/brand-system)

Author a production-grade brand book + design system in one shot: long-form `BRAND.md` (20 sections), printable `BRAND.html` rendered to `BRAND.pdf` via Chrome headless, plus `tokens.css` (Tailwind v4 `@theme` + light/dark `:root`) and `tokens.json` (W3C DTCG, consumable by Style Dictionary / Tokens Studio). An anti-template interview won't finalize without one invented proper noun, three falsifiable principles, three real don'ts, and a 150-word voice sample. WCAG 2.2 AA audited at authoring time.

#### [brand-assets](skills/brand-assets)

The mechanical-pixel sibling to `brand-system`. Five pipelines that run locally in seconds: **vectorize** (split-by-color-mask + potrace, not one-shot vtracer which muddies palettes), **finalize-svg** (snap fills to exact brand hexes, normalize viewBox), **rasterize** SVG -> pristine PNG, **icon-pack** (one SVG -> favicon + apple-touch-icon + PWA pack with iOS-opaque background and PWA-maskable safe area), **color-audit** (histogram opaque pixels per hex; fails on >1% drift). Bash + Python stdlib.

#### [image-generation](skills/image-generation)

Generate logos, icons, UI mockups, hero images, and product shots via **OpenAI gpt-image-2** (default since Apr 2026 - took #1 in Image Arena by +242 pts within 12 hours of release) or **Gemini Nano Banana 2 / Pro**. Packages model-selection logic, provider-specific prompt grammars (OpenAI wants labeled segments + negatives; Gemini wants narrative paragraphs + positives only - mixing them up degrades outputs), asset templates, a transparent-background pipeline (gpt-image-2 + `rembg`), Hebrew/RTL guidance, and an iteration loop where Claude reads the saved image with vision and decides ship/edit/rewrite before showing the user.

### Engineering decisions

#### [tech-design-doc](skills/tech-design-doc)

Author technical design review documents - RFCs, ADRs, design docs, KEPs, partner-mode TDRs - sized correctly for the audience and the decision being made. Triages format first (1-2 page mini ADR vs 6-page standard RFC vs 10-20 page heavyweight KEP vs partner-mode for external dev partners), scaffolds from research-grounded templates, enforces load-bearing sections (BLUF summary, goals/non-goals with quantified targets, >=3 alternatives, cross-cutting checklist, decision log), inserts mandatory C4 + sequence diagrams in mermaid, and runs a static audit against best-practice anti-patterns. Pairs with `gdoc-sync` to push the finished doc to a live Google Doc for stakeholder review.

### Building agents

#### [prompt-engineer](skills/prompt-engineer)

Expert prompt-engineering reference for AI agents on **Claude / GPT / Gemini** APIs. Covers system-prompt structure, tool descriptions (the single highest-leverage quality factor), context engineering, provider differences (instruction placement, verbosity defaults, persona handling, temperature, caching), budget-model patterns, cross-provider compatibility, anti-patterns, and evaluation/judge-prompt design. Use when writing system prompts, tool descriptions, function-calling schemas, agent instructions, or when an agent keeps misfiring.

#### [writing-project-instructions](skills/writing-project-instructions)

Author or audit a CLAUDE.md / AGENTS.md project-instruction file (the file an AI coding agent reads at session start for project context). Encodes Anthropic's cardinal include/exclude rules, the under-200-line target, the falsifiability test, locations + loading semantics, AGENTS.md interop via `@import`, and Boris Cherny's compounding-engineering loop. Use when authoring a new CLAUDE.md, auditing an existing one for bloat, trimming a too-long file, or diagnosing why Claude isn't following its instructions.

### Utilities

#### [namecheap-domains](skills/namecheap-domains)

Check domain availability via Namecheap's `domains.check` API. One domain, batches up to 50, or TLD sweeps (`com,io,ai,dev,co,app,xyz`). Surfaces premium and EAP fees so you don't fall in love with a `$2,999` "available" name. Stdlib-only Python; auto-chunks lists >50 (the API's hard cap).

#### [office-render](skills/office-render)

Render a Microsoft Office file (`.docx` / `.pptx` / `.xlsx`) to PDF and then to page images using the **real** installed Office app (Word / PowerPoint / Excel) on macOS — pixel-faithful, unlike LibreOffice, which substitutes fonts and re-flows complex tables and slide grids. One command produces page JPGs Claude can read, for previewing a doc or visually QA-ing a generated `.docx`/`.pptx`. Bakes in the macOS permission gotchas it took real debugging to find: Automation consent, the Office sandbox's per-file access prompt, Full Disk Access for the Office apps (and the quit-and-relaunch needed for it to apply), and the `with timeout` wrapper that prevents AppleEvent timeouts on PDF export.

#### [viewing-videos](skills/viewing-videos)

Claude can't watch video — this skill is how it sees one anyway: turn the file into the **fewest frames that answer the question** via ffmpeg. Three strategies (targeted seek for known timestamps, scene-change detection for screen shares / slides, interval sampling for continuous motion), frames renamed to their meeting timestamp, an ImageMagick contact sheet to triage 60+ frames in one look, and a crop+upscale recipe for table text at the edge of 720p legibility. Born from a real need: a 30-min Zoom recording whose transcript missed the numbers shown on screen.

#### [proton-pass](skills/proton-pass)

Manage credentials and secrets from the CLI via **Proton Pass** (`pass-cli`): list vaults and items, view / create / update / delete logins, generate random passwords or passphrases, and resolve `pass://vault/item/field` secret references into template files or a command's environment. Bakes in the security guardrails (never print secrets to chat, prefer `inject` / `run` over inline values, always name the vault) and a load-bearing gotcha — the `run -- env X="pass://…"` form has been seen passing the literal URI instead of the resolved secret, so resolve explicitly with command substitution and length-check when correctness matters. macOS/Homebrew binary path.

---

## How they compose

A few of these are designed to work together:

- `presentation-generator` calls `image-generation` for every slide.
- `presentation-generator` consumes `brand-system`'s `BRAND.md` for palette / typography / motif lock when present in the directory.
- `brand-system` (the document) and `brand-assets` (the pixels) are siblings - run both for a complete brand rollout.
- `gdoc-sync`, `gslides-sync`, and `gsheets` share Google service-account setup; one SA works for all three APIs.
- `tech-design-doc` calls `gdoc-sync` at the end of the workflow to push the finished TDR to a live Google Doc for stakeholder comments.

---

## Compatibility

These are standard [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills) (SKILL.md-format). They work in any harness that reads the format:

- **Claude Code** (CLI) - full plugin marketplace support; install via `/plugin install` as above.
- **claude.ai** - upload skills via Settings -> Capabilities -> Skills.
- **Codex CLI** - point Codex at the skill folder; it reads SKILL.md natively.
- **Cursor** - drop the skill into your `~/.cursor/skills/` (or wherever your Cursor config expects).
- **Gemini CLI** - point at the skill via `gemini extensions install`.
- **OpenClaw / other harnesses** - any tool that respects SKILL.md frontmatter works.

---

## License

MIT. See [LICENSE](LICENSE).
