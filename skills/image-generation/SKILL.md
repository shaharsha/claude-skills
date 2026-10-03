---
name: image-generation
description: Generate logos, icons, UI mockups, hero images, product shots, and other design assets using OpenAI GPT Image 2.5 (Sunburst, Flare) or Google Gemini (Nano Banana 2, Nano Banana Pro, Nano Banana 2 Lite). Use whenever the user asks to create, design, generate, mock up, render, or illustrate a visual asset, needs a transparent PNG, or asks for image prompt engineering. Picks the right model and quality for the job, writes a model-specific prompt following the official prompting rules of each provider, calls the API, and saves the image to disk. Also use when turning photos of real people into consistent cartoon or anime characters, when drawing scenes with several recurring characters (only one appears, names get swapped, subtitles show up), or when a phone or tablet screen renders from behind.
allowed-tools: Read, Write, Bash, WebFetch
---

# Image Generation

Two model families, three jobs.

## Models covered

| Model ID | Family | Use for | Cost (1024×1536, measured 2026-10-02) |
|---|---|---|---|
| `gpt-image-2.5-sunburst` | OpenAI (Images 2.5, 2026-09-08) | **Default.** Anything that may ship. #1 on every major leaderboard (generation, editing, text rendering, portraits) | `max` ≈ $0.165, ~90 s · `high` ≈ $0.041, ~35 s |
| `gpt-image-2.5-flare` | OpenAI (Images 2.5) | **Quick drafts** — exploring directions, testing a prompt. Same prompts as Sunburst, ~2× faster | `medium` ≈ $0.01, ~15 s |
| `gemini-3-pro-image` | Google (Nano Banana Pro) | Close-up natural skin/hair when votes and reviewers disagree; up to 14 references | $0.134 (1K/2K) · $0.24 (4K) |
| `gemini-3.1-flash-image` | Google (Nano Banana 2) | Extreme aspect ratios (1:4…8:1), image-search grounding | $0.067 (1K) |
| `gemini-3.1-flash-lite-image` | Google (Nano Banana 2 Lite) | Cheapest Gemini exploration; 1K only, returns JPEG | $0.034 |

`gpt-image-2` still works (not deprecated) but is a step below both 2.5 models. The Gemini `*-preview` IDs and all Imagen models are **shut down** — the scripts refuse them.

## The three jobs of this skill

1. **Pick the model and the quality** for the asset. See [reference/model-selection.md](reference/model-selection.md).
2. **Write the prompt** following the model's house rules. **The two providers want opposite things:**
   - **OpenAI GPT Image 2.5** wants labeled sections (scene / subject / details / constraints), exact text in quotes, and accepts inline exclusions ("no extra text, no watermarks"). Read [reference/openai-gpt-image.md](reference/openai-gpt-image.md).
   - **Gemini** wants narrative paragraphs, **negative phrasing backfires** (rewrite "no people" as "empty street"), aspect ratio goes in `imageConfig`. Read [reference/gemini-image.md](reference/gemini-image.md).
3. **Run the API** via the bundled scripts. See [scripts/README.md](scripts/README.md).

## Quality on 2.5 — the trap

**The 2.5 quality ladder was re-cut.** At the same size, 2.5 `high` buys about the output tokens of gpt-image-2 `medium`; 2.5 `max` buys what gpt-image-2 `high` did (measured: Sunburst 1024×1536 `high` = 1,372 output tokens, `max` = 5,488). Copying "quality=high" from old habits silently ships a medium-detail image.

**Promote drafts with an edit, not a re-roll.** Every fresh generation composes a new image, so re-running an approved draft's prompt at `max` gives you a *different* picture. Instead, pass the chosen draft as a reference to a Sunburst `max` edit that changes only rendering quality and preserves everything else. Verified 2026-10-02: a Flare `medium` poster promoted this way kept its composition, people, poses, colors and Hebrew text, and gained texture and detail ($0.18, 85 s).

| Stage | Model + quality | Why |
|---|---|---|
| Explore directions, test a prompt | Flare `medium` (`--draft`) | ~1¢ and ~15 s, so 6 directions cost less than one final |
| Promote the chosen draft | Sunburst `max` edit with `--ref <draft>` and the promote prompt in `reference/openai-gpt-image.md` | Keeps the look the user picked, adds full detail |
| A final straight from a locked prompt | Sunburst `max` (the script default) | Full detail; ~90 s, ~$0.17 |
| Sunburst when time matters more than fine detail | Sunburst `high` | A quarter of the tokens, ~35 s |

Never use `auto` — it lands on different budgets for identical calls.

## Default model selection — the 30-second rule

```
Exploring directions / "a few quick options" / testing whether a prompt works?
  YES → Flare medium (--draft). Promote the user's pick with a Sunburst max edit (--ref <draft>).
  NO  ↓

Close-up photoreal human face where skin texture is the point?
  YES → Sunburst max first (it leads the portrait votes); if skin reads over-sharpened on zoom,
        compare with gemini-3-pro-image 4K and let the human pick.
  NO  ↓

Ultra-wide/tall banner beyond 3:1 (1:4, 4:1, 1:8, 8:1)?
  YES → gemini-3.1-flash-image (GPT Image caps at 3:1).
  NO  ↓

Everything else → Sunburst at quality=max.
  └── Transparent PNG? Native: --background transparent (png/webp). No rembg needed.
```

Full decision tree per asset type: [reference/model-selection.md](reference/model-selection.md).

## Workflow per request

1. **Confirm scope.** Asset type, brand context, color/style direction, target aspect ratio + size, where to save. If the request already says, proceed.
2. **Pick model and quality.** Use the rule above; explain the choice in one sentence.
3. **Read the model-specific reference** — `reference/openai-gpt-image.md` or `reference/gemini-image.md`. Don't write from memory: the two providers want opposite prompt structures, and the 2.5 guidance changed several gpt-image-2 habits.
4. **Transparent background?** On GPT Image 2.5 it's native. Read [reference/transparent-backgrounds.md](reference/transparent-backgrounds.md) only for Gemini outputs or for cutting an existing image.
5. **Open the matching template** in `templates/` and fill in the placeholders.
6. **Hebrew or RTL text in the image?** Read [reference/hebrew-rtl.md](reference/hebrew-rtl.md) first.
7. **Show the prompt to the user before calling the API** unless they said "just do it." One prompt review prevents most expensive regenerations.
8. **Run the script.** Save to `./generated-images/<descriptive-name>.png` in the cwd unless told otherwise. The OpenAI script prints latency, output tokens and cost per call — keep the running total.
9. **Read the saved image with the Read tool — Claude is multimodal and will actually see the pixels.** Critique against the brief: composition, text spelled exactly as quoted and appearing once, colors, defects (mangled letters, extra fingers, broken geometry), grain in smooth areas. Spot issues before the user has to.
10. **Show the user.** `open <path>`, summarize what you see (good and bad), and propose ship / iterate with a specific change / rewrite.

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

## Recurring characters and story panels

For comics, storyboards and animated episodes where the same people appear in many images:

- **Characters from photos.** Never pass whole photos as references: the edit endpoint restyles the photo (copies pose, clothes and background, adds caption text) instead of drawing the person. The working pipeline:
  1. Crop the faces first: `python3 <this-skill-dir>/scripts/crop_faces.py photos/ faces/ --sheet faces/_sheet.jpg`.
  2. Make an anime face from the crops.
  3. Edit that face into a half-body costume card, stating the body type.
  4. Get human approval, then promote.

  Prompts and the review loop: [reference/characters-from-photos.md](reference/characters-from-photos.md).
- **Scenes with 2+ characters.**
  - Draft with Sunburst `high`, not Flare: Flare drew only Image 1, outdoors, with subtitles.
  - Bind each name to its card on first mention: "Dana (the woman from Image 1)".
  - Forbid subtitles in any language.
  - Phone and tablet screens render from behind: generate the screen content as its own image and composite it.

  Recipe: [reference/multi-character-scenes.md](reference/multi-character-scenes.md).
- **Batch billing.** `credit_balance_exhausted` means the OpenAI account is out of credit, not a bad request. Stop, list which shots finished, and after the top-up rerun only the missing ones.

## API keys and dependencies

**API keys** come from environment variables, set from your own secret store in the shell that runs the script (every fresh shell needs them again):

- `OPENAI_IMAGE_API_KEY` for `scripts/openai-image.sh`
- `GEMINI_IMAGE_API_KEY` (or `GEMINI_API_KEY`) for `scripts/gemini-image.sh`; the same Google AI Studio key also works for generating-video-clips

These keys are image-gen scoped. Don't reuse them for chat or embeddings, and never print them — load them into a variable, don't echo.

**Local tools** (only for cutting Gemini outputs or existing images): `rembg` (`pip install "rembg[cli]" onnxruntime`), optionally ImageMagick.

## Output convention

- Default save location: `./generated-images/<descriptive-name>.png` in the current working directory.
- Filename: descriptive kebab-case (`logo-agentleh-monochrome-v1.png`); drafts get `-draft-N` (`logo-agentleh-draft-3.png`).
- Versioning: append `-v1`, `-v2`, … when iterating. Never overwrite a previous generation without asking.
- Transparent outputs: append `-transparent` after the version.
- `open <path>` on macOS to show the user right after generation.

## Iteration patterns — autonomous "iterate until perfect" loop

The agent's job is to drive the image to "good enough to ship" *before* asking the user:

```
1. Generate (script call)
2. Read the saved file with the Read tool — Claude SEES the pixels
3. Self-critique against the brief:
   - Composition landed? (placement, framing, balance, hierarchy, negative space)
   - Text spelled exactly as quoted, each string appearing once, legible?
   - Colors right? (hex match, palette adherence)
   - Defects? (mangled letterforms, extra fingers, broken geometry, grain in skies/backdrops)
   - Brief actually satisfied?
4. Decide:
   - SHIP    → meets the brief; show the user
   - EDIT    → one localized fix; edit with --ref <previous> and a prompt that says
               "change only X" and RESTATES every earlier fix and preserved detail
   - REWRITE → fundamental prompt issue; rewrite from scratch, don't tweak
5. Stop when: 5 iterations used, or $3 spent on this asset (sum the script's cost lines),
   or it's shippable.
```

**The user is the final judge — but Claude is the first judge.** Don't show a flawed result and ask "is this good?" Show it after you've verified it meets the brief, or with your critique attached ("the wordmark kerning is off; fixing it next").

### Mechanics by model

- **GPT Image 2.5 edits** go through `/v1/images/edits` via `scripts/openai-image.sh --ref <image>` (up to 16 references). Without a mask the whole canvas is regenerated each turn, so drift accumulates — **restate every earlier change and every preserved detail on each turn**, not just the new request. If a region must stay pixel-identical, composite the approved edit into the original instead of hoping the prompt holds it.
- **Gemini multi-turn editing:** `scripts/gemini-image.sh --ref <previous-output> --prompt "change X, keep Y"`, always ending with "Keep everything else in the image exactly the same — composition, lighting, colors, all other elements."
- **Drift discipline.** After 3 unsuccessful iterations on the same image, switch strategy: rewrite the base prompt, or change models.

## Pricing

GPT Image 2, 2.5 Flare and 2.5 Sunburst share token rates ($30/1M image output, $8/1M image input, $5/1M text input; Batch API halves them), but tokens per image differ by quality, size and model — so read the cost the script prints rather than assuming. Gemini is priced per image. Full table and worked scenarios: [reference/pricing.md](reference/pricing.md).

## Hebrew / RTL

Sunburst and Flare both rendered a Hebrew headline correctly in a 2026-10-02 test (right letters, right order, right direction, alongside English and a badge). Try direct rendering first; fall back to the composite workflow for long Hebrew lines or a required licensed typeface. Hebrew is **not** on Google's best-performance language list for Gemini image models — prefer GPT Image for Hebrew text. See [reference/hebrew-rtl.md](reference/hebrew-rtl.md).

## When NOT to use this skill

- The user wants editable vector files (SVG with paths). These models output rasters; use the `brand-assets` skill, or Recraft V4.1 Vector (`recraftv4_1_vector`, native SVG, not wired into these scripts).
- The user wants exact pixel dimensions outside the supported sizes (e.g. 1200×630). Generate at the closest supported aspect, then crop/resize.
- The user wants a real-world photo of a specific real person. Both providers refuse or produce inaccurate likenesses, and there are policy issues.
- The user wants general "AI art" without a design brief — point them to ChatGPT or the Gemini app; this skill is tuned for design work.
