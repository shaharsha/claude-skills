# Google Gemini image models — operational reference

Read this file before writing any prompt for `gemini-3.1-flash-image-preview` or `gemini-3-pro-image-preview`. Sources: Google AI image-generation docs (primary), Vertex AI docs, Google Cloud "Ultimate prompting guide for Nano Banana," DeepMind model cards.

## API surface

- **Endpoint:** `POST https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent`
- **Auth:** `x-goog-api-key: $GEMINI_IMAGE_API_KEY`
- **Model IDs:**
  - `gemini-3.1-flash-image-preview` (Nano Banana 2 Flash)
  - `gemini-3-pro-image-preview` (Nano Banana Pro)

The bundled `scripts/gemini-image.sh` wraps this. See [../scripts/README.md](../scripts/README.md).

## Request shape (REST)

Minimal text-to-image:
```json
{
  "contents": [{"parts": [{"text": "PROMPT"}]}],
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "imageConfig": {
      "aspectRatio": "16:9",
      "imageSize": "2K"
    }
  }
}
```

With reference images (inline base64):
```json
{
  "contents": [{
    "parts": [
      {"text": "PROMPT"},
      {"inline_data": {"mime_type": "image/png", "data": "<BASE64>"}}
    ]
  }],
  "generationConfig": { ... }
}
```

With thinking mode (Flash only — Pro has thinking on by default):
```json
{
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "thinkingConfig": {"thinkingLevel": "high", "includeThoughts": false}
  }
}
```

**Critical gotchas:**
- `imageSize` value uses **uppercase K**: `"2K"` works, `"2k"` is rejected.
- `aspectRatio` MUST be set in `imageConfig`. **Putting "16:9" in the prompt text is ignored or produces inconsistent results.**
- Output is always PNG, returned as base64 in `inline_data`. There is no URL-returning mode and no JPEG/WebP output mode.
- For multi-turn raw REST, you MUST echo `thought_signature` from the previous turn's response into the next turn's parts, or the call fails. The Python SDK's chat object handles this automatically.

## Flash vs Pro — full spec

| | Flash 3.1 | Pro 3 |
|---|---|---|
| Knowledge cutoff | Jan 2025 | Jan 2025 |
| Input token limit | 131,072 | 65,536 |
| Output token limit | 32,768 | 32,768 |
| Reference images | up to 14 (10 obj + 4 char) | up to 14 (6 obj + 5 char) |
| Resolutions | 0.5K, 1K (default), 2K, 4K | 1K (default), 2K, 4K |
| Aspect ratios | 1:1, 1:4, 4:1, 1:8, 8:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 | Same minus extreme (1:4, 4:1, 1:8, 8:1) |
| Thinking mode | controllable (`minimal`/`high`) | on by default, not user-tunable |
| Google Search grounding | web + image search | web only |
| Character consistency | Good | Up to 5 people |
| Cost / image | $0.045 (0.5K) - $0.151 (4K) | $0.134 (1K-2K) - $0.24 (4K) |
| SynthID watermark | always on | always on |

**Pick Pro when:** brand-critical final · 4K · text-heavy · multi-character (≤5 people) · reasoning-heavy composition · multi-language (non-RTL).
**Pick Flash when:** exploration · high volume · 0.5K thumbnails · extreme aspect (1:4, 8:1) · image-search grounding · explicit `thinkingLevel: minimal` cost control.

## Prompt structure — house rules

Gemini is **deeply narrative**, not keyword-driven. Verbatim from Google: *"Describe the scene, don't just list keywords. The model's core strength is its deep language understanding. A narrative, descriptive paragraph will almost always produce a better, more coherent image than a list of disconnected words."*

### The official six-element scaffolding

1. **Subject** — be specific. *"A stoic robot barista with glowing blue optics."*
2. **Composition** — framing. *"Extreme close-up" / "wide shot" / "portrait" / "Dutch angle."*
3. **Action** — what's happening. *"Brewing a cup of coffee."*
4. **Location** — setting. *"A futuristic cafe on Mars."*
5. **Style** — *"3D animation" / "film noir" / "watercolor" / "editorial photography."*
6. **Editing (if modifying)** — *"be direct and specific: change the man's tie to green."*

### The Google Cloud "Creative Director" formula

`[Subject] + [Action] + [Location/context] + [Composition] + [Style]`

Verbatim example:
> *"[Subject] A striking fashion model wearing a tailored brown dress, sleek boots, and holding a structured handbag. [Action] Posing with a confident, statuesque stance, slightly turned. [Location/context] A seamless, deep cherry red studio backdrop. [Composition] Medium-full shot, center-framed. [Style] Fashion magazine style editorial, shot on medium-format analog film, pronounced grain, high saturation, cinematic lighting effect."*

### Length

**2-6 sentences.** The Gemini 3 family is responsive to *concise, direct* prompts. Hit the six elements but don't pad.

### Negative phrasing — DO NOT USE

Verbatim from docs: *"Use positive framing: Describe what you want, not what you don't want (e.g. 'empty street' instead of 'no cars')."*

**Negative prompts ("no text, no watermark, no people") are actively counterproductive on these models — they anchor attention on the forbidden concept.** Always rewrite as positive constraints:

| ❌ Don't say | ✅ Say |
|---|---|
| "no people" | "empty street" / "deserted plaza" |
| "no text" | "uncluttered composition without typography" or just don't mention text |
| "no watermark" | (don't mention watermarks) |
| "no gradients" | "flat solid colors" |
| "no background" | "pure white background" |

### Conversational vs structured

Both work. Bracketed `[Subject]...[Style]` scaffolding is more reproducible across a batch. Pure narrative is better for one-off hero shots.

### "Show, don't tell" reasoning prompts

Reasoning prompts that exploit Gemini 3's thinking layer:

> *"Create a diagram of photosynthesis as if it were a recipe, showing sunlight as an ingredient, chlorophyll as the chef."*

Use for infographics, conceptual illustrations, anything benefiting from a planning step.

## Multi-turn editing (the killer feature)

Pattern: **target the change, lock the rest.**

Verbatim semantic-masking pattern:
> *"Using the provided image, change only the [specific element] to [new element]. Keep everything else in the image exactly the same."*

**The "keep everything else exactly the same" clause is load-bearing.** Without it the model drifts.

Other tested patterns:
- **Removal:** *"Remove the man from the photo."*
- **Style transfer with structure preserved:** *"Transform the provided photograph of a modern city street at night into the artistic style of Vincent van Gogh's 'Starry Night', with swirling brushstrokes and deep blues/bright yellows. Keep the original composition and silhouettes."*
- **Aspect-ratio lock on edit:** include *"Do not change the input aspect ratio."*
- **Character naming for consistency:** *"The character 'Dana' as established. Now show Dana at the café."*

### State model

The API is *nominally* stateless per HTTP call, but the Python SDK's `chat` object maintains an in-memory transcript. With raw REST you must (a) re-send the full prior `contents` array including previous image parts each turn, and (b) echo `thought_signature` verbatim, or the turn fails.

### "Change X, keep Y" three rules

1. **Lead with the target:** *"Change only the background..."*
2. **End with preservation:** *"...keep the subject, pose, lighting, and framing exactly the same."*
3. **Avoid ambiguous "this image" references** when multiple are attached — say "the first image / the product photo / the reference labeled A."

## Reference images / style consistency

**Limits (both models cap at 14):**
- Flash: up to 10 object + 4 character images
- Pro: up to 6 object + 5 character images

(Google doesn't document what classifies object vs character at the API level — the model decides internally. For brand work, treat all as "object" and stay under budget.)

### Role assignment

Pro guidance verbatim: *"Clearly define the role of each. (e.g., Use Image A for pose)"*. Assign roles explicitly:

> *"Image 1 is the product. Image 2 is the lighting reference. Image 3 is the color palette. Image 4 is the background style. Compose a product hero shot using Image 1 as the subject, Image 2's three-point softbox setup, Image 3's color grading, Image 4's minimalist negative-space composition."*

### Brand-style-guide loading pattern (Pro-only, exploits 14-image window)

> *"Style guide references: Images 1-3 are the logo in light/dark/mono variants. Images 4-6 are the brand color palette swatches. Images 7-9 are hero photography style. Images 10-12 are typography samples. Image 13 is the product. Generate a launch hero for 'Spring 2026 Collection' that (a) uses the wordmark from Image 1, (b) pulls primary color from Image 4, (c) matches the photographic style of Images 7-9, (d) uses typography from Image 12. Aspect ratio 16:9, 4K."*

### Subject consistency across shots

Sketch the initial subject, then in subsequent calls: *"Using the same character established above..."* Works in chat mode. For stateless mode, re-attach the canonical character image as a reference every call.

## Text rendering

Pro is the best-in-class model for text in images — ~94% character accuracy on Google's internal benchmark.

### Rules (verbatim Google Cloud)

1. **Quote the exact text:** `"Happy Birthday"`, `"URBAN EXPLORER"`.
2. **Describe the font:** *"bold, white, sans-serif font"* or *"Century Gothic 12px font"*.
3. **Translate/localize:** write the prompt in English, name the target-language text output.
4. **Text-first hack:** *"When generating text for an image, Gemini Image models work best if you first converse with it to generate the text concepts, and then ask for an image with that text."* In chat: first ask Gemini to *write* the headline, then ask for the image using that headline.

### Multi-text styling example (verbatim)

> *"A high-end, glossy commercial beauty shot of a sleek, minimalist nude-colored face moisturizer jar resting on a warm studio background. The lighting is soft and radiant. Next to the product, render three lines of text with the following exact styling: For the top line, the word 'GLOW' in a flowing, elegant Brush Script font. For the middle line, the text '10% OFF' in a heavy, blocky Impact font. For the bottom line, the text 'Your First Order' in a thin, minimalist Century Gothic font."*

### Text-as-window example (verbatim)

> *"A typographic poster with a solid black background, bold letters spell 'New York', filling the center of the frame. The text acts as a cut-out window. A photograph of New York skyline is visible ONLY inside the letterforms."*

### Hebrew / Arabic / RTL

**Known weak spot.** See [hebrew-rtl.md](hebrew-rtl.md). Default to a two-stage workflow (text-free image + composite text in post). Don't put Hebrew text in the Gemini prompt for production output.

## Output controls

| Control | How |
|---|---|
| Aspect ratio | `imageConfig.aspectRatio` — NOT in prompt text |
| Resolution | `imageConfig.imageSize`: `"512"`, `"1K"`, `"2K"`, `"4K"`. Uppercase K mandatory |
| Modalities | `responseModalities`: `["TEXT", "IMAGE"]` standard; `["IMAGE"]` image-only (cleaner, slightly cheaper) |
| Format | Always PNG in `inline_data`. No JPEG/WebP output |
| Count per call | Default 1; `candidateCount` is exposed but capped at 1 for these models. For N variants: parallel calls, OR ask "generate 4 variations arranged in a 2×2 grid on one canvas" and slice client-side |
| Seed / determinism | Not documented. Lock via specific prompt + reference images, not a seed |
| Watermark | SynthID always on, cannot be disabled via API |
| Transparent background | **Not natively supported.** Generate on white, post-process with background removal (`rembg`, `remove.bg`, or run a follow-up Gemini turn: *"Remove the background from this image, output transparent"*) |

## Thinking mode

**What it does:** internal reasoning phase before generation. Plans composition, checks facts, resolves conflicting instructions, decides layout. Especially helpful for:
- Infographics and diagrams (facts must be correct)
- Complex multi-reference compositions (5+ inputs)
- Text-heavy images with specific styling rules
- Prompts with conditional logic

**How to enable / configure:**
- **Pro:** thinking is on by default. Not user-tunable. You can set `includeThoughts: true` to inspect the reasoning trace.
- **Flash:** `thinkingConfig: { thinkingLevel: "minimal" | "high", includeThoughts: true|false }`. Use `"high"` for quality-sensitive jobs; `"minimal"` (default) for cost/latency.

**Cost/latency impact:**
- Adds latency.
- Pro produces images in ~6-10s with thinking on.
- On Flash, thinking tokens are **always billed** even if you hide the trace — `includeThoughts: false` saves bandwidth, not money.

## Pricing (per image, AI Studio paid tier, April 2026)

| Model | Resolution | Per-image cost |
|---|---|---|
| Flash 3.1 | 0.5K | $0.045 |
| Flash 3.1 | 1K | $0.067 |
| Flash 3.1 | 2K | $0.101 |
| Flash 3.1 | 4K | $0.151 |
| Pro 3 | 1K | $0.134 |
| Pro 3 | 2K | $0.134 |
| Pro 3 | 4K | $0.24 |

Token rates: Flash $0.50/M input · $60/M output. Pro $2/M input · $120/M output (image), $12/M output (text).

**Batch API** ≈ 50% off, 24h turnaround. Use for high-volume non-interactive jobs.

**No free tier** for these preview models.

## Failure modes

1. **No transparent backgrounds.** Generate on white, post-process.
2. **Negative prompts backfire.** Use positive framing only.
3. **Small text fidelity degrades** (<16pt rendered). Compose small text in post.
4. **Arabic/Hebrew RTL shaping is unreliable.** Use Pro + text-free workflow + composite. See [hebrew-rtl.md](hebrew-rtl.md).
5. **Aspect ratio in prompt text ignored.** Use `imageConfig.aspectRatio` only.
6. **Character consistency drifts past 5 people** (Pro's documented limit).
7. **Grammar in translations can break** on long passages. For translated marketing copy, translate manually and quote the final text.
8. **Complex blending artifacts** when 14 references are packed with conflicting styles. Choose references that complement.
9. **Facts can be wrong even with Search grounding.** Always verify numbers on infographics.
10. **Safety policies block:** deceptive imagery, real-person deepfakes without consent, explicit content. No per-prompt safety dial.
11. **Thought signatures must be preserved** across multi-turn raw-REST calls.
12. **`thinkingLevel="minimal"` on Flash doesn't save cost,** only latency — thinking tokens always billed.
13. **Preview status** — both models can break/change. Pin your version, don't auto-upgrade silently.

## Canonical examples by asset type (verbatim from Google)

**Fashion editorial (5-element framework):**
```
[Subject] A striking fashion model wearing a tailored brown dress, sleek
boots, and holding a structured handbag. [Action] Posing with a confident,
statuesque stance, slightly turned. [Location/context] A seamless, deep
cherry red studio backdrop. [Composition] Medium-full shot, center-framed.
[Style] Fashion magazine style editorial, shot on medium-format analog
film, pronounced grain, high saturation, cinematic lighting effect.
```

**Product photography:**
```
A high-resolution, studio-lit product photograph of a minimalist ceramic
coffee mug in matte black on polished concrete with three-point softbox
setup.
```

**Photorealistic portrait:**
```
A photorealistic close-up portrait of an elderly Japanese ceramicist with
deep, sun-etched wrinkles, inspecting a tea bowl in a sun-drenched
workshop, golden hour light streaming through rice-paper windows.
Captured with an 85mm portrait lens at f/1.8, shallow depth of field.
```

**Sticker (white-bg workaround for transparent need):**
```
A kawaii-style sticker of a happy red panda wearing a tiny bamboo hat,
bold outlines, simple cel-shading, vibrant palette. The background must
be pure white.
```

**Style transfer edit:**
```
Transform the provided photograph of a modern city street at night into
the artistic style of Vincent van Gogh's 'Starry Night', with swirling
brushstrokes and deep blues and bright yellows. Keep the original
composition and silhouettes.
```

**Precise inpainting:**
```
Using the provided image, change only the color of the sofa to deep navy
blue. Keep everything else in the image exactly the same — lighting,
framing, all other objects, the texture of the wall.
```

**Grounded infographic (use with `tools: [{google_search: {}}]` on Pro):**
```
Create a diagram of photosynthesis as if it were a recipe, showing
sunlight as an ingredient, chlorophyll as the chef, glucose and oxygen as
the dish. Scientifically accurate. Rendered in a warm illustrated cookbook
style, labeled text in clean sans-serif, 16:9.
```

For more design-specific examples filled in, see [../examples.md](../examples.md).