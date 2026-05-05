---
name: image-generation
description: Generate logos, icons, UI mockups, hero images, product shots, and other design assets using OpenAI gpt-image-2 or Google Gemini (Nano Banana 2 Flash, Nano Banana Pro). Use whenever the user asks to create, design, generate, mock up, render, or illustrate a visual asset, or asks for image prompt engineering. Picks the right model for the job, writes a model-specific prompt following the official prompting rules of each provider, calls the API, and saves the PNG to disk.
allowed-tools: Read, Write, Bash, WebFetch
---

# Image Generation

Two model families, three jobs.

## Models covered

| Model ID | Family | Strengths | Default cost |
|---|---|---|---|
| `gpt-image-2` | OpenAI (ChatGPT Images 2.0) | **New default.** Best-in-class text in any language, near-total prompt adherence, agentic layout reasoning, neutral color accuracy, fast | $0.006 / $0.053 / $0.211 per 1024² at low/medium/high |
| `gemini-3.1-flash-image-preview` | Google (Nano Banana 2 Flash) | Cheap throwaway exploration; strongest 0.5K preview tier | ~$0.07 / image (1K) |
| `gemini-3-pro-image-preview` | Google (Nano Banana Pro) | Hyper-realistic portraiture & cinematic lifestyle; character-lock across up to 14 reference images; multi-turn chat editing | ~$0.13 / image (2K), ~$0.24 / image (4K) |

**Released 2026-04-21:** `gpt-image-2` took #1 across every Image Arena category by +242 points over Nano Banana 2 — the largest gap in Arena history. It dethrones `gpt-image-1.5` everywhere except native transparent backgrounds, which we now handle via `scripts/rembg.sh`.

## The three jobs of this skill

1. **Pick the model** for the asset and brief. See [reference/model-selection.md](reference/model-selection.md).
2. **Write the prompt** following the model's house rules. **The two providers have OPPOSITE prompt structures** — get this wrong and outputs degrade badly:
   - **OpenAI gpt-image-2** wants labeled segments / line breaks, accepts negative prompts, and rewards explicit constraints. Read [reference/openai-gpt-image-2.md](reference/openai-gpt-image-2.md).
   - **Gemini** wants narrative paragraphs, **negative phrasing actively backfires** (rewrite "no people" as "empty street"), aspect ratio goes in `imageConfig` not in the prompt text. Read [reference/gemini-image.md](reference/gemini-image.md).
3. **Run the API** via the bundled scripts. See [scripts/README.md](scripts/README.md).

## Default model selection — the 30-second rule

```
Hyper-realistic human face or cinematic portrait?
  YES → Gemini Pro 4K.
  NO  ↓

Need 5+ reference images for character-lock / brand-consistent variants?
  YES → Gemini Pro (up to 14 refs with role-assignment).
  NO  ↓

Throwaway exploration where you'll discard half the outputs?
  YES → Gemini Flash 1K or 2K. Promote the keeper to gpt-image-2 high.
  NO  ↓

Everything else → gpt-image-2 at quality=high.
  └── Transparent PNG needed? Generate on flat-white backdrop + scripts/rembg.sh.
       See reference/transparent-backgrounds.md.
```

Full decision tree per asset type: [reference/model-selection.md](reference/model-selection.md).

## Workflow per request

1. **Confirm scope.** Ask the user for: asset type, brand context, color/style direction, target aspect ratio + size, and where to save. If the user gave you all of this in the request, skip and proceed.
2. **Pick the model.** Use the rule above; explain your choice in one sentence.
3. **Read the model-specific reference** — `reference/openai-gpt-image-2.md` or `reference/gemini-image.md`. Do not skip this. The two models have opposite prompt structures and you will get it wrong from memory.
4. **If the final asset needs a transparent background, read [reference/transparent-backgrounds.md](reference/transparent-backgrounds.md).** The two-step generate + `rembg` pipeline replaces native transparent mode.
5. **Open the matching template** in `templates/` for the asset type. Fill in the placeholders.
6. **For Hebrew or RTL text in the image, read [reference/hebrew-rtl.md](reference/hebrew-rtl.md) FIRST.** Defaults changed with gpt-image-2 — most Hebrew work no longer needs the two-stage composite workflow.
7. **Show the prompt to the user before calling the API** unless they explicitly asked you to "just do it." One round of prompt review prevents most expensive re-generations.
8. **Run the script.** Save to `./generated-images/<descriptive-name>.png` in the cwd unless told otherwise. Create the directory if needed.
9. **Read the saved image with the Read tool — Claude is multimodal and will actually see the pixels.** This is the most important step in the loop. Critique the result against the brief: did the composition land? Is text legible? Are colors accurate? Did anything mangle (extra fingers, broken letterforms, wrong product geometry)? Spot the issues *before* the user has to.
10. **Show the user.** Use `open <path>` on macOS to surface the file, summarize what you see (good and bad), and propose either (a) ship it, (b) iterate with a specific change, or (c) regenerate from a revised prompt.

## Templates by asset type

| Asset | Template |
|---|---|
| Brand logo / mark / wordmark | [templates/logo.md](templates/logo.md) |
| Icon set (consistent style across icons) | [templates/icon-set.md](templates/icon-set.md) |
| Mobile app UI screen | [templates/ui-mobile.md](templates/ui-mobile.md) |
| Web dashboard / SaaS UI | [templates/ui-dashboard.md](templates/ui-dashboard.md) |
| Marketing hero image / banner | [templates/hero-image.md](templates/hero-image.md) |
| Product photography / hero shot | [templates/product-shot.md](templates/product-shot.md) |

For verbatim worked examples, see [examples.md](examples.md).

## API keys and dependencies

**API keys** live in `~/.claude/projects/-Users-shaharshavit/memory/api-keys.md`. Sections:

- **OpenAI (image generation)** → export as `OPENAI_IMAGE_API_KEY` before calling `scripts/openai-image.sh`
- **Google AI Studio (image generation)** → export as `GEMINI_IMAGE_API_KEY` before calling `scripts/gemini-image.sh`

These keys are *image-gen scoped*. Do not reuse them for chat completions or embeddings.

**Local tools** (for the transparent-bg pipeline):

- `rembg` CLI — install once: `pip install "rembg[cli]" onnxruntime`. First run of each model downloads weights (~200-400MB) to `~/.u2net/`.
- `ImageMagick` (optional but recommended for pure line art) — `brew install imagemagick`.

## Output convention

- Default save location: `./generated-images/<descriptive-name>.png` in the current working directory.
- Filename: descriptive kebab-case based on the brief (e.g., `logo-agentleh-monochrome-v1.png`, `hero-saas-landing-blue-v2.png`).
- Versioning: append `-v1`, `-v2`, etc. when iterating. Never overwrite a previous generation without asking.
- Transparent outputs: append `-transparent` after the version (e.g., `logo-agentleh-v1-transparent.png`).
- Use `open <path>` on macOS to show the user immediately after generation.

## Iteration patterns — autonomous "iterate until perfect" loop

The agent's job is to drive the image to "good enough to ship" *before* asking the user. Run this loop:

```
1. Generate (script call)
2. Read the saved file with the Read tool — Claude is multimodal and SEES the pixels
3. Self-critique against the brief. Score yourself honestly:
   - Did the composition land? (subject placement, framing, balance)
   - Is text legible and spelled correctly? (especially logos/UI labels)
   - Are colors right? (hex match, palette adherence)
   - Any defects? (mangled letterforms, extra fingers, broken geometry,
     wrong product details, drifted style)
   - Is the brief actually satisfied?
4. Decide:
   - SHIP → it meets the brief; show the user, summarize, suggest next steps
   - EDIT → specific localized fix needed; call the script again with --ref
            and a "change X, keep Y" prompt (Gemini) or /edits (OpenAI).
            Re-enter the loop.
   - REWRITE → fundamental prompt issue; rewrite the prompt from scratch
              (don't tweak). Re-enter the loop.
5. Stop conditions (one or both must be checked every iteration):
   - 5 iterations consumed → stop and consult the user before continuing
   - $3 spent on this single asset → stop and consult the user
   - The result is shippable → stop, present, await user verdict
```

**The user is the final judge — but Claude is the first judge.** Don't show the user a flawed result and ask "is this good?" Show them after you've already verified it meets the brief, OR show them with an explicit critique ("the wordmark is off, I'm about to fix it — here's the plan") so they know you saw what they'd see.

### Mechanics by model

- **gpt-image-2 iteration** uses `/v1/images/edits` via `scripts/openai-image.sh --ref <previous>.png`. Every reference is processed at high fidelity automatically — no flag needed. For multi-reference brand work, pass logo + color swatch + typography + moodboard simultaneously. Repeat the preserve-list on every iteration to prevent drift.
- **Gemini multi-turn editing** is the workhorse for refinement when you're already on Gemini. `scripts/gemini-image.sh --ref <previous-output> --prompt "change X, keep Y"`. Always include the explicit preservation clause: *"Keep everything else in the image exactly the same — composition, lighting, colors, all other elements."*
- **Drift discipline.** After 3 unsuccessful iterations on the *same* image, switch strategy — don't keep tweaking. Either rewrite the base prompt or change models (Flash → gpt-image-2 for quality lift; gpt-image-2 → Gemini Pro for photoreal portraiture).
- **Budget tracking.** Roughly track spend in your head (see [reference/pricing.md](reference/pricing.md)). 5 gpt-image-2 high calls at 1024² = $1.05. If you blow past the asset's reasonable budget, surface it to the user before continuing.

## Pricing

Per-image cost matters for iteration discipline. Quick reference:

- gpt-image-2 at quality=low (1024²): $0.006
- gpt-image-2 at quality=medium (1024²): $0.053
- gpt-image-2 at quality=high (1024²): $0.211
- gpt-image-2 at quality=high (portrait/landscape 1024×1536): $0.165
- Gemini Flash 1K: $0.067
- Gemini Pro 2K: $0.134
- Gemini Pro 4K: $0.24

Full table + worked scenarios: [reference/pricing.md](reference/pricing.md).

## Hebrew / RTL — not a weak spot anymore

gpt-image-2 renders Hebrew, Arabic, CJK, Hindi, and Bengali materially better than any prior model. The two-stage "generate text-free + composite text" workflow is no longer the default — try gpt-image-2 first.

Fall back to the composite workflow only when:
- Brand requires a specific licensed Hebrew typeface the model can't match.
- The text block is longer than ~30-40 characters per line.
- The first attempt shows mangled glyphs (rare, but iterate-or-fallback).

See [reference/hebrew-rtl.md](reference/hebrew-rtl.md) for both paths.

## When NOT to use this skill

- The user wants editable vector files (SVG with paths). These models output rasters; "vector-like" is aesthetic only. Use the `brand-assets` skill or Illustrator / Figma for SVG work.
- The user wants exact pixel-perfect dimensions outside the supported sizes (e.g., 1200×630 OG image). Generate at the closest supported aspect, then crop/resize in post.
- The user wants a real-world photo of a specific real person. Both providers refuse / produce inaccurate likenesses, and there are policy issues.
- The user is asking for general "AI art" without a design brief — point them to the consumer Gemini app or ChatGPT instead; this skill is tuned for design work.
