# Model selection — full decision tree

Read this when the 30-second rule in SKILL.md doesn't settle it. Leaderboards as of late September 2026 (Artificial Analysis and arena.ai); costs measured 2026-10-02 unless noted.

## The 30-second decision

```
Exploring directions / testing a prompt?        → Flare medium (--draft); promote the pick with a Sunburst max edit
Close-up face where skin texture is the point?  → Sunburst max; if skin reads over-sharpened, compare Gemini Pro 4K
Wider or taller than 3:1 (banners 1:4…8:1)?     → gemini-3.1-flash-image
Needs real-world visual grounding (image search)? → gemini-3.1-flash-image with --search
Everything else                                  → Sunburst max
Transparent PNG                                  → native on Sunburst/Flare (--background transparent)
Editable SVG                                     → not these models (brand-assets skill, or Recraft V4.1 Vector)
```

## Why Sunburst is the default

| Board | Sunburst | Flare | gpt-image-2 | Best Gemini |
|---|---|---|---|---|
| AA text-to-image (Elo) | **1197** (#1) | 1191 (#2) | 1172 (#3) | Nano Banana 2 1125 (#6), Pro 1102 (#11) |
| AA image editing | **1182** (#1) | 1162 (#2) | 1122 (#5) | Nano Banana 2 1108 (#8), Pro 1099 (#13) |
| Arena text-to-image | **1424** (#1) | 1401 (#2) | 1383 (#3) | 3.1 Flash [web search] 1261 (#9), Pro 1246 (#14) |
| Arena image edit | **1520** (#1) | 1491 (#2) | 1461 (#3) | Pro 2k 1390 (#9) |
| Arena text rendering | **1467** (#1) | 1435 (#2) | 1425 (#3) | Nano Banana 2 1295 (#9) |
| Arena portraits | **1469** (#1) | 1452 (#2) | 1431 (#3) | Pro 2k 1259 (#14) |

Sunburst and Flare overlap within confidence intervals on several boards; Sunburst leads consistently on editing, which is why it's the tier for anything that gets refined. Quality over cost is this skill's default bias; at `max`, Sunburst costs about what gpt-image-2 `high` did.

## Comparison matrix

| | Sunburst | Flare | Gemini Pro | Gemini 3.1 Flash | Gemini Lite |
|---|---|---|---|---|---|
| Model ID | `gpt-image-2.5-sunburst` | `gpt-image-2.5-flare` | `gemini-3-pro-image` | `gemini-3.1-flash-image` | `gemini-3.1-flash-lite-image` |
| Role here | finals, edits | drafts | skin-critical portraits, many refs | extreme ratios, search grounding | cheapest Gemini drafts |
| Typical latency | ~35 s (`high`) – ~90 s (`max`) | ~15 s (`medium`) | ~10-30 s | ~9 s | ~4 s |
| Max size | 3840×2160 (≤ 3:1) | same | 4K, 10 standard ratios | 4K, ratios to 1:8 / 8:1 | 1K only |
| Transparent | ✅ native | ✅ native | ❌ (rembg) | ❌ (rembg) | ❌ (rembg) |
| References | ≤ 16 | ≤ 16 | ≤ 14 (5 high-fidelity; 6 objects / 5 characters / 3 style) | ≤ 14 (10 objects / 4 characters) | objects only; weak at multi-ref |
| Hebrew text | ✅ verified | ✅ verified | not on Google's language list | not on list | not on list |
| Prompt style | labeled sections, exclusions OK | same prompts as Sunburst | narrative, no negatives | narrative, no negatives | narrative |
| Cost | `max` ≈ $0.17-0.21 | `medium` ≈ $0.01 | $0.134 / $0.24 (4K) | $0.067 (1K) | $0.034 |

## Decision by asset type

### Brand logo / mark / wordmark
Explore 4-6 directions on Flare `--draft` at 1024×1024. Promote the pick with a Sunburst `max` edit. Transparent: `--background transparent`. Monochrome line art can also be keyed with ImageMagick for mathematically clean alpha. Hebrew wordmarks: Sunburst/Flare, never Gemini.

### Icon set (multiple icons sharing a style)
One grid call keeps the style locked: Sunburst `max`, 6-8 icons per grid (≤ 12), explicit grid spec ("strict 3×2 grid, each icon inside the central 70% of its cell"). Transparent natively. For a new icon in an existing set, edit with the set as references. App Store icons can't be transparent — ship a flattened iOS copy.

### Mobile UI / web dashboard
Sunburst `max` — UI is text-dense and text rendering is where it leads most. Describe the UI as shipped, not as a sketch. Portrait 1024×1536 for phones; 1536×1024 or 2048×1152 for dashboards.

### Marketing hero / banner
Sunburst `max` at the target aspect (≤ 3:1). Wider than 3:1 → gemini-3.1-flash-image, which goes to 8:1. If a headline is in the image, keep it short and quoted.

### Product photography
Sunburst `max`. Catalog cutouts: native transparent background. Multi-angle consistency: pass the first approved shot as a reference to the next.

### Portraits / lifestyle with people
Sunburst `max` first — it leads the portrait votes. Reviewers still call close-up 2.5 skin over-sharpened or "fractal" on zoom; when skin texture is the point, generate the same brief on Gemini Pro 4K and let the human pick.

### Infographic / diagram / slide
Sunburst `max`. Specify the grid, hierarchy and every label in quotes. Keep labels short; dense small text is still the weak spot. For data that must be exact, generate the frame and set the numbers in a real design tool.

### Illustration / stylized work
Sunburst `max`; some testers preferred gpt-image-2 for style transfer, so if a stylization brief disappoints, A/B against `--model gpt-image-2 --quality high`.

## Specialists outside these scripts

Worth knowing, not wired in:
- **Native SVG:** Recraft V4.1 Vector (`recraftv4_1_vector`, ~$0.08; Pro Vector ~$0.30) — the only major model that outputs real vector paths. Its text layout supports Latin/Greek/Cyrillic only, so not for Hebrew.
- **Cheap high-volume API models:** MAI-Image-2.6 (Microsoft Foundry, ~$0.039), Grok Imagine Image 2.0 ($0.04-0.08), Meta Muse Image (~$0.01, under 2K). Midjourney still has no official API.

## Tiebreakers

1. Text in the image, any language → Sunburst.
2. Will be edited further → Sunburst (leads editing by the widest margin).
3. Speed matters and it won't ship as-is → Flare.
4. Shape the 3:1 cap can't hold → Gemini 3.1 Flash.
5. Still unsure → generate on Sunburst and Flare at the same prompt (Flare is ~1¢) and let the human pick.
