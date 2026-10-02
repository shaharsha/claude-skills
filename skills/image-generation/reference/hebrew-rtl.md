# Hebrew & RTL text in generated images

**GPT Image 2.5 renders Hebrew directly.** Verified 2026-10-02: the same poster prompt (Hebrew headline "קפה של שכונה" + English "GRAND OPENING" + a "20% OFF" badge) came out with correct letters, order and direction on Sunburst `high`, Sunburst `max` and Flare `medium` — and survived a Sunburst `max` draft-promotion edit intact. No published third-party 2.5 Hebrew test exists yet, so the letter-by-letter check below is mandatory, not optional.

The default:
1. Generate directly on Sunburst (`max` for finals; Flare `--draft` while exploring). Quote the Hebrew exactly, say it's right-to-left, specify typography, and say it appears exactly once.
2. Read the output and check every letter (checklist below).
3. Fall back to the two-stage "generate text-free + composite" workflow only for the cases documented below.

Gemini is still the wrong tool for Hebrew text — Hebrew isn't on Google's best-performance language list for its image models. If the image must come from Gemini (e.g. a skin-critical portrait with Hebrew signage), keep the text out of the Gemini prompt and composite it.

## Letter-by-letter check (do this on every Hebrew output)

Read right to left, at 2× zoom:
- **Final forms** at word ends: ם ן ץ ף ך — the most common error is an open מ where ם belongs (e.g. the end of "לחם").
- **Lookalike pairs:** ח vs ה (closed top), ר vs ד, ב vs כ, ו vs ז, ס vs ם, ט vs ש.
- **Order and direction:** words in the right order, nothing mirrored, Hebrew and English blocks on the lines you asked for.
- **Count:** exactly the letters you quoted, no niqqud unless requested, no extra words, the string appearing once.
- **Legibility at final size:** logos at 128 px and 32 px; UI labels at 1×.

## When to use the direct (one-stage) workflow — default

- **Any Hebrew text ≤ ~30 characters per line** — logos, headlines, buttons, labels.
- **UI mockups with Hebrew labels** — GPT Image 2.5 renders standard Heebo / Assistant / Rubik letterforms directly.
- **Marketing headlines in Hebrew** — Sunburst `max` handles these one-shot most of the time.
- **Mixed Hebrew + English** — GPT Image 2.5 handles bidi better than any prior model.

Recipe:

```
BACKGROUND: [scene or flat backdrop].

SUBJECT: [the asset].

DETAILS: ... Render the Hebrew headline exactly as: "ברוכים הבאים"
(Hebrew script, right-to-left, modern sans-serif typography like Heebo Bold,
no nikud, high contrast).

CONSTRAINTS: [standard constraints]. The Hebrew text must read right-to-left
in the correct letter order, with no mirrored glyphs.
```

**Iterate up to 3 times** if the first result has glyph errors. If still wrong, fall back to two-stage.

## When to use the two-stage (composite) workflow — fallback

Still use the composite workflow for three specific cases:

| Use case | Why fallback is warranted |
|---|---|
| **Brand demands a specific licensed Hebrew typeface** (e.g. FbGalil, Narkiss Block Pro) that GPT Image 2.5 can't match | The model renders generic Heebo/Assistant-style letterforms; it won't match a specific commissioned typeface |
| **Hebrew text block longer than ~30-40 characters per line** | Any image model degrades on dense long-form text |
| **First 3 direct attempts showed glyph errors you can't prompt away** | Occasional failures happen; don't burn budget |

## Two-stage workflow — the canonical recipe

### Stage 1: generate the text-free image

Use Sunburst `max` (or Gemini Pro 4K for photoreal people scenes) at the target final resolution.

Prompt pattern:
```
[Standard prompt — BACKGROUND, SUBJECT, DETAILS, CONSTRAINTS]

Composition note: leave a clean text area in the [top-left / center / bottom-right]
sized approximately [N%] of the canvas. The text area should be a [solid color /
soft gradient / blurred background] with no detail, suitable for overlaying a
headline in post-production. Do not render any text or typography in this image.
```

Save the result as the *background plate*.

### Stage 2: composite Hebrew text

Three options, in increasing fidelity:

**Option A: SVG overlay (web)**
```html
<div style="position: relative; width: 1920px; height: 1080px;">
  <img src="background-plate.png" style="position: absolute; inset: 0;" />
  <div dir="rtl" style="
    position: absolute;
    top: 80px; right: 80px;
    font-family: 'Heebo', 'Assistant', sans-serif;
    font-size: 96px;
    font-weight: 700;
    color: white;
    text-shadow: 0 2px 8px rgba(0,0,0,0.4);
  ">
    ברוכים הבאים לאג'נטלה
  </div>
</div>
```
Render to PNG via headless Chrome / Puppeteer if you need a static asset.

**Option B: Pillow (Python, deterministic, scriptable)**
```python
from PIL import Image, ImageDraw, ImageFont
from bidi.algorithm import get_display

img = Image.open("background-plate.png").convert("RGBA")
draw = ImageDraw.Draw(img)
font = ImageFont.truetype("/path/to/Heebo-Bold.ttf", 96)

text = "ברוכים הבאים לאג'נטלה"
display_text = get_display(text)  # applies BIDI algorithm
draw.text((1840, 80), display_text, font=font, fill="white", anchor="rt")

img.save("final.png")
```

**Option C: Figma (highest design fidelity, manual)**
- Place background plate as image fill in a frame.
- Add a text layer with `dir=rtl` (Figma respects this for Hebrew/Arabic fonts).
- Use Heebo, Assistant, Rubik, or another web-safe Hebrew font.
- Export as PNG / SVG.

## Common failure modes when rendering Hebrew directly

If the direct workflow produces junk, look for:

- Letters rendering as lookalike Latin/Cyrillic glyphs (ב → b-shape) — rare on GPT Image 2.5, common on prior models.
- Missing final-form letters (ך ם ן ף ץ rendered as their non-final forms).
- Wrong letter order (read left-to-right instead of right-to-left).
- Mirrored / disconnected glyphs.
- Random extra letters added.
- Incorrect nikud when nikud wasn't requested.

When any of these appear, **re-generate with an explicit preservation clause**:
```
Render the Hebrew exactly as written. Do not alter letter order, do not add
vowels or nikud, do not substitute lookalike glyphs. Use Heebo Bold or a
similar modern sans-serif Hebrew typeface.
```

If still wrong after 3 attempts on Sunburst `max`, fall back to two-stage.

## Hebrew web-safe font reference

Use these Hebrew-supporting fonts for the composite stage (or to describe in a direct prompt):

| Font | Use for | Source |
|---|---|---|
| **Heebo** | UI, body text | Google Fonts |
| **Assistant** | UI, headings | Google Fonts |
| **Rubik** | UI, marketing | Google Fonts |
| **Frank Ruhl Libre** | Editorial, serif | Google Fonts |
| **Suez One** | Display, headlines | Google Fonts |
| **Secular One** | Display, headings | Google Fonts |

Default to **Heebo Bold** for UI mockups and **Assistant** for body text — they match Israeli web design conventions.

## Mixed Hebrew + English text

When the design has both Hebrew and English (common in Israeli marketing):

- GPT Image 2.5 handles bidi paragraphs well. Quote each block in its own language and specify direction: `"The Hebrew subtitle 'ברוכים הבאים' appears RTL above the English headline 'Welcome home' which appears LTR."`
- For the composite fallback, use a **single multilingual font** that supports both scripts (Heebo, Assistant, Rubik all do).
- Mind the visual weight balance — Hebrew letters tend to look heavier at the same size; bump English up by ~5-10% to match.

## Logos with Hebrew wordmarks — the brand-safe pipeline

For everyday Hebrew wordmarks, try GPT Image 2.5 direct first:

```
SUBJECT: A warm, simple logo for [brand].
DETAILS: [mark details]. Below the mark, the Hebrew wordmark "אג'נטלה"
rendered right-to-left in Heebo Bold, color [hex].
CONSTRAINTS: [standard]. The Hebrew must read right-to-left in correct
letter order with no mirrored glyphs. No nikud.
```

For **commissioned brand typefaces** or legally-prescribed Hebrew lockups:

1. Generate the **mark** (icon/symbol only) with Sunburst `max` at 1024². Prompt:
   ```
   [Brand brief]. Mark only — no text, no wordmark, no typography. Centered
   on pure white background, generous padding. Flat vector aesthetic, suitable
   for SVG conversion.
   ```
2. Vectorize the mark via the `brand-assets` skill (or Illustrator Image Trace, VectorizerAI).
3. Set the Hebrew wordmark in your design tool with the specific typeface.
4. Compose mark + wordmark in your locked brand layout.

This is the **only** pipeline that produces production-quality Hebrew logos when a specific commissioned typeface is non-negotiable.
