# Marketing hero image / banner template

**Default model:**
- `gpt-image-2.5-sunburst` at `quality=max` (the script default) for heroes — best composition control and prompt adherence, and it renders brand-grade headline typography directly in the image if you want a single-layer deliverable. This includes heroes **with** a prominent human face: Sunburst leads the portrait votes, so render it first.
- **Gemini Pro 4K** (`gemini-3-pro-image`) as the comparison render when close-up skin is the point and Sunburst's skin reads over-sharpened on zoom - let the human pick. Also for multi-character heroes that need identity lock across many reference photos.
- `gpt-image-2.5-flare` at `medium` (`--draft`, ~1¢) for concept exploration; Gemini Lite (`--model lite`, $0.034) is an alternative cheap tier.

## Required inputs

- Brand / product name + what it sells
- Headline copy: decide upfront whether to render it in-image (GPT Image 2.5) or composite in post (Gemini Pro, or long copy)
- Visual concept (what's in the image)
- Mood (energetic / calm / aspirational / playful / serious / nostalgic)
- Color story (warm / cool / monochrome / brand palette with hex codes)
- Aspect ratio (16:9 web hero / 21:9 ultra-wide / 4:5 social / 9:16 vertical)
- Where headline goes (top-left / center / bottom-right) — affects composition

## GPT Image 2.5 variant (labeled) — DEFAULT

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
[HEX], tight kerning. Render the headline exactly once, verbatim.

CONSTRAINTS: [ASPECT]. No watermark, no trademark symbols. No other text
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

**Run with:** `--size 1536x1024` (3:2) or `--size 2048x1152` (premium 16:9) or `--size 1024x1536` (portrait 2:3). Sunburst `max` is the default (≈ $0.165 at 1024×1536; the script prints the actual cost). Explore with `--draft` at the same size, then promote the chosen draft with a Sunburst `max` edit - `--ref hero-draft.png`, same `--size`, promote prompt from [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md) - instead of re-rolling, which composes a different picture.

## Gemini Pro variant — COMPARISON FOR SKIN-CRITICAL HUMAN HEROES

```
[SUBJECT — what's in the hero, with concrete details]. [ACTION — what's
happening, mood and motion]. [LOCATION/CONTEXT]. [COMPOSITION — framing,
leading lines, where the eye lands. INCLUDE: a clean text area in the
(TOP-LEFT/CENTER/BOTTOM-RIGHT) sized approximately (N%) of the canvas
with (solid soft tone / gradient / blurred backdrop) suitable for
overlaying a headline in post-production; the whole image is pure
photography, with every surface plain and unlettered]. [STYLE — editorial photography / cinematic illustration / 3D
render / etc.]. [LIGHTING — golden hour / soft overcast / studio
three-point / rim light, etc.]. [COLOR GRADING — warm/cool, palette
references with hex codes].
```

**Run with:** `--model pro --aspect 16:9 --size 4K` (`gemini-3-pro-image`, $0.24 at 4K).

## Filled example — SaaS landing hero (with headline, GPT Image 2.5)

**Brief:** Hero for "MetricsCo" SaaS analytics. Headline "Stop guessing. Start measuring." Visual: a desk with data on a holographic display. Aspirational, modern. Cool blue palette. 16:9. Headline goes top-left.

**GPT Image 2.5 prompt:**
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

**Run with:** `--size 2048x1152` (Sunburst `max`, the default).

## Filled example — same brief, Gemini Pro with post-composite

```
A modern wooden desk in a softly-lit office, with a translucent floating
holographic display of glowing data charts and metrics. Composition: the
desk and display placed in the right two-thirds of the frame, with a
clean text area in the top-left third sized about 30% of the canvas
showing a soft out-of-focus office wall in muted cool tones suitable for
overlaying a headline in post-production. Every surface in the scene is
plain and unlettered. Style: editorial photography, shot on medium-format film,
cinematic color grading. Lighting: cool morning light from a large window
on the left, with subtle warm fill from the holographic display. Color
palette: deep navy #0B5FFF accents from the display, neutral cool grays
for the office. 16:9 aspect.
```

**Run with:** `--model pro --aspect 16:9 --size 4K`, then composite "Stop guessing. Start measuring." in the top-left via Figma.

## Hero with people — multi-character consistency

When the hero has multiple recognizable people, Sunburst edits take up to 16 references numbered by role (see [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md) §"Multi-image reference pattern"). For hard identity lock across 5+ reference photos, compare with Gemini Pro and its character references (up to 5 character refs). See [../reference/gemini-image.md](../reference/gemini-image.md) §"Reference images / style consistency."

## Tips

- **Sunburst renders in-image headlines reliably** at ≤30-40 chars per line. Longer copy still degrades; reserve a text area and composite instead.
- **Smooth areas show grain on 2.5.** Skies and studio backdrops are the most-reported weak spot; check them at 100% zoom and denoise in post if it matters.
- **Always specify lighting concretely.** "Soft" alone is meaningless. "Soft cool morning light from a large window on the left" is actionable.
- **Avoid stock-photo aesthetics.** If output looks too "AI stock photo," append: *"Avoid generic stock-photo aesthetic, dramatic color grading, or stylized composition. Should feel honest and unposed."*
- **For ultra-wide banners**, 21:9 still fits GPT Image's 3:1 ratio cap (e.g. `--size 2688x1152`). Beyond 3:1 (4:1, 8:1) route to `gemini-3.1-flash-image` (`--model flash`).
- **For portrait headshots anchoring a hero**, render Sunburst `max` first; if skin reads over-sharpened at 100% zoom, render the Gemini Pro 4K variant too and let the human pick.
