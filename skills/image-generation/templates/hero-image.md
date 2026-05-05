# Marketing hero image / banner template

**Default model:**
- `gpt-image-2` at `quality=high` for heroes **without** a prominent human face (product hero, abstract scene, environment) — best composition control and prompt adherence, and it can now render brand-grade headline typography directly in the image if you want a single-layer deliverable.
- **Gemini Pro 4K** for heroes **with** a prominent human face or cinematic lifestyle content — Pro's skin/hair/film-grain quality is unmatched.
- Gemini Flash 2K for concept exploration.

## Required inputs

- Brand / product name + what it sells
- Headline copy: decide upfront whether to render it in-image (gpt-image-2) or composite in post (Gemini Pro)
- Visual concept (what's in the image)
- Mood (energetic / calm / aspirational / playful / serious / nostalgic)
- Color story (warm / cool / monochrome / brand palette with hex codes)
- Aspect ratio (16:9 web hero / 21:9 ultra-wide / 4:5 social / 9:16 vertical)
- Where headline goes (top-left / center / bottom-right) — affects composition

## gpt-image-2 variant (labeled) — DEFAULT FOR NON-PORTRAIT HEROES

### With in-image headline

```
BACKGROUND: [LOCATION/ENVIRONMENT, TIME OF DAY, MOOD].

SUBJECT: [CONCRETE VISUAL DESCRIPTION].

DETAILS: [COMPOSITION — framing, leading lines, where the eye lands].
[LIGHTING — e.g., "golden hour, soft rim light from behind"]. [STYLE —
e.g., "editorial photography, medium-format film look, cinematic color
grading"]. Color palette: [HEX REFERENCES].

HEADLINE: Render the headline "[EXACT COPY]" in the [TOP-LEFT / CENTER /
BOTTOM-RIGHT] area of the frame. Typography: [BOLD SANS / GEOMETRIC
SERIF / etc.], [FONT SIZE feeling — "large display weight"], color
[HEX], tight kerning. Include ONLY this headline text, verbatim.

CONSTRAINTS: [ASPECT]. No watermark, no trademark symbols, no extra text
beyond the headline.
```

### Without in-image headline (reserve text area for post-composite)

```
BACKGROUND: [LOCATION/ENVIRONMENT, TIME OF DAY, MOOD].

SUBJECT: [CONCRETE VISUAL DESCRIPTION].

DETAILS: [COMPOSITION — include "leave a clean text area in the
(TOP-LEFT/CENTER/BOTTOM-RIGHT) sized approximately (N%) of the canvas
with (solid soft tone / gradient / blurred backdrop) suitable for
overlaying a headline in post-production"]. [LIGHTING]. [STYLE].
[COLOR PALETTE with hex codes].

CONSTRAINTS: [ASPECT]. Do not render any text or typography in the
image. No watermark, no logos.
```

**Run with:** `--quality high --size 1536x1024` (16:9-ish) or `--size 2048x1152` (premium 16:9) or `--size 1024x1536` (portrait 2:3).

## Gemini Pro variant — DEFAULT FOR PHOTOREAL HUMAN HEROES

```
[SUBJECT — what's in the hero, with concrete details]. [ACTION — what's
happening, mood and motion]. [LOCATION/CONTEXT]. [COMPOSITION — framing,
leading lines, where the eye lands. INCLUDE: a clean text area in the
(TOP-LEFT/CENTER/BOTTOM-RIGHT) sized approximately (N%) of the canvas
with (solid soft tone / gradient / blurred backdrop) suitable for
overlaying a headline in post-production. Do not render any text in the
image]. [STYLE — editorial photography / cinematic illustration / 3D
render / etc.]. [LIGHTING — golden hour / soft overcast / studio
three-point / rim light, etc.]. [COLOR GRADING — warm/cool, palette
references with hex codes].
```

**Run with:** `--model gemini-3-pro-image-preview --aspect 16:9 --size 4K`.

## Filled example — SaaS landing hero (with headline, gpt-image-2)

**Brief:** Hero for "MetricsCo" SaaS analytics. Headline "Stop guessing. Start measuring." Visual: a desk with data on a holographic display. Aspirational, modern. Cool blue palette. 16:9. Headline goes top-left.

**gpt-image-2 prompt:**
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
display weight, white color, tight kerning, left-aligned. Include ONLY
this headline text, verbatim.

CONSTRAINTS: 16:9 aspect. No watermark, no trademark symbols, no extra
text beyond the headline.
```

**Run with:** `--quality high --size 2048x1152`.

## Filled example — same brief, Gemini Pro with post-composite

```
A modern wooden desk in a softly-lit office, with a translucent floating
holographic display of glowing data charts and metrics. Composition: the
desk and display placed in the right two-thirds of the frame, with a
clean text area in the top-left third sized about 30% of the canvas
showing a soft out-of-focus office wall in muted cool tones suitable for
overlaying a headline in post-production. Do not render any text in the
image. Style: editorial photography, shot on medium-format film,
cinematic color grading. Lighting: cool morning light from a large window
on the left, with subtle warm fill from the holographic display. Color
palette: deep navy #0B5FFF accents from the display, neutral cool grays
for the office. 16:9 aspect.
```

**Run with:** `--model gemini-3-pro-image-preview --aspect 16:9 --size 4K`, then composite "Stop guessing. Start measuring." in the top-left via Figma.

## Hero with people — multi-character consistency

When the hero has multiple recognizable people, use Gemini Pro and pass character references (up to 5 character refs). See [../reference/gemini-image.md](../reference/gemini-image.md) §"Reference images / style consistency."

## Tips

- **gpt-image-2 can render in-image headlines reliably** at ≤30-40 chars per line. Longer copy still degrades; reserve a text area and composite instead.
- **Always specify lighting concretely.** "Soft" alone is meaningless. "Soft cool morning light from a large window on the left" is actionable.
- **Avoid stock-photo aesthetics.** If output looks too "AI stock photo," append: *"Avoid generic stock-photo aesthetic, dramatic color grading, or stylized composition. Should feel honest and unposed."*
- **For ultra-wide 21:9 banners**, Gemini supports it directly; gpt-image-2 can't exceed the 3:1 ratio cap.
- **For portrait headshots anchoring a hero**, route to Gemini Pro — its photoreal portraiture is a notch above gpt-image-2.
