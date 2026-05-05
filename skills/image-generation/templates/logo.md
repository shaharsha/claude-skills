# Logo prompt template

**Default model:** `gpt-image-2` at `quality=high` for finals. Gemini Flash for exploration. Gemini Pro only when the logo uses a photoreal element (e.g. a photographed mascot).

## Required inputs (collect from user before writing prompt)

- Brand name
- Industry / what the business does
- Personality (3 adjectives — e.g., "warm, simple, timeless")
- Style direction (flat vector / hand-drawn / geometric / monogram / wordmark / combination mark)
- Color palette (name colors + hex codes; or "monochrome black" / "monochrome white")
- Background (transparent / pure white / specific color)
- Language of wordmark — English, Hebrew, CJK, etc. gpt-image-2 handles all of them natively now.

## gpt-image-2 variant (labeled segments) — DEFAULT

```
BACKGROUND: Pure flat [#FFFFFF white / SPECIFIED HEX], no gradient, no texture, no shadow.

SUBJECT: A [3 PERSONALITY ADJECTIVES] logo for [BRAND NAME], a [INDUSTRY].

DETAILS: [STYLE DIRECTION — e.g., "A flat-vector geometric monogram combining the letters X and Y, balanced negative space, clean proportions"]. Below the mark, the wordmark "[EXACT BRAND NAME]" set in a [TYPOGRAPHY — e.g., "bold geometric sans-serif"]. Color: [HEX], all strokes clean, no gradients [unless specified].

CONSTRAINTS: Single centered logo with generous padding (25% on all sides). [BACKGROUND SPEC]. No shadow, no texture, no tagline. Render the wordmark exactly as: [BRAND NAME] (verbatim, no extra characters). No watermark, no trademark symbols.
```

**Run with:** `--quality high --size 1024x1024` (or 2048×2048 for premium finals).

**For transparent PNG:** add `"Isolated on flat #FFFFFF, no drop shadow, no contact shadow"` to CONSTRAINTS, then run through `scripts/rembg.sh`. See [../reference/transparent-backgrounds.md](../reference/transparent-backgrounds.md).

**For pure monochrome line art:** use ImageMagick color-key instead of rembg — `magick in.png -fuzz 5% -transparent white out.png` gives mathematically perfect alpha.

## Gemini Flash variant (exploration only)

```
Create an original, non-infringing logo for [BRAND NAME], a [INDUSTRY].
The logo should feel [3 PERSONALITY ADJECTIVES]. [STYLE DIRECTION].
[COLOR DESCRIPTION]. Composition: single centered logo with generous
padding (25% on all sides), pure white background, crisp edges, suitable
for SVG conversion.
```

**Run with:** `--model gemini-3.1-flash-image-preview --aspect 1:1 --size 1K`. Use for cheap exploration; promote the keeper to gpt-image-2 high for the final.

## For brand-consistent variant set (multiple logos in same style)

Two paths:

1. **gpt-image-2 multi-reference:** pass logo + color swatch + typography reference + vibe reference to `/v1/images/edits`. Every reference is processed at high fidelity automatically. See [../reference/openai-gpt-image-2.md](../reference/openai-gpt-image-2.md) §"Brand-consistent variant workflow."
2. **Gemini Pro character-lock:** when the variants must preserve a specific character or face across frames, use Pro's up-to-14-reference workflow.

## Filled example

**Brief:** Logo for "Field & Flour," a local bakery. Warm, simple, timeless. Flat design with a wheat-stalk + ampersand mark above the wordmark. Deep terracotta #B5533C and warm cream #F3EAD3.

**gpt-image-2 prompt:**
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
wordmark exactly as: Field & Flour (verbatim, no extra characters). No
watermark, no trademark symbols.
```

**Run with:** `--quality high --size 1024x1024`.
