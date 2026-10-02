# Logo prompt template

**Default model:** `gpt-image-2.5-sunburst` at `quality=max` (the script default, no flag needed) for finals. `gpt-image-2.5-flare` at `medium` (`--draft`) for exploration; Gemini Lite (`--model lite`) is an alternative cheap tier. Gemini Pro only when the logo uses a photoreal element (e.g. a photographed mascot).

## Required inputs (collect from user before writing prompt)

- Brand name
- Industry / what the business does
- Personality (3 adjectives - e.g., "warm, simple, timeless")
- Style direction (flat vector / hand-drawn / geometric / monogram / wordmark / combination mark)
- Color palette (name colors + hex codes; or "monochrome black" / "monochrome white")
- Background (transparent / pure white / specific color)
- Language of wordmark - English, Hebrew, CJK, etc. GPT Image 2.5 handles all of them natively; check non-Latin output letter by letter.

## GPT Image 2.5 variant (labeled segments) — DEFAULT

```
BACKGROUND: Pure flat [#FFFFFF white / SPECIFIED HEX], no gradient, no texture, no shadow.

SUBJECT: A [3 PERSONALITY ADJECTIVES] logo for [BRAND NAME], a [INDUSTRY].

DETAILS: [STYLE DIRECTION — e.g., "A flat-vector geometric monogram combining the letters X and Y, balanced negative space, clean proportions"]. Below the mark, the wordmark "[EXACT BRAND NAME]" set in a [TYPOGRAPHY — e.g., "bold geometric sans-serif"]. Color: [HEX], all strokes clean, no gradients [unless specified].

CONSTRAINTS: Single centered logo with generous padding (25% on all sides). [BACKGROUND SPEC]. No shadow, no texture, no tagline. Render the wordmark "[BRAND NAME]" exactly once, verbatim. No other text. No watermark, no trademark symbols.
```

**Run with:** `--size 1024x1024` (Sunburst `max`, ≈ $0.21) or 2048×2048 for premium finals.

**Explore first, then promote:** run the same prompt with `--draft` (Flare `medium`, ~1¢ each) for several directions. Promote the user's pick with a Sunburst `max` edit - `--ref logo-draft-N.png --size <same as draft>` and the promote prompt in [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md) ("Image 1 is an approved draft. Re-render it as the final at full detail..."). Don't re-roll the prompt at `max`; that composes a different logo.

**For transparent PNG:** native on 2.5 - add `--background transparent --output-format png` and replace the BACKGROUND/CONSTRAINTS background spec with "Transparent background, no drop shadow, no contact shadow". No rembg needed. See [../reference/transparent-backgrounds.md](../reference/transparent-backgrounds.md) for Gemini outputs or cutting an existing logo.

**For pure monochrome line art (any source):** ImageMagick color-key is still valid and gives mathematically perfect alpha - `magick in.png -fuzz 5% -transparent white out.png`.

**Logo doubling as an iOS app icon:** Apple rejects 1024×1024 App Store icons with transparency - ship a flattened (opaque) copy for iOS.

## Gemini Flash variant (exploration only)

```
Create an original, non-infringing logo for [BRAND NAME], a [INDUSTRY].
The logo should feel [3 PERSONALITY ADJECTIVES]. [STYLE DIRECTION].
[COLOR DESCRIPTION]. Composition: single centered logo with generous
padding (25% on all sides), pure white background, crisp edges, suitable
for SVG conversion.
```

**Run with:** `--model flash --aspect 1:1 --size 1K` (`gemini-3.1-flash-image`, $0.067) or `--model lite` (`gemini-3.1-flash-lite-image`, $0.034, 1K only, returns JPEG). Promote the keeper with the Sunburst `max` edit above (`--ref` the Gemini draft).

## For brand-consistent variant set (multiple logos in same style)

Two paths:

1. **GPT Image 2.5 multi-reference:** pass logo + color swatch + typography reference + vibe reference to `/v1/images/edits` (up to 16 references), numbered by role. Every reference is processed at high fidelity automatically. See [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md) §"Multi-image reference pattern."
2. **Gemini Pro character-lock:** when the variants must preserve a specific character or face across frames, use Pro's up-to-14-reference workflow.

## Filled example

**Brief:** Logo for "Field & Flour," a local bakery. Warm, simple, timeless. Flat design with a wheat-stalk + ampersand mark above the wordmark. Deep terracotta #B5533C and warm cream #F3EAD3.

**GPT Image 2.5 prompt:**
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

**Run with:** `--size 1024x1024` (Sunburst `max`, the default). Drafts: add `--draft`.
