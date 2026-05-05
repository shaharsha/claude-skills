# Image generation scripts

Three CLI wrappers: two for image generation (OpenAI + Google) and one for local background removal. Designed for use by the parent `image-generation` skill but can be run standalone.

## Setup

Both generation scripts require `curl`, `jq`, and `base64` (preinstalled on macOS). Make them executable once:

```bash
chmod +x ~/.claude/skills/image-generation/scripts/*.sh
```

Export API keys before running the generation scripts. Sources are documented in `~/.claude/projects/-Users-shaharshavit/memory/api-keys.md`:

```bash
export OPENAI_IMAGE_API_KEY='sk-proj-...'   # from "OpenAI (image generation)" section
export GEMINI_IMAGE_API_KEY='AQ.Ab8RN...'   # from "Google AI Studio (image generation)" section
```

The `rembg.sh` script needs no API key but requires the `rembg` Python CLI installed once:

```bash
pip install "rembg[cli]" onnxruntime
```

## openai-image.sh — gpt-image-2

```bash
# Basic generation
./openai-image.sh \
  --prompt "minimalist black ceramic mug on marble, soft studio light" \
  --output ./generated-images/mug-hero.png \
  --quality high \
  --size 1024x1024

# Custom resolution (2560×1440 dashboard)
./openai-image.sh \
  --prompt "SaaS dashboard UI..." \
  --output ./generated-images/dashboard.png \
  --quality high \
  --size 2560x1440

# 4 ideation variants in one call (cheap)
./openai-image.sh \
  --prompt "..." \
  --output ./generated-images/explore.png \
  --quality low \
  --n 4

# Transparent logo (generate + rembg)
./openai-image.sh \
  --prompt "Logo brief: ... isolated on flat #FFFFFF, no drop shadow" \
  --output ./generated-images/logo-v1.png \
  --quality high \
  --size 1024x1024
./rembg.sh \
  --input  ./generated-images/logo-v1.png \
  --output ./generated-images/logo-v1-transparent.png

# Edit endpoint (presence of --ref switches modes)
./openai-image.sh \
  --prompt "Replace only the clothing with the navy suit. Preserve identity." \
  --output ./generated-images/edited.png \
  --ref ./model.png \
  --ref ./suit.png \
  --quality high
```

**gpt-image-2 notes:**

- `--background transparent` is not supported. The script rejects it with a pointer to `rembg.sh`. See [../reference/transparent-backgrounds.md](../reference/transparent-backgrounds.md).
- `--input-fidelity` is not configurable — gpt-image-2 processes every reference at high fidelity automatically. The script rejects this flag too.
- Size constraints: each edge ≤ 3840px, both edges multiples of 16, ratio ≤ 3:1, total pixels 655,360–8,294,400. The script validates these.

## gemini-image.sh — Flash / Pro

```bash
# Default Flash 1K square
./gemini-image.sh \
  --prompt "..." \
  --output ./generated-images/test.png

# Pro 4K landscape hero (for photoreal portraits / lifestyle)
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

# Cheap exploration with Flash, thinking off
./gemini-image.sh \
  --prompt "..." \
  --output ./generated-images/explore.png \
  --model flash \
  --thinking minimal
```

## rembg.sh — local background remover

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
- The Gemini script only adds `thinkingConfig` when calling Flash; Pro thinks by default and doesn't accept the field.
- `rembg.sh` first-run of each model downloads weights (~200-400MB) to `~/.u2net/`. Subsequent runs hit the cache.

## Quick test

```bash
mkdir -p /tmp/imagetest

# Generate with gpt-image-2
./openai-image.sh \
  --prompt "A red apple on a white plate, photorealistic studio shot, clean white background, no shadow under the apple." \
  --output /tmp/imagetest/apple.png \
  --quality high \
  --size 1024x1024

# Remove background
./rembg.sh \
  --input  /tmp/imagetest/apple.png \
  --output /tmp/imagetest/apple-transparent.png

open /tmp/imagetest/apple-transparent.png
```
