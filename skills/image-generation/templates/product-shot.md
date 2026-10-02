# Product photography template

**Default model:**
- `gpt-image-2.5-sunburst` at `quality=max` (the script default) for object hero shots and catalog work — best composition, prompt adherence, color accuracy, and it can render in-image product text or labels if needed. Transparent catalog cutouts are native: `--background transparent --output-format png`.
- Lifestyle photography with a human model holding/wearing the product: Sunburst `max` first (it leads the portrait votes); when skin is the point and Sunburst's reads over-sharpened on zoom, compare with **Gemini Pro 4K** and let the human pick.
- `gpt-image-2.5-flare` at `medium` (`--draft`, ~1¢) for lighting / angle exploration; Gemini Lite (`--model lite`, $0.034) is an alternative cheap tier.

## Required inputs

- Product (with material, color, finish description — be specific)
- Shot type (hero / lifestyle / catalog cutout / flat-lay / detail)
- Background (studio white / marble / concrete / lifestyle setting)
- Lighting setup (three-point softbox / golden hour / studio rim / overcast)
- Camera angle (eye-level / 45° / overhead flat-lay / low hero)
- Lens / aperture vibe (85mm portrait / 50mm standard / 100mm macro / wide)
- Color grade (warm / cool / neutral / brand palette)
- Aspect ratio (1:1 catalog / 4:5 social / 16:9 banner / 3:4 magazine)
- Transparent output needed? → native on GPT Image 2.5 (`--background transparent`); rembg only for Gemini outputs or existing photos

## GPT Image 2.5 variant (labeled) — DEFAULT

```
BACKGROUND: [SURFACE/ENVIRONMENT — e.g., "polished white Carrara marble
countertop with subtle gray veining"].

SUBJECT: [PRODUCT WITH MATERIAL/COLOR/FINISH DETAIL].

DETAILS: [ACTION/PRESENTATION — e.g., "resting on the surface", "floating
against", "held in mid-air"]. Lit by [LIGHTING — e.g., "soft three-point
softbox with gentle rim light from behind right"], creating [SHADOW
QUALITY — e.g., "subtle contact shadow, soft reflection in the surface"].
Captured with [LENS — e.g., "85mm lens at f/2.8"], [DEPTH OF FIELD].
Style: [POST-PRODUCTION FEEL — e.g., "editorial commercial e-commerce,
warm neutral color grading"].

CONSTRAINTS: [ASPECT]. Realistic textures, accurate material rendering.
No text, no logos visible on the product, no watermark.
```

**Run with:** `--size 1536x1024` (landscape) or `--size 1024x1024` (catalog square) or `--size 1024x1536` (portrait). Sunburst `max` is the default. Try lighting and angles with `--draft`, then promote the chosen draft with a Sunburst `max` edit (`--ref shot-draft.png`, same `--size`, promote prompt from [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md)).

## Gemini Pro variant — COMPARISON FOR SKIN-CRITICAL LIFESTYLE

```
A lifestyle [SHOT TYPE] photograph of [PRODUCT WITH DETAIL], [PRESENTATION
— e.g., "held by a person in a soft cotton shirt"], [LOCATION — e.g.,
"sitting at the edge of a winding mountain hiking trail"]. Lit by
[LIGHTING], creating [SHADOW/LIGHT DETAILS]. Captured with [LENS],
[DEPTH OF FIELD]. Style: [POST-PRODUCTION FEEL]. Color palette:
[DESCRIPTION with hex codes].
```

**Run with:** `--model pro --aspect 1:1 --size 4K` (`gemini-3-pro-image`, $0.24 at 4K; or target aspect).

## Transparent catalog cutouts — native on GPT Image 2.5

1. Generate directly with a transparent background:
   ```
   USE: Commercial e-commerce catalog cutout.

   SUBJECT: [PRODUCT WITH DETAILS], isolated object.

   DETAILS: [LIGHTING, CAMERA ANGLE]. Centered, generous padding, product
   fills ~70% of the frame. Clean commercial e-commerce catalog
   photography.

   CONSTRAINTS: Transparent background, no drop shadow, no contact shadow,
   no text, no logos visible, no watermark. 1:1 aspect.
   ```
2. Inspect edges on a dark and a light backdrop (checkerboard composite, see [../reference/transparent-backgrounds.md](../reference/transparent-backgrounds.md)).

**Run with:** `--background transparent --output-format png --size 1024x1024` (Sunburst `max`). Verified 2026-10-02: Sunburst returns a real RGBA alpha channel. Use `scripts/rembg.sh` only for Gemini outputs or to cut an existing product photo.

## Filled examples

### Hero shot — premium ceramic mug (GPT Image 2.5)

**Brief:** Matte black ceramic coffee mug, hero shot. Marble countertop, warm studio light, shallow depth of field. 1:1 catalog aspect.

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
commercial e-commerce photography, warm neutral color grading, clean
minimalist composition.

CONSTRAINTS: 1:1 aspect. Realistic textures, accurate material rendering.
No text, no logo visible on the mug, no watermark.
```

**Run with:** `--size 1024x1024` (Sunburst `max`, ≈ $0.21).

### Catalog cutout — sneaker (GPT Image 2.5, native transparent)

**Brief:** Sneaker for product catalog, transparent PNG for catalog overlay.

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

**Run with:** `--background transparent --output-format png --size 1024x1024` (Sunburst `max`). One call, no rembg.

### Lifestyle hero — outdoor bottle (Gemini Pro)

**Brief:** Stainless water bottle, lifestyle hero on a hiking trail at golden hour. 4:5 social aspect.

```
A lifestyle hero photograph of a brushed stainless steel insulated water
bottle with a black silicone grip band, sitting on a moss-covered rock
at the edge of a winding mountain hiking trail. The trail recedes into
soft alpine forest in the background, shallow blurred. Lit by warm
golden-hour backlight filtering through pine trees, creating a soft rim
glow on the bottle and dappled light on the moss. Subtle lens flare in
the upper-right corner. Captured with a 50mm standard lens at f/2.0,
shallow depth of field with the bottle in crisp focus. Style: outdoor
lifestyle editorial photography, warm earthy color grading, cinematic
mood. Color palette: warm golden light, deep forest greens, soft moss
tones, brushed silver accents. 4:5 aspect.
```

**Run with:** `--model pro --aspect 4:5 --size 4K`. The same brief also works as a GPT Image 2.5 labeled prompt at `--size 1024x1280` (4:5) - compare the two when photoreal mood matters.

### Identity-preserving virtual try-on

For "model wearing the product" shots where both the model and product photos already exist, use a Sunburst edit with the photos as numbered references (up to 16) + explicit preserve clauses - see [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md) §"Virtual try-on (multi-image)" and the examples.md worked example. For hard identity lock, compare with Gemini Pro (up to 5 character references); see [../reference/gemini-image.md](../reference/gemini-image.md) §"Reference images".

## Tips

- **Material vocabulary matters.** "Matte black ceramic" beats "black mug." "Brushed stainless steel" beats "silver." "Hand-formed rim" beats "ceramic edge."
- **Lighting vocabulary matters more.** Specifying "three-point softbox" or "golden-hour backlight" steers realism reliably. Generic "good lighting" is meaningless.
- **Don't ask for logos or product text** on the product itself — the model will mangle them. Add real branding/labels in post via mockup tools.
- **For seamless backdrops**, specify color + sweep: "pure white seamless studio backdrop with subtle gradient" beats "white background."
- **For transparent output**, always say "no drop shadow, no contact shadow" in CONSTRAINTS - it keeps shadows out of a native cutout and out of rembg's way on Gemini outputs.
- **For hyper-realistic skin/model shots**, render Sunburst `max` first; reviewers call its close-up skin over-sharpened on zoom, so compare with Gemini Pro 4K and let the human pick.
