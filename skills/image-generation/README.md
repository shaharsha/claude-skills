# image-generation

Generate logos, icons, UI mockups, hero images, and product shots using **OpenAI GPT Image 2.5** (gpt-image-2.5-sunburst / gpt-image-2.5-flare) and **Google Gemini Nano Banana 2 / Pro / 2 Lite** (gemini-3.1-flash-image / gemini-3-pro-image / gemini-3.1-flash-lite-image).

Part of [shaharsha/claude-skills](../..). MIT.

---

As of 2026-10-02, **gpt-image-2.5-sunburst at quality `max`** is the default for anything that may ship. Released 2026-09-08, Sunburst and Flare took #1 and #2 on Artificial Analysis and Arena for text-to-image, image editing, text rendering and portraits. **gpt-image-2.5-flare at `medium`** (`--draft`, ~1¢) is the quick-draft tier: explore cheaply, then promote the chosen draft with a Sunburst `max` edit that keeps the look and adds full detail. `gpt-image-2` still works but is previous-generation. Gemini Pro is retained as the comparison for skin-critical close-ups and 14-reference identity lock; Gemini Flash for banners beyond 3:1; Gemini Lite as an alternative cheap draft tier. The Gemini `*-preview` IDs are shut down.

What changed from the gpt-image-2 version of this skill:

- **The quality ladder was re-cut.** On 2.5, `high` ≈ old gpt-image-2 `medium` and `max` ≈ old `high`. The script defaults to `max`; never use `auto`.
- **Transparent PNGs are native** (`--background transparent --output-format png`). rembg is now only for Gemini outputs or cutting existing images.
- **Draft, then promote.** Flare `--draft` for directions, then a Sunburst `max` edit with `--ref draft.png` and a promote prompt - not a re-roll, which composes a different picture.
- **Text in quotes only**, each string "exactly once", "no other text". Hebrew rendered correctly on Sunburst and Flare in a 2026-10-02 test.

The skill packages:

- **Model selection logic** — when to reach for Sunburst vs Flare vs Gemini Pro / Flash / Lite, and at which quality, by asset type and brief.
- **Provider-specific prompt-engineering references** — the two providers have *opposite* prompt structures (OpenAI wants labeled segments + negative phrasing; Gemini wants narrative paragraphs + positive phrasing only). Mixing them up degrades outputs badly.
- **Asset templates** — fill-in-the-blank prompt scaffolds for logos, icon sets, mobile UI, dashboards, hero images, product shots.
- **Transparent backgrounds** — native on GPT Image 2.5 (png/webp, real RGBA alpha). For Gemini outputs or existing images the skill bundles a `rembg` post-process, plus an ImageMagick color-key path for monochrome line art from any source.
- **Hebrew/RTL guidance** — GPT Image 2.5 handles Hebrew/Arabic directly for most cases (still check letter by letter, final forms especially); the two-stage composite workflow is a documented fallback.
- **Bundled scripts** — `scripts/openai-image.sh` (GPT Image 2.5 / 2 wrapper; prints latency, tokens and cost per call), `scripts/gemini-image.sh` (Gemini wrapper), `scripts/rembg.sh` (local background remover).
- **Recurring characters and story panels** - real people from photos turned into consistent cartoon/anime characters (face crops via `scripts/crop_faces.py`, anime face, costume card, promote), and multi-character scenes that keep every character (Sunburst `high`, names bound to their reference images, screens composited separately).
- **Iteration discipline** — a self-critique loop where Claude reads the saved image with its multimodal vision, scores against the brief, and decides ship / edit / rewrite before showing the user.

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install brand-and-visuals@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/image-generation" ~/.claude/skills/image-generation
```

Optional: the local background-removal tool, needed only for Gemini outputs or cutting existing images (one-time, ~200-400MB of model weights on first use):

```bash
pip install "rembg[cli]" onnxruntime
```

Optional for pure line-art logos (a fast color-key path instead of rembg):

```bash
brew install imagemagick
```

Then add your API keys to wherever you store them, and export them before invoking the scripts:

```bash
export OPENAI_IMAGE_API_KEY='sk-proj-...'
export GEMINI_IMAGE_API_KEY='...'
```

Quick start (from the skill directory):

```bash
# Final render - Sunburst at max is the default (~$0.17 at 1024x1536)
./scripts/openai-image.sh --size 1024x1536 --output out/poster.png --prompt "..."

# Quick drafts - Flare at medium (~1¢ each)
./scripts/openai-image.sh --draft --n 4 --size 1024x1536 --output out/poster-draft.png --prompt "..."

# Promote the chosen draft - a Sunburst max edit, same size as the draft
./scripts/openai-image.sh --ref out/poster-draft-3.png --size 1024x1536 --output out/poster.png \
  --prompt "Image 1 is an approved draft. Re-render it as the final at full detail: change only the rendering quality ... Preserve exactly ..."

# Native transparent PNG
./scripts/openai-image.sh --background transparent --output-format png --output out/logo.png --prompt "..."

# Gemini: banner beyond 3:1, or the cheapest draft tier
./scripts/gemini-image.sh --model flash --aspect 4:1 --size 2K --output out/banner.png --prompt "..."
./scripts/gemini-image.sh --model lite --output out/idea.jpg --prompt "..."
```

The skill's [SKILL.md](SKILL.md) references a per-user file at `~/.claude/projects/-Users-shaharshavit/memory/api-keys.md` for key storage — adjust that path to match your own setup.

## Entry point

Claude Code loads [SKILL.md](SKILL.md) when the skill is invoked. Start there to see the full workflow.

## Layout

```
SKILL.md                          ← agent entry point
README.md                         ← you are here
examples.md                       ← worked end-to-end examples

reference/
  model-selection.md              ← when to use which model, by asset type
  openai-gpt-image.md             ← OpenAI GPT Image 2.5 prompt grammar + API quirks
  gemini-image.md                 ← Gemini prompt grammar + API quirks
  transparent-backgrounds.md      ← native transparency + rembg / color-key fallbacks
  hebrew-rtl.md                   ← Hebrew/Arabic text-in-image workflow
  pricing.md                      ← per-image cost tables for budget tracking

templates/
  logo.md
  icon-set.md
  ui-mobile.md
  ui-dashboard.md
  hero-image.md
  product-shot.md

scripts/
  README.md
  openai-image.sh                 ← POST /v1/images/generations & /edits (GPT Image 2.5 / 2)
  gemini-image.sh                 ← POST /v1beta/models/<model>:generateContent
  rembg.sh                        ← local rembg wrapper (Gemini outputs / existing images)
```

## Gotchas

- **The two providers want opposite prompt structures.** OpenAI wants labeled segments and accepts negative phrasing; Gemini wants narrative paragraphs and **negative phrasing actively backfires** — rewrite "no people" as "empty street". Mixing them up degrades outputs badly, which is why the skill makes you read the provider reference before writing a prompt.
- **Gemini's aspect ratio goes in `imageConfig`, not the prompt text.** Asking for "16:9" in prose does nothing.
- **On 2.5, `high` is not high.** It buys about the output tokens of gpt-image-2 `medium`; `max` matches old `high`. The script defaults to `max`; never use `auto`, which lands on different budgets for identical calls.
- **Promote drafts with an edit, not a re-roll.** Re-running an approved draft's prompt at `max` composes a different picture; pass the draft as `--ref` to a Sunburst `max` edit at the same `--size`.
- **Transparent PNGs are native on 2.5** (`--background transparent`, png or webp). Apple rejects 1024×1024 App Store icons with transparency, so ship a flattened copy for iOS.
- **Read the generated image before showing the user.** Claude is multimodal and will actually see the pixels: mangled letterforms, wrong hex, broken geometry. Catch it first; don't ask "is this good?" about something you haven't looked at.
- **After 3 unsuccessful iterations on the same image, change strategy** — rewrite the base prompt or switch models. Tweaking a fourth time rarely converges.
- **Never pass whole photos as references for a character.** The edit endpoint restyles the photo (same pose, clothes, background, sometimes invented captions). Crop the face first.
- **Two or more characters in one panel need Sunburst `high`.** Flare drew only Image 1, outdoors, with subtitles.
- **Dimensions must be multiples of 16** for GPT Image. `1920×1080` is invalid because 1080 isn't; use `2560×1440`.
- **Gemini `*-preview` IDs are shut down.** Use `gemini-3.1-flash-image`, `gemini-3-pro-image`, `gemini-3.1-flash-lite-image` (aliases `flash`, `pro`, `lite`); the smallest Gemini size is spelled `512`.

## Notes

- The bash scripts assume `bash`, `curl`, `jq`, `base64`, and `file` are on PATH.
- `rembg` (optional) requires Python 3.10+ on PATH.
- Both API keys must be paid-tier.
- Generated outputs default to `./generated-images/` in the current working directory.
- Budget discipline: Sunburst `max` ≈ $0.21 at 1024² and ≈ $0.165 at 1024×1536, so 5 finals at 1024² ≈ $1.05; Sunburst `high` ≈ $0.041 and Flare `medium` ≈ $0.01 at 1024×1536. Gemini: Pro $0.134 (1K/2K) / $0.24 (4K), Flash $0.067 (1K), Lite $0.034. The OpenAI script prints the actual cost per call. Full cost tables in [reference/pricing.md](reference/pricing.md).

## Related skills

- [presentation-generator](../presentation-generator) — calls this skill's `openai-image.sh` once per slide.
- [brand-assets](../brand-assets) — takes a generated logo raster and turns it into production SVG/PNG/favicon assets.
- [brand-system](../brand-system) — authors the brand book whose palette and motif these prompts should honour.

## License

MIT — see [LICENSE](../../LICENSE).
