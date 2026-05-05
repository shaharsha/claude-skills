# Per-slide image prompting — engineering each slide for gpt-image-2

The deck's `style_brief` handles the global look. Each slide's `image_prompt` handles **what's in the frame and how it's arranged**. The two get concatenated automatically by `generate-deck.py`.

This doc covers how to write `image_prompt` for the kinds of slides you'll actually generate — structured infographics, diagrams, charts, comparison cards — not just photographs. gpt-image-2 is excellent at all of these.

## The model

gpt-image-2 (released April 2026, took #1 across every Image Arena category by +242 points). Notable strengths for slide work:

- **Best-in-class text rendering** in any major language including Hebrew, Arabic, CJK, Hindi, Bengali. Letters are crisp and spelled correctly the vast majority of the time.
- **Near-total prompt adherence** — it actually puts things where you tell it to.
- **Agentic layout reasoning** — it understands "card with icon left, heading center, three bullets right" and lays it out.
- **Color accuracy** — hex codes in prompts get respected.

Caveats:

- Each edge of the output must be ≤ 3840px and a multiple of 16. **`1920×1080` is invalid** because 1080 is not a multiple of 16. Use `2560×1440` (the skill's default).
- Long-to-short ratio ≤ 3:1 (16:9 = 1.78:1, fine).
- No native transparent background.

## Prompt structure that works

For *every* slide, the prompt should answer four questions in order:

1. **What kind of image is this?** ("Cover slide", "Architecture flowchart", "Comparison split-screen", "Big-number infographic", etc. — name the composition explicitly.)
2. **What's the global frame?** Aspect, background color from palette, generous margins.
3. **What's on the canvas, where?** Element by element, position by position. Use spatial language: "top-center", "lower-third", "left half", "evenly spaced across the bottom", "centered horizontally with 80px gap below the title".
4. **What text appears, exactly?** Quote the wording. Specify color and rough size relative to other text.

Don't repeat the deck's `style_brief` content (palette, motif, typography vibe) — that's appended automatically.

## Prompt skeleton — annotated walkthrough

Slide 5 from the example deck — an architecture flowchart:

> "Architecture flowchart, 16:9, near-black background. Title at top in white bold: 'Router & Orchestration Architecture'.
>
> [^^ Names the composition. Names the global frame. Specifies title position and exact wording.]
>
> Below the title, a system diagram. Top-center node: a thin-bordered rounded rectangle labeled 'Shopper Profile + Context' (loyalty tier, recent orders, app location).
>
> [^^ Spatial position (top-center). Element type (rounded rectangle). Exact label text.]
>
> An arrow flows down to a larger glowing lime-green rounded rectangle labeled 'The Router (Gemini Flash) — Evaluate intent and sentiment'.
>
> [^^ Connector specified. Next element with exact label.]
>
> From the Router, three arrows fan downward and outward: leftmost arrow (gray, dashed) to a muted gray node 'Branch A: Escalation (high frustration / urgent issue) → Live agent handoff'; middle arrow (lime) to a node 'Branch B: Returns Intent → Returns Agent (Sonnet) → Order History + Policy KB (RAG)'; rightmost arrow (lime) to a node 'Branch C: Recommendations Intent → Recommendations Agent (Sonnet) → Tool Calling: Cart updates, Upsell, Loyalty redemption'.
>
> [^^ Three branches. Each with its own color treatment. Each with its own exact label. Notice how Branch A is muted — the model uses that to indicate "this is the de-emphasized path" without being told to.]
>
> A caption at the bottom in white: 'Router enables accuracy, saves cost on simple queries, and keeps returns and recommendations context separate from the start.'
>
> [^^ Caption with exact wording.]
>
> All connectors are thin lines with arrowheads. Faint dotted background lines."
>
> [^^ Final detail nudges and a callback to the deck-wide motif (the dotted lines).]

That prompt produces a clean architecture diagram. Notice what's NOT in it: palette hex codes, typography names, card-treatment language. All of that lives in `style_brief` and gets appended.

## Text in the image — getting wording right

This is the model's biggest failure mode. Tactics:

- **Quote the exact text in the prompt.** "labeled 'The Router (Gemini Flash)'", not "labeled with the router name".
- **Don't paraphrase across iterations.** If the first attempt mis-spelled "Containment", the second attempt's prompt should still say `"Containment"` exactly the same way.
- **Long body text loses fidelity.** Anything past ~12-15 words per text block starts mangling. Keep text-in-image tight; push longer prose into `speaker_notes` instead.
- **Headlines first, captions second.** The model gets headline text right ~95% of the time; smaller secondary text ~80%. If you have many text blocks, prioritize the most important.
- **For numbers, use the digit form.** `'>60%'` works better than `'sixty percent'`.
- **Foreign-script text** — write it in the target script. `'תוכנית מוצר'` not `"Tochnit Mutzar"`. gpt-image-2 reads the script and renders it natively. For long Hebrew/RTL paragraphs that mangle, see `~/.claude/skills/image-generation/reference/hebrew-rtl.md`.

## Anti-prior text resistance — for named entities the model wants to invent

The model has strong category priors. When a slide describes a recognizable schema — milestone names in a project plan, bullets in a "monthly retainer" service description, payment-term boilerplate, generic SaaS feature lists — gpt-image-2 will sometimes ignore the verbatim text in your prompt and substitute its own *plausible-sounding-but-wrong* fill-in. Real failures observed:

- A project-plan timeline: prompt specified `"M2 - Quarterly Hardware Refresh"` and `"M3 - Field Service Sync"`. Model rendered `"M2 - Performance Optimization"` and `"M3 - Analytics Dashboard"` — invented from "what M2/M3 of an enterprise SaaS quote usually look like."
- A retainer-services list: prompt specified four bullets including `"Operational support for Alex and Jordan"`. Model substituted `"Performance monitoring, uptime checks"`, `"Content and data updates - product details, editorial copy, pricing, and analytics data"`. The model recognized "retainer service description" and reached for its prior.

When a slide names specific business entities, project codes, milestone names, fee amounts, dates, or product-specific bullets, **assume the model will try to substitute** unless you actively block it. Use this pattern:

1. **Wrap the literal strings in a `CRITICAL:` block.** Place the critical-text block AFTER the layout description, near the bottom of the prompt (recency bias helps). Use ALL CAPS for the word `CRITICAL`.
2. **Quote each string verbatim.** Use straight quotes around every string the model must render: `Bullet 1 (verbatim): "Operational support for Alex and Jordan"`.
3. **Forbid the specific anti-prior.** Don't just say "use exact text" — name what the model is likely to substitute and forbid it: *"Do NOT mention performance monitoring, content updates, analytics, security & compliance, or anything not listed below."*
4. **State the structural rule.** *"Render the FOUR bullets exactly as written. Do not invent. Do not paraphrase. Do not substitute."*

Worked example block (drop this verbatim into an `image_prompt` near the bottom):

```
CRITICAL: Render the FOUR bullets exactly as written below.
Do NOT invent or substitute. Do NOT mention performance monitoring,
content updates, analytics, security & compliance, or anything not
listed below.

Bullet 1 (verbatim): "Third-party dependency maintenance - the 5 source
APIs and AI models change over time; we test, re-validate, re-tune,
handle deprecations"
Bullet 2 (verbatim): "Bug fixes beyond the 30-day defect-support windows"
Bullet 3 (verbatim): "Operational support for Alex and Jordan"
Bullet 4 (verbatim): "Small enhancements as needs surface"
```

The same pattern works for milestone names, dates, dollar amounts, person names, organization names, product codes — any slot the model has a strong prior for. If a slide fails the same way twice (model substitutes the same wrong thing), step up to this pattern; don't keep tweaking the surface prompt.

When in doubt about whether the model has a strong prior: it does. If the slide's content is "the kind of thing a stock-photo SaaS deck would have," the model has a prior for it.

## Spatial language that works

The model understands all of these:

- **Halves**: "left half", "right half", "upper half", "lower half"
- **Thirds**: "upper third", "middle third", "lower third", "left third"
- **Specific positions**: "top-center", "bottom-right corner", "centered horizontally"
- **Distributions**: "three boxes evenly spaced left to right", "stacked vertically with small gaps", "arranged in a 2×2 grid"
- **Sizes (relative)**: "the middle box is larger than the outer two", "the central element occupies ~30% of the canvas width"
- **Margins**: "generous margins around all elements", "padded inside each card"

It is less good with:

- **Pixel-precise positioning** ("32px from the top edge"). Use rough fractions instead.
- **Multi-step instructions about flow** ("first the user sees X, then Y"). Just describe the static layout.
- **Implicit references** ("the box from before"). Re-state every element on every prompt.

## Layout patterns that gpt-image-2 lays out cleanly

1. **Card grids** — 2×2, 3×1, 3×2 with explicit "evenly spaced" instruction. Excellent fidelity.
2. **Vertical stacks** — "four cards stacked vertically with small gaps between them, each card has [structure]". Excellent.
3. **Two-column comparisons** — "split-screen with vertical divider down the middle". Excellent.
4. **Flowcharts with up to ~7 nodes** — describe each node, then the connectors. Excellent up to ~7; degrades past 10.
5. **Big-number callouts** — "very large [number] in [color] occupying ~35% of canvas, centered, with [label] below". Excellent.
6. **Single hero photo with one text overlay** — classic. Excellent.
7. **UI mockups with side annotations** — describe the phone/screen, then the connector lines and annotation text. Excellent for 3-5 annotations; gets crowded past that.

Layout patterns to avoid:

- **More than ~10 distinct elements on a single slide** — composition collapses. Split into two slides.
- **Diagonal or curved layouts** without strong reason — model gets confused. Stick to horizontal / vertical / grid.
- **Fine-grained chart axes with many tick labels** — text mangles. Use editorial-chart style: one label per bar, axis implicit.

## Palette injection — the top-level brief does the heavy lifting

The deck's `style_brief` already names hex codes and their roles ("primary background #0E1116, accent #C5F542, body text #FFFFFF"). Per-slide prompts should reference colors by *role*, not by hex:

- ✅ "Headline in [accent], body in white, secondary text in slate."
- ❌ "Headline in #C5F542, body in #FFFFFF, secondary text in #7A8493."

This keeps prompts readable and makes future palette changes a one-place edit.

If a slide deliberately needs a non-palette color (e.g., a brand-specific yellow for a comparison element), say so explicitly and provide the hex: "Card 1's icon is in deep amber #FFA500 (deliberately outside the deck palette to flag attention)."

## Model selection per slide — when to switch from gpt-image-2 to Gemini

Default is gpt-image-2. Switch a single slide to `model: gemini` when:

- You need to merge **3+ reference images** into one slide (e.g., a UI mockup combining a product logo, a phone bezel reference, and a screen-content reference). Gemini Pro accepts up to 14 refs; gpt-image-2's `/edits` endpoint also accepts multiple but Gemini is designed for it.
- gpt-image-2 has failed the same composition twice with style drift. Gemini sometimes nails what gpt-image-2 misses, particularly hyper-realistic portraits.
- The slide contains a real-life portrait or photo-like human likeness. Gemini Pro is stronger here.

Don't switch the entire deck to Gemini just because one slide needs it. Per-slide override via the `model` field.

## Iteration discipline

When a slide needs regeneration after Phase 5 QA:

- **First retry**: same prompt, regenerate. The model is non-deterministic; ~30% of failures resolve on retry alone.
- **Second retry**: refine the prompt — be more specific about whatever was wrong. Tighten text, name an exact element, add a "do NOT include X" if it kept hallucinating.
- **Third retry**: rewrite the prompt from scratch. Don't tweak. Pick a different angle on the slide's idea.

After 2 retries, surface to the user. Don't silently burn $0.20 per attempt forever.
