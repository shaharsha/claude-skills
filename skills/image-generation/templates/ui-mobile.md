# Mobile UI mockup template

**Default model:** `gpt-image-2.5-sunburst` at `quality=max` (the script default) for hi-fi - best-in-class small-text rendering keeps button labels, headlines, and status-bar elements legible (on 2.5, `high` is only about old gpt-image-2 `medium` and smears small glyphs). `gpt-image-2.5-flare` at `medium` (`--draft`) for exploring layouts; Gemini Flash or Lite for lo-fi wireframes. Gemini Pro only when the UI is anchored by a photoreal human subject (e.g. a photo hero in the top half).

## Required inputs

- App / product name
- Screen type (onboarding / feed / detail / settings / etc.)
- Device frame (iPhone 15 Pro / iPhone SE / Pixel 8 Pro / unframed canvas)
- Style direction (clean minimal / brutalist / playful / corporate)
- Color palette (primary + neutral grays, hex codes)
- Real content for headlines/labels (avoid lorem ipsum — name actual copy)
- Language — GPT Image 2.5 handles Hebrew/Arabic/CJK directly; see [../reference/hebrew-rtl.md](../reference/hebrew-rtl.md) for nuances.

## GPT Image 2.5 variant (labeled, shipped-product language) — DEFAULT

```
BACKGROUND: A realistic, shipped mobile app screen — not a design sketch.

SUBJECT: A [STYLE] [iOS / Android] app screen for "[APP NAME]", a [WHAT IT DOES].

DETAILS:
- Status bar (9:41, full battery, 5G).
- Top nav: [DESCRIBE — e.g., "back arrow, centered title 'Today's Market'"].
- Main content: [DESCRIBE — list real elements with real copy].
- Bottom tab bar: [DESCRIBE ICONS AND LABELS].

Style: [SPECIFIC — e.g., "clean minimal, [FONT] typography, 16pt body,
24pt headings, generous whitespace"]. Color: [BG HEX], [ACCENT HEX].
Device frame: [e.g., "iPhone 15 Pro natural titanium bezel, photographed
straight on"].

CONSTRAINTS: Realistic content, no Lorem Ipsum. Render every quoted
string verbatim, each exactly once; no other text. Shipped-product
appearance. No extra graphics outside the device frame. No watermark.
```

**Run with:** `--size 1024x1536` (portrait; Sunburst `max` ≈ $0.165). Explore with `--draft` (≈ 1¢), then promote the chosen screen with a Sunburst `max` edit: `--ref screen-draft.png --size 1024x1536` and the promote prompt from [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md), listing every quoted string in its preserve clause.

## Gemini Flash variant (wireframe / exploration)

```
Low-fidelity grayscale wireframe of a [SCREEN TYPE] for [APP NAME].
Placeholder boxes for images, simple line work, dashed outlines for
interactive areas, [PLACEHOLDER COPY]. Balsamiq / pen-and-paper aesthetic.
No color, no photography, no typography beyond labels. Inside a simple
unstyled phone outline.
```

**Run with:** `--model flash --aspect 9:16 --size 1K` (`gemini-3.1-flash-image`) or `--model lite` (cheapest, 1K only, JPEG).

## Filled example — onboarding screen

**Brief:** Onboarding screen for "Field & Flour" bakery loyalty app. Hero illustration of a baguette + pastries top half, headline "Welcome to Field & Flour", body "Earn a free pastry with every 5 visits.", primary button "Get Started", "Already a member? Sign in" link below.

**GPT Image 2.5 prompt:**
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

**Run with:** `--size 1024x1536` (Sunburst `max`, the default).

## Hebrew/RTL UI — default is direct now

Sunburst (`high`/`max`) and Flare `medium` rendered Hebrew correctly in a 2026-10-02 test, so render directly first and still check every string letter by letter (final forms ם ן ץ ף ך especially). Write the prompt in English, quote Hebrew strings literally, and add an RTL layout clause:

```
[Standard GPT Image 2.5 prompt]. The UI is in Hebrew, right-to-left. The
headline reads "ברוכים הבאים" (Hebrew, RTL, Heebo Bold). The primary
button reads "התחל כאן" (Hebrew, RTL). Navigation back arrow is on the
right side. All icons mirrored appropriately for RTL. Each quoted string
appears exactly once; no other text.
```

See [../reference/hebrew-rtl.md](../reference/hebrew-rtl.md) for the full rules + fallback to two-stage composite if the direct approach fails (rare now).
