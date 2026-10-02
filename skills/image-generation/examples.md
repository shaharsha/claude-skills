# Worked examples

A library of full prompts that produced good results, with the model used and the reasoning. Use these as patterns to adapt, not verbatim copy.

## Logos

### Example 1 — Bakery wordmark + mark, GPT Image 2.5 Sunburst (labeled segments)

```
BACKGROUND: Pure flat #FFFFFF, no gradient, no texture, no shadow.

SUBJECT: A warm, simple, timeless logo for "Field & Flour", a local bakery.

DETAILS: A stylized flat-vector wheat-stalk and ampersand mark above the
wordmark, balanced negative space, geometric proportions. Below the mark,
the wordmark "Field & Flour" set in a clean geometric sans-serif in deep
terracotta #B5533C. All strokes clean, no gradients, suitable for SVG
conversion.

CONSTRAINTS: Single centered logo with generous padding (25% on all sides).
Pure white background, no shadow, no texture, no tagline. Render the
wordmark "Field & Flour" exactly once, verbatim. No other text. No
watermark, no trademark symbols.
```

**Model:** `gpt-image-2.5-sunburst` at `max` (the script default), `--size 1024x1024` (≈ $0.21). **Why this model:** Best text fidelity in any model for the wordmark; one-shot wins are common. Exploring several marks first? Add `--draft` (Flare `medium`, ~1¢) and promote the pick as in Example 14.

### Example 2 — Tech startup mark, transparent PNG

One call, native transparency on GPT Image 2.5:
```
BACKGROUND: Transparent, no backdrop, no texture, no shadow.

SUBJECT: A precise, modern, technical logo for "Quanta", a developer-tools startup.

DETAILS: A minimalist geometric monogram combining a "Q" and a circuit
trace, balanced negative space. Below the mark, the wordmark "QUANTA" set
in a bold geometric sans-serif. Monochrome black #000000 only.

CONSTRAINTS: Single centered logo, 30% padding, scales cleanly from
favicon to billboard. Transparent background, no drop shadow, no contact
shadow. Flat design, minimal strokes, no gradients. Render the wordmark
"QUANTA" exactly once, verbatim. No other text. No watermark, no
trademark symbols.
```

```bash
./scripts/openai-image.sh --background transparent --output-format png \
  --size 1024x1024 --output logo-quanta-v1-transparent.png --prompt "..."
```

**Model:** `gpt-image-2.5-sunburst` at `max`, native transparent PNG. **Why this pipeline:** transparency is native on 2.5 (png/webp), so there's no rembg step; check edges on a dark and a light backdrop. If the mark will also be an iOS app icon, ship a flattened copy - Apple rejects 1024×1024 App Store icons with transparency. rembg stays for Gemini outputs or cutting an existing logo.

### Example 3 — Hebrew brand, direct (one-stage, GPT Image 2.5)

```
BACKGROUND: Pure flat #FFFFFF, no gradient, no texture, no shadow.

SUBJECT: A modern, friendly logo for "אג'נטלה" (Agentleh), a Hebrew-first
WhatsApp AI assistant for small businesses.

DETAILS: A simple geometric abstraction combining a speech bubble and a
spark, suggesting communication and intelligence, drawn with clean strokes
in WhatsApp green #25D366. Below the mark, the Hebrew wordmark "אג'נטלה"
rendered right-to-left in Heebo Bold, color matching the mark.

CONSTRAINTS: Single centered logo, 30% padding, flat vector aesthetic,
suitable for SVG conversion. Pure white background, no shadow. The Hebrew
text must read right-to-left in the correct letter order, with no mirrored
glyphs and no nikud. Render the wordmark "אג'נטלה" exactly once,
verbatim. No other text. No watermark, no trademark symbols.
```

**Model:** `gpt-image-2.5-sunburst` at `max`, `--size 1024x1024`. **Why this model:** Sunburst (`high` and `max`) and Flare `medium` all rendered Hebrew correctly in a 2026-10-02 test. Still check the output letter by letter - final forms ם ן ץ ף ך especially. If it fails after 3 attempts, fall back to the two-stage composite workflow - see [reference/hebrew-rtl.md](reference/hebrew-rtl.md).

## Icons

### Example 4 — 6-icon UI set, single grid call

```
BACKGROUND: Plain white background, no texture, no shadow.

SUBJECT: A set of 6 UI icons arranged in a 3×2 grid, evenly spaced.

DETAILS: Icons in reading order (left-to-right, top-to-bottom):
1. home (house outline)
2. user (head and shoulders)
3. settings (gear)
4. search (magnifying glass)
5. bell (notification)
6. cart (shopping basket)

Style for ALL icons: 2px black stroke (#000000), rounded stroke caps, no
fill, same optical weight across all icons, centered in each tile at
consistent scale, 30% padding around each icon. Flat 2D vector aesthetic,
suitable for a design system.

CONSTRAINTS: No overlap between tiles. No text labels. No extra decorative
elements. Monochrome black on plain white. No watermark.
```

**Model:** `gpt-image-2.5-sunburst` at `max`, `--size 1024x1024`. **Why this model:** Sunburst's prompt adherence locks style consistency across all 6 icons in a single call.

### Example 5 — Single transparent icon

Native transparent on GPT Image 2.5 (`--background transparent --output-format png`):
```
BACKGROUND: Transparent, no texture, no shadow.

SUBJECT: A single minimalist line icon of a magnifying glass over a document.

DETAILS: 2px stroke weight, rounded stroke ends, no fill, monochrome
#000000. Flat 2D vector aesthetic, centered, 30% padding.

CONSTRAINTS: Transparent background, no drop shadow. Suitable for a design
system. No text, no watermark.
```

Already have it on white (a Gemini output, or an older render)? Since this is pure monochrome line art, ImageMagick color-key works from any source and is sharper than rembg for 2-color line art:
```bash
magick icon.png -fuzz 5% -transparent white icon-transparent.png
```

## UI mockups

### Example 6 — Mobile onboarding screen, GPT Image 2.5

```
BACKGROUND: A realistic, shipped mobile app screen — not a design sketch.

SUBJECT: A warm, minimal iOS onboarding screen for "Field & Flour", a
local bakery loyalty app.

DETAILS:
- Status bar (9:41, full battery, 5G).
- Top 45% of the screen: a warm illustration of a rustic baguette and
  assorted pastries on a wooden board, soft warm light.
- Headline "Welcome to Field & Flour" in a friendly bold serif typeface.
- Subheading "Earn a free pastry with every 5 visits." in a clean
  sans-serif at 60% opacity.
- A wide rounded primary button labeled "Get Started" in deep terracotta
  #B5533C.
- A smaller text link below reading "Already a member? Sign in" in muted gray.

Style: warm cream background #F3EAD3, generous whitespace, 16pt body text.
Device frame: iPhone 15 Pro natural titanium bezel, photographed straight on.

CONSTRAINTS: Realistic content, no Lorem Ipsum. Render all text exactly
as specified above (verbatim), each string exactly once. No other text.
No extra graphics outside the device frame. No watermark.
```

**Model:** `gpt-image-2.5-sunburst` at `max`, `--size 1024x1536` (≈ $0.165). **Why this model:** Hi-fi mobile UI with multiple text elements at different sizes - Sunburst's small-text fidelity at `max` keeps them all legible (`high` on 2.5 is only about old gpt-image-2 `medium`).

### Example 7 — SaaS dashboard, GPT Image 2.5 at 2560×1440

```
BACKGROUND: A shipped, production-grade web dashboard UI.

SUBJECT: "MetricsCo" SaaS analytics dashboard, light mode.

DETAILS:
- Left sidebar 240px wide: "MetricsCo" wordmark at top, 6 nav items
  (Overview active, Users, Revenue, Reports, Integrations, Settings),
  each with a clean line icon.
- Top header: search bar with placeholder "Search customers, events...";
  notification bell with small red dot; circular avatar showing "JD".
- KPI cards top-row (3 across):
  - Card 1: "Active Users" value "12,847" trend "+8.2% this week"
  - Card 2: "Monthly Recurring Revenue" value "$284K" trend "+12.4% MoM"
  - Card 3: "Uptime" value "99.94%" trend "30-day SLA met"
- A large multi-line chart titled "Weekly Traffic", x-axis Mon-Sun,
  y-axis 1.2k-4.8k, two lines (this week vs last week).
- A 5-row data table with columns: Customer, Plan, MRR, Status, Last
  Active. Rows show "Acme Corp / Enterprise / $4,200 / Active / 2 hours
  ago" and four similar realistic SaaS rows.

Style: modern flat design, white background, 1px light-gray dividers,
subtle soft shadows on cards, 8px rounded corners, Inter font family.
Primary #0B5FFF, neutral grays #F5F7FA and #1A1F36.

CONSTRAINTS: Realistic content, no Lorem Ipsum. Render all text exactly
as specified above (verbatim), each string exactly once. No other text.
No watermark. 16:9 aspect.
```

**Model:** `gpt-image-2.5-sunburst` at `max`, `--size 2560x1440`. **Why this model:** Dense small-text regions (KPI trends, table cells, axis labels). Sunburst leads every text-rendering leaderboard, and layout/hierarchy is where 2.5 improved most.

## Hero images

### Example 8 — SaaS landing hero with in-image headline, GPT Image 2.5

```
BACKGROUND: A modern, softly-lit office with cool morning light from a
large window on the left.

SUBJECT: A sleek wooden desk with a translucent floating holographic
display of glowing data charts and metrics.

DETAILS: Subject placed in the right two-thirds of the frame. Cool morning
light from the window, subtle warm fill from the holographic display
creating a soft rim. Style: editorial photography, medium-format film
look, cinematic color grading. Color palette: deep navy #0B5FFF accents
from the display, neutral cool grays for the office.

HEADLINE: Render the headline "Stop guessing. Start measuring." in the
top-left third of the frame. Typography: bold geometric sans-serif, large
display weight, white color, tight kerning, left-aligned. Render the
headline exactly once, verbatim.

CONSTRAINTS: 16:9 aspect. No watermark, no trademark symbols. No other
text beyond the headline.
```

**Model:** `gpt-image-2.5-sunburst` at `max`, `--size 2048x1152`. **Why this model:** Sunburst renders brand-grade headline typography directly in the image - no post-composite needed for short headlines.

### Example 9 — Portrait-anchored hero, Gemini Pro

```
A person in their late 30s sitting at a sleek wooden desk in a modern,
softly-lit office, leaning forward and studying a translucent floating
holographic display of glowing data charts and metrics. Their expression
is focused and intrigued. Composition: subject placed in the right
two-thirds of the frame, with a clean text area in the top-left third
sized about 30% of the canvas showing a soft out-of-focus office wall in
muted cool tones suitable for overlaying a headline in post-production.
Do not render any text in the image. Style: editorial photography, shot
on medium-format film, cinematic color grading. Lighting: cool morning
light from a large window on the left, with subtle warm fill from the
holographic display creating a soft rim around the subject. Color
palette: deep navy #0B5FFF accents from the display, neutral cool grays
for the office, subtle warm skin tones. 16:9 aspect.
```

**Model:** `gemini-3-pro-image` (`--model pro`), `--aspect 16:9 --size 4K` ($0.24). **Then composite "Stop guessing. Start measuring." in the top-left text area via Figma.** **Why Gemini Pro here:** the hero is anchored by a human face. Sunburst `max` leads the portrait votes, so render it first; reviewers call its close-up skin over-sharpened on zoom, so this Pro render is the comparison when skin is the point - let the human pick.

## Product shots

### Example 10 — Premium ceramic mug hero (GPT Image 2.5)

```
BACKGROUND: Polished white Carrara marble countertop with subtle gray
veining.

SUBJECT: A minimalist matte black ceramic coffee mug with a slightly
tapered cylindrical silhouette and hand-formed rim.

DETAILS: Mug resting on the marble. Lit by a soft three-point softbox
setup with a gentle rim light from behind right, creating a subtle
contact shadow on the marble and soft reflections in the matte glaze.
Captured with an 85mm lens at f/2.8, shallow depth of field with the
marble veining gently blurred in the background. Style: editorial
commercial e-commerce photography, warm neutral color grading.

CONSTRAINTS: 1:1 aspect. Realistic textures, accurate material rendering.
No text, no logo visible on the mug, no watermark.
```

**Model:** `gpt-image-2.5-sunburst` at `max`, `--size 1024x1024`.

### Example 11 — Catalog cutout sneaker, native transparent (GPT Image 2.5)

```
USE: Commercial e-commerce catalog cutout.

SUBJECT: A white-and-blue running sneaker with a knit upper and chunky
white midsole, isolated object.

DETAILS: Centered, eye-level three-quarter view (side profile plus a hint
of the upper). Lit by even softbox lighting from above and slightly left,
no harsh shadows. Captured with a 50mm lens at f/8. Clean commercial
e-commerce catalog photography, accurate product colors, no color grading.

CONSTRAINTS: Transparent background, no drop shadow, no contact shadow.
Generous padding, sneaker fills 70% of frame. Realistic textures, accurate
material rendering. No text, no logos visible on the sneaker, no
watermark. 1:1 aspect.
```

**Model:** `gpt-image-2.5-sunburst` at `max`, `--background transparent --output-format png --size 1024x1024`. **Why this pipeline:** verified 2026-10-02, Sunburst returns a real RGBA alpha channel, so one call replaces generate-on-white + rembg. Use `scripts/rembg.sh` (birefnet-general) only for a Gemini render or an existing product photo; for pure line-art icons, ImageMagick color-key.

## Edits / iterations

### Example 12 — Gemini "change X, keep Y" edit

```
Using the provided image, change only the color of the sofa to deep navy
blue (#1A2A4A). Keep everything else in the image exactly the same —
lighting, framing, all other objects, the texture of the wall, the
character in the background, all proportions and composition.
```

**Model:** `gemini-3-pro-image` (`--model pro`), called with `--ref previous-output.png`.

### Example 13 — GPT Image 2.5 virtual try-on via /edits

```
Edit the image to dress the woman using the provided clothing images. Do
not change her face, facial features, skin tone, body shape, pose, or
identity in any way. Preserve her exact likeness, expression, hairstyle,
and proportions. Replace only the clothing, fitting the garments
naturally to her existing pose and body geometry with realistic fabric
behavior. Match lighting, shadows, and color temperature to the original
photo so the outfit integrates photorealistically, without looking pasted
on. Do not change the background, camera angle, framing, or image
quality, and do not add accessories, text, logos, or watermarks.
```

**Model:** `gpt-image-2.5-sunburst` `/edits` endpoint (via `scripts/openai-image.sh --ref model.png --ref clothing.png`, up to 16 references). Every reference is processed at high fidelity automatically - no flag needed.

### Example 14 - Promote an approved Flare draft (Sunburst max edit)

Drafts first, cheap: `./scripts/openai-image.sh --draft --size 1024x1536 --n 4 --output poster-draft.png --prompt "..."` (Flare `medium`, ~1¢ each). Then promote the user's pick with an edit, not a re-roll:

```
Image 1 is an approved draft. Re-render it as the final at full detail:
change only the rendering quality - sharper linework, richer texture,
cleaner typography. Preserve exactly: the composition, every object and
its position, the people and their poses, the color palette, and all
text - "קפה של שכונה" and "GRAND OPENING" - each appearing once in the
same place and typography. No new elements, no extra text, no watermark.
```

**Model:** `gpt-image-2.5-sunburst` at `max` (the default), `--ref poster-draft-3.png --size 1024x1536` - always the same `--size` as the draft. **Why this pipeline:** a fresh generation composes a new picture, so re-running the prompt at `max` loses the look the user chose. Verified 2026-10-02 on a Flare `medium` poster with Hebrew + English text: composition, poses, colors and every string kept; texture and detail improved; $0.18, 85 s.

## Common reasons examples fail

When adapting these templates, watch for:

1. **Vagueness creep** — replacing "matte black ceramic with hand-formed rim" with "black mug" tanks the result.
2. **Forgetting "real content" instruction** for UIs — produces Lorem Ipsum.
3. **Putting aspect ratio in Gemini prompts** — set it in `--aspect`, not the prompt text.
4. **Negative prompts on Gemini** — "no people" → say "empty street."
5. **Missing the text-area reservation in hero prompts** (if you're post-compositing) — composited headlines collide with the subject.
6. **Forgetting the "keep everything else exactly the same" clause** on Gemini edits — drift compounds.
7. **Generating on white + rembg for an OpenAI transparent asset** - transparency is native on 2.5: `--background transparent --output-format png` (or webp; never jpeg). rembg is for Gemini outputs and existing images.
8. **Shipping a close-up portrait without a skin check** - Sunburst `max` leads portrait votes but can read over-sharpened on zoom; compare with Gemini Pro 4K when skin is the point.
9. **Copying `--quality high` from gpt-image-2 habits** - on 2.5 `high` ≈ old `medium`; `max` (the default) ≈ old `high`. Never `auto`.
10. **Re-rolling an approved draft at `max`** - you get a different picture. Promote with a `--ref` edit (Example 14).
