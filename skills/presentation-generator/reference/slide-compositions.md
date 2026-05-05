# Slide compositions — the visual format vocabulary

A slide's **composition** is *what kind of image* it is — independent of its narrative role. A "problem" slide can be a photograph, a comparison split, a diagram, or a big-number callout. Pick the composition that fits what the slide must communicate, not a default mode.

The deck's **style** (palette, typography, decorative motif) locks globally via `style_brief`. The **composition** varies per slide. This is how the deck stays coherent (one visual language) while keeping the audience visually awake (no two adjacent slides look the same).

gpt-image-2 is the workhorse — it handles photos, structured layouts, diagrams, infographics, UI mockups, charts, *and* legible text in any major language including Hebrew and Arabic. So the question is never "can the model do this composition" — it's "which composition does this slide actually need."

---

## The vocabulary

Below is a non-exhaustive catalog. Each entry includes when to use it and a prompt skeleton. Mix freely. Invent new ones if a slide needs something none of these capture — `composition` is a free-form string in the schema, not an enum.

### 1. Full-bleed photographic / cinematic

A single edge-to-edge photograph or photoreal scene. Carries mood, sets tone, lands an emotion.

**When**: title slides, story slides, problem slides where the pain needs to be *felt*, takeaway slides where a single image embodies the idea.

**Prompt skeleton**: "Wide cinematic photograph of [subject] in [setting]. [Light direction and quality]. Composition uses [rule of thirds / centered / leading lines] with [where the empty space is, for any text overlay]. Mood: [single emotional word]."

### 2. Big-number callout

ONE huge number or stat occupies the visual center. Optional small label and supporting metric cards orbiting it.

**When**: data slides where the magnitude is the message. Conversion rates, lift figures, market sizes, benchmark scores.

**Prompt skeleton**: "Editorial infographic, [palette]: a single very large number '[NUMBER]' rendered in bold sans-serif typography, occupying roughly 40% of the canvas, centered. Below it, a one-line label '[LABEL]'. Around it on left and right, four smaller secondary stat cards each with a smaller number and a one-word label. Decorative [motif] elements in the background. The big number glows softly."

### 3. Comparison split-screen

Two halves of the canvas show contrasted states. Old vs new, before vs after, them vs us, what-is vs what-could-be.

**When**: making a contrast inescapable. Setup slides for SCQA's "complication," value-prop slides, anti-pattern slides.

**Prompt skeleton**: "Split-screen 16:9 composition divided vertically down the middle. Left half: '[TITLE-LEFT]' header at top, [visual content describing the 'before' state]. Right half: '[TITLE-RIGHT]' header at top, [visual content describing the 'after' state]. The two halves share [aesthetic anchor] but use contrasting [palette mapping — left desaturated/muted, right saturated/glowing]. A thin vertical [palette-accent] line separates them."

### 4. Comparison cards (multi-column)

Two, three, or four cards side by side, each with a heading, icon, and short description. Used for value props, principle lists, scenario lineups.

**When**: enumerating a small set of parallel things — features, principles, scenarios, options.

**Prompt skeleton**: "Three-column infographic on [palette-bg-dark] background. Each column is a card with rounded corners, [palette-accent]-colored thin glowing border. Card 1 ('[T1]'): icon of [icon1] at top, heading '[T1]' in [palette-accent], 2-3 short bullet lines below in [palette-fg]. Card 2 ('[T2]'): icon of [icon2], heading '[T2]', bullets. Card 3 ('[T3]'): icon of [icon3], heading '[T3]', bullets. Cards are evenly spaced. Decorative [motif] in the background. The center card has a brighter glow than the outer two to indicate emphasis."

### 5. Architecture flowchart / system diagram

Boxes (or pills, or rounded rectangles) connected by arrows, labels on each box, optional swim lanes. A literal diagram of how a system works.

**When**: technical decks, system overviews, process explanations, decision trees.

**Prompt skeleton**: "System architecture diagram on [palette-bg] background. Top: a single [palette-accent]-glowing rounded rectangle labeled '[ROOT-LABEL]'. From it, three arrows fan down to three child rectangles labeled '[A]', '[B]', '[C]'. Box B's outline glows brighter than A and C to indicate the focus path. Connectors are thin [palette-accent] lines with arrowheads. Each box has a small icon to its left. Decorative [motif] in the corners. All text legible at 16:9. Use [palette-fg] for body labels."

### 6. Timeline / process

Horizontal sequence of stages, each labeled, connected by arrows or a flowing line. Optional callouts under each stage.

**When**: roadmaps, milestones, process explanations, before/during/after structures.

**Prompt skeleton**: "Horizontal timeline 16:9, [palette-bg] background. Three glowing [palette-accent] circular nodes evenly spaced left-to-right, connected by a thin curving line. Each node labeled above with 'Phase 1', 'Phase 2', 'Phase 3' and a short subtitle. Below each node, a card with 2-3 short bullets describing that phase. The middle phase node is larger and glows brighter for emphasis. Decorative [motif] in the background."

### 7. Quote card

A pulled quote, large and centered, with attribution. Sometimes overlaid on an atmospheric image, sometimes on a flat colored background.

**When**: surfacing a powerful sentence from research, a customer, a luminary. Pause-the-deck moments.

**Prompt skeleton**: "Quote card 16:9. Large centered serif (or whatever typography) text: '\"[EXACT QUOTE]\"' rendered prominently. Below in smaller type: '— [ATTRIBUTION]'. Background: [either a softly-defocused atmospheric scene OR a flat palette-bg color]. Generous margin around the quote. The opening and closing quote marks are oversized in [palette-accent]."

### 8. UI mockup with annotations

A phone screen, dashboard, or web UI mockup, with thin connector lines from elements to side annotations explaining each.

**When**: explaining a product feature, walking through a screen, showing a UI design decision. Almost always has callouts.

**Prompt skeleton**: "Two phone mockups centered on a 16:9 [palette-bg] canvas. Each phone shows a [describe the app screen exactly: header, content blocks, button labels in exact wording, color scheme matching deck palette]. From specific UI elements, thin curving [palette-accent] connector lines lead to side annotations: '[ANNOTATION 1 TEXT]', '[ANNOTATION 2 TEXT]', '[ANNOTATION 3 TEXT]'. Annotation text is in [palette-fg], smaller than headers. Decorative [motif] wave-pattern in background."

### 9. Infographic with icon grid

A 2×2, 3×2, or 3×3 grid of icons with short labels. Often used for principles, capabilities, or feature inventories.

**When**: small, parallel set of items where icons earn their keep — abstract principles, product features, brand attributes.

**Prompt skeleton**: "Icon grid infographic, 16:9, [palette-bg] background. Four equal cells in a 2×2 arrangement. Each cell contains: a line-art icon of [icon] in [palette-accent], a heading '[T]' below it in bold [palette-fg], and a 1-line caption in lighter [palette-fg] beneath the heading. Cells are separated by thin [palette-accent] lines. Generous padding within each cell. Decorative [motif] at the corners."

### 10. Stacked principle cards (vertical list)

Vertically arranged horizontal cards, each card spanning most of the canvas width, with icon left + heading + description. Used for ordered or numbered principle lists.

**When**: 3-5 numbered principles, design rules, requirements.

**Prompt skeleton**: "Four horizontally-oriented cards stacked vertically on a [palette-bg] background. Each card has rounded corners and a [palette-accent] glowing left edge. Inside each card: on the right, a line-art icon in [palette-accent]; in the center, a bold heading '[T]' in [palette-accent]; below the heading, 1-2 lines of body text in [palette-fg]. The four headings are: '[H1]', '[H2]', '[H3]', '[H4]'. Cards are evenly spaced. Decorative [motif] in the background."

### 11. Data visualization / chart

A magazine-cover-style chart: ONE bar, line, or pie that does the talking. Editorial in feel, not Excel-default.

**When**: data slides where the *shape* of the data carries the meaning, not just one number.

**Prompt skeleton**: "Editorial-style data visualization on [palette-bg] background. A single bar chart with three bars labeled '[L1]', '[L2]', '[L3]' on the x-axis. The middle bar is dramatically taller than the others and glows in [palette-accent]. Y-axis is implicit — no gridlines, no tick marks, no numbers along the axis except for one annotated callout. A short caption below the chart in [palette-fg]: '[CAPTION]'. The composition feels like a chart on the cover of The Economist, not a spreadsheet output."

### 12. Title / cover with central motif

A bold title slide with a decorative central element, large title text, and a subtitle line. Optionally a "version" or "date" tag in the corner.

**When**: deck cover, section dividers in long decks.

**Prompt skeleton**: "Cover slide 16:9 on [palette-bg]. Top center: a decorative [motif element described in detail — e.g., 'a Newton's cradle of five glowing lime-green orbs hanging from thin black cords'], occupying the upper third. Below it, large bold sans-serif title text: '[TITLE]'. Below the title, smaller subtitle in lighter weight: '[SUBTITLE]'. Bottom-right corner: small text '[DATE / VERSION TAG]'. Generous margin around all text. The motif glows softly."

### 13. Map / geographic frame

A stylized map with pins, regions, or routes marked. Used for distribution, expansion, geographic data.

**When**: anything geographic.

**Prompt skeleton**: "Stylized minimalist map of [region] on [palette-bg] background. Coastlines and borders rendered in thin [palette-fg] lines. Three glowing [palette-accent] pin markers at [LOCATION-A], [LOCATION-B], [LOCATION-C], each labeled with a short caption. A subtle [palette-accent] arc connecting the pins to suggest a route. Decorative [motif] in the corners."

### 14. Hand-drawn whiteboard sketch

Loose, illustrative, deliberately imperfect lines — like an explainer doodle on a whiteboard. Useful when you want the deck to feel human / casual / explanatory.

**When**: educational explainers, casual decks, when the "polished AI deck" aesthetic is exactly what you want to avoid.

**Prompt skeleton**: "Whiteboard-style hand-drawn illustration, on a [palette-bg] background that resembles a whiteboard. The whole composition is rendered in loose, slightly imperfect [palette-accent] marker lines. [Describe the sketch: e.g., 'a stick figure holding a flag, standing at the top of a mountain made of layered lines, with three other stick figures climbing up']. Hand-lettered annotations in [palette-fg]: '[A1]', '[A2]'. The lines look organic, slightly wavy, with occasional small overshoots — confidently imperfect."

### 15. Two-column do/don't or pros/cons table

A table-like comparison with one column showing the desired pattern (✓) and another showing the anti-pattern (✗).

**When**: codifying rules, brand patterns, do/don't lists, methodology choices.

**Prompt skeleton**: "Two-column do/don't comparison on [palette-bg] background. Left column header: '✓ Brand Patterns' in [palette-accent]. Right column header: '✗ Anti-Patterns' in muted [palette-fg]. Below each header, three rows. Each row has a category label in the leftmost gutter ('[CAT1]', '[CAT2]', '[CAT3]'), a 'do' description in the left column, and a 'don't' description in the right column. Thin horizontal divider lines between rows. The do-column entries are tighter and more emphatic than the don't-column."

---

## Picking a composition — quick guide

```
Is this slide's job to make the audience feel something?
  YES → photographic / cinematic / quote card.
  NO  ↓

Is the slide's payload a single number or stat?
  YES → big-number callout.
  NO  ↓

Is the slide's payload a contrast between two states?
  YES → comparison split-screen (or comparison cards if 3-4 things).
  NO  ↓

Is the slide's payload a small set of parallel items (3-5)?
  YES → comparison cards / icon grid / stacked principle cards.
  NO  ↓

Is the slide's payload a system, process, or sequence?
  YES → flowchart / timeline / process diagram.
  NO  ↓

Is the slide's payload a UI or product surface?
  YES → UI mockup with annotations.
  NO  ↓

Is the slide's payload a powerful single sentence?
  YES → quote card.
  NO  ↓

Default to a hero photographic frame for atmosphere; pull the meaning into speaker notes.
```

---

## Compositions that need extra care — known failure modes

Most compositions in this catalog render cleanly on the first attempt. A few have specific failure modes worth knowing about *before* you spec them, so you can either avoid them or apply the documented fix on attempt one rather than discovering it through three regenerations.

### Stacked principle cards with multi-line content (5+ items)

The **stacked principle cards** composition (entry 10) is one of the most useful — but it has a sharp cliff at 5+ cards each containing multiple text fields (numeral + bold lead phrase + supporting sub-line). Real failure: a 5-card "What we heard" slide rendered the branded-blue numerals 01-05 cleanly but dropped *every single* lead phrase and supporting line. The cards rendered as boxes containing only the numeral. Repeated twice with prompt refinements; failed both times.

**Why**: the model treats each card as a separate text-rendering subtask; with 5 cards × 3 text elements = 15 text strings, attention is diluted and the secondary content gets dropped.

**Fix that worked**: drop the card chrome entirely. Use a clean typographic vertical list — large numerals + bold statement on a single line, no boxes, no supporting sub-lines (push those into `speaker_notes`). The single-line statement reliably renders for all 5 items.

```
GOOD (renders):
01   Anchor on durability.
02   Cadence beats one-off output.
03   Run on the customer's stack.
04   Specificity, not AI polish.
05   Close the feedback loop.

RISKY (drops content):
[card] 01  |  Anchor on durability.       |  Outputs should match the existing print artifact...
[card] 02  |  Cadence beats one-off ...   |  Each cadenced output should feed the next by pre-defined rules...
... (5 cards × 3 text fields each → secondary text gets dropped)
```

If you genuinely need both lead and supporting text on 5 items, split into two slides (3 + 2) or step the body text down to 1 sentence and prompt aggressively for it.

### Multi-bar gantt across N week-columns

Multi-band timelines work well — *up to a point*. A composition with 3 horizontal milestone bars overlaid on an 8-column week grid (gantt-style), plus a fourth IR-time row beneath, failed: only the M1 bar rendered with its label; M2 and M3 rendered as empty bars; the IR-time row was completely omitted.

**Why**: when bars span fractional column widths (`spans columns 1-4`, `spans columns 5-7`, `spans columns 7-8 with overlap`), the model has to compute geometry AND render labels INSIDE narrow rectangles AND maintain a separate row beneath. Too many concurrent constraints.

**Fix that worked**: drop the column-grid and use full-width labeled milestone bands. Each band spans the entire content width with the milestone name + week range + ship date all readable inside it. Below the bands, use a single horizontal callout row (4 cells) for the milestone-week summary instead of a per-column row.

If the gantt-across-columns layout is essential, cap at 2 bars and ≤6 columns, and make the bars span whole columns (no fractional spans).

### Small text inside a colored shape against the canvas

Small or footer-sized colored banners with text inside them have a high text-drop rate. Real failure: a closing slide's deep-navy `#00132F` CTA banner at the bottom rendered as a navy rectangle containing **no text at all** — the geometry rendered, the centered "Sign by Friday" headline did not.

**Why**: the model treats the banner as a decorative element first, text-bearing element second, when it occupies <40% of the canvas. White-on-dark in a small region is also high-contrast strain.

**Fix that worked**: make the banner the dominant element (40-60% of canvas height), use a much larger headline (60pt+), and reduce other elements on the slide so the banner isn't competing for the model's attention budget. Stating *"the headline must be the largest text on the slide"* as part of the prompt also helps.

For footer-strip CTAs that should remain small, render the text on the white canvas itself and use the colored band only as a thin underline accent — not as the text container.

### Card grids past ~6 cells

The **icon grid** and **comparison cards** compositions (entries 4, 9) work well at 2×2, 3×1, 3×2. Past ~6 cells (3×3 or 4×3), text inside cells starts dropping — same root cause as the stacked-principle issue: too many parallel text-rendering subtasks.

**Fix**: split into two slides. Six items on one slide, six on the next. Or: keep the grid but use icons-only cells with the labels in a legend below.

### Heuristic — when a composition is risky

Sum the text strings the model needs to render correctly:
- Headline + section labels: ~2-3 strings
- Each card / cell / bar: count its text fields (label, sub-label, metric)
- Each annotation callout: 1-2 strings

If the total goes past **~25 text strings** on a single slide, expect at least one to drop. Either restructure or split.

---

## Composition rhythm — alternate to keep audiences awake

Across the deck, **no two adjacent slides should use the same composition**. Alternate between high-info structured slides (cards, diagrams, charts) and low-info atmospheric slides (photo, quote, big-number). The pacing keeps the audience visually engaged. NotebookLM does this rigorously — examine any of their Cinematic Video Overviews and you'll see no two consecutive frames share a composition type.

For an 8-slide deck, a typical rhythm:

```
1. cover (title + motif)
2. photographic (problem, atmospheric)
3. comparison split (the rupture)
4. big-number (the cost)
5. flowchart (the proposed solution)
6. icon grid (the supporting principles)
7. quote card (the takeaway)
8. cover-style closing (CTA)
```

Notice: every slide uses a different composition. The deck still feels unified because the palette, typography, and motif are constant.

---

## Adapting to brand systems

If the user has run the `brand-system` skill on their project and there's a `BRAND.md` file, set `brand_source` in the deck plan and *derive* the `style_brief` from BRAND.md verbatim — palette hex codes, typography names, motif language. This gives you pixel-tight brand fidelity: the codified brand (palette + motif + typography + element treatment) gets applied to every slide composition, so the deck reads as one engagement.

See [visual-style-brief.md](visual-style-brief.md) for how to write a `style_brief` that actually locks style.
