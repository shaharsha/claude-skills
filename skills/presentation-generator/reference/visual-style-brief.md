# Writing a `style_brief` — the single most important paragraph in the deck plan

The `style_brief` is a 3-6 sentence paragraph in `deck-plan.json` that gets **appended to every per-slide image prompt automatically** by `generate-deck.py`. It is the consistency lever. Every slide passes through it.

If the brief is sloppy ("modern aesthetic with nice colors"), every slide will drift. If the brief is precise (named hex codes, specific motif language, named typography vibe, decorative treatment), every slide will share a recognizable visual DNA — even when their compositions are wildly different (a flowchart on slide 3, a photograph on slide 4, a big-number on slide 5).

## What a great brief specifies

1. **Aesthetic register** — one phrase. "Modern dark UI infographic." "Editorial photography, documentary feel." "Hand-drawn whiteboard explainer." "Corporate isometric with soft gradients." If you can't name it in eight words, you don't have a single aesthetic and the deck won't cohere.
2. **Background treatment** — what is the dominant background? Solid near-black? White? Cream? Gradient? Textured?
3. **Palette with hex codes** — exact colors. Name what each color is FOR ("primary background #0E1116, accent for emphasis #C5F542, body text #FFFFFF, secondary text #7A8493").
4. **Typography vibe** — not the exact font (gpt-image-2 picks the actual letterforms), but the family register. "Bold modern sans-serif." "Editorial serif with high contrast." "Geometric sans, monoline weight." "Hand-lettered marker."
5. **Recurring motif** — the ONE visual element that appears (in some form) across most slides. "Glowing lime-green outlined rounded cards." "Soft watercolor wash on edges." "Thin dotted connector lines." "Isometric grid as background." Specify both the form AND how it should appear (in the corners? throughout? as borders?).
6. **Icon style** — if the deck uses icons, lock the style. "Line-art icons, 1.5px stroke, in [accent color]." "Filled flat icons in primary." "Hand-drawn marker icons."
7. **Card / element treatment** — how do bordered elements look? "Rounded corners (~16px radius), 1px [accent] borders with subtle outer glow."
8. **What NEVER appears** — sometimes the strongest constraint is exclusion. "Never use white or light backgrounds." "No photographic content." "No serif fonts." "No 3D effects."

## A great brief, annotated

This is the brief from [templates/deck-plan.example.json](../templates/deck-plan.example.json):

> "Every slide is a structured infographic on a near-black (#0E1116) background.
>
> [^^ Locks the dominant register and the bg color.]
>
> The single accent color is bright lime green (#C5F542); use it sparingly for headlines, glowing borders, key numbers, and highlighted icons.
>
> [^^ Locks WHEN the accent is used — not just that it exists.]
>
> Body text is white (#FFFFFF) for readable copy and slate (#7A8493) for secondary captions.
>
> [^^ Names the role of each color, not just lists them.]
>
> Cards have rounded corners (~16px radius), 1px lime-green borders with a subtle outer glow.
>
> [^^ Specifies the card treatment — exact radius, border weight, and the glow.]
>
> Icons are minimalist line-art in lime.
>
> [^^ Locks icon style.]
>
> Across every slide a faint background texture of curving dotted lines and small floating circular nodes ties the deck together.
>
> [^^ The recurring motif, explicitly described.]
>
> Typography is bold modern sans-serif (Inter or similar), large for headlines, regular for body, never serif.
>
> [^^ Locks typography register AND excludes serifs.]
>
> The deck is dark-mode-only — never use white or light backgrounds."
>
> [^^ Final exclusion — strongest possible constraint, prevents drift.]

Every clause is doing work. There are no decorative sentences.

## Three style brief examples (different aesthetics, same level of precision)

### A. Editorial photography

> "Every slide is a single full-bleed photographic frame in the style of a documentary editorial spread (Atlantic, New Yorker). Lighting is warm, low-key, and directional — one practical light source per scene. Backgrounds are softly defocused but not empty. The palette is locked: deep navy (#1A1F2E) as the dominant dark tone, warm amber (#E2A663) as the singular accent, cream (#F1ECDF) and slate (#5C6275) as neutrals. Composition uses the rule of thirds; subjects always slightly off-center. Subtle 35mm grain across the whole image. No text overlays unless explicitly requested per-slide; when text appears it is small, lower-third, in cream serif."

### B. Minimalist tech / corporate

> "Every slide is a clean, generously-spaced infographic on a pure white (#FFFFFF) background. Single accent color is electric blue (#2D5BFF), used for headings, key numbers, and one-color line-art icons. Body text is graphite (#1A1A1A) at body size, soft gray (#9CA3AF) for captions. Generous margins (at least 8% of canvas width on each side). Cards have no borders — only soft drop-shadows and 12px rounded corners. Typography is geometric sans-serif (Inter / SF Pro vibe), regular weight for body, bold for headings, never italic. Recurring motif: a single thin blue underline beneath every primary headline, exactly the width of the headline."

### C. Hand-drawn whiteboard

> "Every slide is rendered as a hand-drawn whiteboard sketch on a slightly off-white (#F8F5EE) textured background that resembles paper or whiteboard. Lines are loose, slightly imperfect, in dark ink (#1A1A1A) and one accent color: muted teal (#3D8B89). Strokes show occasional small overshoots and hesitations — confidently imperfect, not vector-clean. Hand-lettered annotations in the same ink. No filled shapes — everything is line-only, with occasional cross-hatching for emphasis. Recurring motif: small spiral or wavy decorative marks in the corners, like idle doodles. Typography is hand-lettered sans-serif throughout — irregular spacing, slight variation in letter sizes. Never use printed/typeset typography."

## Brand-system integration — when a `BRAND.md` exists

If the user has run the `brand-system` skill on the project (or has a brand book), set `brand_source: "./BRAND.md"` (or wherever it lives) in `deck-plan.json` and *derive* the `style_brief` from BRAND.md verbatim. Specifically:

1. Read BRAND.md.
2. Pull the exact hex codes from the Color section.
3. Pull the typography family names and register.
4. Pull the "signature primitive" or visual motif.
5. Pull the surface / card treatment language.
6. Compose the `style_brief` as a paragraph that names all of these explicitly.

This is the path to **pixel-tight brand fidelity**. When a brand has been codified (palette + motif language + typography + element treatment), every slide composition gets filtered through that codification, and the deck reads as one engagement rather than eight independent images.

## Iterating on the brief

If the Phase 3 style refs come back wrong:

- **Wrong palette**: the hex codes aren't getting through. Make them more prominent — front-load them in the brief, repeat once.
- **Wrong aesthetic register**: the opening phrase is too vague. Replace "modern" with something more specific ("dark UI dashboard", "editorial documentary", "hand-drawn explainer").
- **Motif missing**: describe the motif more concretely. Not "geometric shapes" → "thin glowing lime-green concentric circles in the lower-right corner of every frame."
- **Drift between refs**: shorten the brief. A long brief gives the model too many ways to interpret it. Aim for 4-6 tight sentences.

## Anti-patterns

- **Vague aesthetic words**: "modern", "clean", "professional", "engaging" — these mean nothing to the model. Replace with concrete reference points.
- **Too many constraints**: more than ~8 distinct constraints and the model picks favorites. Prioritize: aesthetic + palette + typography + motif. Everything else is decoration.
- **Color names instead of hex codes**: "blue" is ambiguous; "#2D5BFF" is not.
- **Adjective stacking**: "minimalist, modern, sophisticated, premium, refined aesthetic" — pick one and commit.
- **Overlapping descriptions**: "soft warm light" + "low-key directional lighting" + "moody atmospheric scene" all do the same job. Pick one and let the model fill the rest.
