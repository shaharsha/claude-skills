# Pricing reference (April 2026)

Per-image cost matters because iteration discipline depends on it. Numbers below are list price; batch APIs and tier discounts may apply separately.

## Per-image cost — head-to-head

| Model | 0.5K | 1K / 1024² | 2K | 4K |
|---|---|---|---|---|
| Gemini Flash 3.1 | $0.045 | $0.067 | $0.101 | $0.151 |
| Gemini Pro 3 | n/a | $0.134 | $0.134 | $0.24 |
| OpenAI gpt-image-2 (low) | n/a | $0.006 | ~$0.021 | ~$0.078 |
| OpenAI gpt-image-2 (medium) | n/a | $0.053 | ~$0.19 | ~$0.73 |
| OpenAI gpt-image-2 (high) | n/a | $0.211 | ~$0.75 | ~$2.90 |

`gpt-image-2` pricing scales with pixel count (roughly linearly above 1024²). Constraint: each edge ≤ 3840px, multiples of 16, ratio ≤ 3:1, total pixels 655,360–8,294,400.

At the common fixed sizes, gpt-image-2 pricing:

| Quality | 1024×1024 | 1024×1536 (portrait) | 1536×1024 (landscape) |
|---|---|---|---|
| `low` | $0.006 | $0.005 | $0.005 |
| `medium` | $0.053 | $0.041 | $0.041 |
| `high` | $0.211 | $0.165 | $0.165 |

## Common scenarios — total cost calculator

### Logo project (exploration → final)

| Step | Calls | Model | Cost each | Subtotal |
|---|---|---|---|---|
| Initial exploration | 8 | Gemini Flash 1K | $0.067 | $0.54 |
| Refinement (3 directions × 3 variants) | 9 | Gemini Flash 1K | $0.067 | $0.60 |
| Final delivery with wordmark text | 3 | gpt-image-2 high 1024² | $0.211 | $0.63 |
| Transparent PNG post-process (local rembg) | 3 | rembg | $0 | $0 |
| **Total** | 20 | | | **$1.77** |

Why this routing: exploration on Flash is cheap; gpt-image-2 wins on text fidelity for the wordmark; rembg handles transparency locally.

### UI mockup project (mobile + desktop, 5 screens)

| Step | Calls | Model | Cost each | Subtotal |
|---|---|---|---|---|
| Wireframe sketches | 5 | Gemini Flash 1K | $0.067 | $0.34 |
| Hi-fi 5 mobile screens (1024×1536 portrait) | 5 | gpt-image-2 high | $0.165 | $0.83 |
| Hi-fi 1 desktop dashboard (2560×1440) | 1 | gpt-image-2 high | ~$0.40 | $0.40 |
| 1 device-framed marketing shot | 1 | gpt-image-2 high 1536×1024 | $0.165 | $0.17 |
| **Total** | 12 | | | **$1.74** |

gpt-image-2's small-text fidelity at 2K+ is the main reason to use it for hi-fi UI over Gemini Pro 4K — same quality on composition, better on button labels / table cells.

### Marketing hero set (3 hero images for landing page, no prominent human face)

| Step | Calls | Model | Cost each | Subtotal |
|---|---|---|---|---|
| Concept exploration | 6 | Gemini Flash 2K | $0.101 | $0.61 |
| Final hero × 3 variants (1536×1024) | 3 | gpt-image-2 high | $0.165 | $0.50 |
| **Total** | 9 | | | **$1.11** |

For a hero with a prominent human face, swap the final to Gemini Pro 4K at $0.24 × 3 = $0.72 (total $1.33).

### Icon set (24 icons, consistent style, transparent)

| Step | Calls | Model | Cost each | Subtotal |
|---|---|---|---|---|
| Style locking (3 candidate 3×2 grids) | 3 | Gemini Flash 2K | $0.101 | $0.30 |
| Final 24 icons as 4 grids of 6 each | 4 | gpt-image-2 high 1024² | $0.211 | $0.84 |
| Split grids into 24 individual PNGs (local, Pillow) | 24 | local crop | $0 | $0 |
| rembg (birefnet-general) per icon | 24 | rembg | $0 | $0 |
| **Total** | 7 API calls + local | | | **$1.14** |

Or: if the icons are pure monochrome line art, skip rembg and use ImageMagick color-key (`magick in.png -fuzz 5% -transparent white out.png`) — instantaneous, mathematically perfect alpha.

### Product photography set (10 product shots)

| Step | Calls | Model | Cost each | Subtotal |
|---|---|---|---|---|
| Lighting/angle exploration on 1 product | 5 | Gemini Flash 2K | $0.101 | $0.51 |
| Final 10 product shots with humans/models | 10 | Gemini Pro 4K | $0.24 | $2.40 |
| **Total** | 15 | | | **$2.91** |

If the products are objects only (no human model), swap the final to gpt-image-2 high 1536×1024 at $0.165: 10 × $0.165 = $1.65 (total $2.16).

### Transparent catalog cutout set (10 products)

| Step | Calls | Model | Cost each | Subtotal |
|---|---|---|---|---|
| Generate on pure-white backdrop | 10 | gpt-image-2 high 1024² | $0.211 | $2.11 |
| rembg (birefnet-general) per product | 10 | rembg | $0 | $0 |
| **Total** | 10 | | | **$2.11** |

### Portrait / founder headshot (photoreal)

| Step | Calls | Model | Cost each | Subtotal |
|---|---|---|---|---|
| Pose / framing exploration | 3 | Gemini Flash 2K | $0.101 | $0.30 |
| Final 4K portrait | 1 | Gemini Pro 4K | $0.24 | $0.24 |
| **Total** | 4 | | | **$0.54** |

Don't use gpt-image-2 for a hero portrait unless the image also has prominent in-image text.

## Batch API discounts

- **Gemini Batch API:** ≈ 50% off, 24-hour turnaround. Use for non-interactive bulk generation.
- **OpenAI Batch API:** 50% off, 24-hour turnaround.

For interactive design work (the main use of this skill), batch APIs are useless because you need to see results to iterate. They matter for one-shot bulk jobs.

## Cost discipline rules

1. **Default to Flash for first 3 calls** when exploring. Only promote to gpt-image-2 high once you've locked the prompt structure.
2. **Don't use gpt-image-2 high for exploration.** $0.21/call × 30 explorations = $6.30 vs $2 on Flash.
3. **Don't use 4K until the final.** For gpt-image-2 the jump from 1024² to 2K costs ~4×; from 2K to 4K another ~4×.
4. **Don't iterate >3 times on the same image.** Drift compounds, cost compounds. Rewrite the prompt from scratch.
5. **For transparent PNGs, prefer local post-process.** rembg + birefnet-general is free and produces excellent edges. Only reach for `remove.bg` API ($0.20/image) on premium hero assets with genuinely hard edges (wispy hair, glass, fur).
6. **For 24+ assets in the same style, prefer grid-based generation** on gpt-image-2 high — its prompt adherence and reasoning lock style consistency across grid cells better than independent calls.

## Sanity-check budgets per asset type

| Asset | Reasonable budget | Red flag if you exceed |
|---|---|---|
| Single logo, exploration to final | $1-3 | $5 |
| Icon set of 12-24 | $1-3 | $5 |
| 5-screen UI mockup (mobile) | $1-2 | $4 |
| 1-screen hi-fi dashboard | $0.50-1 | $2 |
| 3-image hero set for landing | $1-2 | $3 |
| 10-image product catalog (objects) | $2-4 | $6 |
| 10-image product catalog (people) | $3-5 | $8 |
| Portrait / founder headshot | $0.50-1 | $2 |

If you're approaching the red flag, pause and ask the user whether to keep going or pivot strategy.
