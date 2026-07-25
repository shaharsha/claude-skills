# image-generation

Generate logos, icons, UI mockups, hero images, and product shots using **OpenAI gpt-image-2** and **Google Gemini Nano Banana 2 / Pro** (gemini-3.1-flash-image-preview / gemini-3-pro-image-preview).

Part of [shaharsha/claude-skills](../..). MIT.

---

As of 2026-04-21, **gpt-image-2** is the default model for most jobs — it took #1 across every Image Arena category by +242 points over Nano Banana 2 within 12 hours of release (the largest gap in Arena history). Gemini Pro is retained for hyper-realistic portraiture and multi-reference brand work where Pro still wins. Gemini Flash is retained for cheap exploration.

The skill packages:

- **Model selection logic** — when to reach for Flash vs Pro vs gpt-image-2, by asset type and brief.
- **Provider-specific prompt-engineering references** — the two providers have *opposite* prompt structures (OpenAI wants labeled segments + negative phrasing; Gemini wants narrative paragraphs + positive phrasing only). Mixing them up degrades outputs badly.
- **Asset templates** — fill-in-the-blank prompt scaffolds for logos, icon sets, mobile UI, dashboards, hero images, product shots.
- **Transparent-background pipeline** — `gpt-image-2` does not support native transparent output. The skill bundles a two-step "generate on flat white + `rembg` post-process" recipe that produces cleaner edges than the old native mode on empirical testing.
- **Hebrew/RTL guidance** — gpt-image-2 handles Hebrew/Arabic directly for most cases; the two-stage composite workflow is now a documented fallback.
- **Bundled scripts** — `scripts/openai-image.sh` (gpt-image-2 wrapper), `scripts/gemini-image.sh` (Gemini wrapper), `scripts/rembg.sh` (local background remover).
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

Install the local background-removal tool (one-time, ~200-400MB of model weights on first use):

```bash
pip install "rembg[cli]" onnxruntime
```

Optional but recommended for pure line-art logos (uses a fast color-key path instead of rembg):

```bash
brew install imagemagick
```

Then add your API keys to wherever you store them, and export them before invoking the scripts:

```bash
export OPENAI_IMAGE_API_KEY='sk-proj-...'
export GEMINI_IMAGE_API_KEY='AQ.Ab8RN...'
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
  openai-gpt-image-2.md           ← OpenAI prompt grammar + API quirks
  gemini-image.md                 ← Gemini prompt grammar + API quirks
  transparent-backgrounds.md      ← two-step transparent PNG pipeline
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
  openai-image.sh                 ← POST /v1/images/generations & /edits (gpt-image-2)
  gemini-image.sh                 ← POST /v1beta/models/<model>:generateContent
  rembg.sh                        ← local rembg wrapper (birefnet-general default)
```

## Gotchas

- **The two providers want opposite prompt structures.** OpenAI wants labeled segments and accepts negative phrasing; Gemini wants narrative paragraphs and **negative phrasing actively backfires** — rewrite "no people" as "empty street". Mixing them up degrades outputs badly, which is why the skill makes you read the provider reference before writing a prompt.
- **Gemini's aspect ratio goes in `imageConfig`, not the prompt text.** Asking for "16:9" in prose does nothing.
- **gpt-image-2 has no native transparent output.** Generate on flat white and post-process with `scripts/rembg.sh` — empirically cleaner edges than the old native mode anyway.
- **Read the generated image before showing the user.** Claude is multimodal and will actually see the pixels: mangled letterforms, wrong hex, broken geometry. Catch it first; don't ask "is this good?" about something you haven't looked at.
- **After 3 unsuccessful iterations on the same image, change strategy** — rewrite the base prompt or switch models. Tweaking a fourth time rarely converges.
- **Dimensions must be multiples of 16** for gpt-image-2. `1920×1080` is invalid because 1080 isn't; use `2560×1440`.

## Notes

- The bash scripts assume `bash`, `curl`, `jq`, `base64`, and `file` are on PATH.
- `rembg` requires Python 3.10+ on PATH.
- Both API keys must be paid-tier.
- Generated outputs default to `./generated-images/` in the current working directory.
- Budget discipline: 5 gpt-image-2 high calls at 1024² ≈ $1.05. Full cost tables in [reference/pricing.md](reference/pricing.md).

## Related skills

- [presentation-generator](../presentation-generator) — calls this skill's `openai-image.sh` once per slide.
- [brand-assets](../brand-assets) — takes a generated logo raster and turns it into production SVG/PNG/favicon assets.
- [brand-system](../brand-system) — authors the brand book whose palette and motif these prompts should honour.

## License

MIT — see [LICENSE](../../LICENSE).
