# OpenAI GPT Image 2.5 (Sunburst, Flare) — operational reference

Read this before writing any prompt for an OpenAI image model. Primary source: OpenAI's **GPT Image 2.5 prompting guide** (developers.openai.com/api/docs/guides/image-prompting — append `.md` for the raw markdown), which replaced the Cookbook notebook in September 2026. Also: the image-generation guide, the two model pages, and measurements made for this skill on 2026-10-02.

**Released 2026-09-08.** Sunburst and Flare took #1 and #2 on Artificial Analysis and Arena for text-to-image, image editing, text rendering and portraits (late Sept 2026), ahead of `gpt-image-2`.

## API surface

- **Generate:** `POST https://api.openai.com/v1/images/generations`
- **Edit / inpaint / combine:** `POST https://api.openai.com/v1/images/edits` (up to 16 reference images; optional mask applies to the first)
- **Also:** `v1/batch` (half price) and the Responses API `image_generation` tool — where you must set `model` explicitly, because the tool's default is still `gpt-image-1`, which shuts down 2026-10-23.
- **Auth:** `Authorization: Bearer $OPENAI_IMAGE_API_KEY`

| Model ID | Snapshot | Official positioning |
|---|---|---|
| `gpt-image-2.5-sunburst` | `gpt-image-2.5-sunburst-2026-09-08` | "Our most capable model for image generation and editing" — the base model, "higher image quality than GPT Image 2", best editing precision |
| `gpt-image-2.5-flare` | `gpt-image-2.5-flare-2026-09-08` | "Fast, high-quality everyday image generation" — the small model, "image quality comparable to GPT Image 2", ~50% lower latency |
| `gpt-image-2` | `gpt-image-2-2026-04-21` | Previous generation; not deprecated |

**This skill's split:** Sunburst for anything that may ship; Flare for drafts. (OpenAI suggests Flare as most apps' default — this skill favours quality.) **Prompts are identical across the two** — OpenAI's guide uses the same prompts for both, so a prompt tuned on Flare drafts carries over to the Sunburst final unchanged.

Retiring: `gpt-image-1` (2026-10-23); `gpt-image-1.5`, `gpt-image-1-mini`, `chatgpt-image-latest` (2026-12-01).

## Parameters

| Param | Values | Notes |
|---|---|---|
| `quality` | `low` `medium` `high` `xhigh` `max` `auto` | **Re-cut on 2.5 — see below.** `xhigh`/`max` exist only on 2.5. Never `auto`: identical calls land on different budgets. |
| `size` | any `WxH` | Each edge ≤ 3840 and a multiple of 16; ratio ≤ 3:1; total 655,360–8,294,400 px (max 3840×2160). Above 2560×1440 is "experimental". |
| `background` | `opaque` `transparent` `auto` | **Transparent is native on 2.5** (png/webp only). Preview on `gpt-image-2`, reported flaky. |
| `output_format` | `png` `jpeg` `webp` | png for text/line art/transparency. |
| `output_compression` | 0-100 | jpeg/webp only. |
| `n` | 1-10 | Several variants of one prompt in one call. |
| `moderation` | `auto` `low` | |
| `stream` + `partial_images` | 0-3 | +100 output tokens per partial. |
| `input_fidelity` | — | Don't send it: `gpt-image-2` ignores it, 2.5 doesn't list it. References get high fidelity automatically. |

No `seed`, no `style`, no reasoning-effort control, no SVG/layers.

### The quality ladder was re-cut (the #1 migration trap)

| quality | gpt-image-2 output tokens | 2.5 output tokens |
|---|---|---|
| low | 157 | 157 |
| medium | 1,413 | 367 |
| high | 5,650 | 1,413 |
| xhigh | — | 2,511 |
| max | — | 5,650 |

(2048×1152, from Tosea's measurement against OpenAI's calculator. Confirmed for this skill 2026-10-02 at 1024×1536 on Sunburst: `high` 1,372 tokens / 35 s, `max` 5,488 tokens / 87 s; Flare `medium` 343 tokens / 15 s.)

So **2.5 `max` ≈ gpt-image-2 `high`**, and **2.5 `high` ≈ gpt-image-2 `medium`**. Map old settings up one rung. OpenAI's own advice: "Compare quality levels before rewriting the prompt", and "The same quality label does not imply the same image quality or response time across models."

**Promote a draft with an edit, not a re-roll.** A re-run composes a new image, so drafting at a low tier and re-running the prompt at `max` gives you a different picture. Pass the chosen draft as Image 1 to a Sunburst `max` edit instead:

```
Image 1 is an approved draft. Re-render it as the final at full detail: change only the
rendering quality — sharper linework, richer texture, cleaner typography. Preserve exactly:
the composition, every object and its position, [the people and their poses], the color
palette, and all text — [each quoted string] — each appearing once in the same place and
typography. No new elements, no extra text, no watermark.
```

`./scripts/openai-image.sh --ref draft.png --size <same as draft> --output final.png --prompt "..."` (Sunburst `max` is the default). Verified 2026-10-02 on a Flare `medium` poster with Hebrew + English text: composition, poses, colors and every string were kept; texture and detail improved; $0.18, 85 s. Always keep the same `--size` as the draft.

## OpenAI's 8 prompting fundamentals (2.5 guide, verbatim)

1. "**Define the result.** Name the subject and intended use, such as a product photograph, advertisement, or diagram. Specify the composition, aspect ratio, and important placement constraints. For complex requests, organize the prompt as scene, subject, details, and constraints, using labeled sections."
2. "**Choose a maintainable format.** Short prompts, descriptive paragraphs, JSON-like structures, instructions, and tags can all express the same intent. Choose the format that makes the requirements easiest to read and update rather than relying on special syntax."
3. "**Describe visible details.** Name materials, lighting, colors, and the visual medium. Request 'photorealistic' or 'real photograph' explicitly when that is the goal, and describe framing and texture. Treat camera specifications as cues for appearance, not a guarantee of exact physical simulation. For wide, cinematic, low-light, rainy, or neon scenes, specify scale, atmosphere, and color instead of relying on mood words alone."
4. "**Specify people and actions.** Describe body framing, relative scale, gaze, and interaction with objects…" — e.g. "full body visible, feet included", "hands naturally gripping the handlebars".
5. "**Specify exact text.** Put required wording in quotes and describe its position and typography. Spell unusual words or brand names letter by letter when needed. Ask for no extra text, then check spelling and legibility in the output."
6. "**Separate changes from constraints.** For edits, say 'change only X' and list the details to preserve, such as identity, geometry, layout, lighting, or labels. State exclusions such as unwanted text, logos, or watermarks."
7. "**Assign roles to references.** Identify each input by number and purpose: subject, style, clothing, or background. Explain how the inputs should combine and which elements should move where."
8. "**Iterate deliberately.** Pass the previous output as the next edit input, request one change, and repeat the details to preserve… restate critical constraints if the result drifts."

Plus: "If a region must remain pixel-identical, composite the approved edit into the original image instead of relying on prompting alone."

### What changed from the gpt-image-2 habits

- **Text: quotes only.** The old "quotes or ALL CAPS" is gone. Quote the string, say where it goes, and say how many times it appears: "Render the tagline exactly once."
- **Camera specs are appearance cues, not physics.** "50mm, f/2.8" still steers the look; don't expect a simulation.
- **Mood words → scale, atmosphere, color.** "Moody" does less than "low tungsten light, wet asphalt reflecting red neon, wide frame".
- **Edits lock more than the subject.** Also name saturation, contrast, arrows, camera angle and surrounding objects that must not change.
- **Restate earlier edits each turn.** Without a mask the whole canvas regenerates; carry the full preserve list forward ("the mug must still be black, the sticky note must still be gone").

## The labeled-section prompt structure

Still the backbone for complex prompts (fundamental 1). One section per line or paragraph:

```
USE:         Artifact type and purpose — "marketing poster", "mobile UI screen", "product hero photograph".
SCENE:       Location, time, background, environment.
SUBJECT:     The focal point (who/what), framing, scale, gaze, action.
DETAILS:     Materials, lighting, colors (name + hex), medium, composition, texture.
TEXT:        Each string in quotes with role, position, typography — and "exactly once".
CONSTRAINTS: Exclusions ("no extra text, no watermarks, no unrelated logos") and what must be preserved.
```

Why USE matters: the model adjusts layout defaults by artifact type — "editorial magazine cover" composes differently from "infographic". **Length:** 2-5 lines for simple work; 8-15 for dense UI/infographics. Vagueness is penalized, length isn't. Prompts can run to 32,000 characters.

## Anti-slop rules

1. **Visual facts over praise.** ❌ "stunning, epic, masterpiece, 8K" ✅ "overcast daylight, brushed aluminum, chipped paint, clean kerning, soft bounce light". Hype doesn't render.
2. **Style tags need visual targets.** ❌ "minimalist brutalist editorial luxury" ✅ "cream background, heavy black condensed sans serif, asymmetrical type block, one hero object, generous negative space".
3. **Say the real thing.** If a transit kiosk must appear, write "transit kiosk".
4. **In edits: change only X, preserve Y, match physics.** "Replace the parked car with a vintage bicycle. Preserve the house, fence, driveway, landscaping, lighting direction and time of day exactly. Match the bicycle's scale and shadow to the scene."
5. **One revision per turn**, with the whole preserve list repeated.
6. **Name the failure modes you fear.** "No duplicated pins, no random text, no misspellings" works as an inline exclusion. (There's no negative-prompt parameter; inline exclusions are officially endorsed and used in nearly every OpenAI example.)

## Named references that trigger world knowledge

- **Film stocks:** `Kodak Portra 400`, `Fujifilm Pro 400H`, `CineStill 800T`, `Kodak Ektar 100`.
- **Cameras / lenses (as look cues):** `Hasselblad X2D 80mm`, `Fujifilm X100V 23mm`, `Leica M10 35mm f/1.4`.
- **Publications:** `editorial portrait for The New Yorker`, `Monocle cover treatment`, `Apartamento interiors feel`.
- **Designers / movements:** `Saul Bass`, `Swiss grid tradition`, `Memphis Group palette`, `Bauhaus typography`, `Dieter Rams product language`.
- **Era / place:** `1970s Manhattan`, `1990s Tokyo neon`, `early 2000s flash photography`.
- **Lighting archetypes:** `tungsten mixed with neon`, `golden hour low sun`, `soft box eliminating harsh shadows`.

## Text rendering rules

1. **Quote every literal string** and name its role: headline, subhead, badge, caption.
2. **Position + typography per string:** "headline, top, bold condensed sans, terracotta #C65D3B".
3. **Count it:** "each appears exactly once"; "no other text".
4. **Spell unusual words letter by letter:** `"F-I-E-L-D & F-L-O-U-R"`.
5. **Keep in-image text short.** Short text is reliable; dense small text is still the weak spot ("Mercantile" came back "Merchantile" in one tester's run). Testers keep landing on 3-4 words per block.
6. **Quality matters for text:** `max` on Sunburst for anything with small or dense text. `low`/`medium` smear small glyphs.
7. **Fonts:** OpenAI's own example names one ("modern sans-serif typography like Inter") with "clean kerning"; naming a font steers the character but isn't a guarantee.
8. **Hex colors:** no official guidance; pair the hex with a color name ("terracotta #C65D3B") so either can land.

### Multilingual / non-Latin text

Write each language as its own quoted, labeled block — never paraphrase or translate inside the prompt:

```
TEXT (exact, verbatim, each appears once):
- headline in Hebrew: "קפה של שכונה"
- below it in English: "GRAND OPENING"
Constraints: render the Hebrew right-to-left exactly as given, no Latin substitutions, no niqqud unless requested.
```

Verified 2026-10-02: this exact prompt rendered the Hebrew correctly on Sunburst `high`, Sunburst `max` and Flare `medium`. No published 2.5 Hebrew test exists beyond that — check every Hebrew output letter by letter (see [hebrew-rtl.md](hebrew-rtl.md)).

## Character consistency across scenes

Anchor the character once with identity invariants, then copy that block verbatim into every later prompt and change only the scene. OpenAI's 2.5 example uses labeled blocks:

```
Character: Mara — short dark hair with blunt bangs, warm brown skin, light freckles,
  oversized orange knit sweater, dark jeans.
Theme: rescuing a frightened squirrel after a winter storm.
Style: hand-painted watercolor, earthy palette, soft outlines.
Character Consistency:
- Same orange knit sweater
- Same facial features, proportions, and color palette
Constraints:
- Do not redesign the character
- No text
- No watermarks
```

For hard identity lock across 5+ reference photos, compare with Gemini Pro (up to 14 references, 5 at high fidelity).

## Multi-image reference pattern

`/v1/images/edits` takes up to 16 references. Number them by role (fundamental 7):

```
Image 1: base scene to preserve.
Image 2: jacket reference.
Image 3: boots reference.

Dress the person from Image 1 using the jacket from Image 2 and the boots from Image 3.
Preserve the face, body shape, pose, background, lighting and framing from Image 1.
Fit the garments naturally with realistic folds and contact shadows.
No extra accessories, no text, no logos.
```

OpenAI's own combine example: "Place the dog from the second image into the setting of image 1, right next to the woman, use the same style of lighting, composition and background. Do not change anything else." Downscale large references — input image tokens cost $8/1M.

## Masks and inpainting

The mask applies to the first image and must be a PNG under 4 MB with the same dimensions. Masking is "entirely prompt-based. The model uses the mask as guidance, but may not follow its exact shape with complete precision." For pixel-exact regions, composite.

## Vocabulary that works

- **Lighting:** "soft coastal daylight", "golden hour", "rim light from behind", "diffused overcast", "soft box eliminating harsh shadows", "pools of amber light"
- **Composition:** "centered", "eye-level", "medium close-up", "top-down", "generous padding", "strict 4×4 grid, each item inside the central 68% of its cell" (explicit grid specs work well — layout and hierarchy are where 2.5 improved most)
- **Materials:** "weathered skin, visible pores", "brushed aluminum", "paper grain", "stitching repairs"
- **Realism anchors:** "honest and unposed", "no glamorization", "no heavy retouching", "photorealistic" / "real photograph" stated explicitly
- **UI:** describe it as shipped — "a modern, shipped SaaS dashboard" — not as a sketch

## Vocabulary that fails

- **Hype adjectives** ("stunning", "8K", "award-winning") — no effect, sometimes negative.
- **Contradictions** ("photorealistic cartoon") — describe the blend instead.
- **Concept-art words for UI** ("wireframe concept", "mood exploration") — produce sketches.
- **Overused "cinematic"** for documentary work — add "avoid cinematic lighting and dramatic grading".
- **Mood words alone** for night, rain, neon or wide scenes — give scale, atmosphere and color.

## Known failure modes on 2.5

- **Grain/noise in smooth areas** — skies, studio backdrops, low light. The most-reported 2.5 complaint (TechRadar reproduced it). Asking for "smooth gradients, no visual noise" did **not** fix it in TechRadar's test; check smooth regions at 100% zoom and denoise in post if it matters.
- **Small detail / microglyphs** blur, and fine detail can be lost across edits.
- **Edit drift** — lower than gpt-image-2 but real; restate the preserve list every turn, composite for pixel-exact regions.
- **Stylization:** some testers preferred gpt-image-2 for style transfer; logos were sharper on 2.5. If a stylized brief disappoints, A/B against `gpt-image-2` (`--model gpt-image-2 --quality high`).
- **Close-up skin:** wins votes, but reviewers call it over-sharpened on zoom. For skin-critical portraits, compare with Gemini Pro 4K.
- **Moderation:** strict — weapons, real-person likeness, trademarked logos get refused.

## Pricing

Same token rates for Sunburst, Flare and gpt-image-2: **image output $30/1M, image input $8/1M, text input $5/1M** (cached input $2/1M applies only via the Responses API tool; Batch API halves everything). Per-image cost therefore depends on output tokens — read the cost line `scripts/openai-image.sh` prints. Measured at 1024×1536: Sunburst `max` ≈ $0.165, Sunburst `high` ≈ $0.041, Flare `medium` ≈ $0.01. Artificial Analysis puts either model at `max` at ~$0.21 per 1024×1024. See [pricing.md](pricing.md).

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

### Catalog cutout (native transparent)
```
USE: Commercial e-commerce catalog cutout.
SUBJECT: A white-and-blue running sneaker with a knit upper and chunky
white midsole, isolated object.
DETAILS: Centered, eye-level three-quarter view (side profile plus a hint
of the upper). Even softbox lighting from above and slightly left. 50mm
look at f/8. Accurate product colors, no color grading.
CONSTRAINTS: Transparent background, no drop shadow, no contact shadow.
Sneaker fills 70% of the frame. No text, no logos visible, no watermark.
```
Run with: `--background transparent --output-format png --size 1024x1024` (Sunburst `max`). Verified 2026-10-02: Sunburst returns a real RGBA alpha channel. Check edges on a dark and a light backdrop before shipping.

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
