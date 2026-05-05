# Product photography template

**Default model:**
- `gpt-image-2` at `quality=high` for object hero shots and catalog work — best composition, prompt adherence, color accuracy, and it can render in-image product text or labels if needed. For transparent catalog cutouts, generate on white + post-process with `scripts/rembg.sh`.
- **Gemini Pro 4K** for lifestyle photography with a human model holding/wearing the product — Pro still wins on skin/hair/film-grain realism.
- Gemini Flash 2K for lighting / angle exploration.

## Required inputs

- Product (with material, color, finish description — be specific)
- Shot type (hero / lifestyle / catalog cutout / flat-lay / detail)
- Background (studio white / marble / concrete / lifestyle setting)
- Lighting setup (three-point softbox / golden hour / studio rim / overcast)
- Camera angle (eye-level / 45° / overhead flat-lay / low hero)
- Lens / aperture vibe (85mm portrait / 50mm standard / 100mm macro / wide)
- Color grade (warm / cool / neutral / brand palette)
- Aspect ratio (1:1 catalog / 4:5 social / 16:9 banner / 3:4 magazine)
- Transparent output needed? → plan the post-process step (rembg)

## gpt-image-2 variant (labeled) — DEFAULT FOR OBJECT SHOTS

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

**Run with:** `--quality high --size 1536x1024` (landscape) or `--size 1024x1024` (catalog square) or `--size 1024x1536` (portrait).

## Gemini Pro variant — DEFAULT FOR LIFESTYLE WITH MODEL

```
A lifestyle [SHOT TYPE] photograph of [PRODUCT WITH DETAIL], [PRESENTATION
— e.g., "held by a person in a soft cotton shirt"], [LOCATION — e.g.,
"sitting at the edge of a winding mountain hiking trail"]. Lit by
[LIGHTING], creating [SHADOW/LIGHT DETAILS]. Captured with [LENS],
[DEPTH OF FIELD]. Style: [POST-PRODUCTION FEEL]. Color palette:
[DESCRIPTION with hex codes].
```

**Run with:** `--model gemini-3-pro-image-preview --aspect 1:1 --size 4K` (or target aspect).

## Transparent catalog cutouts — post-process pipeline

1. Generate on pure white with gpt-image-2:
   ```
   BACKGROUND: Pure flat #FFFFFF, no texture, no shadow.

   SUBJECT: [PRODUCT WITH DETAILS].

   DETAILS: [LIGHTING, CAMERA ANGLE]. Centered, generous padding, product
   fills ~70% of the frame. Clean commercial e-commerce catalog
   photography.

   CONSTRAINTS: Pure white background, no drop shadow, no contact shadow,
   no gradient, no text, no logos visible, no watermark. 1:1 aspect.
   ```
2. Post-process with `scripts/rembg.sh`:
   ```
   ./scripts/rembg.sh --input product.png --output product-transparent.png
   ```
3. Inspect edges with a checkerboard composite (see [../reference/transparent-backgrounds.md](../reference/transparent-backgrounds.md)).

**Run with:** `--quality high --size 1024x1024`.

## Filled examples

### Hero shot — premium ceramic mug (gpt-image-2)

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

**Run with:** `--quality high --size 1024x1024`.

### Catalog cutout — sneaker (gpt-image-2 + rembg)

**Brief:** Sneaker for product catalog, transparent PNG for catalog overlay.

```
BACKGROUND: Pure flat #FFFFFF, no texture, no shadow.

SUBJECT: A white-and-blue running sneaker with a knit upper and chunky
white midsole.

DETAILS: Centered, eye-level three-quarter view (side profile plus a hint
of the upper). Lit by even softbox lighting from above and slightly left,
no harsh shadows. Captured with a 50mm lens at f/8. Clean commercial
e-commerce catalog photography, accurate product colors, no color grading.

CONSTRAINTS: Pure white background, no drop shadow, no contact shadow,
no gradient. Generous padding, sneaker fills 70% of frame. Realistic
textures, accurate material rendering. No text, no logos visible on the
sneaker, no watermark. 1:1 aspect.
```

**Run with:** `--quality high --size 1024x1024`. Then `./scripts/rembg.sh --input sneaker.png --output sneaker-transparent.png`.

### Lifestyle hero — outdoor bottle with model (Gemini Pro)

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

**Run with:** `--model gemini-3-pro-image-preview --aspect 4:5 --size 4K`.

### Identity-preserving virtual try-on

For "model wearing the product" shots where both the model and product photos already exist, use Gemini Pro with up to 5 character references + explicit preserve clauses. See [../reference/gemini-image.md](../reference/gemini-image.md) §"Reference images" and the examples.md worked example.

## Tips

- **Material vocabulary matters.** "Matte black ceramic" beats "black mug." "Brushed stainless steel" beats "silver." "Hand-formed rim" beats "ceramic edge."
- **Lighting vocabulary matters more.** Specifying "three-point softbox" or "golden-hour backlight" steers realism reliably. Generic "good lighting" is meaningless.
- **Don't ask for logos or product text** on the product itself — the model will mangle them. Add real branding/labels in post via mockup tools.
- **For seamless backdrops**, specify color + sweep: "pure white seamless studio backdrop with subtle gradient" beats "white background."
- **For transparent output**, always generate with explicit "no drop shadow, no contact shadow, no gradient" in CONSTRAINTS — this makes rembg's job much easier.
- **For hyper-realistic skin/model shots**, route to Gemini Pro — its photoreal portrait quality is still a notch above gpt-image-2.
