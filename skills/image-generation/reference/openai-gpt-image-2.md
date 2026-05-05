# OpenAI gpt-image-2 — operational reference

Read this file before writing any prompt for `gpt-image-2`. Sources: OpenAI Cookbook prompting guide (primary), OpenAI API image-generation guide, OpenAI model card for `gpt-image-2-2026-04-21`, fal.ai prompt guide, imagine.art 70-prompt guide, awesome-gpt-image-2 community prompts.

**Released:** 2026-04-21. Took #1 across every Image Arena category by **+242 points** over Nano Banana 2 within 12 hours — the largest gap in Arena history. Dethrones `gpt-image-1.5` on almost every axis.

## API surface

- **Endpoint (generate):** `POST https://api.openai.com/v1/images/generations`
- **Endpoint (edit/inpaint):** `POST https://api.openai.com/v1/images/edits`
- **Model ID:** `gpt-image-2`
- **Snapshot ID:** `gpt-image-2-2026-04-21`
- **Auth:** `Authorization: Bearer $OPENAI_IMAGE_API_KEY`

The bundled `scripts/openai-image.sh` wraps both endpoints.

## What changed from gpt-image-1.5

| Dimension | gpt-image-1.5 | gpt-image-2 |
|---|---|---|
| **English text fidelity** | Very good | ~100% accuracy, reads as native typography |
| **Multilingual text** | Weak for non-Latin | Strong for CJK, Hindi, Bengali, Hebrew, Arabic |
| **Prompt adherence** | Good | Near-total: a 15-element list lands all 15 |
| **Reasoning about layout** | None | Agentic — plans composition before drawing |
| **Latency** | 10-30s, up to 2min | ~3s typical, ~10-30s at high quality with dense text |
| **Max resolution** | 1536px on long edge | 3840px on long edge |
| **Size system** | 3 fixed sizes | Arbitrary: max 3840px edge, both edges multiples of 16, ratio ≤ 3:1, total px 655,360–8,294,400 |
| **`background=transparent`** | ✅ supported | ❌ **not supported** — post-process via rembg |
| **`input_fidelity=high`** | Opt-in flag | Always on — no longer configurable |
| **Color accuracy** | Tended warm (amber tint on whites) | Neutral — true whites, true grays |

**When you still want gpt-image-1.5:** nowhere. The skill drops it. For native transparent PNGs, use `gpt-image-2 --background opaque` with a clean monochrome backdrop in the prompt, then run `rembg` (see [transparent-backgrounds.md](transparent-backgrounds.md)).

## When NOT to use gpt-image-2

- **Hyper-realistic human portraits / cinematic lifestyle:** Gemini Pro still wins on skin texture, fine hair, film grain authenticity. gpt-image-2 scores 4.5/5 on realism but a notch behind Pro on faces specifically. Arena splits this cleanly: **gpt-image-2 wins on structure (text, layouts, multi-image, reasoning); Pro wins on aesthetics (photoreal, lighting, textures).**
- **Brand work with 5+ reference images for character consistency:** Pro accepts up to 14 references with stronger role-assignment.
- **Cheap high-volume exploration:** Gemini Flash at $0.067 undercuts gpt-image-2 low on latency + consistency in a grid; use Flash for throwaway exploration, promote to gpt-image-2 high for the keeper.

## Parameter cheatsheet

| Param | Values | When to use |
|---|---|---|
| `quality` | `low` \| `medium` \| `high` \| `auto` | `high` for anything with text or small detail; `medium` general-purpose; `low` for fast previews only. |
| `size` | any valid `WxH` | Constraints: each edge ≤ 3840px, each edge a multiple of 16, long-to-short ratio ≤ 3:1, total pixels 655,360–8,294,400. Above 2560×1440 outputs are more variable but usable. |
| `background` | `opaque` \| `auto` | **`transparent` is not supported.** Generate with `opaque` and a clean backdrop, then `rembg`. |
| `output_format` | `png` \| `jpeg` \| `webp` | `png` for text or line art; `jpeg` for photos; `webp` for web. |
| `output_compression` | `0-100` (jpeg/webp only) | Default fine. |
| `n` | integer | `n=4` for ideation; single request returns coherent variants. |
| `moderation` | `auto` \| `low` | `low` for edgy marketing / historical / political work within policy. |
| `response_format` | `b64_json` \| `url` | `b64_json` for server pipelines (bundled script uses this). |
| `stream` + `partial_images` | bool + 0-3 | Each partial = +100 output tokens; skip for batch. |
| ~~`input_fidelity`~~ | — | **Not configurable on gpt-image-2.** Every reference image is processed at high fidelity automatically. |

## The 5-slot prompt structure

The canonical gpt-image-2 template. Write each slot on its own line or paragraph; do not merge them into one block.

```
SCENE:     Location, time, background, environment.
SUBJECT:   Main focal point (who/what).
DETAILS:   Materials, lighting, camera, mood, composition, micro-details.
USE CASE:  Artifact type — "editorial photograph", "product mockup",
           "mobile UI screen", "marketing poster", "infographic",
           "indie film poster", "museum archive photograph".
CONSTRAINTS: What must not appear (no watermark, no extra people),
           what must be preserved (faces, geometry, layout), exclusion
           of drift ("no duplicate text", "no plastic skin").
```

Why the **USE CASE** slot matters: gpt-image-2 adjusts its layout rules by artifact type. Declaring "editorial magazine cover" invokes different composition defaults than "UI mockup" or "infographic." Cookbook quote: *"The fifth slot is where most mediocre prompts fail silently."* Bounding creative freedom prevents unwanted invention.

**Length:** 2-5 sentences per slot for simple work; 8-15 lines across all slots for dense UI mockups / infographics. Vagueness is penalized; length is not.

## Anti-slop rules (the #1 source of bad outputs)

gpt-image-2's reasoning is strong enough that vague hype actively hurts. Rewrite around these rules.

### 1. Visual facts over vague praise

❌ *"stunning, incredible, epic, masterpiece, gorgeous, insane detail, 8K, ultra-detailed"*
✅ *"overcast daylight, brushed aluminum, chipped paint, clean kerning, 50mm feel, soft bounce light"*

Generic hype doesn't render. Concrete visible facts do. Cookbook quote: *"Excitement does not render. The second version gives the model something to draw."*

### 2. Style tags need visual targets

❌ *"minimalist brutalist editorial luxury photoreal"*
✅ *"Cream background, heavy black condensed sans serif, asymmetrical type block, one hero object, generous negative space"*

Don't stack aesthetic adjectives — describe the execution.

### 3. Say the real thing

Name concrete objects directly. If a transit kiosk must appear, say "transit kiosk." If text must be readable, state that explicitly. The model is literal about nouns and explicit about constraints.

### 4. In edits: separate change from preserve

Every edit prompt is three sentences:

1. **What changes:** *"Replace the parked car with a vintage bicycle."*
2. **What stays locked:** *"Preserve the house, fence, driveway concrete, landscaping, lighting direction, and time of day exactly."*
3. **Physical realism:** *"Match the bicycle scale and shadow pattern to the existing scene."*

Repeat the preserve list every iteration — drift compounds.

### 5. One revision per turn

Good: `"Make the light warmer."` Then next turn: `"Remove the extra chair."` Then: `"Restore the original wall texture."`
Bad: combining multiple changes in a single edit prompt.

### 6. Treat text like typography, not paraphrased language

Wrap literal text in quotes or ALL CAPS. Specify font style, size, color, placement. Spell hard words letter-by-letter when the model keeps ghosting them. See "Text rendering rules" below for the full treatment.

## Named references that trigger world knowledge

gpt-image-2 was trained on enough photography / design discourse that real-world references outperform generic adjectives:

- **Film stocks:** `Kodak Portra 400`, `Fujifilm Pro 400H`, `CineStill 800T`, `Kodak Ektar 100`.
- **Cameras / lenses:** `Hasselblad X2D 80mm f/5.6`, `Fujifilm X100V 23mm f/2 ISO 1600`, `Leica M10 35mm f/1.4`, `medium format 80mm f/2 4:5`.
- **Publications:** `editorial portrait for The New Yorker profile`, `Monocle cover treatment`, `FT Weekend magazine photography`, `Apartamento interiors feel`.
- **Designers / movements:** `in the style of Saul Bass`, `Swiss grid tradition`, `Memphis Group palette`, `Bauhaus typography`, `Dieter Rams product language`.
- **Era / place:** `1970s Manhattan`, `1990s Tokyo neon`, `1992-era CRT monitor`, `early 2000s flash photography`.
- **Lighting archetypes:** `tungsten mixed with neon`, `golden hour low sun`, `soft box eliminating harsh shadows`, `overhead museum archive light`.

These trigger world-aware reasoning about physics, color science, typography, and material behavior — not generic "AI-stock" averaging.

## Text rendering rules

Core rule: **put literal text in quotes or ALL CAPS, specify typography details, name the role of each text block.**

### Techniques

1. **Wrap literal text in double quotes** — the model treats quoted content as verbatim.
2. **Name the role of each text block** — `headline`, `subhead`, `callout`, `caption`, `credits block`. Example: `"Title (bold serif, centered top): 'MIDNIGHT SESSION'. Subhead (thin mono type, centered below): 'A FILM BY CHLOE ARIN · IN THEATERS OCTOBER 17'. Credits block (7pt Helvetica, bottom center)."`
3. **Always use `quality="medium"` or `"high"`** for any image with text. `low` smears small glyphs.
4. **Spell tricky words letter-by-letter** for brand names: `"F-I-E-L-D & F-L-O-U-R"`.
5. **Demand uniqueness** to block hallucinated extras: `"Render the text exactly as written. No extra words. No duplicate text. No substitutions."`
6. **Specify typography concretely:** font family ("7pt Helvetica", "bold condensed sans"), weight, color, placement, alignment, kerning.
7. **Declare artifact first** — *"indie film poster"* / *"menu board"* / *"protest sign"* — the layout type shapes how text is rendered.

### Multilingual / non-Latin text

gpt-image-2 is the first OpenAI model to handle Japanese, Korean, Chinese, Hindi, Bengali, Hebrew, and Arabic reliably. But it still rewards explicit constraints:

```
[Language prefix]: exact text in double quotes
- "Japanese: 本日のおすすめ"
- "English: Today's Special"
- "Korean: 한복 미래 — 1987년부터"

Constraints for non-Latin scripts:
- Do not romanize
- Render [Hebrew / Arabic / Hangul / Kanji] characters exactly as given
- [For Arabic / Hebrew]: right-to-left, correct ligatures, no Latin substitutions
- No invented characters, no mirrored glyphs, no nikud/vowel points unless requested
```

For multilingual compositions, **write each language as its own quoted block, separately labeled — never paraphrase or translate in the prompt.** Pasting exact glyphs prevents character corruption.

## Character consistency across scenes

For multi-panel stories, marketing campaigns, or brand mascots needing a consistent character:

**First prompt** — anchor the character with identity invariants:
```
Create an illustration introducing the main character. A young forest
helper named Mara: short dark hair with blunt bangs, warm brown skin,
light freckles, dark brown eyes, wearing an oversized orange knit sweater
and dark jeans. Hand-painted watercolor look, earthy colors, soft outlines,
whimsical but grounded. No text, no watermark.
```

**Subsequent prompts** — repeat identity invariants, change only the scene:
```
Continue the story using the same character. Mara is now rescuing a
frightened squirrel after a winter storm.
Keep the same face, same short dark hair with blunt bangs, same freckles,
same orange knit sweater, same body proportions, same watercolor look,
same color palette. Do not redesign the character.
Snowy forest light, warm comforting mood. No text, no watermark.
```

State invariants **once as a block** that you copy verbatim each turn. This is how gpt-image-2 locks identity across scenes.

For higher-fidelity character lock with 5+ references, route to **Gemini Pro** — its multi-ref character-lock is still stronger than gpt-image-2's.

## Multi-image reference pattern

The `/v1/images/edits` endpoint accepts multiple reference images. Every reference is processed at high fidelity automatically.

**Label each input by role, reference them by index:**

```
Image 1: base scene to preserve.
Image 2: jacket reference.
Image 3: boots reference.

Instruction: Dress the person from Image 1 using the jacket from Image 2
and the boots from Image 3. Preserve the face, body shape, pose,
background, lighting, and framing from Image 1. Fit the garments
naturally with realistic folds and contact shadows. No extra accessories,
no text, no logos.
```

For brand-consistent variant work, pass logo + color swatch + typography specimen + vibe reference as labeled inputs. For 5+ character references with hard identity lock, use Gemini Pro instead.

## Vocabulary that works

**Photography terms** outperform generic quality words:

- **Lens:** "35mm lens," "50mm lens," "35mm film photograph," "macro," "medium format 80mm"
- **Aperture:** "shallow depth of field," "deep focus," "f/2.8", "f/8"
- **Lighting:** "soft coastal daylight," "golden hour," "rim lighting from behind," "diffused overcast light," "soft box lighting eliminating harsh shadows," "pools of amber light," "tasteful bokeh lights"
- **Film:** "subtle film grain," "natural color balance," "Kodak Portra 400", "CineStill 800T"

**Composition:** "centered," "eye-level," "medium close-up," "wide-angle view," "close-up macro shot," "bird's eye view," "top-down," "Dutch angle," "generous padding"

**Materials/texture:** "weathered skin," "visible wrinkles, pores," "worn materials," "fabric wear," "stitching repairs," "faded," "realistic textures", "paper grain", "brushed aluminum"

**Style references:** "flat design," "vector-like shapes," "hand-painted watercolor look," "documentary photography style," "professional studio photography," "cinematic composition," "whimsical and friendly," "technical illustration"

**Realism anchors:** "honest and unposed," "no glamorization," "no heavy retouching," "grounded, authentic, and unstyled, as if captured in a real moment", "visible pores and fine lines"

## Vocabulary that fails

- **Hype adjectives:** "stunning," "incredible," "epic," "masterpiece," "gorgeous," "insane detail," "8K," "ultra-detailed," "award-winning" — no effect, sometimes negative.
- **Contradictions:** "photorealistic cartoon," "minimalist detailed." Resolve by describing the blend: "photorealistic rendering with subtle anime-inspired character proportions."
- **Concept-art language for UI work:** "design sketch," "wireframe concept," "mood exploration" produce sketch-like output. **Describe UI as if it already exists** — *"a modern, beautiful, shipped SaaS dashboard"*.
- **Overusing "cinematic"** for documentary-style work — add `Avoid cinematic lighting, dramatic color grading, or stylized composition` for grounded realism.
- **Vague subjects without environment.** Add setting, lighting, time-of-day.
- **Culturally specific motifs without references** (regional dress, ceremonial objects, subculture markers) — still drift; provide reference images or explicit per-element descriptions.

## Quality progression

Start at `medium`, promote to `high` (+ custom high-resolution) only for hero assets. Don't max out by default — a `medium` preview plus one `high` final is typically cheaper and better-aimed than three `high` runs.

For print or retina hero work, go to `high` at 2K+ custom sizes. For everything else, `medium` at the default 1024² is often enough.

## Three operating modes

### Mode 1 — Generate from scratch

Endpoint: `/v1/images/generations`. Use the 5-slot template.

### Mode 2 — Edit one image

Endpoint: `/v1/images/edits`, one reference. Three-sentence pattern:

- **Change:** exactly what should change.
- **Preserve:** face, identity, pose, lighting, framing, background, geometry, text, layout.
- **Constraints:** no extra objects, no redesign, no logo drift.

Example (cleanup):
```
Remove every advertising sign and poster from the shop windows in this
storefront photograph. Preserve the awning, the brick facade, the
mullions, the window reflections, the sidewalk, and every person on the
sidewalk exactly. Reconstruct the glass naturally: clean reflections of
the street, no ghosting of the removed posters, no leftover adhesive
marks, no logo drift. Match the original lighting, white balance, and
film grain. No watermark.
```

### Mode 3 — Combine multiple images

Endpoint: `/v1/images/edits`, multiple references. Label each input by role, reference them by index. See "Multi-image reference pattern" above.

## Failure modes

- **Text fidelity degrades on dense small-font layouts over ~30-40 chars per line.** Break the layout into fewer, larger text blocks.
- **Multi-iteration drift** — fix by repeating the preserve list every turn and applying the one-revision-per-turn rule.
- **Overloaded prompts produce chaos** — break into base + iteration.
- **Concept-art language for UI** produces sketchy output. Use shipped-product language.
- **Culturally specific motifs** blur into generic interpretation — provide references.
- **Hyper-realistic portraits** are 4.5/5 but Gemini Pro is 5/5. Route portraits to Pro.
- **Moderation refuses:** explicit content, graphic violence, real-person impersonation, disallowed/trademarked logos.

## Pricing (per image, OpenAI API as of April 2026)

| Quality | 1024×1024 | 1024×1536 (portrait) | 1536×1024 (landscape) |
|---|---|---|---|
| `low` | $0.006 | $0.005 | $0.005 |
| `medium` | $0.053 | $0.041 | $0.041 |
| `high` | $0.211 | $0.165 | $0.165 |

Larger custom sizes scale proportionally with pixel count. Each streamed `partial_image` adds +100 output tokens. See [pricing.md](pricing.md) for full scenarios.

---

## Pattern library (copy-paste starting points)

### Photoreal editorial portrait
```
SCENE: A quiet classical museum gallery in soft afternoon light.
SUBJECT: A woman in her 30s standing casually in front of a large oil painting.
DETAILS: Natural smile, realistic skin texture, beige knit sweater, dark
jeans, white sneakers, eye-level full-body framing, marble floor
reflections, warm neutral color balance, shallow depth of field,
believable indoor ambient light.
USE CASE: Editorial lifestyle photograph.
CONSTRAINTS: No watermark, no logos, no extra people in the foreground,
no heavy retouching.
```

### Documentary street scene
```
SCENE: A narrow side street in Istanbul just after light rain at blue hour.
SUBJECT: A florist locking up for the night.
DETAILS: Wet pavement reflections, metal shutter half closed, green apron,
tired posture, a paper bundle of unsold tulips in one hand, mixed cool
street light and warm shop light, 50mm documentary feel, slight film
grain, realistic skin texture, no posed glamour.
USE CASE: Editorial newspaper feature photo.
CONSTRAINTS: No watermark, no logos, no tourist postcard color grading.
```

### Product photography (hero)
```
SCENE: Polished white Carrara marble countertop with subtle gray veining.
SUBJECT: A minimalist matte black ceramic coffee mug with a tapered
cylindrical silhouette and hand-formed rim.
DETAILS: Mug resting on the marble. Soft three-point softbox with gentle
rim light from behind right. Subtle contact shadow on the marble, soft
reflection in the matte glaze. Hasselblad X2D 80mm f/5.6, shallow depth
of field, marble veining gently blurred. Warm neutral color grading.
USE CASE: Editorial commercial e-commerce product photograph.
CONSTRAINTS: Realistic textures, accurate material rendering. No text, no
logo visible on the mug, no watermark. 1:1 aspect.
```

### Catalog cutout (before rembg)
```
SCENE: Pure flat #FFFFFF, no gradient, no texture, no shadow.
SUBJECT: A white-and-blue running sneaker with a knit upper and chunky
white midsole.
DETAILS: Centered, eye-level three-quarter view (side profile plus a hint
of the upper). Even softbox lighting from above and slightly left. 50mm
lens at f/8. Accurate product colors, no color grading.
USE CASE: Commercial e-commerce catalog photograph.
CONSTRAINTS: Pure white background, no drop shadow, no contact shadow,
no gradient. Generous padding, sneaker fills 70% of frame. No text, no
logos visible, no watermark. 1:1 aspect.
```
Then: `./scripts/rembg.sh --input sneaker.png --output sneaker-transparent.png`.

### Logo with wordmark
```
SCENE: Pure flat #FFFFFF, no gradient, no texture, no shadow.
SUBJECT: A warm, simple, timeless logo for "Field & Flour", a local bakery.
DETAILS: Flat-vector wheat-stalk and ampersand mark above the wordmark,
balanced negative space, geometric proportions. Wordmark "Field & Flour"
set in a clean geometric sans-serif in deep terracotta #B5533C. All
strokes clean, no gradients.
USE CASE: Brand logo sheet.
CONSTRAINTS: Single centered logo with generous padding (25% on all sides).
Pure white background, no shadow, no texture, no tagline. Render the
wordmark exactly as: Field & Flour (verbatim, no extra characters).
No watermark, no trademark symbols.
```

### Mobile app screen
```
SCENE: A realistic, shipped mobile app screen — not a design sketch.
SUBJECT: A minimalist to-do app called "DAYBREAK" on its main screen.
DETAILS:
- Top status bar: 9:41 AM, full battery, 5G.
- Headline (bold sans, top): "DAYBREAK".
- Subhead (regular sans, muted gray): "Tuesday, 23 April".
- Four tasks listed (left-aligned, 16pt body):
  - "Review quarterly notes"
  - "Call mom"
  - "Ship the image update"
  - "Pick up bread"
- One task checked off (first one).
- Muted cream background, deep navy accent, rounded sans serif, soft
  card shadows, perfect legibility, generous spacing.
USE CASE: iOS mobile app screenshot inside an iPhone 15 Pro frame,
natural titanium bezel, photographed straight on.
CONSTRAINTS: Render all text exactly as written (verbatim). No Lorem
Ipsum. No extra graphics outside the device frame. No watermark.
```

### SaaS dashboard (dense text)
```
SCENE: A shipped, production-grade web dashboard UI.
SUBJECT: "MetricsCo" SaaS analytics dashboard, light mode.
DETAILS:
- Left sidebar 240px: "MetricsCo" wordmark top, 6 nav items (Overview
  active, Users, Revenue, Reports, Integrations, Settings), each with
  a clean line icon.
- Top header: search bar "Search customers, events..."; notification
  bell with red dot; circular avatar "JD".
- KPI cards (3 across):
  - "Active Users" / "12,847" / "+8.2% this week"
  - "Monthly Recurring Revenue" / "$284K" / "+12.4% MoM"
  - "Uptime" / "99.94%" / "30-day SLA met"
- Weekly traffic chart, Mon-Sun x-axis, 1.2k-4.8k y-axis, two lines.
- 5-row customer table: Customer / Plan / MRR / Status / Last Active.
USE CASE: Production-grade web dashboard screenshot.
CONSTRAINTS: Inter font, 8px rounded corners, 1px light-gray dividers,
soft card shadows. Primary #0B5FFF, neutrals #F5F7FA and #1A1F36.
Realistic content, no Lorem Ipsum. Render every text element verbatim.
No watermark. 16:9 aspect.
```

### Poster with headline text (in-image typography)
```
SCENE: Dark, moody background with a soft amber spotlight from top right.
SUBJECT: An event poster for a jazz night called "MIDNIGHT SESSION".
DETAILS:
- Title (bold condensed serif, extra large, centered top, warm off-white):
  "MIDNIGHT SESSION"
- Subhead (thin mono type, centered below title, cream):
  "A FILM BY CHLOE ARIN · IN THEATERS OCTOBER 17"
- Hero element: a silhouette of a tenor saxophone bisecting the poster
  vertically, rim-lit from the amber spotlight.
- Credits block (7pt Helvetica, bottom center, cream):
  "DIR. CHLOE ARIN / PROD. LUNA PICTURES / DP. SAM WEBER"
USE CASE: A1 indie film poster in the tradition of Saul Bass.
CONSTRAINTS: Render all text exactly as written (verbatim). No extra
words. No duplicate text. No additional logos. No watermark.
```

### Billboard with short headline
```
SCENE: A roadside billboard at sunset, overcast sky softening the light.
SUBJECT: A product bottle on the right, generous negative space on the left.
DETAILS:
- Billboard headline (EXACT TEXT, one line only, left side):
  "Fresh and clean"
- Typography: bold sans serif, centered vertically on the left half, high
  contrast, clean kerning, easy to read from a distance.
USE CASE: Outdoor advertising billboard photograph.
CONSTRAINTS: Render the headline verbatim. No extra words. No duplicate
text. No additional logos. No watermark.
```

### Storefront cleanup (edit)
```
Remove every advertising sign and poster from the shop windows in this
storefront photograph.
Preserve the awning, the brick facade, the mullions, the window
reflections, the sidewalk, and every person on the sidewalk exactly.
Reconstruct the glass naturally: clean reflections of the street, no
ghosting of the removed posters, no leftover adhesive marks, no logo
drift. Match the original lighting, white balance, and film grain.
No watermark.
```

### Virtual try-on (multi-image)
```
Image 1: the woman to preserve.
Image 2: the jacket reference.
Image 3: the boots reference.

Dress the woman from Image 1 using the clothing from Images 2 and 3.
Preserve her face, facial features, skin tone, body shape, hands, pose,
hair, expression, background, camera angle, framing, and lighting
exactly. Replace only the clothing. Fit the garments naturally with
realistic folds, drape, occlusion, and shadows.
Do not add jewelry, bags, text, or logos.
```

### Character consistency — panel 1 (anchor)
```
SCENE: A hand-painted forest at golden hour.
SUBJECT: A main character for a children's book — a young forest helper
named Mara. Short dark hair with blunt bangs, warm brown skin, light
freckles, dark brown eyes, wearing an oversized orange knit sweater,
soft brown boots, and a small belt pouch. Kind expression, gentle eyes.
DETAILS: Hand-painted watercolor look, earthy colors, soft outlines,
whimsical but grounded.
USE CASE: Children's book opening illustration.
CONSTRAINTS: No text, no watermark.
```

### Character consistency — panel 2 (continuation)
```
SCENE: A snowy forest after a winter storm, warm afternoon light through
the clouds.
SUBJECT: The same character, Mara, rescuing a frightened squirrel.
DETAILS: Keep the same face, same short dark hair with blunt bangs, same
freckles, same orange knit sweater, same body proportions, same watercolor
look, same earthy color palette. Snowy forest light, warm comforting mood.
USE CASE: Children's book continuation illustration.
CONSTRAINTS: Do not redesign the character. Same watercolor style as
panel 1. No text, no watermark.
```

### Non-Latin signage (e.g. izakaya)
```
SCENE: A Shinjuku back-alley izakaya at 11 PM, rain on the pavement.
SUBJECT: The entrance — red chochin lantern glowing overhead, vertical
wooden sign next to the sliding door.
DETAILS:
- Red chochin lantern reads (EXACT, Japanese): "居酒屋 とんぼ"
- Vertical wooden sign reads (EXACT, Japanese): "刺身・焼き鳥・生ビール 500円"
- Fujifilm X100V 23mm f/2 ISO 1600, documentary feel, wet reflections,
  warm tungsten spilling out onto the street.
USE CASE: Documentary travel photograph.
CONSTRAINTS: All Japanese text rendered verbatim. Do not romanize. No
invented characters. No watermark.
```

### Hebrew logo (direct, no composite)
```
SCENE: Pure flat #FFFFFF, no gradient, no texture, no shadow.
SUBJECT: A modern, friendly logo for "אג'נטלה" (Agentleh), a Hebrew-first
WhatsApp AI assistant for small businesses.
DETAILS: A simple geometric abstraction combining a speech bubble and a
spark, drawn with clean strokes in WhatsApp green #25D366. Below the
mark, the Hebrew wordmark "אג'נטלה" in Heebo Bold, color matching the mark.
USE CASE: Brand logo sheet.
CONSTRAINTS: Single centered logo, 30% padding, flat vector aesthetic.
The Hebrew must read right-to-left in the correct letter order, no
mirrored glyphs, no nikud. Render the wordmark exactly as: אג'נטלה. No
watermark, no trademark symbols.
```
