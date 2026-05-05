# Model selection — full decision tree

The one-line rule: **default to `gpt-image-2` at high quality; promote to Gemini Pro for hyper-realistic portraits and multi-reference brand work; drop to Gemini Flash only for throwaway exploration.**

This file is the long version, by asset type.

## The 30-second decision

```
Is the subject a hyper-realistic human face / cinematic portrait / lifestyle scene?
  YES → Gemini Pro at 4K.
  NO  ↓

Do you need 5+ reference images for character-lock / brand-consistent variants?
  YES → Gemini Pro (up to 14 refs with role-assignment).
  NO  ↓

Is this throwaway exploration where you'll discard half the outputs?
  YES → Gemini Flash 1K or 2K. Promote the keeper to gpt-image-2 high.
  NO  ↓

Everything else → gpt-image-2 at quality=high.
  └── Need transparent PNG? Generate on flat-white backdrop, then scripts/rembg.sh.
       See reference/transparent-backgrounds.md.
```

## Why gpt-image-2 is the new default

Released 2026-04-21. Took #1 across every Image Arena category by **+242 points** over Nano Banana 2 within 12 hours — the largest gap in Arena history.

- **Text rendering:** ~100% accuracy on English; renders CJK / Hindi / Bengali / Hebrew / Arabic well for the first time in an OpenAI model.
- **Prompt adherence:** a 15-element constraint list lands all 15. Rare to need iteration on structure.
- **Reasoning:** agentic — plans layout before drawing. You can describe intent ("left sidebar with primary nav, sized for a standard SaaS dashboard") instead of pixel-specifying.
- **Latency:** ~3s typical, ~10-30s at high quality with dense text.
- **Sizes:** any WxH up to 3840px per edge (edges divisible by 16, ratio ≤ 3:1).
- **Color accuracy:** true whites, true grays (prior OpenAI models had an amber tint).

**The one regression to know:** no native transparent backgrounds. Handled by the two-step `rembg` pipeline, which on empirical testing produces *cleaner* edges than native mode ever did. See [transparent-backgrounds.md](transparent-backgrounds.md).

## Comparison matrix

| Capability | Gemini Flash 3.1 | Gemini Pro 3 | OpenAI gpt-image-2 |
|---|---|---|---|
| **Max resolution** | 4K (4096px) | 4K (4096px) | 3840px on each edge |
| **Default resolution** | 1K | 1K | 1024² |
| **Aspect ratios** | 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, plus extreme (1:4, 4:1, 1:8, 8:1) | Same minus extreme | Any ratio ≤ 3:1, edges ÷16, total px 655K–8.3M |
| **Reference images** | Up to 14 | Up to 14 | Multiple (no hard cap; refs always processed at high fidelity) |
| **Native transparent bg** | ❌ post-process with rembg | ❌ post-process with rembg | ❌ post-process with rembg |
| **Text rendering — English** | Very good | Best-in-class for Latin (~94%) | **~100% accuracy** (industry-leading) |
| **Text rendering — Hebrew/Arabic/CJK/Hindi/Bengali** | Flaky | Better but unreliable for RTL | **Strong — first OpenAI model to handle these well** |
| **Multi-turn / chat editing** | ✅ native, with thought-signature passing | ✅ native | ❌ stateless; use `/edits` endpoint with previous image |
| **Identity preservation on edits** | Good | Up to 5 character refs | Excellent — every ref at high fidelity automatically |
| **Reasoning before drawing** | Optional, `thinkingLevel: minimal\|high` | On by default, not user-tunable | On by default (agentic; not user-tunable) |
| **Prompt adherence on 15-element briefs** | Inconsistent | Good | **Near-total** |
| **Hyper-realistic portrait quality** | Good | **Best-in-class** (skin, hair, film grain) | 4.5/5 — a notch behind Pro on faces |
| **Output format** | PNG only (base64) | PNG only (base64) | PNG / JPEG / WebP |
| **Cost / image (typical)** | $0.07 (1K) / $0.10 (2K) / $0.15 (4K) | $0.13 (1K-2K) / $0.24 (4K) | $0.006 low / $0.053 medium / $0.211 high (1024²) |
| **Latency** | ~2-4s | ~6-10s (with thinking) | ~3s typical, up to ~30s at high quality with dense text |
| **SynthID watermark** | Always on, invisible | Always on, invisible | Not applied |

## Decision by asset type

### Brand logo / mark / wordmark

| Stage | Model | Why |
|---|---|---|
| **Exploration** (10-30 variants) | Gemini Flash 1K | Cheap, fast, produces enough variation per call |
| **Final deliverable, any-language text** | **gpt-image-2 high, 1024² or 2048×2048** | Best text fidelity in any model; one-shot wins are common |
| **Final with Hebrew/Arabic text** | gpt-image-2 high | Handles RTL directly; fallback to text-free + composite only if it fails (see [hebrew-rtl.md](hebrew-rtl.md)) |
| **Transparent PNG needed** | gpt-image-2 high + `scripts/rembg.sh` | Include "isolated on flat #FFFFFF, no shadow" in the prompt; for pure line art use ImageMagick color-key (see [transparent-backgrounds.md](transparent-backgrounds.md)) |
| **Brand variant set (5+ refs, character lock)** | Gemini Pro | Pro's 14-ref role-assignment beats gpt-image-2 here |

### Icon set (multiple icons sharing a style)

| Stage | Model | Why |
|---|---|---|
| **Single icon, exploration** | Gemini Flash 1K, square | Cheap |
| **Coherent set of 4-12 icons** | Two strategies: (a) **gpt-image-2 high** as a single 3×4 grid — its prompt adherence now lands all the icons with consistent style in one call; (b) gpt-image-2 multi-turn via `/edits` with first icon as reference | Strategy (a) is the new default — gpt-image-2's reasoning keeps all items in the grid stylistically locked. |
| **Transparent icons** | gpt-image-2 high + `scripts/rembg.sh` per icon | Use ImageMagick color-key if the icons are monochrome line art |

Icons under 24px need post-vectorization to look crisp regardless of model — see the `brand-assets` skill.

### Mobile UI mockup

| Stage | Model | Why |
|---|---|---|
| **Wireframe / lo-fi** | Gemini Flash 1K, 9:16 | Cheap iteration |
| **Hi-fi UI with realistic content** | **gpt-image-2 high, 1024×1536 or 1024×1792** | Best-in-class small-text rendering keeps button labels and headlines legible |
| **Device-framed mockup (iPhone / Pixel)** | **gpt-image-2 high, portrait** | gpt-image-2 renders the device chrome cleanly and keeps UI text sharp |
| **Hebrew/RTL UI** | **gpt-image-2 high** | Renders Hebrew natively now; only fall back to text-free + composite for brand-typeface-critical work |

### Web dashboard / SaaS UI

| Stage | Model | Why |
|---|---|---|
| **Quick concept** | Gemini Flash 2K, 16:9 | Cheap |
| **Hi-fi production-grade** | **gpt-image-2 high, 2560×1440** (landscape) | Best text fidelity for dense tables, KPI cards, chart axis labels; reasoning handles multi-region layouts |
| **4K retina master** | gpt-image-2 high at 3840×2160 (within ratio/pixel caps) | Use only when the asset is going into hero/marketing |
| **Hebrew/RTL dashboard** | gpt-image-2 high | Same as above |

### Marketing hero image / banner

| Stage | Model | Why |
|---|---|---|
| **Concept exploration** | Gemini Flash 2K | Cheap; narrative-prompt strength suits hero composition |
| **Final hero without a prominent human face** | **gpt-image-2 high**, target aspect (16:9, 21:9) | Cleanest composition + any required text handled |
| **Final hero with prominent human face / cinematic portrait** | **Gemini Pro 4K** | Pro's skin/hair/film-grain quality is unmatched |
| **Final hero with headline text** | gpt-image-2 high at the target aspect | gpt-image-2 renders brand-grade headline typography directly in the image |
| **Hero with multiple people / character-lock across frames** | Gemini Pro 4K with up to 5 character refs | Pro's multi-ref character-lock beats gpt-image-2 |

### Product photography / hero shot

| Stage | Model | Why |
|---|---|---|
| **Lighting / angle exploration** | Gemini Flash 2K | Iterate camera angles cheaply |
| **Final hero shot (objects)** | **gpt-image-2 high** at target aspect | Best composition control and prompt adherence for object hero shots |
| **Final hero shot (human model wearing/holding product)** | **Gemini Pro 4K** | Photographic skin quality wins |
| **Catalog cutout (transparent)** | gpt-image-2 high + `scripts/rembg.sh` | Generate on pure white with zero shadow, then rembg |
| **Virtual try-on / identity-preserving edit with multiple refs** | Gemini Pro (up to 5 character refs) | Pro's multi-ref character-lock with explicit preserve clauses is the workflow of record |

### Portraits / headshots / lifestyle people

| Stage | Model | Why |
|---|---|---|
| **All cases (default)** | **Gemini Pro 4K** | Best-in-class for skin texture, fine hair, film grain, cinematic lighting |
| **Portrait with headline text overlaid in-image** | gpt-image-2 high | Only case where gpt-image-2 beats Pro for portraits — when the text is the hero of the image |

### Infographic / diagram

| Stage | Model | Why |
|---|---|---|
| **All cases** | **gpt-image-2 high** at 2048×1152 or larger | Reasoning handles the multi-region layout; best text rendering for dense labels. Promote to Gemini Pro with `--search` grounding only if the content requires live fact-checking |

### Illustration / editorial / stylized work

| Stage | Model | Why |
|---|---|---|
| **Flat illustration / vector-style** | gpt-image-2 high | Clean prompt-adherence for styled work |
| **Painterly / watercolor / textured illustration** | Gemini Pro at 4K | Pro has a stronger painterly range |
| **Anime / manga** | Gemini Pro with the style tags it prefers; Flash for exploration | Neither model is specialized for this — iterate |

## When gpt-image-2 wins outright

1. **Text in any language** — English, CJK, Hindi, Bengali, Hebrew, Arabic. First OpenAI model to handle non-Latin reliably.
2. **UI mockups with small labels** — dense dashboards, mobile screens, data tables.
3. **Dense multi-element briefs** where every constraint must land — a 15-item list lands all 15.
4. **Latency-sensitive iteration** — ~3s per call at the default sizes.
5. **Color accuracy** — true neutral whites, no amber tint.
6. **Logos with in-image wordmark typography at ≤30-40 chars per line.**

## When Gemini Pro wins outright

1. **Hyper-realistic human portraits** — skin, hair, eyes, film grain.
2. **Cinematic lifestyle photography** — people in scenes, editorial, fashion.
3. **Multi-turn iterative refinement** where you keep editing the same image with "change X, keep Y" via chat state.
4. **Character-lock across 5+ reference images** — Pro supports up to 14 references with role-assignment.
5. **Factual content requiring Google Search grounding** (via `--search` flag on `gemini-image.sh`).
6. **Painterly / textured illustration styles.**

## When Gemini Flash wins outright

1. **High-volume throwaway exploration** — generate 30 logo variants for $2.10 instead of $6.30 on gpt-image-2 high.
2. **Real-time UX** where ~3s is still too slow and ~1s matters.
3. **0.5K thumbnail / preview** generation (neither Pro nor gpt-image-2 outputs below 1K).
4. **Extreme aspect ratios** like 1:8 or 8:1 banners (gpt-image-2 is capped at 3:1).

## Tiebreakers

- **50/50 between gpt-image-2 and Gemini Pro for a hero with a person in it:** pick Pro. If the face isn't the hero, pick gpt-image-2.
- **50/50 between gpt-image-2 and Gemini Flash:** pick Flash for the first 3 calls, then promote to gpt-image-2 high for the keeper.
- **50/50 between gpt-image-2 high and Pro 4K for a non-portrait deliverable:** pick gpt-image-2 high — same quality on composition, faster, and materially stronger on text rendering.
