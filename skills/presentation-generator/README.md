# presentation-generator

A Claude Code skill that generates **superb 16:9 widescreen presentations** (PDF and PPTX) where every slide is a custom AI-rendered image — not a templated layout filled with stock photos.

The skill makes Claude think like a creative director:

1. **Research** the topic (local files or web)
2. **Design the narrative** — pick an audience, a single takeaway, an arc (SCQA / Duarte oscillation / Kawasaki 10/20/30)
3. **Lock the visual style** globally via a reference image (palette, typography vibe, recurring motif)
4. **Choose a composition per slide** — full-bleed photo, structured infographic, architecture flowchart, big-number callout, comparison split, UI mockup with annotations, timeline, quote card, etc. — whatever the slide actually needs
5. **Generate all slides in parallel** (concurrency 4) via the `image-generation` skill (gpt-image-2)
6. **QA** by reading every PNG and regenerating any that drift
7. **Assemble** into PDF (Chrome headless) and PPTX (`python-pptx`)

Style locks across the deck. Composition varies per slide. The same architecture both NotebookLM Cinematic Video Overviews and well-designed brand decks use to feel coherent without feeling templated.

## Why this skill exists

AI deck generators (Gamma, Tome, Beautiful.AI) produce decks that *look* AI-generated: generic stock-photo aesthetic, jarring style shifts between slides, walls of text, no narrative arc. Anthropic's official `pptx` skill goes the other way — it composes natively-editable PowerPoint with text and shapes, which is excellent for editable decks but stops short of producing visually distinctive ones.

This skill fills the gap: every slide is a custom-rendered 16:9 image, but the rendering is intentional and varied — the same skill produces a documentary-photographic editorial deck, a dark-UI infographic deck with cards and flowcharts, a hand-drawn whiteboard explainer, or a corporate isometric brief. All from the same pipeline.

## Quickstart

In a Claude Code conversation, in a directory where you want the deck to live:

> "Use presentation-generator to make a 7-slide deck about [topic], audience: [audience]. Use the [aesthetic] aesthetic with [palette description]."

Or, if a `BRAND.md` from the `brand-system` skill already exists in the directory:

> "Use presentation-generator to build a deck of [topic] from BRAND.md."

The skill walks Claude through research → narrative plan → style lock → parallel generation → QA → assemble, producing both `.pdf` and `.pptx` in `./output/`.

## Output

```
./
├── deck-plan.json         # Narrative + composition plan (Claude writes this)
├── refs/
│   ├── style-ref-1.png    # Style anchor candidates
│   └── style-ref-2.png
├── slides/
│   ├── slide-01-cover.png
│   ├── slide-02-comparison-split.png
│   └── ...                # One full-bleed 16:9 PNG per slide
└── output/
    ├── <deck-slug>-v1.pdf
    └── <deck-slug>-v1.pptx
```

A 10-slide deck typically costs ~$3-5 in image API spend. Wall-clock time at concurrency 4 is roughly 2-3 minutes for generation plus assembly.

## Prerequisites

- `OPENAI_IMAGE_API_KEY` — get from your OpenAI account
- Python 3.10+ with `python-pptx` and `Pillow` installed
- Chrome / Chromium for PDF rendering
- The `image-generation` skill installed alongside this one (this skill calls its `openai-image.sh`)

## Documentation

The skill's full documentation lives alongside it:

- [SKILL.md](SKILL.md) — the entry point Claude reads when invoking the skill
- [reference/narrative-frameworks.md](reference/narrative-frameworks.md) — SCQA, Pyramid, Duarte oscillation
- [reference/slide-compositions.md](reference/slide-compositions.md) — 15+ slide composition formats with prompt skeletons
- [reference/visual-style-brief.md](reference/visual-style-brief.md) — how to write the global style brief
- [reference/image-prompting.md](reference/image-prompting.md) — per-slide gpt-image-2 prompt engineering
- [reference/consistency-tactics.md](reference/consistency-tactics.md) — style lock vs composition variety
- [reference/output-formats.md](reference/output-formats.md) — PDF/PPTX dimensions and gotchas
- [scripts/README.md](scripts/README.md) — script-level CLI reference
- [templates/deck-plan.example.json](templates/deck-plan.example.json) — fully worked 8-slide example with eight different compositions

## Related skills

- [`image-generation`](../image-generation/) — the engine. This skill calls `openai-image.sh` from it.
- [`brand-system`](../brand-system/) — when a project has a BRAND.md, this skill consumes its palette / typography / motif for pixel-tight brand fidelity.
- [`brand-assets`](../brand-assets/) — for logo and icon asset preparation that may feed individual slides.
- Anthropic's [official `pptx` skill](https://github.com/anthropics/skills/tree/main/skills/pptx) — use it instead when the user wants natively-editable PowerPoint with text and shapes (this skill produces image-as-slide PPTX, which is intentionally not text-editable).

## License

Author: Shahar Shavit. Same license as the rest of the user's `~/.claude/skills/` collection.
