# claude-skills

A curated set of [Claude Code](https://claude.com/claude-code) skills I've built and use day-to-day. Each one lives in its own repo so you can install only what you need.

By [@shaharsha](https://github.com/shaharsha) · MIT-licensed individually.

---

## Install

Each skill installs to `~/.claude/skills/<name>/` and Claude Code auto-discovers it on next session. The repo names carry a `claude-skill-` prefix; the on-disk directory does not.

```bash
git clone https://github.com/shaharsha/claude-skill-<NAME>.git ~/.claude/skills/<NAME>
```

Examples below.

---

## Skills

### Documents & decks

#### [gdoc-sync](https://github.com/shaharsha/claude-skill-gdoc-sync)

Push a local `.md` to an existing Google Doc, then fix the four things Google's converter breaks: `#anchor` links arriving as broken URL strings, `other.md#anchor` cross-doc refs, inline images at 1500pt+ wrecking layout, and missing RTL for Hebrew/Arabic. One Python script, stdlib + `google-auth`.

```bash
git clone https://github.com/shaharsha/claude-skill-gdoc-sync ~/.claude/skills/gdoc-sync
```

#### [gslides-sync](https://github.com/shaharsha/claude-skill-gslides-sync)

Sister to `gdoc-sync` for `.pptx` → existing Google Slides. Rewrites broken slide-anchor and cross-presentation links into native `pageObjectId` references, scales oversized images, applies RTL per text shape. Same service-account setup works for both.

```bash
git clone https://github.com/shaharsha/claude-skill-gslides-sync ~/.claude/skills/gslides-sync
```

#### [presentation-generator](https://github.com/shaharsha/claude-skill-presentation-generator)

Generate 16:9 PDF + PPTX decks where every slide is a custom AI-rendered image — not a templated layout with stock photos. Style locks globally via a reference image (palette, typography, motif); composition varies per slide (full-bleed photo, infographic, architecture flowchart, big-number callout, timeline, quote card, etc.). Research → narrative arc (SCQA / Duarte / Kawasaki) → style lock → parallel generation at concurrency 4 → QA → assemble. ~$3-5 in image-API spend for a 10-slide deck.

```bash
git clone https://github.com/shaharsha/claude-skill-presentation-generator ~/.claude/skills/presentation-generator
```

### Brand & visuals

#### [brand-system](https://github.com/shaharsha/claude-skill-brand-system)

Author a production-grade brand book + design system in one shot: long-form `BRAND.md` (20 sections), printable `BRAND.html` rendered to `BRAND.pdf` via Chrome headless, plus `tokens.css` (Tailwind v4 `@theme` + light/dark `:root`) and `tokens.json` (W3C DTCG, consumable by Style Dictionary / Tokens Studio). An anti-template interview won't finalize without one invented proper noun, three falsifiable principles, three real don'ts, and a 150-word voice sample. WCAG 2.2 AA audited at authoring time.

```bash
git clone https://github.com/shaharsha/claude-skill-brand-system ~/.claude/skills/brand-system
```

#### [brand-assets](https://github.com/shaharsha/claude-skill-brand-assets)

The mechanical-pixel sibling to `brand-system`. Five pipelines that run locally in seconds: **vectorize** (split-by-color-mask + potrace, not one-shot vtracer which muddies palettes), **finalize-svg** (snap fills to exact brand hexes, normalize viewBox), **rasterize** SVG → pristine PNG, **icon-pack** (one SVG → favicon + apple-touch-icon + PWA pack with iOS-opaque background and PWA-maskable safe area), **color-audit** (histogram opaque pixels per hex; fails on >1% drift). Bash + Python stdlib.

```bash
git clone https://github.com/shaharsha/claude-skill-brand-assets ~/.claude/skills/brand-assets
```

#### [image-generation](https://github.com/shaharsha/claude-skill-image-generation)

Generate logos, icons, UI mockups, hero images, and product shots via **OpenAI gpt-image-2** (default since Apr 2026 — took #1 in Image Arena by +242 pts within 12 hours of release) or **Gemini Nano Banana 2 / Pro**. Packages model-selection logic, provider-specific prompt grammars (OpenAI wants labeled segments + negatives; Gemini wants narrative paragraphs + positives only — mixing them up degrades outputs), asset templates, a transparent-background pipeline (gpt-image-2 + `rembg`), Hebrew/RTL guidance, and an iteration loop where Claude reads the saved image with vision and decides ship/edit/rewrite before showing the user.

```bash
git clone https://github.com/shaharsha/claude-skill-image-generation ~/.claude/skills/image-generation
```

### Building agents

#### [prompt-engineer](https://github.com/shaharsha/claude-skill-prompt-engineer)

Expert prompt-engineering reference for AI agents on **Claude / GPT / Gemini** APIs. Covers system-prompt structure, tool descriptions (the single highest-leverage quality factor), context engineering, provider differences (instruction placement, verbosity defaults, persona handling, temperature, caching), budget-model patterns, cross-provider compatibility, anti-patterns, and evaluation/judge-prompt design. Use when writing system prompts, tool descriptions, function-calling schemas, agent instructions, or when an agent keeps misfiring.

```bash
git clone https://github.com/shaharsha/claude-skill-prompt-engineer ~/.claude/skills/prompt-engineer
```

### Utilities

#### [namecheap-domains](https://github.com/shaharsha/claude-skill-namecheap-domains)

Check domain availability via Namecheap's `domains.check` API. One domain, batches up to 50, or TLD sweeps (`com,io,ai,dev,co,app,xyz`). Surfaces premium and EAP fees so you don't fall in love with a `$2,999` "available" name. Stdlib-only Python; auto-chunks lists >50 (the API's hard cap).

```bash
git clone https://github.com/shaharsha/claude-skill-namecheap-domains ~/.claude/skills/namecheap-domains
```

---

## How they compose

A few of these are designed to work together:

- `presentation-generator` calls `image-generation` for every slide.
- `presentation-generator` consumes `brand-system`'s `BRAND.md` for palette / typography / motif lock when present in the directory.
- `brand-system` (the document) and `brand-assets` (the pixels) are siblings — run both for a complete brand rollout.
- `gdoc-sync` and `gslides-sync` share Google service-account setup; one SA works for both APIs.

---

## Why separate repos?

I keep each skill in its own repo (rather than a monorepo) so installs stay one `git clone`, each skill versions independently, and individual skills can rank in GitHub search on their own merits. This index repo is a pointer, not a bundle.

---

## License

Each skill is MIT-licensed in its own repo. See the individual `LICENSE` file in each.
