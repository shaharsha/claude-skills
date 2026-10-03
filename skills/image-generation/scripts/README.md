# Image generation scripts

Three CLI wrappers: two for image generation (OpenAI + Google) and one for local background removal (only needed for Gemini outputs or cutting existing images - GPT Image 2.5 does transparency natively). Designed for use by the parent `image-generation` skill but can be run standalone.

## Setup

Both generation scripts require `curl`, `jq`, and `base64` (preinstalled on macOS). Make them executable once:

```bash
chmod +x ~/.claude/skills/image-generation/scripts/*.sh
```

Export API keys before running the generation scripts. Sources are documented in `~/.claude/projects/-Users-shaharshavit/memory/api-keys.md`:

```bash
export OPENAI_IMAGE_API_KEY='sk-proj-...'   # from "OpenAI (image generation)" section
export GEMINI_IMAGE_API_KEY='...'   # from "Google AI Studio (image generation)" section
```

The `rembg.sh` script needs no API key but requires the `rembg` Python CLI installed once (optional - only for Gemini outputs or existing images):

```bash
pip install "rembg[cli]" onnxruntime
```

## openai-image.sh — GPT Image 2.5 (Sunburst / Flare) and gpt-image-2

Defaults: `--model gpt-image-2.5-sunburst`, `--quality max`, `--size 1024x1024`, `--background opaque`, `--output-format png`. So a bare call is already a final-quality render.

```bash
# Final render (Sunburst at max is the default - no --quality flag needed)
./openai-image.sh \
  --prompt "minimalist black ceramic mug on marble, soft studio light" \
  --output ./generated-images/mug-hero.png \
  --size 1024x1024

# Quick drafts: --draft = --model gpt-image-2.5-flare --quality medium (~15 s, ~1¢ at 1024x1536).
# Put --draft AFTER any --model/--quality, since it overrides both.
./openai-image.sh \
  --prompt "..." \
  --output ./generated-images/explore.png \
  --size 1024x1536 \
  --draft \
  --n 4

# Promote the chosen draft: a Sunburst max EDIT with the draft as Image 1, same --size.
# Not a re-roll - re-running the prompt at max composes a different picture.
./openai-image.sh \
  --prompt "Image 1 is an approved draft. Re-render it as the final at full detail: change only the rendering quality - sharper linework, richer texture, cleaner typography. Preserve exactly: the composition, every object and its position, the color palette, and all text - \"...\" - each appearing once in the same place and typography. No new elements, no extra text, no watermark." \
  --output ./generated-images/explore-final.png \
  --ref ./generated-images/explore-3.png \
  --size 1024x1536

# Custom resolution (2560×1440 dashboard)
./openai-image.sh \
  --prompt "SaaS dashboard UI..." \
  --output ./generated-images/dashboard.png \
  --size 2560x1440

# Transparent logo - native on 2.5 (png or webp; jpeg is rejected)
./openai-image.sh \
  --prompt "Logo brief: ... Transparent background, no drop shadow, no contact shadow." \
  --output ./generated-images/logo-v1-transparent.png \
  --background transparent \
  --output-format png \
  --size 1024x1024

# Edit endpoint (presence of --ref switches modes; up to 16 references)
./openai-image.sh \
  --prompt "Image 1: the model to preserve. Image 2: the suit. Replace only the clothing with the navy suit from Image 2. Preserve identity, pose, background and lighting." \
  --output ./generated-images/edited.png \
  --ref ./model.png \
  --ref ./suit.png
```

Every call prints one line to stderr with latency, output tokens and cost, e.g. `  87s · output_tokens=5488 · cost≈$0.165`. Sum these lines to track spend.

**Notes:**

- **`--model`**: `gpt-image-2.5-sunburst` (default; anything that may ship), `gpt-image-2.5-flare` (fast drafts, ~2× faster), `gpt-image-2` (previous generation, not deprecated).
- **`--quality low|medium|high|xhigh|max|auto`**, default `max`. The 2.5 ladder is re-cut: 2.5 `high` ≈ gpt-image-2 `medium` in output tokens, and 2.5 `max` ≈ gpt-image-2 `high`. `xhigh`/`max` exist only on the 2.5 models (the script rejects them on `gpt-image-2`). Avoid `auto` - it lands on different budgets for identical calls. Measured at 1024×1536: Sunburst `max` ≈ $0.165 (~90 s), Sunburst `high` ≈ $0.041 (~35 s), Flare `medium` ≈ $0.01 (~15 s).
- **`--background transparent`** is native on 2.5 and needs `--output-format png` or `webp`. On `gpt-image-2` it is a preview feature that fails intermittently; the script warns. See [../reference/transparent-backgrounds.md](../reference/transparent-backgrounds.md).
- **`--ref`** is repeatable up to 16 and switches to `/v1/images/edits`. Number references by role in the prompt ("Image 1 = product, Image 2 = style").
- `--input-fidelity` is not sent - `gpt-image-2` ignores it and the 2.5 models don't list it; references get high fidelity automatically. The script rejects this flag.
- Size constraints: each edge ≤ 3840px, both edges multiples of 16, ratio ≤ 3:1, total pixels 655,360–8,294,400; above 2560×1440 is experimental. The script validates these.
- Prompts can run to 32,000 characters. See [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md) for prompt structure.

## gemini-image.sh — Flash / Pro / Lite

`--model` aliases: `flash` = `gemini-3.1-flash-image` (default, $0.067 at 1K), `pro` = `gemini-3-pro-image` ($0.134 at 1K/2K, $0.24 at 4K), `lite` = `gemini-3.1-flash-lite-image` ($0.034, 1K only, returns JPEG). A full model ID also works. The `*-preview` IDs were shut down on 2026-06-25 and the script refuses them. `--size 512|1K|2K|4K` (the smallest size is spelled `512`; Pro has no 512; Lite is 1K only). Up to 14 `--ref` images.

```bash
# Default Flash 1K square
./gemini-image.sh \
  --prompt "..." \
  --output ./generated-images/test.png

# Pro 4K landscape hero (comparison render for skin-critical portraits / lifestyle)
./gemini-image.sh \
  --prompt "..." \
  --output ./generated-images/hero.png \
  --model pro \
  --aspect 16:9 \
  --size 4K

# Multi-turn edit — pass previous output as reference
./gemini-image.sh \
  --prompt "Change only the sofa color to deep navy. Keep everything else exactly the same." \
  --output ./generated-images/edited.png \
  --model pro \
  --ref ./generated-images/original.png

# Brand-consistent variant with multiple references
./gemini-image.sh \
  --prompt "Image 1 is the logo. Image 2 is the brand color. Image 3 is the typography. Generate a launch hero..." \
  --output ./generated-images/branded-hero.png \
  --model pro \
  --aspect 16:9 \
  --size 4K \
  --ref ./brand/logo.png \
  --ref ./brand/colors.png \
  --ref ./brand/type.png

# Infographic with Google Search grounding (Pro only)
./gemini-image.sh \
  --prompt "Diagram of photosynthesis as a recipe..." \
  --output ./generated-images/photosynthesis.png \
  --model pro \
  --aspect 16:9 \
  --size 4K \
  --search

# Banner beyond GPT Image's 3:1 cap (Flash only: 1:4, 4:1, 1:8, 8:1)
./gemini-image.sh \
  --prompt "..." \
  --output ./generated-images/banner.png \
  --model flash \
  --aspect 4:1 \
  --size 2K

# Cheapest exploration: Lite (1K only, saved as .jpg)
./gemini-image.sh \
  --prompt "..." \
  --output ./generated-images/explore.jpg \
  --model lite \
  --thinking minimal
```

## crop_faces.py - face crops for character references

Never pass whole photos as `--ref` for character work: the edit endpoint restyles the photo instead of drawing the person. Crop the faces first.

```bash
pip install opencv-python-headless   # the one dependency
python3 crop_faces.py photos/ faces/ --sheet faces/_sheet.jpg
# faces/<photo-stem>-<n>.png per detected face (largest first, 60% margin, square)
# --sheet: numbered contact sheet so the human can say which crop is whom
# --margin 0.6   --min 120 (smallest face side, px)
```
A photo with no detectable face prints `0 face(s)`. Crop it by hand with `sips` or ffmpeg's `crop` filter. HEIC must be converted first (`sips -s format jpeg in.heic --out out.jpg`). The full pipeline (crop, face, card, promote) is in `../reference/characters-from-photos.md`.

## rembg.sh — local background remover

Use for Gemini outputs (which have no transparent mode) or to cut an existing image. For OpenAI renders, ask for `--background transparent` instead.

```bash
# Default (birefnet-general, MIT license, best general-purpose)
./rembg.sh \
  --input  ./generated-images/logo-v1.png \
  --output ./generated-images/logo-v1-transparent.png

# Portrait-specialized model
./rembg.sh \
  --input  ./generated-images/headshot.png \
  --output ./generated-images/headshot-transparent.png \
  --model birefnet-portrait

# Fastest fallback
./rembg.sh \
  --input  ./generated-images/quick.png \
  --output ./generated-images/quick-transparent.png \
  --model u2net
```

**Supported `--model` values:** `birefnet-general` (default, MIT), `bria-rmbg` (non-commercial), `birefnet-portrait` (people), `isnet-anime` (2D characters), `u2net` (legacy/fast).

**For pure monochrome line-art logos/icons,** skip rembg and use ImageMagick color-key instead — it's instantaneous and mathematically perfect:

```bash
magick in.png -fuzz 5% -transparent white out.png
```

See [../reference/transparent-backgrounds.md](../reference/transparent-backgrounds.md) for the full decision tree.

## Behavior notes

- All three scripts print progress to stderr and the final saved path to stdout. Capture with `OUT=$(./openai-image.sh ...)` or pipe to `xargs open` to view immediately.
- `openai-image.sh --n 4` saves the first image as `--output` and additional images with `-2`, `-3`, `-4` appended before the extension.
- Gemini doesn't support `n>1` per call — use parallel calls for multiple variants, or ask for "4 variations arranged in a 2×2 grid on one canvas" in the prompt and slice client-side.
- Errors from either image API are echoed in JSON to stderr with exit code 1.
- The Gemini script only adds `thinkingConfig` when calling Flash or Lite; Pro thinks by default and doesn't accept the field.
- The Gemini script corrects the output extension to match the returned MIME type (Lite returns JPEG, so `out.png` is saved as `out.jpg`).
- `rembg.sh` first-run of each model downloads weights (~200-400MB) to `~/.u2net/`. Subsequent runs hit the cache.

## Quick test

```bash
mkdir -p /tmp/imagetest

# Cheapest smoke test (Flare medium, ~1¢)
./openai-image.sh \
  --prompt "A red apple on a white plate, photorealistic studio shot." \
  --output /tmp/imagetest/apple-draft.png \
  --size 1024x1024 \
  --draft

# Native transparent final (Sunburst max, ~$0.21) - no rembg step
./openai-image.sh \
  --prompt "A red apple, photorealistic studio shot, isolated object. Transparent background, no shadow under the apple." \
  --output /tmp/imagetest/apple-transparent.png \
  --background transparent \
  --output-format png \
  --size 1024x1024

open /tmp/imagetest/apple-transparent.png
```
